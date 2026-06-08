using Godot;

public partial class PlayerMovementModule : Node
{
    /// <summary>
    /// Максимальная горизонтальная скорость игрока. Увеличение делает движение быстрее; уменьшение делает перемещение медленнее и тяжелее.
    /// </summary>
    [ExportGroup("Движение")]
    [Export(PropertyHint.Range, "0,20,0.1,suffix:m/s")] public float MoveSpeed { get; set; } = 6.0f;

    /// <summary>
    /// Скорость разгона горизонтального вектора движения. Увеличение даёт более резкий старт и смену направления; уменьшение делает разгон плавнее.
    /// </summary>
    [ExportSubgroup("Legacy")]
    [Export(PropertyHint.Range, "0,80,0.1,suffix:m/s^2")] public float Acceleration { get; set; } = 18.0f;

    /// <summary>
    /// Доля управления движением в воздухе. Увеличение позволяет сильнее менять траекторию в прыжке; уменьшение делает полёт более инерционным.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05")] public float AirControlMultiplier { get; set; } = 0.35f;

    /// <summary>
    /// Обычный разгон по земле, когда игрок нажимает WASD без резкой смены направления. Увеличение делает старт движения быстрее; уменьшение оставляет больше инерции.
    /// </summary>
    [ExportGroup("Movement Response")]
    [Export(PropertyHint.Range, "0,120,0.5,suffix:m/s^2")] public float GroundAcceleration { get; set; } = 24.0f;

    /// <summary>
    /// Торможение по земле, когда игрок не держит WASD. Увеличение быстрее гасит скорость; уменьшение делает остановку более скользкой.
    /// </summary>
    [Export(PropertyHint.Range, "0,120,0.5,suffix:m/s^2")] public float GroundDeceleration { get; set; } = 28.0f;

    /// <summary>
    /// Включает отдельное ускорение при резкой смене направления; для диагностики jitter можно временно отключить.
    /// </summary>
    [Export] public bool EnableDirectionChangeAcceleration { get; set; } = true;

    /// <summary>
    /// Ускорение при резкой смене направления по земле. Увеличение делает D->A и W->S отзывчивее; уменьшение оставляет больше старой инерции.
    /// </summary>
    [Export(PropertyHint.Range, "0,160,0.5,suffix:m/s^2")] public float GroundDirectionChangeAcceleration { get; set; } = 55.0f;

    /// <summary>
    /// Включает множитель counter-strafe acceleration; для диагностики jitter можно временно отключить.
    /// </summary>
    [Export] public bool EnableCounterStrafeBoost { get; set; } = true;

    /// <summary>
    /// Дополнительный множитель для почти противоположного направления ввода. Увеличение сильнее ускоряет counter-strafe; уменьшение делает разворот мягче.
    /// </summary>
    [Export(PropertyHint.Range, "1,3,0.05")] public float CounterStrafeBoost { get; set; } = 1.25f;

    /// <summary>
    /// Порог dot product для определения резкой смены направления. Увеличение чаще включает direction-change acceleration; уменьшение требует более противоположного ввода.
    /// </summary>
    [Export(PropertyHint.Range, "-1,1,0.05")] public float DirectionChangeDotThreshold { get; set; } = 0.35f;

    /// <summary>
    /// Разгон в воздухе при удержании WASD. Увеличение даёт больше air control; уменьшение сохраняет траекторию более инерционной.
    /// </summary>
    [Export(PropertyHint.Range, "0,60,0.5,suffix:m/s^2")] public float AirAcceleration { get; set; } = 8.0f;

    /// <summary>
    /// Торможение в воздухе без WASD-ввода. Увеличение быстрее гасит горизонтальную скорость в прыжке; уменьшение почти не трогает полёт.
    /// </summary>
    [Export(PropertyHint.Range, "0,30,0.5,suffix:m/s^2")] public float AirDeceleration { get; set; } = 2.0f;

    /// <summary>
    /// Ускорение смены направления в воздухе. Увеличение делает air strafe отзывчивее; уменьшение помогает double jump redirect оставаться отдельной сильной механикой.
    /// </summary>
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s^2")] public float AirDirectionChangeAcceleration { get; set; } = 12.0f;

    /// <summary>
    /// Имя Input Map action для движения вперёд. Смена значения привязывает движение вперёд к другому действию; неверное имя отключит ввод вперёд.
    /// </summary>
    [ExportGroup("Input Actions")]
    [Export] public string MoveForwardAction { get; set; } = "move_forward";

    /// <summary>
    /// Имя Input Map action для движения назад. Смена значения привязывает движение назад к другому действию; неверное имя отключит ввод назад.
    /// </summary>
    [Export] public string MoveBackAction { get; set; } = "move_back";

    /// <summary>
    /// Имя Input Map action для движения влево. Смена значения привязывает strafe left к другому действию; неверное имя отключит ввод влево.
    /// </summary>
    [Export] public string MoveLeftAction { get; set; } = "move_left";

    /// <summary>
    /// Имя Input Map action для движения вправо. Смена значения привязывает strafe right к другому действию; неверное имя отключит ввод вправо.
    /// </summary>
    [Export] public string MoveRightAction { get; set; } = "move_right";

    private PlayerController _player;

    public void Initialize(PlayerController player)
    {
        _player = player;
    }

    public void UpdateHorizontalVelocity(double delta)
    {
        if (_player.SlingshotGrappleModule?.IsNormalMovementBlocked == true)
        {
            return;
        }

        if (_player.CrouchSlideModule?.IsSliding == true)
        {
            return;
        }

        if (_player.AbilityStateModule != null
            && !_player.AbilityStateModule.CanWrite(PlayerAbilityTag.DefaultMovement, PlayerAbilityLock.HorizontalVelocity))
        {
            return;
        }

        Vector2 input = GetMovementInput();
        bool hasInput = input.LengthSquared() > 0.0f;
        Vector3 direction = GetMovementDirection(input);
        Vector3 velocity = _player.Velocity;

        float speedMultiplier = _player.CrouchSlideModule?.CurrentSpeedMultiplier ?? 1.0f;
        Vector3 targetHorizontalVelocity = hasInput ? direction * CurrentMoveSpeed * speedMultiplier : Vector3.Zero;
        Vector3 currentHorizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        float selectedAcceleration = SelectMovementResponse(currentHorizontalVelocity, direction, hasInput);
        float step = selectedAcceleration * (float)delta;

        // Keep acceleration aligned with the intended horizontal movement vector.
        Vector3 newHorizontalVelocity = currentHorizontalVelocity.MoveToward(targetHorizontalVelocity, step);

        velocity.X = newHorizontalVelocity.X;
        velocity.Z = newHorizontalVelocity.Z;

        _player.Velocity = velocity;
    }

    private float SelectMovementResponse(Vector3 currentHorizontalVelocity, Vector3 desiredDirection, bool hasInput)
    {
        bool isGrounded = _player.IsGrounded;

        if (!hasInput)
        {
            return isGrounded ? CurrentGroundDeceleration : AirDeceleration;
        }

        float selectedAcceleration = isGrounded ? CurrentGroundAcceleration : AirAcceleration;
        if (currentHorizontalVelocity.LengthSquared() <= 0.0025f)
        {
            return selectedAcceleration;
        }

        float dot = currentHorizontalVelocity.Normalized().Dot(desiredDirection);
        if (CurrentEnableDirectionChangeAcceleration && dot < DirectionChangeDotThreshold)
        {
            selectedAcceleration = isGrounded ? CurrentGroundDirectionChangeAcceleration : AirDirectionChangeAcceleration;
        }

        if (CurrentEnableCounterStrafeBoost && dot < 0.0f)
        {
            selectedAcceleration *= CurrentCounterStrafeBoost;
        }

        return selectedAcceleration;
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private float CurrentMoveSpeed => TuningProfile?.MoveSpeed ?? MoveSpeed;
    private float CurrentGroundAcceleration => TuningProfile?.GroundAcceleration ?? GroundAcceleration;
    private float CurrentGroundDeceleration => TuningProfile?.GroundDeceleration ?? GroundDeceleration;
    private bool CurrentEnableDirectionChangeAcceleration => TuningProfile?.EnableDirectionChangeAcceleration ?? EnableDirectionChangeAcceleration;
    private float CurrentGroundDirectionChangeAcceleration => TuningProfile?.GroundDirectionChangeAcceleration ?? GroundDirectionChangeAcceleration;
    private bool CurrentEnableCounterStrafeBoost => TuningProfile?.EnableCounterStrafeBoost ?? EnableCounterStrafeBoost;
    private float CurrentCounterStrafeBoost => TuningProfile?.CounterStrafeBoost ?? CounterStrafeBoost;

    private Vector2 GetMovementInput()
    {
        Vector2 input = new(
            Input.GetActionStrength(MoveRightAction) - Input.GetActionStrength(MoveLeftAction),
            Input.GetActionStrength(MoveForwardAction) - Input.GetActionStrength(MoveBackAction)
        );

        return input.LengthSquared() > 1.0f ? input.Normalized() : input;
    }

    private Vector3 GetMovementDirection(Vector2 input)
    {
        if (input == Vector2.Zero)
        {
            return Vector3.Zero;
        }

        Basis playerBasis = _player.GlobalTransform.Basis.Orthonormalized();
        Vector3 forward = -playerBasis.Z;
        Vector3 right = playerBasis.X;

        forward.Y = 0.0f;
        right.Y = 0.0f;

        return (forward.Normalized() * input.Y + right.Normalized() * input.X).Normalized();
    }
}
