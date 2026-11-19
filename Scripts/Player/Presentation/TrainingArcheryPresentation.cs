using Godot;
using System;

// Drives only the first-person art. Shot acceptance, charge, camera and movement
// continue to belong to the modules on the real player.
public partial class TrainingArcheryPresentation : CanvasLayer
{
    [ExportGroup("Aim")]
    [Export(PropertyHint.Range, "2,300,1,suffix:m")] public float SightDistance { get; set; } = 160;
    [Export(PropertyHint.Layers3DPhysics)] public uint SightMask { get; set; } = 5;

    [ExportGroup("Movement feedback")]
    [Export(PropertyHint.Range, "0,1.5,0.05")] public float PostureWeight { get; set; } = 1;
    [Export(PropertyHint.Range, "2,40,0.5")] public float PostureFollowSpeed { get; set; } = 14;

    private static readonly StringName Present = "present", Align = "align_arrow", WorldArrow = "arrow_in_world";
    private static readonly StringName TurnSway = "turn_sway", SecondaryMotionGain = "secondary_motion_gain";
    private PlayerController _player;
    private PlayerBowShootModule _shoot;
    private MainCharacterV4 _host;
    private PlayerRmbCombat _combat;
    private Node3D _model;
    private SubViewport _viewport;
    private Camera3D _viewCamera;
    private PhysicsRayQueryParameters3D _sight;
    private Func<Transform3D?> _previousFrame;
    private bool _firstPersonEnabled = true, _grounded, _powerDraw;
    private float _sightDepth, _verticalImpulse;
    private Vector3 _posturePosition, _postureAngles;

    public override void _Ready()
    {
        _viewport = GetNode<SubViewport>("ViewContainer/ViewViewport");
        _viewCamera = _viewport.GetNode<Camera3D>("Studio/ViewCamera");
        _model = _viewport.GetNode<Node3D>("Studio/ViewModel");
        ProcessPriority = 30; // Gameplay camera and V4 have both published this frame.
        ProcessPhysicsPriority = 60;
        TryAttach();
        UpdateVisibility();
    }

    public void Bind(PlayerController player)
    {
        if (_player != player)
        {
            Detach();
            _player = player;
        }
        TryAttach();
    }

    public void SetFirstPersonVisible(bool enabled)
    {
        _firstPersonEnabled = enabled;
        UpdateVisibility();
    }

    public Transform3D GetArrowFrame() => _model.Call(WorldArrow, _viewCamera, _player.Camera).AsTransform3D();

    private Transform3D? FrameForShot() => Visible && _shoot is { IsEquipped: true } ? GetArrowFrame() : null;

    private void TryAttach()
    {
        if (_model == null || _shoot != null || _player?.BowShootModule == null) return;
        _shoot = _player.BowShootModule;
        _host = _player.GetNode<MainCharacterV4>("MainCharacterV4");
        _combat = _player.GetNode<PlayerRmbCombat>("PlayerRmbCombat");
        _shoot.DrawBegan += OnDraw;
        _shoot.DrawCanceled += OnCancel;
        _shoot.ShotReleased += OnShot;
        _shoot.EquippedChanged += OnEquipped;
        _previousFrame = _shoot.PresentedArrowFrame;
        _shoot.PresentedArrowFrame = FrameForShot;
        _combat.PowerShotStarted += OnPowerDraw;
        _combat.PowerShotReleased += OnPowerRelease;
        _sight = new PhysicsRayQueryParameters3D
        {
            Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() },
            CollideWithAreas = true,
        };
        _sightDepth = SightDistance;
        _grounded = _player.IsGrounded;
        if (!_shoot.IsEquipped) OnEquipped(false);
        else if (_shoot.IsDrawing) OnDraw();
        UpdateVisibility();
    }

    public override void _ExitTree() => Detach();

    private void Detach()
    {
        if (IsInstanceValid(_shoot))
        {
            _shoot.DrawBegan -= OnDraw;
            _shoot.DrawCanceled -= OnCancel;
            _shoot.ShotReleased -= OnShot;
            _shoot.EquippedChanged -= OnEquipped;
            if (_shoot.PresentedArrowFrame == FrameForShot) _shoot.PresentedArrowFrame = _previousFrame;
        }
        if (IsInstanceValid(_combat))
        {
            _combat.PowerShotStarted -= OnPowerDraw;
            _combat.PowerShotReleased -= OnPowerRelease;
        }
        _shoot = null;
        _combat = null;
        _player = null;
        _powerDraw = false;
    }

    private void OnDraw()
    {
        _powerDraw = false;
        _model.Call("begin_draw");
    }

    private void OnCancel()
    {
        _powerDraw = false;
        _model.Call("cancel_draw");
    }

    private void OnShot(float amount, bool precision)
    {
        _powerDraw = false;
        _model.Call("release_draw", precision ? 1.0f : amount);
    }

    private void OnEquipped(bool equipped)
    {
        _powerDraw = false;
        _model.Call("set_equipped", equipped);
        UpdateVisibility();
    }

    private void OnPowerDraw()
    {
        if (_shoot.IsDrawing || !_shoot.IsEquipped) return;
        _powerDraw = true;
        _model.Call("begin_draw");
    }

    private void OnPowerRelease(Vector3 origin, Vector3 direction, float amount, bool full)
    {
        if (!_powerDraw) return;
        _powerDraw = false;
        _model.Call("release_draw", amount);
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_shoot == null) return;
        bool ground = _player.IsGrounded;
        if (_player.JumpModule.JumpConsumedThisTick || (_grounded && !ground))
        {
            _model.Call("on_jump");
            _verticalImpulse = -0.018f;
        }
        else if (!_grounded && ground)
        {
            _model.Call("on_land");
            _verticalImpulse = -0.025f;
        }
        _grounded = ground;
        if (!_firstPersonEnabled) return;
        Transform3D eye = _player.Camera.GetCameraTransform();
        _sight.From = eye.Origin;
        _sight.To = eye.Origin - eye.Basis.Z * SightDistance;
        _sight.CollisionMask = SightMask;
        var hit = _player.GetWorld3D().DirectSpaceState.IntersectRay(_sight);
        _sightDepth = hit.Count == 0 ? SightDistance : eye.Origin.DistanceTo(hit["position"].AsVector3());
    }

    public override void _Process(double delta)
    {
        if (_shoot == null)
        {
            TryAttach(); // Bind may run before the parent initializes its modules.
            if (_shoot == null) return;
        }
        if (_powerDraw && _combat.State == PlayerRmbCombat.CombatState.Idle) OnCancel();
        float dt = (float)delta;
        float draw = _powerDraw ? _combat.ChargeAmount : _shoot.DrawAmount;
        bool precision = _shoot.IsEquipped && _shoot.IsPrecisionReady;
        var locomotion = _host.Locomotion;
        bool wall = locomotion is PresentationState.WallrunLeft or PresentationState.WallrunRight;
        float speed = locomotion is PresentationState.Idle or PresentationState.Slide ? 0
            : new Vector2(_player.Velocity.X, _player.Velocity.Z).Length();
        _model.Call(TurnSway, _player.LookModule.ConsumeLookDelta());
        _model.Call(Present, dt, draw, speed, precision, wall);
        ApplyPosture(locomotion, _combat.State, dt, precision ? 1 : draw);
        UpdateVisibility();
        if (Visible) _model.Call(Align, _viewCamera, _player.Camera, _sightDepth, dt);
    }

    private void ApplyPosture(PresentationState locomotion, PlayerRmbCombat.CombatState combat, float dt, float aim)
    {
        // The authored clip supplies the hands. Move the whole assembly so the
        // grip, nock, string and arrow remain together through each motor state.
        (Vector3 shift, Vector3 tilt) = locomotion switch
        {
            PresentationState.Slide => (new(-.020f, .034f, -.057f), new(-1.5f, -3, -6)),
            PresentationState.Crouch => (new(0, -.018f, .010f), new(-2, 0, -3)),
            PresentationState.WallrunLeft => (new(.034f, -.008f, .012f), new(-2, 2, -10)),
            PresentationState.WallrunRight => (new(-.034f, -.008f, .012f), new(-2, -2, 10)),
            PresentationState.GrapplePull => (new(-.014f, .028f, -.050f), new(-1, -2, -4.5f)),
            PresentationState.GrappleLaunch => (new(.010f, .020f, -.045f), new(-2, 0, 3)),
            PresentationState.GrappleFlight => (new(0, .018f, -.018f), new(3, 0, 3)),
            _ => (Vector3.Zero, Vector3.Zero)
        };
        switch (combat)
        {
            case PlayerRmbCombat.CombatState.RmbAnticipation:
                shift += new Vector3(-.018f, .023f, .010f); tilt.Z += 10; break;
            case PlayerRmbCombat.CombatState.Melee:
                shift += new Vector3(.060f, .036f, -.095f); tilt += new Vector3(8, -14, -23); break;
            case PlayerRmbCombat.CombatState.ParrySuccess:
                shift += new Vector3(-.038f, .067f, -.045f); tilt += new Vector3(6, 9, 25); break;
        }
        float weight = PostureWeight * Mathf.Lerp(1.0f, 0.24f, aim);
        float follow = 1.0f - Mathf.Exp(-PostureFollowSpeed * dt);
        _posturePosition = _posturePosition.Lerp(shift * weight, follow);
        _postureAngles = _postureAngles.Lerp(tilt * weight, follow);
        _verticalImpulse *= Mathf.Exp(-11.0f * dt);
        // present() restores the authored base and turn sway on every frame.
        if (!_model.Visible) return;
        float impact = _verticalImpulse * weight * _model.Get(SecondaryMotionGain).AsSingle();
        _model.Position += _posturePosition + Vector3.Up * impact;
        _model.RotationDegrees += _postureAngles;
    }

    private void UpdateVisibility()
    {
        bool show = _firstPersonEnabled && _shoot != null && _model is { Visible: true };
        Visible = show;
        if (_viewport != null)
            _viewport.RenderTargetUpdateMode = show ? SubViewport.UpdateMode.Always : SubViewport.UpdateMode.Disabled;
    }
}
