using Godot;

// Visual pose generator only. The existing sway module writes the shared
// bow-and-hands root; this node never writes player velocity or camera transforms.
public partial class ViewModelGait : Node
{
    [ExportGroup("Ground Gait")]
    [Export] public bool Enabled { get; set; } = true;
    [Export(PropertyHint.Range, "0.5,12,0.1,suffix:m/step")] public float StepDistance { get; set; } = 5.5f;
    [Export(PropertyHint.Range, "1,6,0.1,suffix:steps/s")] public float MaxStepCadence { get; set; } = 4.2f;
    [Export(PropertyHint.Range, "0,2,0.05,suffix:m/s")] public float MinimumSpeed { get; set; } = 0.2f;
    [Export(PropertyHint.Range, "1,40,0.5,suffix:m/s")] public float FullAmplitudeSpeed { get; set; } = 18;

    [ExportGroup("Gait Pose")]
    [Export(PropertyHint.Range, "0,0.04,0.001,suffix:m")] public float VerticalAmount { get; set; } = 0.012f;
    [Export(PropertyHint.Range, "0,0.02,0.001,suffix:m")] public float LateralAmount { get; set; } = 0.006f;
    [Export(PropertyHint.Range, "0,1,0.05,suffix:deg")] public float RollDegrees { get; set; } = 0.5f;

    [ExportGroup("Gait Blending")]
    [Export(PropertyHint.Range, "1,40,1,suffix:/s")] public float BlendInSpeed { get; set; } = 12;
    [Export(PropertyHint.Range, "1,60,1,suffix:/s")] public float BlendOutSpeed { get; set; } = 24;
    [Export(PropertyHint.Range, "0.08,0.6,0.01,suffix:s")] public float RecoverySeconds { get; set; } = 0.24f;

    // Unwrapped steps: integer crossings alternate feet; two steps form a cycle.
    // Keep advancing under draw suppression so future footstep consumers remain
    // independent of the aiming pose. No audio/events are emitted in this pass.
    public double StepProgress { get; private set; }
    public float PhaseRadians => (float)(StepProgress % 2.0) * Mathf.Pi;
    public bool IsStepping { get; private set; }
    public float Cadence { get; private set; }
    public float Amplitude { get; private set; }
    public Vector3 PositionOffset { get; private set; }
    public Vector3 RotationOffsetDegrees { get; private set; }

    private PlayerController _player;
    private float _groundWeight;
    private float _locomotionWeight = 1;

    public void Initialize(PlayerController player) => _player = player;

    public void ResetGait()
    {
        StepProgress = 0;
        IsStepping = false;
        Cadence = Amplitude = _groundWeight = 0;
        _locomotionWeight = 1;
        PositionOffset = RotationOffsetDegrees = Vector3.Zero;
    }

    public void Evaluate(float dt, float locomotionWeight)
    {
        var grapple = _player?.SlingshotGrappleModule;
        bool groundLocomotion = Enabled && _player != null
            && Input.MouseMode == Input.MouseModeEnum.Captured
            && _player.IsOnFloor() && _player.Velocity.Y <= 0.1f
            && _player.CrouchSlideModule?.IsSliding != true
            && _player.WallRunModule?.IsWallRunning != true
            && grapple?.IsSlingshotActive != true && grapple?.IsNormalMovementBlocked != true;

        // Integrate the resolved movement velocity, not key strength or wall time.
        // At parkour speeds stride length grows to bound cadence as well as pose.
        float speed = _player == null ? 0 : new Vector2(_player.Velocity.X, _player.Velocity.Z).Length();
        IsStepping = groundLocomotion && speed > MinimumSpeed;
        Cadence = IsStepping ? Mathf.Min(speed / Mathf.Max(StepDistance, 0.1f), MaxStepCadence) : 0;
        StepProgress += Cadence * dt;

        float target = IsStepping
            ? Mathf.Sqrt(Mathf.Clamp((speed - MinimumSpeed) / Mathf.Max(FullAmplitudeSpeed - MinimumSpeed, 0.1f), 0, 1)) : 0;
        float response = target > _groundWeight ? BlendInSpeed : BlendOutSpeed;
        _groundWeight = Mathf.Lerp(_groundWeight, target, 1 - Mathf.Exp(-response * dt));
        if (target == 0 && _groundWeight < 0.001f) _groundWeight = 0;

        // Draw suppresses immediately with its existing blend. Recovery may later
        // hold this input low through a release transient without restarting phase.
        float aimTarget = Mathf.Clamp(locomotionWeight, 0, 1);
        _locomotionWeight = aimTarget < _locomotionWeight ? aimTarget
            : Mathf.MoveToward(_locomotionWeight, aimTarget, dt / Mathf.Max(RecoverySeconds, 0.01f));
        Amplitude = _groundWeight * _locomotionWeight;

        float phase = PhaseRadians;
        // Two vertical steps per lateral cycle, with a small alternate-foot and
        // higher-harmonic accent. This avoids a circular, perfectly symmetric bob.
        float vertical = 0.75f * Mathf.Sin(2 * phase) + 0.2f * Mathf.Sin(4 * phase + 0.35f) + 0.05f * Mathf.Sin(phase);
        float lateral = 0.8f * Mathf.Sin(phase) + 0.2f * Mathf.Sin(3 * phase + 0.25f);
        float roll = 0.85f * Mathf.Sin(phase + 0.45f) + 0.15f * Mathf.Sin(2 * phase);
        PositionOffset = new Vector3(lateral * LateralAmount, vertical * VerticalAmount, 0) * Amplitude;
        RotationOffsetDegrees = new Vector3(0, 0, -roll * RollDegrees) * Amplitude;
    }
}
