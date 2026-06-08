using Godot;

public partial class PlayerSpeedFovModule : Node
{
    /// <summary>
    /// Включает расширение FOV от скорости движения игрока. Если выключено, модуль всегда возвращает нулевой FOV-бонус.
    /// </summary>
    [ExportGroup("Speed FOV")]
    [Export] public bool EnableSpeedFov { get; set; } = true;

    /// <summary>
    /// Главная сила эффекта: насколько каждый м/с сверх MinSpeedForFov увеличивает FOV.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float SpeedFovMultiplier { get; set; } = 0.45f;

    /// <summary>
    /// Скорость, ниже которой speed FOV не добавляет FOV-бонус.
    /// </summary>
    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float MinSpeedForFov { get; set; } = 5.0f;

    /// <summary>
    /// Максимальная прибавка к FOV от скорости, чтобы быстрый slide или slingshot launch не раздувал камеру бесконечно.
    /// </summary>
    [Export(PropertyHint.Range, "0,40,1,suffix:deg")] public float MaxSpeedFovBonus { get; set; } = 18.0f;

    /// <summary>
    /// Скорость плавного расширения FOV при разгоне.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,25,0.1")] public float SpeedFovSmoothUp { get; set; } = 8.0f;

    /// <summary>
    /// Скорость плавного возврата FOV при замедлении.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,25,0.1")] public float SpeedFovSmoothDown { get; set; } = 6.0f;

    /// <summary>
    /// Если включено, speed FOV учитывает полную скорость Vector3, включая вертикальный вылет от slingshot. Если выключено, учитывается только XZ-скорость.
    /// </summary>
    [Export] public bool UseFullVelocityForSpeedFov { get; set; } = true;

    /// <summary>
    /// Если включено, speed FOV отключается во время precision aiming, чтобы не спорить со снайперским сужением FOV.
    /// </summary>
    [Export] public bool DisableSpeedFovDuringPrecisionAim { get; set; } = true;

    /// <summary>
    /// Если включено, speed FOV раскладывает горизонтальную скорость на forward/back и strafe относительно камеры.
    /// </summary>
    [ExportGroup("Speed FOV / Axis Influence")]
    [Export] public bool UseAxisBasedSpeedFov { get; set; } = true;

    /// <summary>
    /// Множитель влияния боковой скорости A/D на FOV. Значение 0 полностью отключает вклад strafe.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float StrafeSpeedFovMultiplier { get; set; } = 0.0f;

    /// <summary>
    /// Боковая скорость, ниже которой strafe не добавляет FOV-бонус.
    /// </summary>
    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float MinStrafeSpeedForFov { get; set; } = 5.0f;

    /// <summary>
    /// Если включено, движение назад S влияет на forward FOV так же, как движение вперёд.
    /// </summary>
    [Export] public bool IncludeBackwardSpeedInForwardFov { get; set; } = true;

    /// <summary>
    /// Текущий сглаженный FOV-бонус от скорости. Его читает PlayerCameraFovModule и прибавляет к своему базовому FOV.
    /// </summary>
    public float CurrentSpeedFovBonus { get; private set; }

    /// <summary>
    /// Последний рассчитанный целевой FOV-бонус до smoothing. Полезен для debug-наблюдения за формулой speed FOV.
    /// </summary>
    public float CurrentTargetSpeedFovBonus { get; private set; }

    /// <summary>
    /// Последняя измеренная скорость игрока для диагностики jitter/FOV.
    /// </summary>
    public float CurrentSpeed { get; private set; }

    /// <summary>
    /// Последняя forward/back скорость относительно камеры для диагностики axis-based speed FOV.
    /// </summary>
    public float CurrentForwardSpeed { get; private set; }

    /// <summary>
    /// Последняя strafe скорость относительно камеры для диагностики axis-based speed FOV.
    /// </summary>
    public float CurrentStrafeSpeed { get; private set; }

    private PlayerController _player;

    /// <summary>
    /// Инициализирует модуль и сохраняет ссылку на PlayerController как источник velocity и tuning profile.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        CurrentSpeedFovBonus = 0.0f;
        CurrentTargetSpeedFovBonus = 0.0f;
    }

    /// <summary>
    /// Обновляет сглаженный FOV-бонус от скорости и возвращает значение, которое должен применить владелец Camera3D.Fov.
    /// </summary>
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

    /// <summary>
    /// Считает целевой FOV-бонус по формуле clamp((speed - MinSpeedForFov) * SpeedFovMultiplier, 0, MaxSpeedFovBonus).
    /// </summary>
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
