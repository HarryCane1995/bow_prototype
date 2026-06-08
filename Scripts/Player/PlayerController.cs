using Godot;

public partial class PlayerController : CharacterBody3D
{
    /// <summary>
    /// Data-only профиль runtime-настроек игрока и оружия. Если назначен и UseTuningProfile включён, модули читают значения из него в Play.
    /// </summary>
    [ExportGroup("Runtime Tuning")]
    [Export] public PlayerTuningProfile TuningProfile { get; set; }

    /// <summary>
    /// Включает чтение значений из TuningProfile. Если выключить или оставить профиль пустым, модули используют свои локальные Export-поля как fallback.
    /// </summary>
    [Export] public bool UseTuningProfile { get; set; } = true;

    /// <summary>
    /// Путь к узлу-пивоту камеры. Если указать другой узел, mouse look будет наклонять камеру вокруг него; неверный путь сломает инициализацию игрока.
    /// </summary>
    [ExportGroup("Связи игрока")]
    [Export] public NodePath CameraPivotPath { get; set; } = new("CameraPivot");

    /// <summary>
    /// Путь к основной FPS-камере. От этой камеры зависят обзор игрока и направление стрельбы; неверный путь оставит связанные модули без камеры.
    /// </summary>
    [Export] public NodePath CameraPath { get; set; } = new("CameraPivot/Camera3D");

    /// <summary>
    /// Путь к RayCast3D для дополнительной проверки земли. Более точная ссылка улучшает grounded-состояние; неверная ссылка отключит этот запасной ground check.
    /// </summary>
    [Export] public NodePath GroundCheckPath { get; set; } = new("GroundCheck");

    [ExportGroup("Модули игрока")]
    /// <summary>
    /// Путь к модулю арбитража ability/motor authority. Если модуль отсутствует, существующие механики работают по старым локальным guard-флагам.
    /// </summary>
    [Export] public NodePath AbilityStateModulePath { get; set; } = new("PlayerAbilityStateModule");

    /// <summary>
    /// Путь к модулю горизонтального движения. Смена пути подключает другой movement-модуль; неверный путь ломает инициализацию движения.
    /// </summary>
    [Export] public NodePath MovementModulePath { get; set; } = new("PlayerMovementModule");

    /// <summary>
    /// Путь к модулю прыжка и гравитации. Смена пути подключает другой jump-модуль; неверный путь отключит вертикальное движение.
    /// </summary>
    [Export] public NodePath JumpModulePath { get; set; } = new("PlayerJumpModule");

    /// <summary>
    /// Путь к модулю приседа и подката. Смена пути подключает другой crouch/slide-модуль; неверный путь отключит присед, подкат и изменение высоты коллайдера.
    /// </summary>
    [Export] public NodePath CrouchSlideModulePath { get; set; } = new("PlayerCrouchSlideModule");

    /// <summary>
    /// Путь к модулю slingshot grapple. Смена пути подключает другой модуль внешнего управления velocity; неверный путь отключит зацепы-рогатки.
    /// </summary>
    [Export] public NodePath SlingshotGrappleModulePath { get; set; } = new("PlayerSlingshotGrappleModule");

    /// <summary>
    /// Путь к модулю обзора мышью. Смена пути подключает другой look-модуль; неверный путь отключит поворот камеры и игрока.
    /// </summary>
    [Export] public NodePath LookModulePath { get; set; } = new("PlayerLookModule");

    /// <summary>
    /// Путь к модулю FOV камеры. Смена пути подключает другой FOV-модуль; неверный путь отключит zoom для precision shot.
    /// </summary>
    [Export] public NodePath CameraFovModulePath { get; set; } = new("PlayerCameraFovModule");

    /// <summary>
    /// Путь к модулю speed-based FOV. Если модуль отсутствует, базовый и precision FOV продолжают работать без бонуса от скорости.
    /// </summary>
    [Export] public NodePath SpeedFovModulePath { get; set; } = new("PlayerSpeedFovModule");

    /// <summary>
    /// Путь к модулю игровой стрельбы из лука. Смена пути подключает другой shoot-модуль; неверный путь отключит создание projectile-стрел.
    /// </summary>
    [Export] public NodePath BowShootModulePath { get; set; } = new("PlayerBowShootModule");

    /// <summary>
    /// Путь к модулю визуала лука. Смена пути подключает другой visual-модуль; неверный путь отключит синхронизацию Draw-анимации и визуальной стрелы.
    /// </summary>
    [Export] public NodePath BowVisualModulePath { get; set; } = new("PlayerBowVisualModule");

    /// <summary>
    /// Путь к модулю отдельного рендера FPS viewmodel. Смена пути подключает другой render-модуль; неверный путь отключит настройку SubViewport/cull mask для лука.
    /// </summary>
    [Export] public NodePath ViewModelRenderModulePath { get; set; } = new("PlayerViewModelRenderModule");

    /// <summary>
    /// Путь к модулю procedural sway для FPS viewmodel. Если модуль отсутствует, визуал лука остаётся статичным относительно viewmodel root.
    /// </summary>
    [Export] public NodePath ViewModelSwayModulePath { get; set; } = new("PlayerViewModelSwayModule");

    public Node3D CameraPivot { get; private set; }
    public Camera3D Camera { get; private set; }
    public RayCast3D GroundCheck { get; private set; }
    public PlayerAbilityStateModule AbilityStateModule { get; private set; }
    public PlayerMovementModule MovementModule { get; private set; }
    public PlayerJumpModule JumpModule { get; private set; }
    public PlayerCrouchSlideModule CrouchSlideModule { get; private set; }
    public PlayerSlingshotGrappleModule SlingshotGrappleModule { get; private set; }
    public PlayerLookModule LookModule { get; private set; }
    public PlayerCameraFovModule CameraFovModule { get; private set; }
    public PlayerSpeedFovModule SpeedFovModule { get; private set; }
    public PlayerBowShootModule BowShootModule { get; private set; }
    public PlayerBowVisualModule BowVisualModule { get; private set; }
    public PlayerViewModelRenderModule ViewModelRenderModule { get; private set; }
    public PlayerViewModelSwayModule ViewModelSwayModule { get; private set; }

    public bool IsGrounded => IsOnFloor() || (Velocity.Y <= 0.0f && GroundCheck?.IsColliding() == true);
    public PlayerTuningProfile ActiveTuningProfile => UseTuningProfile ? TuningProfile : null;

    public override void _Ready()
    {
        AddToGroup("player");

        CameraPivot = GetNode<Node3D>(CameraPivotPath);
        Camera = GetNode<Camera3D>(CameraPath);
        GroundCheck = GetNode<RayCast3D>(GroundCheckPath);
        AbilityStateModule = GetNodeOrNull<PlayerAbilityStateModule>(AbilityStateModulePath);
        if (AbilityStateModule == null)
        {
            GD.PushWarning($"PlayerAbilityStateModule was not found at path: {AbilityStateModulePath}. Ability/motor authority arbitration is disabled for this player.");
        }
        MovementModule = GetNode<PlayerMovementModule>(MovementModulePath);
        JumpModule = GetNode<PlayerJumpModule>(JumpModulePath);
        CrouchSlideModule = GetNode<PlayerCrouchSlideModule>(CrouchSlideModulePath);
        SlingshotGrappleModule = GetNodeOrNull<PlayerSlingshotGrappleModule>(SlingshotGrappleModulePath);
        if (SlingshotGrappleModule == null)
        {
            GD.PushWarning($"PlayerSlingshotGrappleModule was not found at path: {SlingshotGrappleModulePath}. Slingshot grapple is disabled for this player.");
        }
        LookModule = GetNode<PlayerLookModule>(LookModulePath);
        CameraFovModule = GetNode<PlayerCameraFovModule>(CameraFovModulePath);
        SpeedFovModule = GetNodeOrNull<PlayerSpeedFovModule>(SpeedFovModulePath);
        if (SpeedFovModule == null)
        {
            GD.PushWarning($"PlayerSpeedFovModule was not found at path: {SpeedFovModulePath}. Speed-based FOV bonus is disabled for this player.");
        }
        BowShootModule = GetNode<PlayerBowShootModule>(BowShootModulePath);
        BowVisualModule = GetNode<PlayerBowVisualModule>(BowVisualModulePath);
        ViewModelRenderModule = GetNode<PlayerViewModelRenderModule>(ViewModelRenderModulePath);
        ViewModelSwayModule = GetNodeOrNull<PlayerViewModelSwayModule>(ViewModelSwayModulePath);
        if (ViewModelSwayModule == null)
        {
            GD.PushWarning($"PlayerViewModelSwayModule was not found at path: {ViewModelSwayModulePath}. Procedural viewmodel sway is disabled for this player.");
        }

        AbilityStateModule?.Initialize(this);
        MovementModule.Initialize(this);
        JumpModule.Initialize(this);
        CrouchSlideModule.Initialize(this);
        SlingshotGrappleModule?.Initialize(this);
        LookModule.Initialize(this);
        CameraFovModule.Initialize(this);
        SpeedFovModule?.Initialize(this);
        ViewModelRenderModule.Initialize(this);
        ViewModelSwayModule?.Initialize(this);
        BowVisualModule.Initialize(this);
        BowShootModule.Initialize(this);
    }

    public override void _PhysicsProcess(double delta)
    {
        SlingshotGrappleModule?.ProcessSlingshotInput();

        if (SlingshotGrappleModule?.BlocksJump != true)
        {
            JumpModule.UpdateVerticalVelocity(delta);
        }

        Vector3 velocity = Velocity;
        CrouchSlideModule.ProcessCrouchSlide(delta, ref velocity);
        Velocity = velocity;
        SlingshotGrappleModule?.UpdateSlingshot(delta);
        MovementModule.UpdateHorizontalVelocity(delta);
        MoveAndSlide();
    }

    public override void _Input(InputEvent @event)
    {
        LookModule.HandleInput(@event);
    }
}
