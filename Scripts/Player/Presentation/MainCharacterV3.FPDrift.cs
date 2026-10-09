using Godot;

public partial class MainCharacterV3
{
    // Baseline: 4a22f21 PlayerViewModelSwayModule + its serialized tuning profile.
    // Later mouse filters, draw lock and gait are deliberately not part of this port.
    [ExportGroup("FP Legacy Drift / A-B")]
    [Export] public bool FPDriftEnabled { get; set; } = true;
    [Export(PropertyHint.Range,"0,1,0.05")] public float FPDriftWeight { get; set; } = 1;
    [Export] public Key FPDriftToggleKey { get; set; } = Key.F4;
    [Export(PropertyHint.Range,"0,1,0.05")] public float MouseDriftWeight { get; set; } = 1;
    [Export(PropertyHint.Range,"0,1,0.05")] public float MovementSwayWeight { get; set; } = 1;
    [Export(PropertyHint.Range,"0,1,0.05")] public float LandingSwayWeight { get; set; } = 1;
    [Export(PropertyHint.Range,"0,1,0.05")] public float RollWeight { get; set; } = 1;

    [ExportGroup("FP Drift / Original Mouse Lag")]
    [Export(PropertyHint.Range,"0,0.08,0.001,suffix:m")] public float MouseLagPositionAmount { get; set; } = 0.015f;
    [Export(PropertyHint.Range,"0,8,0.1,suffix:deg")] public float MouseLagRotationAmount { get; set; } = 1.5f;
    [Export(PropertyHint.Range,"0,0.2,0.001,suffix:m")] public float MouseLagMaxPositionOffset { get; set; } = 0.08f;
    [Export(PropertyHint.Range,"0,20,0.1,suffix:deg")] public float MouseLagMaxRotationDegrees { get; set; } = 5;

    [ExportGroup("FP Drift / Original Movement Inertia")]
    [Export(PropertyHint.Range,"0,0.03,0.001,suffix:m")] public float MovementInertiaPositionAmount { get; set; } = 0.004f;
    [Export(PropertyHint.Range,"0,4,0.05,suffix:deg")] public float MovementInertiaRotationAmount { get; set; } = 0.35f;
    [Export(PropertyHint.Range,"0,0.2,0.001,suffix:m")] public float MovementInertiaMaxPositionOffset { get; set; } = 0.10f;
    [Export(PropertyHint.Range,"0,20,0.1,suffix:deg")] public float MovementInertiaMaxRotationDegrees { get; set; } = 6;
    [Export(PropertyHint.Range,"1,120,0.5")] public float MovementInertiaVelocityClamp { get; set; } = 40;

    [ExportGroup("FP Drift / Original Landing")]
    [Export(PropertyHint.Range,"0,20,0.1,suffix:m/s")] public float LandingMinImpactSpeed { get; set; } = 4;
    [Export(PropertyHint.Range,"0,0.1,0.001,suffix:m")] public float LandingPositionAmount { get; set; } = 0.025f;
    [Export(PropertyHint.Range,"0,10,0.1,suffix:deg")] public float LandingRotationAmount { get; set; } = 2;
    [Export(PropertyHint.Range,"0,0.2,0.001,suffix:m")] public float LandingMaxPositionOffset { get; set; } = 0.12f;
    [Export(PropertyHint.Range,"0,20,0.1,suffix:deg")] public float LandingMaxRotationDegrees { get; set; } = 8;
    [Export(PropertyHint.Range,"1,80,0.5,suffix:m/s")] public float LandingMaxImpactSpeed { get; set; } = 24;

    [ExportGroup("FP Drift / Original Response")]
    [Export(PropertyHint.Range,"0.1,30,0.1")] public float SwayFollowSpeed { get; set; } = 12;
    [Export(PropertyHint.Range,"0.1,30,0.1")] public float SwayReturnSpeed { get; set; } = 10;
    [Export(PropertyHint.Range,"0.1,30,0.1")] public float ImpulseReturnSpeed { get; set; } = 14;

    public Node3D FPDriftRoot { get; private set; }
    public Vector3 FPDriftPosition { get; private set; }
    public Vector3 FPDriftRotationDegrees { get; private set; }
    public Vector2 FPDriftLookDelta { get; private set; }

    private Vector3 _driftPosition, _driftRotation, _driftLandingPosition, _driftLandingRotation;
    private Vector3 _driftPreviousVelocity;
    private bool _driftPreviousGrounded, _driftWasActive;

    private void ResetFpDrift()
    {
        _driftPosition = _driftRotation = _driftLandingPosition = _driftLandingRotation = Vector3.Zero;
        FPDriftPosition = FPDriftRotationDegrees = Vector3.Zero;
        FPDriftLookDelta = Vector2.Zero;
        if (FPDriftRoot != null) FPDriftRoot.Transform = Transform3D.Identity;
        _driftPreviousVelocity = _player.Velocity;
        _driftPreviousGrounded = _player.IsGrounded;
        _driftWasActive = false;
    }

    private void UpdateFpDrift(double frameDelta)
    {
        // Consume only in the V2/hybrid domain. In F9 fallback the legacy module
        // remains its own consumer. Drain while disabled so enabling never kicks.
        Vector2 look = _world.Enabled ? _player.LookModule.ConsumeLookDelta() : Vector2.Zero;
        bool active = FpVisible && FPDriftEnabled && FPDriftWeight > 0
            && Input.MouseMode == Input.MouseModeEnum.Captured;
        if (!active) { ResetFpDrift(); return; }
        if (!_driftWasActive)
        {
            ResetFpDrift();
            look = Vector2.Zero;
            _driftWasActive = true;
        }
        FPDriftLookDelta = look;
        float dt = Mathf.Max(0.0001f, (float)frameDelta);
        Vector3 velocity = _player.Velocity;
        Vector3 position = DriftClamp(new Vector3(-look.X, look.Y, 0) * MouseLagPositionAmount,
            MouseLagMaxPositionOffset) * Mathf.Clamp(MouseDriftWeight, 0, 1);
        Vector3 rotation = DriftClamp(new Vector3(-look.Y, -look.X, -look.X * 0.35f) * MouseLagRotationAmount,
            MouseLagMaxRotationDegrees) * Mathf.Clamp(MouseDriftWeight, 0, 1);

        Vector3 acceleration = (velocity - _driftPreviousVelocity) / dt;
        acceleration.Y = 0;
        acceleration = DriftClamp(acceleration, MovementInertiaVelocityClamp);
        if (acceleration.LengthSquared() > 0.0001f)
        {
            // Read this render frame's published camera, including wallrun roll.
            // Match legacy horizontal projection; never rotate/compensate camera.
            Basis view = _player.Camera.GlobalBasis.Orthonormalized();
            float x = acceleration.Dot(DriftHorizontal(view.X, _player.GlobalBasis.X));
            float forward = acceleration.Dot(DriftHorizontal(-view.Z, -_player.GlobalBasis.Z));
            float weight = Mathf.Clamp(MovementSwayWeight, 0, 1);
            position += DriftClamp(new Vector3(-x, 0, forward * 0.4f) * MovementInertiaPositionAmount,
                MovementInertiaMaxPositionOffset) * weight;
            rotation += DriftClamp(new Vector3(-forward, 0, x) * MovementInertiaRotationAmount,
                MovementInertiaMaxRotationDegrees) * weight;
        }
        if (!_driftPreviousGrounded && _player.IsGrounded && Mathf.Abs(_driftPreviousVelocity.Y) >= LandingMinImpactSpeed)
        {
            float impact = Mathf.Clamp(Mathf.Abs(_driftPreviousVelocity.Y), 0, LandingMaxImpactSpeed);
            float weight = Mathf.Clamp(LandingSwayWeight, 0, 1);
            _driftLandingPosition = DriftClamp(_driftLandingPosition + new Vector3(0, -impact * LandingPositionAmount, 0) * weight,
                LandingMaxPositionOffset);
            _driftLandingRotation = DriftClamp(_driftLandingRotation + new Vector3(-impact * LandingRotationAmount, 0, 0) * weight,
                LandingMaxRotationDegrees);
        }
        _driftPosition = DriftSmooth(_driftPosition, position,
            position.LengthSquared() > _driftPosition.LengthSquared() ? SwayFollowSpeed : SwayReturnSpeed, dt);
        _driftRotation = DriftSmooth(_driftRotation, rotation,
            rotation.LengthSquared() > _driftRotation.LengthSquared() ? SwayFollowSpeed : SwayReturnSpeed, dt);
        _driftLandingPosition = DriftSmooth(_driftLandingPosition, Vector3.Zero, ImpulseReturnSpeed, dt);
        _driftLandingRotation = DriftSmooth(_driftLandingRotation, Vector3.Zero, ImpulseReturnSpeed, dt);
        float amount = Mathf.Clamp(FPDriftWeight, 0, 1);
        FPDriftPosition = DriftClamp(_driftPosition + _driftLandingPosition,
            Mathf.Max(MouseLagMaxPositionOffset, Mathf.Max(MovementInertiaMaxPositionOffset, LandingMaxPositionOffset))) * amount;
        FPDriftRotationDegrees = DriftClamp(_driftRotation + _driftLandingRotation,
            Mathf.Max(MouseLagMaxRotationDegrees, Mathf.Max(MovementInertiaMaxRotationDegrees, LandingMaxRotationDegrees))) * amount;
        FPDriftRotationDegrees *= new Vector3(1, 1, Mathf.Clamp(RollWeight, 0, 1));
        FPDriftRoot.Position = FPDriftPosition;
        FPDriftRoot.RotationDegrees = FPDriftRotationDegrees;
        _driftPreviousVelocity = velocity;
        _driftPreviousGrounded = _player.IsGrounded;
    }

    private static Vector3 DriftHorizontal(Vector3 axis, Vector3 fallback)
    {
        axis.Y = 0;
        if (axis.LengthSquared() == 0) { axis = fallback; axis.Y = 0; }
        return axis.LengthSquared() > 0 ? axis.Normalized() : Vector3.Zero;
    }
    private static Vector3 DriftSmooth(Vector3 from, Vector3 to, float speed, float dt)
        => from.Lerp(to, 1 - Mathf.Exp(-Mathf.Max(0, speed) * dt));
    private static Vector3 DriftClamp(Vector3 value, float max)
        => max <= 0 || value.LengthSquared() <= max * max ? value : value.Normalized() * max;
}
