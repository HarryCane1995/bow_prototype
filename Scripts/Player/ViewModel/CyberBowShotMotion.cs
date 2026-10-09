using Godot;

// One presentation clock for bow, hands, string, arrow and locomotion priority.
// ShotVisualSequence is the only release trigger; cancelling draw is not a shot.
public partial class CyberBowShotMotion : Node
{
    [ExportGroup("Shot Presentation")]
    [Export] public bool Enabled { get; set; } = true;
    [Export] public Vector3 GripPivot { get; set; } = new(-0.005f, -0.326f, -0.847f);

    [ExportGroup("Draw Composition")]
    [Export(PropertyHint.Range, "0.1,0.4,0.01,suffix:s")] public float VisualDrawSeconds { get; set; } = 0.24f;
    [Export(PropertyHint.Range, "0.08,0.4,0.01,suffix:s")] public float CancelSeconds { get; set; } = 0.18f;
    [Export] public Vector3 DrawRotationDegrees { get; set; } = new(-2, -1.5f, 1);
    [Export] public Vector3 DrawGripOffset { get; set; } = new(0, 0.008f, -0.008f);
    [Export] public Vector3 ExtraDrawPull { get; set; } = new(0.012f, -0.008f, 0.04f);

    [ExportGroup("Release Torque")]
    [Export(PropertyHint.Range, "0.02,0.1,0.005,suffix:s")] public float StringSnapSeconds { get; set; } = 0.045f;
    [Export(PropertyHint.Range, "0.03,0.1,0.005,suffix:s")] public float TorquePeakSeconds { get; set; } = 0.055f;
    [Export(PropertyHint.Range, "0.12,0.35,0.01,suffix:s")] public float TorqueEndSeconds { get; set; } = 0.22f;
    [Export] public Vector3 TorqueDegrees { get; set; } = new(6, 9, -8);

    [ExportGroup("Support Follow Through")]
    [Export(PropertyHint.Range, "0.08,0.2,0.01,suffix:s")] public float FollowPeakSeconds { get; set; } = 0.12f;
    [Export(PropertyHint.Range, "0.2,0.5,0.01,suffix:s")] public float FollowEndSeconds { get; set; } = 0.34f;
    [Export] public Vector3 FollowGripOffset { get; set; } = new(0.022f, -0.008f, -0.038f);
    [Export] public Vector3 FollowRotationDegrees { get; set; } = new(-2, 3, -2);

    [ExportGroup("Drawing Hand And Next Arrow")]
    [Export(PropertyHint.Range, "0.04,0.16,0.01,suffix:s")] public float HandDelaySeconds { get; set; } = 0.09f;
    [Export(PropertyHint.Range, "0.12,0.28,0.01,suffix:s")] public float HandRetrieveSeconds { get; set; } = 0.19f;
    [Export(PropertyHint.Range, "0.18,0.35,0.005,suffix:s")] public float ArrowReturnSeconds { get; set; } = 0.23f;
    [Export(PropertyHint.Range, "0.25,0.5,0.01,suffix:s")] public float ArrowReadySeconds { get; set; } = 0.34f;
    [Export] public Vector3 HandContinuation { get; set; } = new(0.06f, -0.015f, 0.045f);
    [Export] public Vector3 RetrievalOffset { get; set; } = new(0.09f, -0.25f, 0.035f);

    [ExportGroup("Recovery And Interrupt")]
    [Export(PropertyHint.Range, "0.3,0.65,0.01,suffix:s")] public float RecoveryEndSeconds { get; set; } = 0.46f;
    [Export(PropertyHint.Range, "0.03,0.15,0.005,suffix:s")] public float NewDrawInterruptSeconds { get; set; } = 0.075f;

    public Transform3D BowPose { get; private set; } = Transform3D.Identity;
    public float HandDraw { get; private set; }
    public float StringDraw { get; private set; }
    public float StringStraighten { get; private set; }
    public Vector3 HandOffset { get; private set; }
    public Vector3 ArrowLoadOffset { get; private set; }
    public float FingerOpen { get; private set; }
    public bool ArrowVisible { get; private set; } = true;
    public float Stabilization { get; private set; }
    public bool IsRecovering => _shotWeight > 0;
    public float ShotAge => _age;

    private PlayerBowVisualModule _visual;
    private uint _lastShot;
    private float _draw, _shotDraw, _shotWeight, _strength = 1, _age = 10;
    private bool _wasDrawingIntent, _interrupting;

    public void Initialize(PlayerController player)
    {
        _visual = player.BowVisualModule;
        ResetPose();
    }

    public void ResetPose()
    {
        _lastShot = _visual?.ShotVisualSequence ?? 0;
        _draw = _shotDraw = _shotWeight = Stabilization = HandDraw = StringDraw = StringStraighten = FingerOpen = 0;
        _age = 10;
        BowPose = Transform3D.Identity;
        HandOffset = ArrowLoadOffset = Vector3.Zero;
        ArrowVisible = true;
        _wasDrawingIntent = _interrupting = false;
    }

    public void Evaluate(float dt)
    {
        if (_visual == null || !Enabled) { ResetPose(); return; }
        bool drawing = _visual.IsDrawing || _visual.IsPrecisionAiming;
        bool shot = _lastShot != _visual.ShotVisualSequence;
        if (shot)
        {
            _lastShot = _visual.ShotVisualSequence;
            _age = 0;
            _shotDraw = _draw;
            _strength = Mathf.Lerp(0.55f, 1, _draw);
            _shotWeight = 1;
            _interrupting = false;
        }
        else _age += dt;

        // Recovery never owns input. A legal new draw blends away the remaining
        // presentation immediately, including the hidden-arrow retrieval pose.
        if (!shot && drawing && !_wasDrawingIntent) _interrupting = true;
        _wasDrawingIntent = drawing;
        // Holding precision through a shot is the same intent, not a new draw.
        if (_interrupting && !shot)
            _shotWeight = Mathf.MoveToward(_shotWeight, 0, dt / Mathf.Max(NewDrawInterruptSeconds, 0.01f));
        if (_age >= RecoveryEndSeconds) _shotWeight = 0;
        _draw = Mathf.MoveToward(_draw, drawing ? 1 : 0,
            dt / Mathf.Max(drawing ? VisualDrawSeconds : CancelSeconds, 0.01f));

        float w = _shotWeight * (1 - Smooth(ArrowReadySeconds, RecoveryEndSeconds, _age));
        float snap = Smooth(0, StringSnapSeconds, _age);
        float retrieve = Smooth(HandDelaySeconds, HandRetrieveSeconds, _age);
        float handReturn = Smooth(HandRetrieveSeconds, ArrowReadySeconds, _age);
        float composition = Mathf.Lerp(_draw, _shotDraw * (1 - Smooth(HandDelaySeconds, FollowEndSeconds, _age)), w);
        float torque = Pulse(_age, TorquePeakSeconds, TorqueEndSeconds) * w * _strength;
        float follow = Pulse(_age, FollowPeakSeconds, FollowEndSeconds) * w * _strength;
        Vector3 degrees = DrawRotationDegrees * composition + TorqueDegrees * torque + FollowRotationDegrees * follow;
        Basis rotation = Basis.FromEuler(degrees * (Mathf.Pi / 180));
        Vector3 continuation = DrawGripOffset * composition + FollowGripOffset * follow;
        BowPose = new Transform3D(rotation, GripPivot + continuation - rotation * GripPivot);

        HandDraw = Mathf.Lerp(_draw, _shotDraw * (1 - retrieve), w);
        StringDraw = Mathf.Lerp(_draw, _shotDraw * (1 - snap), w);
        StringStraighten = snap * w;
        HandOffset = (HandContinuation * Smooth(0, HandDelaySeconds, _age) * (1 - retrieve)
            + RetrievalOffset * retrieve * (1 - handReturn)) * w;
        // The arrow is carried along the returning hand path, then seats at nock.
        ArrowLoadOffset = RetrievalOffset * (1 - handReturn) * w;
        ArrowVisible = w <= 0 || _age >= ArrowReturnSeconds || (_interrupting && w < 0.65f);
        FingerOpen = Smooth(0, StringSnapSeconds, _age) * (1 - handReturn) * w;
        Stabilization = w;
    }

    private static float Smooth(float start, float end, float value)
    {
        float t = Mathf.Clamp((value - start) / Mathf.Max(end - start, 0.001f), 0, 1);
        return t * t * (3 - 2 * t);
    }

    private static float Pulse(float age, float peak, float end)
        => age < peak ? Smooth(0, peak, age) : 1 - Smooth(peak, end, age);
}
