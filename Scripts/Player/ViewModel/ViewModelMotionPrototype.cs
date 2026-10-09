using Godot;

// Neutral -> locomotion -> draw lock. This only generates a pose; the existing
// sway module remains the single writer of the shared bow-and-hands SwayRoot.
public partial class ViewModelMotionPrototype : Node
{
    [ExportGroup("Prototype A/B")]
    [Export] public bool UseNewMotion { get; set; } = true;
    [Export] public Key ToggleKey { get; set; } = Key.F8;
    [Export] public bool ShowStatus { get; set; } = true;

    [ExportGroup("Neutral Camera Space")]
    [Export] public Vector3 BaseOffset { get; set; } = new(0, 0, -0.12f);
    [Export] public Vector3 BaseRotationDegrees { get; set; } = Vector3.Zero;
    [Export] public Vector3 PrecisionOffset { get; set; } = new(0, 0, -0.12f);

    [ExportGroup("Locomotion")]
    [Export(PropertyHint.Range, "0,10,0.5,suffix:deg")] public float StrafeRollDegrees { get; set; } = 6;
    [Export(PropertyHint.Range, "0,0.15,0.005,suffix:m")] public float ForwardDrop { get; set; } = 0.085f;
    [Export(PropertyHint.Range, "5,30,1,suffix:/s")] public float BodyResponse { get; set; } = 18;

    [ExportGroup("Draw Lock")]
    [Export(PropertyHint.Range, "0.04,0.3,0.01,suffix:s")] public float DrawLockEnterSeconds { get; set; } = 0.12f;
    [Export(PropertyHint.Range, "0.04,0.4,0.01,suffix:s")] public float ReleaseDuration { get; set; } = 0.16f;
    [Export(PropertyHint.Range, "0,0.2,0.01")] public float PrecisionMotionScale { get; set; } = 0.025f;
    [Export] public Vector3 DrawOffset { get; set; } = new(0, 0.025f, 0);
    [Export] public Vector3 DrawRotationDegrees { get; set; } = Vector3.Zero;

    [ExportGroup("Secondary Camera Sway")]
    [Export(PropertyHint.Range, "0,0.02,0.001,suffix:m")] public float LookPosition { get; set; } = 0.002f;
    [Export(PropertyHint.Range, "0,2,0.05,suffix:deg")] public float LookRotationDegrees { get; set; } = 0.25f;
    [Export(PropertyHint.Range, "90,1080,10,suffix:deg/s")] public float FullLookRate { get; set; } = 360;
    [Export(PropertyHint.Range, "5,40,1,suffix:/s")] public float LookResponse { get; set; } = 22;

    [ExportGroup("Composition Limits")]
    [Export(PropertyHint.Range, "0.02,0.2,0.005,suffix:m")] public float MaxDynamicPosition { get; set; } = 0.13f;
    [Export(PropertyHint.Range, "1,12,0.5,suffix:deg")] public float MaxDynamicRotationDegrees { get; set; } = 7;

    // Serialized fields from the previous prototype are retained for scene
    // compatibility. The new grammar deliberately does not evaluate these layers.
    [ExportGroup("Previous Pass - Inactive Compatibility Fields")]
    [Export] public float VerticalTravelOffset { get; set; }
    [Export] public float AccelerationInertia { get; set; }
    [Export] public float SpeedSetback { get; set; }
    [Export] public Vector3 SlideOffset { get; set; }
    [Export] public float WallLeanDegrees { get; set; }
    [Export] public float LandingCompression { get; set; }
    [Export] public float LandingPitchDegrees { get; set; }
    [Export] public Vector3 ReleaseOffset { get; set; }
    [Export] public Vector3 ReleaseRotationDegrees { get; set; }

    public Vector3 DynamicPosition { get; private set; }
    public Vector3 DynamicRotationDegrees { get; private set; }
    public float DrawLockAmount { get; private set; }
    private PlayerController _player;
    private Node3D _holder;
    private ViewModelGait _gait;
    private CyberBowShotMotion _shot;
    private Label _status;
    private Vector2 _movePose, _lookRate;
    private float _lockProgress;
    private static bool? _sessionSelection;

    public override void _Ready()
    {
        UseNewMotion = _sessionSelection ?? UseNewMotion;
        if (!ShowStatus) return;
        var canvas = new CanvasLayer { Name = "MotionStatus", Layer = 15 };
        _status = new Label
        {
            AnchorLeft = 1, AnchorRight = 1,
            OffsetLeft = -330, OffsetRight = -24, OffsetTop = 24, OffsetBottom = 46,
            HorizontalAlignment = HorizontalAlignment.Right,
            MouseFilter = Control.MouseFilterEnum.Ignore
        };
        _status.AddThemeFontSizeOverride("font_size", 15);
        _status.AddThemeColorOverride("font_color", new Color(0.64f, 0.90f, 0.94f));
        canvas.AddChild(_status);
        AddChild(canvas);
    }

    public void Initialize(PlayerController player, Node3D swayRoot)
    {
        _player = player;
        _holder = swayRoot.GetNodeOrNull<Node3D>("BowViewModelHolder");
        _gait = GetNodeOrNull<ViewModelGait>("Gait");
        _gait?.Initialize(player);
        _shot = GetNodeOrNull<CyberBowShotMotion>("ShotMotion");
        _shot?.Initialize(player);
    }

    public override void _Input(InputEvent @event)
    {
        if (@event is not InputEventKey { Pressed: true, Echo: false } key
            || (key.Keycode != ToggleKey && key.PhysicalKeycode != ToggleKey)) return;
        UseNewMotion = !UseNewMotion;
        _sessionSelection = UseNewMotion;
        GD.Print($"VIEWMODEL_MOTION {(UseNewMotion ? "B_DRAW_LOCK" : "A_LEGACY_SWAY")}");
        GetViewport().SetInputAsHandled();
    }

    public override void _Process(double delta)
    {
        if (_status != null)
            _status.Text = UseNewMotion
                ? $"B: {(DrawLockAmount > 0.95f ? "DRAW LOCK" : "LOCOMOTION")}  |  {ToggleKey}"
                : $"A: LEGACY SWAY  |  {ToggleKey}";
    }

    public void ResetMotion()
    {
        _movePose = _lookRate = Vector2.Zero;
        _lockProgress = DrawLockAmount = 0;
        DynamicPosition = DynamicRotationDegrees = Vector3.Zero;
        _gait?.ResetGait();
        _shot?.ResetPose();
    }

    public void Evaluate(float dt, Vector2 mousePixels, out Vector3 position, out Vector3 rotation)
    {
        bool captured = Input.MouseMode == Input.MouseModeEnum.Captured;
        Vector2 move = captured ? new Vector2(Input.GetAxis("move_left", "move_right"),
            Mathf.Max(0, Input.GetAxis("move_back", "move_forward"))) : Vector2.Zero;
        _movePose = _movePose.Lerp(move, 1 - Mathf.Exp(-BodyResponse * dt));

        // Lock begins on active draw, not at full charge. ResetDraw marks both
        // release and cancellation immediately, before DrawAmount decays to zero.
        var visual = _player.BowVisualModule;
        _shot?.Evaluate(dt);
        bool drawing = visual.IsDrawing || visual.IsPrecisionAiming;
        float transition = drawing ? DrawLockEnterSeconds : ReleaseDuration;
        _lockProgress = Mathf.MoveToward(_lockProgress, drawing ? 1 : 0, dt / Mathf.Max(0.01f, transition));
        DrawLockAmount = _lockProgress * _lockProgress * (3 - 2 * _lockProgress);
        DrawLockAmount = Mathf.Max(DrawLockAmount, _shot?.Stabilization ?? 0);
        float freeAmount = Mathf.Lerp(1, PrecisionMotionScale, DrawLockAmount);

        Vector2 rate = mousePixels * (_player.LookModule.MouseSensitivity / dt);
        _lookRate = _lookRate.Lerp(rate, 1 - Mathf.Exp(-LookResponse * dt));
        Vector2 look = (_lookRate / Mathf.DegToRad(Mathf.Max(FullLookRate, 1))).LimitLength(1);
        Vector3 lookPosition = new(-look.X * LookPosition, look.Y * LookPosition, 0);
        Vector3 lookRotation = new(look.Y * LookRotationDegrees, look.X * LookRotationDegrees, 0);

        // W is translation only. Positive strafe banks right (negative camera Z
        // rotation); diagonal input simply combines that roll with the same drop.
        Vector3 locomotionPosition = new(0, -_movePose.Y * ForwardDrop, 0);
        Vector3 locomotionRotation = new(0, 0, -_movePose.X * StrafeRollDegrees);
        _gait?.Evaluate(dt, freeAmount);
        DynamicPosition = ((locomotionPosition + lookPosition) * freeAmount
            + DrawOffset * DrawLockAmount + (_gait?.PositionOffset ?? Vector3.Zero)).LimitLength(MaxDynamicPosition);
        DynamicRotationDegrees = ((locomotionRotation + lookRotation) * freeAmount
            + DrawRotationDegrees * DrawLockAmount + (_gait?.RotationOffsetDegrees ?? Vector3.Zero)).LimitLength(MaxDynamicRotationDegrees);
        float precision = Mathf.Clamp(Mathf.Abs(_holder?.RotationDegrees.Z ?? 0) / 65, 0, 1);
        position = BaseOffset.Lerp(PrecisionOffset, precision) + DynamicPosition;
        rotation = BaseRotationDegrees * (1 - precision) + DynamicRotationDegrees;
    }
}
