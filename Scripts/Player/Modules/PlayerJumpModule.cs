using Godot;

public partial class PlayerJumpModule : Node
{
    /// <summary>
    /// Начальная вертикальная скорость прыжка. Увеличение делает прыжок выше; уменьшение делает прыжок ниже и короче.
    /// </summary>
    [ExportGroup("Прыжок")]
    [Export(PropertyHint.Range, "0,20,0.1,suffix:m/s")] public float JumpVelocity { get; set; } = 5.0f;

    /// <summary>
    /// Множитель проектной гравитации для игрока. Увеличение быстрее тянет вниз и сокращает прыжок; уменьшение делает падение мягче и дольше.
    /// </summary>
    [Export(PropertyHint.Range, "0,5,0.05")] public float GravityMultiplier { get; set; } = 1.0f;

    /// <summary>
    /// Имя Input Map action для прыжка. Смена значения привязывает прыжок к другому действию; неверное имя отключит ввод прыжка.
    /// </summary>
    [Export] public string JumpAction { get; set; } = "jump";

    /// <summary>
    /// Вертикальная скорость, применяемая на земле при падении. Значение ближе к 0 уменьшает оседание после приземления; более отрицательное сильнее прижимает к земле.
    /// </summary>
    [ExportSubgroup("Контакт с землёй")]
    [Export(PropertyHint.Range, "-5,0,0.01,suffix:m/s")] public float GroundedVerticalVelocity { get; set; } = -0.1f;

    /// <summary>
    /// Сколько секунд после потери земли ещё разрешён прыжок. Увеличение делает сход с краёв прощающим; уменьшение требует нажимать прыжок точнее.
    /// </summary>
    [ExportSubgroup("Coyote Time")]
    [Export(PropertyHint.Range, "0,0.5,0.01,suffix:s")] public float CoyoteTime { get; set; } = 0.12f;

    /// <summary>
    /// Включает прыжок короткое время после схода с поверхности. Если выключить, прыгать можно только при текущем grounded-состоянии.
    /// </summary>
    [Export] public bool UseCoyoteTime { get; set; } = true;

    /// <summary>
    /// Разрешает модулю задавать FloorSnapLength игрока при инициализации. Если выключить, будет использоваться значение из CharacterBody3D/сцены.
    /// </summary>
    [ExportSubgroup("Floor Snap")]
    [Export] public bool OverrideFloorSnapLength { get; set; } = true;

    /// <summary>
    /// Длина прилипания CharacterBody3D к полу, склонам и ступеням. Увеличение сильнее удерживает на поверхности; уменьшение снижает ощущение прилипания.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.01,suffix:m")] public float FloorSnapLength { get; set; } = 0.1f;

    private PlayerController _player;
    private float _gravity;
    private float _coyoteTimer;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _gravity = (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble();

        if (OverrideFloorSnapLength)
        {
            _player.FloorSnapLength = FloorSnapLength;
        }
    }

    public void UpdateVerticalVelocity(double delta)
    {
        Vector3 velocity = _player.Velocity;
        bool isGrounded = _player.IsGrounded;

        if (isGrounded)
        {
            _coyoteTimer = CoyoteTime;
        }
        else
        {
            _coyoteTimer = Mathf.Max(0.0f, _coyoteTimer - (float)delta);
        }

        if (isGrounded)
        {
            if (velocity.Y < 0.0f)
            {
                velocity.Y = GroundedVerticalVelocity;
            }
        }
        else
        {
            velocity.Y -= _gravity * GravityMultiplier * (float)delta;
        }

        bool canJump = isGrounded || (UseCoyoteTime && _coyoteTimer > 0.0f);

        if (Input.IsActionJustPressed(JumpAction) && canJump)
        {
            velocity.Y = JumpVelocity;
            _coyoteTimer = 0.0f;
        }

        _player.Velocity = velocity;
    }
}
