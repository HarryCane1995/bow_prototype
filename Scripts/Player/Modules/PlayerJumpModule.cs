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
    /// Включает дополнительный прыжок в воздухе. Если выключить, игрок сможет прыгать только с земли или в coyote window.
    /// </summary>
    [ExportSubgroup("Double Jump")]
    [Export] public bool EnableDoubleJump { get; set; } = true;

    /// <summary>
    /// Максимальное количество прыжков до следующего приземления. Увеличение даёт больше air jumps; уменьшение до 1 отключает двойной прыжок даже при EnableDoubleJump.
    /// </summary>
    [Export(PropertyHint.Range, "1,5,1")] public int MaxJumpCount { get; set; } = 2;

    /// <summary>
    /// Множитель силы второго и последующих прыжков в воздухе. Значение меньше 1 делает double jump слабее; больше 1 делает его сильнее обычного.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,2,0.05")] public float DoubleJumpVelocityMultiplier { get; set; } = 1.0f;

    /// <summary>
    /// Включает резкую смену горизонтального направления при втором прыжке. Если выключить, double jump будет менять только вертикальную скорость.
    /// </summary>
    [ExportSubgroup("Double Jump Redirect")]
    [Export] public bool EnableDoubleJumpRedirect { get; set; } = true;

    /// <summary>
    /// Горизонтальная скорость, которую игрок получает при redirect второго прыжка. Увеличение делает рывок сильнее; уменьшение делает смену направления мягче.
    /// </summary>
    [Export(PropertyHint.Range, "0,30,0.1,suffix:m/s")] public float DoubleJumpRedirectSpeed { get; set; } = 8.0f;

    /// <summary>
    /// Сохраняет более высокую текущую вертикальную скорость при втором прыжке. Если выключено, вертикальная скорость заменяется обычным импульсом double jump.
    /// </summary>
    [Export] public bool DoubleJumpRedirectKeepsVerticalVelocity { get; set; } = false;

    /// <summary>
    /// Минимальная сила WASD-ввода, при которой применяется redirect. Увеличение требует более уверенного ввода; уменьшение делает redirect чувствительнее.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.01")] public float DoubleJumpRedirectMinInput { get; set; } = 0.1f;

    /// <summary>
    /// Если включено, успешный Slingshot Grapple восстанавливает один воздушный прыжок без ground reset и coyote time.
    /// </summary>
    [Export] public bool RestoreDoubleJumpOnGrapple { get; set; } = true;

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
    private int _jumpsUsed;
    private bool _forceNextJumpAsAirJumpFromGrapple;

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
        if (_player.SlingshotGrappleModule?.BlocksJump == true)
        {
            return;
        }

        Vector3 velocity = _player.Velocity;
        bool isGrounded = _player.IsGrounded;

        if (isGrounded)
        {
            _coyoteTimer = CoyoteTime;
            _jumpsUsed = 0;
            _forceNextJumpAsAirJumpFromGrapple = false;
        }
        else
        {
            _coyoteTimer = Mathf.Max(0.0f, _coyoteTimer - (float)delta);

            if (_jumpsUsed == 0 && (!UseCoyoteTime || _coyoteTimer <= 0.0f))
            {
                _jumpsUsed = 1;
            }
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

        if (Input.IsActionJustPressed(JumpAction))
        {
            TryJump(ref velocity, isGrounded);
        }

        _player.Velocity = velocity;
    }

    /// <summary>
    /// Восстанавливает возможность одного air jump после успешного grapple, не меняя grounded-состояние, coyote timer и velocity.
    /// </summary>
    public void RestoreAirJumpChargeFromGrapple()
    {
        if (!CurrentRestoreDoubleJumpOnGrapple || !CurrentEnableDoubleJump)
        {
            return;
        }

        int maxJumpCount = Mathf.Max(1, MaxJumpCount);
        if (maxJumpCount <= 1)
        {
            return;
        }

        _jumpsUsed = maxJumpCount - 1;
        _forceNextJumpAsAirJumpFromGrapple = true;
    }

    private void TryJump(ref Vector3 velocity, bool isGrounded)
    {
        bool canGroundJump = !_forceNextJumpAsAirJumpFromGrapple && (isGrounded || (UseCoyoteTime && _coyoteTimer > 0.0f));
        if (canGroundJump)
        {
            if (_player.CrouchSlideModule?.IsSliding == true && !_player.CrouchSlideModule.TryConsumeSlideJumpBoost(ref velocity))
            {
                return;
            }

            velocity.Y = CurrentJumpVelocity;
            _jumpsUsed = 1;
            _coyoteTimer = 0.0f;
            return;
        }

        int maxJumpCount = CurrentEnableDoubleJump ? Mathf.Max(1, MaxJumpCount) : 1;
        if (_jumpsUsed >= maxJumpCount)
        {
            return;
        }

        bool isSecondJump = _jumpsUsed == 1;
        float doubleJumpVelocity = CurrentJumpVelocity * CurrentDoubleJumpVelocityMultiplier;
        velocity.Y = DoubleJumpRedirectKeepsVerticalVelocity ? Mathf.Max(velocity.Y, doubleJumpVelocity) : doubleJumpVelocity;

        if (isSecondJump && TryGetDoubleJumpRedirectDirection(out Vector3 redirectDirection))
        {
            velocity.X = redirectDirection.X * CurrentDoubleJumpRedirectSpeed;
            velocity.Z = redirectDirection.Z * CurrentDoubleJumpRedirectSpeed;
        }

        _jumpsUsed++;
        _coyoteTimer = 0.0f;
        _forceNextJumpAsAirJumpFromGrapple = false;
    }

    private bool TryGetDoubleJumpRedirectDirection(out Vector3 direction)
    {
        direction = Vector3.Zero;

        if (!CurrentEnableDoubleJumpRedirect)
        {
            return false;
        }

        Vector2 input = GetMovementInput();
        if (input.Length() < DoubleJumpRedirectMinInput)
        {
            return false;
        }

        Basis basis = _player.Camera?.GlobalTransform.Basis.Orthonormalized() ?? _player.GlobalTransform.Basis.Orthonormalized();
        Vector3 forward = GetHorizontalAxis(-basis.Z, -_player.GlobalTransform.Basis.Z);
        Vector3 right = GetHorizontalAxis(basis.X, _player.GlobalTransform.Basis.X);

        Vector3 desiredDirection = forward * input.Y + right * input.X;
        if (desiredDirection.LengthSquared() == 0.0f)
        {
            return false;
        }

        direction = desiredDirection.Normalized();
        return true;
    }

    private Vector3 GetHorizontalAxis(Vector3 axis, Vector3 fallbackAxis)
    {
        axis.Y = 0.0f;
        if (axis.LengthSquared() == 0.0f)
        {
            axis = fallbackAxis;
            axis.Y = 0.0f;
        }

        return axis.LengthSquared() > 0.0f ? axis.Normalized() : Vector3.Zero;
    }

    private Vector2 GetMovementInput()
    {
        PlayerMovementModule movement = _player.MovementModule;
        string moveRightAction = movement?.MoveRightAction ?? "move_right";
        string moveLeftAction = movement?.MoveLeftAction ?? "move_left";
        string moveForwardAction = movement?.MoveForwardAction ?? "move_forward";
        string moveBackAction = movement?.MoveBackAction ?? "move_back";

        Vector2 input = new(
            Input.GetActionStrength(moveRightAction) - Input.GetActionStrength(moveLeftAction),
            Input.GetActionStrength(moveForwardAction) - Input.GetActionStrength(moveBackAction)
        );

        return input.LengthSquared() > 1.0f ? input.Normalized() : input;
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private float CurrentJumpVelocity => TuningProfile?.JumpVelocity ?? JumpVelocity;
    private bool CurrentEnableDoubleJump => TuningProfile?.EnableDoubleJump ?? EnableDoubleJump;
    private float CurrentDoubleJumpVelocityMultiplier => TuningProfile?.DoubleJumpVelocityMultiplier ?? DoubleJumpVelocityMultiplier;
    private bool CurrentEnableDoubleJumpRedirect => TuningProfile?.EnableDoubleJumpRedirect ?? EnableDoubleJumpRedirect;
    private float CurrentDoubleJumpRedirectSpeed => TuningProfile?.DoubleJumpRedirectSpeed ?? DoubleJumpRedirectSpeed;
    private bool CurrentRestoreDoubleJumpOnGrapple => TuningProfile?.RestoreDoubleJumpOnGrapple ?? RestoreDoubleJumpOnGrapple;
}
