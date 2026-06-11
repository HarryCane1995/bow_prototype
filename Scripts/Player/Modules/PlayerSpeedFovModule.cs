using Godot;

public partial class PlayerSpeedFovModule : Node
{
    // Calculates a speed bonus only. PlayerCameraFovModule applies the final gameplay camera FOV.
    [ExportGroup("Speed FOV")]
    [Export] public bool EnableSpeedFov { get; set; } = true;

    [Export(PropertyHint.Range, "0,2,0.05")] public float SpeedFovMultiplier { get; set; } = 0.45f;

    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float MinSpeedForFov { get; set; } = 5.0f;

    [Export(PropertyHint.Range, "0,40,1,suffix:deg")] public float MaxSpeedFovBonus { get; set; } = 18.0f;

    [Export(PropertyHint.Range, "0.1,25,0.1")] public float SpeedFovSmoothUp { get; set; } = 8.0f;

    [Export(PropertyHint.Range, "0.1,25,0.1")] public float SpeedFovSmoothDown { get; set; } = 6.0f;

    [Export] public bool UseFullVelocityForSpeedFov { get; set; } = true;

    [Export] public bool DisableSpeedFovDuringPrecisionAim { get; set; } = true;

    [ExportGroup("Speed FOV / Axis Influence")]
    [Export] public bool UseAxisBasedSpeedFov { get; set; } = true;

    [Export(PropertyHint.Range, "0,2,0.05")] public float StrafeSpeedFovMultiplier { get; set; } = 0.0f;

    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float MinStrafeSpeedForFov { get; set; } = 5.0f;

    [Export] public bool IncludeBackwardSpeedInForwardFov { get; set; } = true;

    public float CurrentSpeedFovBonus { get; private set; }

    public float CurrentTargetSpeedFovBonus { get; private set; }

    public float CurrentSpeed { get; private set; }

    public float CurrentForwardSpeed { get; private set; }

    public float CurrentStrafeSpeed { get; private set; }

    private PlayerController _player;

    public void Initialize(PlayerController player)
    {
        _player = player;
        CurrentSpeedFovBonus = 0.0f;
        CurrentTargetSpeedFovBonus = 0.0f;
    }

    public float UpdateSpeedFovBonus(double delta, bool precisionAimActive)
    {
        if (!CurrentEnableSpeedFov || (precisionAimActive && CurrentDisableSpeedFovDuringPrecisionAim))
        {
            UpdateDebugSpeeds();
            CurrentTargetSpeedFovBonus = 0.0f;
            CurrentSpeedFovBonus = 0.0f;
            return CurrentSpeedFovBonus;
        }

        CurrentTargetSpeedFovBonus = CalculateTargetSpeedFovBonus(precisionAimActive);

        float smooth = CurrentTargetSpeedFovBonus > CurrentSpeedFovBonus ? CurrentSpeedFovSmoothUp : CurrentSpeedFovSmoothDown;
        float t = 1.0f - Mathf.Exp(-smooth * (float)delta);
        CurrentSpeedFovBonus = Mathf.Lerp(CurrentSpeedFovBonus, CurrentTargetSpeedFovBonus, t);
        return CurrentSpeedFovBonus;
    }

    public float CalculateTargetSpeedFovBonus(bool precisionAimActive)
    {
        if (!CurrentEnableSpeedFov || _player == null || (precisionAimActive && CurrentDisableSpeedFovDuringPrecisionAim))
        {
            return 0.0f;
        }

        UpdateDebugSpeeds();

        if (CurrentUseAxisBasedSpeedFov)
        {
            return CalculateAxisBasedSpeedFovBonus();
        }

        float speed = GetPlayerSpeed();
        return Mathf.Clamp((speed - CurrentMinSpeedForFov) * CurrentSpeedFovMultiplier, 0.0f, CurrentMaxSpeedFovBonus);
    }

    private float CalculateAxisBasedSpeedFovBonus()
    {
        Vector3 velocity = _player.Velocity;
        Vector3 horizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        if (horizontalVelocity.IsZeroApprox())
        {
            return 0.0f;
        }

        Basis basis = _player.Camera?.GlobalTransform.Basis ?? _player.GlobalTransform.Basis;
        Vector3 forward = GetFlatDirection(-basis.Z);
        Vector3 right = GetFlatDirection(basis.X);
        if (forward.IsZeroApprox())
        {
            forward = GetFlatDirection(-_player.GlobalTransform.Basis.Z);
        }

        if (right.IsZeroApprox())
        {
            right = GetFlatDirection(_player.GlobalTransform.Basis.X);
        }

        float signedForwardSpeed = horizontalVelocity.Dot(forward);
        float forwardSpeed = CurrentIncludeBackwardSpeedInForwardFov
            ? Mathf.Abs(signedForwardSpeed)
            : Mathf.Max(0.0f, signedForwardSpeed);
        float strafeSpeed = Mathf.Abs(horizontalVelocity.Dot(right));
        CurrentSpeed = GetPlayerSpeed();
        CurrentForwardSpeed = forwardSpeed;
        CurrentStrafeSpeed = strafeSpeed;

        float forwardBonus = Mathf.Max(0.0f, forwardSpeed - CurrentMinSpeedForFov) * CurrentSpeedFovMultiplier;
        float strafeBonus = Mathf.Max(0.0f, strafeSpeed - CurrentMinStrafeSpeedForFov) * CurrentStrafeSpeedFovMultiplier;

        return Mathf.Clamp(forwardBonus + strafeBonus, 0.0f, CurrentMaxSpeedFovBonus);
    }

    private static Vector3 GetFlatDirection(Vector3 direction)
    {
        direction.Y = 0.0f;
        if (direction.IsZeroApprox())
        {
            return Vector3.Zero;
        }

        return direction.Normalized();
    }

    private float GetPlayerSpeed()
    {
        Vector3 velocity = _player.Velocity;
        if (CurrentUseFullVelocityForSpeedFov)
        {
            return velocity.Length();
        }

        return new Vector3(velocity.X, 0.0f, velocity.Z).Length();
    }

    private void UpdateDebugSpeeds()
    {
        if (_player == null)
        {
            CurrentSpeed = 0.0f;
            CurrentForwardSpeed = 0.0f;
            CurrentStrafeSpeed = 0.0f;
            return;
        }

        Vector3 velocity = _player.Velocity;
        Vector3 horizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        Basis basis = _player.Camera?.GlobalTransform.Basis ?? _player.GlobalTransform.Basis;
        Vector3 forward = GetFlatDirection(-basis.Z);
        Vector3 right = GetFlatDirection(basis.X);

        CurrentSpeed = GetPlayerSpeed();
        CurrentForwardSpeed = forward.IsZeroApprox() ? 0.0f : Mathf.Abs(horizontalVelocity.Dot(forward));
        CurrentStrafeSpeed = right.IsZeroApprox() ? 0.0f : Mathf.Abs(horizontalVelocity.Dot(right));
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private bool CurrentEnableSpeedFov => TuningProfile?.EnableSpeedFov ?? EnableSpeedFov;
    private float CurrentSpeedFovMultiplier => TuningProfile?.SpeedFovMultiplier ?? SpeedFovMultiplier;
    private float CurrentMinSpeedForFov => TuningProfile?.MinSpeedForFov ?? MinSpeedForFov;
    private float CurrentMaxSpeedFovBonus => TuningProfile?.MaxSpeedFovBonus ?? MaxSpeedFovBonus;
    private float CurrentSpeedFovSmoothUp => TuningProfile?.SpeedFovSmoothUp ?? SpeedFovSmoothUp;
    private float CurrentSpeedFovSmoothDown => TuningProfile?.SpeedFovSmoothDown ?? SpeedFovSmoothDown;
    private bool CurrentUseFullVelocityForSpeedFov => TuningProfile?.UseFullVelocityForSpeedFov ?? UseFullVelocityForSpeedFov;
    private bool CurrentDisableSpeedFovDuringPrecisionAim => TuningProfile?.DisableSpeedFovDuringPrecisionAim ?? DisableSpeedFovDuringPrecisionAim;
    private bool CurrentUseAxisBasedSpeedFov => TuningProfile?.UseAxisBasedSpeedFov ?? UseAxisBasedSpeedFov;
    private float CurrentStrafeSpeedFovMultiplier => TuningProfile?.StrafeSpeedFovMultiplier ?? StrafeSpeedFovMultiplier;
    private float CurrentMinStrafeSpeedForFov => TuningProfile?.MinStrafeSpeedForFov ?? MinStrafeSpeedForFov;
    private bool CurrentIncludeBackwardSpeedInForwardFov => TuningProfile?.IncludeBackwardSpeedInForwardFov ?? IncludeBackwardSpeedInForwardFov;
}
