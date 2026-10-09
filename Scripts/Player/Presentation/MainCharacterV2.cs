using Godot;
using System.Collections.Generic;

// Visual observer only: PlayerController remains the sole movement/physics owner.
public partial class MainCharacterV2 : Node3D
{
    [ExportGroup("V2 Presentation")]
    [Export] public bool Enabled { get; set; } = true;
    [Export] public Key ToggleV2Key { get; set; } = Key.F9;
    [Export] public Key ExternalViewKey { get; set; } = Key.F10;
    [Export(PropertyHint.Range, "0,0.3,0.01,suffix:s")] public float BlendSeconds { get; set; } = 0.12f;
    [Export] public Vector3 DebugCameraOffset { get; set; } = new(2.2f, 1.6f, 3.2f);
    [Export] public Transform3D BowMeshInHand { get; set; } = Transform3D.Identity;

    public bool ExternalView { get; private set; }
    public string PoseName { get; private set; } = "BH01_IDLE";
    public Vector3 LockedSlideDirection { get; private set; }
    public Skeleton3D Skeleton { get; private set; }
    [Signal] public delegate void PresentationVisibilityChangedEventHandler();
    // Optional visual companion; the V2 path is unchanged when this is false.
    internal bool HybridPresentationActive { get; set; }
    public bool PresentationReady => _ready;
    public Node3D PresentationWeapon => _weapon;
    public void AppendPresentationReadout(string text) { if (_ready) _readout.Text += "\n" + text; }

    private PlayerController _player;
    private Node3D _model, _weapon;
    private Node _weaponParent;
    private Transform3D _weaponTransform;
    private BoneAttachment3D _grip;
    private MeshInstance3D _head;
    private AnimationPlayer _animations;
    private Camera3D _debugCamera;
    private CanvasLayer _legacyCanvas;
    private bool _legacyCanvasVisible, _arrowOwnedByHands, _ready, _sliding;
    private readonly Dictionary<Node, ProcessModeEnum> _legacyProcesses = new();
    private readonly Dictionary<VisualInstance3D, uint> _weaponLayers = new();
    private readonly Dictionary<CanvasLayer, bool> _legacyReadouts = new();
    private Label _readout;
    private PlayerRmbCombat _combat;

    public override void _Ready()
    {
        // Refresh calibrated camera before weapon modules read its gameplay aim ray.
        ProcessPriority = -10;
        ProcessPhysicsPriority = 40;
        TopLevel = true;
        // This entire visual branch is authored every render frame. Interpolating
        // its parent yaw again puts the skin behind the non-interpolated camera.
        PhysicsInterpolationMode = PhysicsInterpolationModeEnum.Off;
        CallDeferred(nameof(Initialize));
    }

    private void Initialize()
    {
        _player = GetParent() as PlayerController;
        _combat = _player?.GetNodeOrNull<PlayerRmbCombat>("PlayerRmbCombat");
        if (_player?.Camera == null) { GD.PushError("MainCharacterV2 needs an initialized Player parent."); return; }
        _model = GetNode<Node3D>("Body");
        Skeleton = _model.GetNode<Skeleton3D>("Skeleton3D");
        InitializeCameraCalibration();
        _head = Skeleton.GetNode<MeshInstance3D>("HEAD");
        _animations = _model.GetNode<AnimationPlayer>("AnimationPlayer");
        _animations.CallbackModeProcess = AnimationMixer.AnimationCallbackModeProcess.Manual;
        _debugCamera = GetNode<Camera3D>("ExternalCamera");
        _debugCamera.PhysicsInterpolationMode = PhysicsInterpolationModeEnum.Off;
        _legacyCanvas = _player.GetNode<CanvasLayer>("CanvasLayer_ViewModel");
        _legacyCanvasVisible = _legacyCanvas.Visible;
        foreach (Node node in _player.ViewModelSwayModule.FindChildren("*", "CanvasLayer", true, false))
            _legacyReadouts[(CanvasLayer)node] = ((CanvasLayer)node).Visible;
        _arrowOwnedByHands = _player.BowVisualModule.ArrowPresentationOwnedByHands;
        string root = "CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot";
        foreach (string path in new[] { root + "/ViewModelSwayRoot/FirstPersonHands", root + "/FirstPersonSlideLegs", "PlayerViewModelSwayModule" })
        {
            Node node = _player.GetNodeOrNull(path);
            if (node != null) _legacyProcesses[node] = node.ProcessMode;
        }
        _weapon = _player.GetNodeOrNull<Node3D>(root + "/ViewModelSwayRoot/BowViewModelHolder/CyberBowAxisCorrection");
        _grip = new BoneAttachment3D { Name = "V2_LeftHandGrip", BoneName = "hand.L" };
        Skeleton.AddChild(_grip);
        InitializeAimLayer();
        CanvasLayer hud = new() { Name = "V2DebugReadout", Layer = 60 };
        AddChild(hud);
        _readout = new Label { Position = new Vector2(18, 150), MouseFilter = Control.MouseFilterEnum.Ignore };
        _readout.AddThemeColorOverride("font_shadow_color", Colors.Black);
        _readout.AddThemeConstantOverride("shadow_offset_x", 2);
        _readout.AddThemeConstantOverride("shadow_offset_y", 2);
        hud.AddChild(_readout);
        _ready = true;
        bool initial = Enabled;
        Enabled = !initial;
        SetV2Enabled(initial);
    }

    public void SetV2Enabled(bool enabled)
    {
        if (!_ready) { Enabled = enabled; return; }
        if (Enabled == enabled) return;
        Enabled = enabled;
        _model.Visible = enabled;
        _legacyCanvas.Visible = enabled ? false : _legacyCanvasVisible;
        foreach (var entry in _legacyReadouts) entry.Key.Visible = enabled ? false : entry.Value;
        foreach (var entry in _legacyProcesses)
            entry.Key.ProcessMode = enabled ? ProcessModeEnum.Disabled : entry.Value;
        if (enabled)
        {
            _arrowOwnedByHands = _player.BowVisualModule.ArrowPresentationOwnedByHands;
            _player.BowVisualModule.ArrowPresentationOwnedByHands = false;
            _sliding = false;
            ObserveState();
            _animations.Play(PoseName, 0);
            AttachWeapon();
            SetCameraCalibrationEnabled(true);
            UpdatePresentation(0);
        }
        else
        {
            RestoreAuthoredBones();
            SetExternalView(false);
            RestoreWeapon();
            SetCameraCalibrationEnabled(false);
            _player.BowVisualModule.ArrowPresentationOwnedByHands = _arrowOwnedByHands;
        }
        _head.Visible = ExternalView;
        EmitSignal(SignalName.PresentationVisibilityChanged);
        GD.Print($"MAIN_CHARACTER_V2 {(Enabled ? "ON" : "OFF")}");
    }

    private void AttachWeapon()
    {
        if (_weapon == null) return;
        _weaponParent = _weapon.GetParent();
        _weaponTransform = _weapon.Transform;
        var mesh = _weapon.FindChild("Bow_Visual", true, false) as MeshInstance3D;
        if (mesh == null) return;
        Transform3D meshInRoot = _weapon.GlobalTransform.AffineInverse() * mesh.GlobalTransform;
        _weaponLayers.Clear();
        foreach (Node node in _weapon.FindChildren("*", "VisualInstance3D", true, false))
        {
            var visual = (VisualInstance3D)node;
            _weaponLayers[visual] = visual.Layers;
            visual.Layers = 1;
        }
        _weapon.Reparent(_grip, false);
        _weapon.Transform = BowMeshInHand * meshInRoot.AffineInverse();
    }

    private void RestoreWeapon()
    {
        if (_weapon == null || _weaponParent == null) return;
        _weapon.Reparent(_weaponParent, false);
        _weapon.Transform = _weaponTransform;
        foreach (var entry in _weaponLayers) entry.Key.Layers = entry.Value;
    }

    public void SetExternalView(bool external)
    {
        if (!_ready) return;
        ExternalView = Enabled && external;
        _head.Visible = ExternalView;
        if (ExternalView) _debugCamera.MakeCurrent();
        else _player.Camera.MakeCurrent();
        EmitSignal(SignalName.PresentationVisibilityChanged);
        GD.Print($"V2_VIEW {(ExternalView ? "EXTERNAL" : "FP")}");
    }

    public override void _Input(InputEvent @event)
    {
        if (!_ready || @event is not InputEventKey { Pressed: true, Echo: false } key) return;
        // Accept logical function keys too: injected input can have a different scan code.
        if (key.Keycode == ToggleV2Key || key.PhysicalKeycode == ToggleV2Key)
            SetV2Enabled(!Enabled);
        else if ((key.Keycode == ExternalViewKey || key.PhysicalKeycode == ExternalViewKey) && Enabled)
            SetExternalView(!ExternalView);
        else return;
        GetViewport().SetInputAsHandled();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_ready && Enabled)
        {
            ObserveState();
        }
    }

    private void ObserveState()
    {
        bool sliding = _player.CrouchSlideModule.IsSliding;
        if (sliding && !_sliding)
        {
            // Snapshot the authoritative trajectory, not camera yaw or a speed heuristic.
            LockedSlideDirection = _player.CrouchSlideModule.SlideDirection;
            LockedSlideDirection = new Vector3(LockedSlideDirection.X, 0, LockedSlideDirection.Z).Normalized();
        }
        if (!sliding) LockedSlideDirection = Vector3.Zero;
        _sliding = sliding;
        UpdateAnimationSelection();
    }

    private void UpdateAnimationSelection()
    {
        StringName locomotion = SelectLocomotionAnimation();
        string pose = _animations.HasAnimation(locomotion) ? locomotion.ToString() : IdleAnimation.ToString();
        StringName requested = _combat?.RequestedAnimation;
        // Keep the authored slide/lower body until an upper-body combat layer is
        // authored. Unexported slots fall back without changing state timing.
        if (!_sliding && requested != null && !requested.IsEmpty && _animations.HasAnimation(requested))
            pose = requested.ToString();
        // Playback scaling is presentation-only; all other clips retain their timing.
        _animations.SpeedScale = pose == RunAnimation.ToString() ? Mathf.Max(0.1f, RunPlaybackSpeedScale) : 1.0f;
        if (PoseName != pose)
        {
            PoseName = pose;
            _animations.Play(PoseName, BlendSeconds);
            GD.Print($"V2_POSE {PoseName} real_slide={_sliding}");
        }
    }

    private void UpdateBodyTransform()
    {
        float yaw = _sliding && !LockedSlideDirection.IsZeroApprox()
            ? Mathf.Atan2(-LockedSlideDirection.X, -LockedSlideDirection.Z)
            : _player.GlobalRotation.Y;
        // Look/effects have finished before this single render-frame sample.
        // Only translation uses physics interpolation; yaw matches camera look.
        Vector3 origin = _player.GetGlobalTransformInterpolated().Origin;
        GlobalTransform = new Transform3D(new Basis(Vector3.Up, yaw), origin);
    }

    public override void _Process(double delta)
    {
        if (!_ready) return;
        _readout.Text = $"MAIN CHARACTER V2: {(Enabled ? "ON" : "OFF")}  |  {(ExternalView ? "3POV DEBUG" : "1POV")}  |  {PoseName}\n{ToggleV2Key}: V2 / fallback    {ExternalViewKey}: 1POV / 3POV    Ctrl: slide";
        if (_combat?.ShowDebugReadout == true) _readout.Text += "\n" + _combat.DebugReadout;
        if (Enabled)
        {
            UpdateAnimationSelection();
            UpdatePresentation(delta);
            Vector3 target = _player.GlobalPosition + Vector3.Up * 0.65f;
            Basis orbit = new Basis(Vector3.Up, _player.GlobalRotation.Y)
                * new Basis(Vector3.Right, Mathf.Clamp(_player.CameraPivot.Rotation.X, -1.0f, 1.0f));
            _debugCamera.GlobalPosition = target + orbit * DebugCameraOffset;
            _debugCamera.LookAt(target, Vector3.Up);
        }
    }

    private void UpdatePresentation(double delta)
    {
        UpdateBodyTransform();
        RestoreAuthoredBones();
        _animations.Advance(delta);
        CacheAuthoredCamera();
        UpdateAimPresentation();
        ApplyCameraCalibration();
    }
}
