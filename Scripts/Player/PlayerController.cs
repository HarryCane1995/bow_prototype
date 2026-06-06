using Godot;

public partial class PlayerController : CharacterBody3D
{
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

    /// <summary>
    /// Путь к модулю горизонтального движения. Смена пути подключает другой movement-модуль; неверный путь не позволит игроку инициализировать движение.
    /// </summary>
    [ExportGroup("Модули игрока")]
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
    /// Путь к модулю обзора мышью. Смена пути подключает другой look-модуль; неверный путь отключит поворот камеры и игрока.
    /// </summary>
    [Export] public NodePath LookModulePath { get; set; } = new("PlayerLookModule");

    /// <summary>
    /// Путь к модулю FOV камеры. Смена пути подключает другой FOV-модуль; неверный путь отключит zoom для precision shot.
    /// </summary>
    [Export] public NodePath CameraFovModulePath { get; set; } = new("PlayerCameraFovModule");

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

    public Node3D CameraPivot { get; private set; }
    public Camera3D Camera { get; private set; }
    public RayCast3D GroundCheck { get; private set; }
    public PlayerMovementModule MovementModule { get; private set; }
    public PlayerJumpModule JumpModule { get; private set; }
    public PlayerCrouchSlideModule CrouchSlideModule { get; private set; }
    public PlayerLookModule LookModule { get; private set; }
    public PlayerCameraFovModule CameraFovModule { get; private set; }
    public PlayerBowShootModule BowShootModule { get; private set; }
    public PlayerBowVisualModule BowVisualModule { get; private set; }
    public PlayerViewModelRenderModule ViewModelRenderModule { get; private set; }

    public bool IsGrounded => IsOnFloor() || (Velocity.Y <= 0.0f && GroundCheck?.IsColliding() == true);

    public override void _Ready()
    {
        CameraPivot = GetNode<Node3D>(CameraPivotPath);
        Camera = GetNode<Camera3D>(CameraPath);
        GroundCheck = GetNode<RayCast3D>(GroundCheckPath);
        MovementModule = GetNode<PlayerMovementModule>(MovementModulePath);
        JumpModule = GetNode<PlayerJumpModule>(JumpModulePath);
        CrouchSlideModule = GetNode<PlayerCrouchSlideModule>(CrouchSlideModulePath);
        LookModule = GetNode<PlayerLookModule>(LookModulePath);
        CameraFovModule = GetNode<PlayerCameraFovModule>(CameraFovModulePath);
        BowShootModule = GetNode<PlayerBowShootModule>(BowShootModulePath);
        BowVisualModule = GetNode<PlayerBowVisualModule>(BowVisualModulePath);
        ViewModelRenderModule = GetNode<PlayerViewModelRenderModule>(ViewModelRenderModulePath);

        MovementModule.Initialize(this);
        JumpModule.Initialize(this);
        CrouchSlideModule.Initialize(this);
        LookModule.Initialize(this);
        CameraFovModule.Initialize(this);
        ViewModelRenderModule.Initialize(this);
        BowVisualModule.Initialize(this);
        BowShootModule.Initialize(this);
    }

    public override void _PhysicsProcess(double delta)
    {
        JumpModule.UpdateVerticalVelocity(delta);
        Vector3 velocity = Velocity;
        CrouchSlideModule.ProcessCrouchSlide(delta, ref velocity);
        Velocity = velocity;
        MovementModule.UpdateHorizontalVelocity(delta);
        MoveAndSlide();
    }

    public override void _Input(InputEvent @event)
    {
        LookModule.HandleInput(@event);
    }
}
