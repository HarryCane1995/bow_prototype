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
    [Export(PropertyHint.Range, "0,80,0.1,suffix:m/s^2")] public float Acceleration { get; set; } = 18.0f;

    /// <summary>
    /// Доля управления движением в воздухе. Увеличение позволяет сильнее менять траекторию в прыжке; уменьшение делает полёт более инерционным.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05")] public float AirControlMultiplier { get; set; } = 0.35f;

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
        Vector2 input = GetMovementInput();
        Vector3 direction = GetMovementDirection(input);
        Vector3 velocity = _player.Velocity;

        Vector3 targetHorizontalVelocity = direction * MoveSpeed;
        Vector3 currentHorizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        float control = _player.IsGrounded ? 1.0f : AirControlMultiplier;
        float step = Acceleration * control * (float)delta;

        // Keep acceleration aligned with the intended horizontal movement vector.
        Vector3 newHorizontalVelocity = currentHorizontalVelocity.MoveToward(targetHorizontalVelocity, step);

        velocity.X = newHorizontalVelocity.X;
        velocity.Z = newHorizontalVelocity.Z;

        _player.Velocity = velocity;
    }

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
