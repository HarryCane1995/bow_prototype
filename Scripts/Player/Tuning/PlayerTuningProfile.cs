using Godot;

[GlobalClass]
public partial class PlayerTuningProfile : Resource
{
    /// <summary>
    /// Максимальная скорость обычного горизонтального движения игрока.
    /// </summary>
    [ExportGroup("Movement")]
    [Export(PropertyHint.Range, "0,30,0.1,suffix:m/s")] public float MoveSpeed { get; set; } = 15.0f;

    /// <summary>
    /// Ускорение по земле при наличии WASD-ввода.
    /// </summary>
    [Export(PropertyHint.Range, "0,160,0.5,suffix:m/s^2")] public float GroundAcceleration { get; set; } = 24.0f;

    /// <summary>
    /// Торможение по земле без WASD-ввода.
    /// </summary>
    [Export(PropertyHint.Range, "0,160,0.5,suffix:m/s^2")] public float GroundDeceleration { get; set; } = 28.0f;

    /// <summary>
    /// Ускорение при резкой смене направления на земле.
    /// </summary>
    [Export(PropertyHint.Range, "0,180,0.5,suffix:m/s^2")] public float GroundDirectionChangeAcceleration { get; set; } = 55.0f;

    /// <summary>
    /// Множитель ускорения при counter-strafe.
    /// </summary>
    [Export(PropertyHint.Range, "1,4,0.05")] public float CounterStrafeBoost { get; set; } = 1.75f;

    /// <summary>
    /// Вертикальная скорость обычного прыжка.
    /// </summary>
    [ExportGroup("Jump")]
    [Export(PropertyHint.Range, "0,30,0.1,suffix:m/s")] public float JumpVelocity { get; set; } = 10.0f;

    /// <summary>
    /// Разрешает дополнительный прыжок в воздухе.
    /// </summary>
    [Export] public bool EnableDoubleJump { get; set; } = true;

    /// <summary>
    /// Множитель силы второго и последующих прыжков в воздухе.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,3,0.05")] public float DoubleJumpVelocityMultiplier { get; set; } = 1.0f;

    /// <summary>
    /// Разрешает менять горизонтальное направление вторым прыжком относительно камеры.
    /// </summary>
    [Export] public bool EnableDoubleJumpRedirect { get; set; } = true;

    /// <summary>
    /// Горизонтальная скорость redirect при втором прыжке.
    /// </summary>
    [Export(PropertyHint.Range, "0,40,0.1,suffix:m/s")] public float DoubleJumpRedirectSpeed { get; set; } = 8.0f;

    /// <summary>
    /// Множитель скорости обычного движения в crouch-состоянии.
    /// </summary>
    [ExportGroup("Crouch / Slide")]
    [Export(PropertyHint.Range, "0.1,1,0.05")] public float CrouchSpeedMultiplier { get; set; } = 0.55f;

    /// <summary>
    /// Начальная скорость slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,40,0.1,suffix:m/s")] public float SlideInitialSpeed { get; set; } = 20.0f;

    /// <summary>
    /// Длительность slide в секундах.
    /// </summary>
    [Export(PropertyHint.Range, "0.05,3,0.01,suffix:s")] public float SlideDuration { get; set; } = 0.55f;

    /// <summary>
    /// Задержка перед повторным slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,3,0.01,suffix:s")] public float SlideCooldown { get; set; } = 0.35f;

    /// <summary>
    /// Скорость затухания slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,60,0.5,suffix:m/s^2")] public float SlideFriction { get; set; } = 14.0f;

    /// <summary>
    /// Сила управления направлением во время slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,3,0.05")] public float SlideSteeringStrength { get; set; } = 0.25f;

    /// <summary>
    /// Максимальная дистанция поиска grapple anchor из камеры.
    /// </summary>
    [ExportGroup("Slingshot Grapple")]
    [Export(PropertyHint.Range, "1,100,0.5,suffix:m")] public float MaxGrappleDistance { get; set; } = 25.0f;

    /// <summary>
    /// Ускорение притяжения к grapple anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0,140,0.5,suffix:m/s^2")] public float PullAcceleration { get; set; } = 45.0f;

    /// <summary>
    /// Максимальная скорость притяжения к grapple anchor.
    /// </summary>
    [Export(PropertyHint.Range, "1,100,0.5,suffix:m/s")] public float MaxPullSpeed { get; set; } = 24.0f;

    /// <summary>
    /// Базовая скорость slingshot launch после достижения anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0,100,0.5,suffix:m/s")] public float LaunchSpeed { get; set; } = 28.0f;

    /// <summary>
    /// Доля pull velocity, наследуемая во время slingshot launch.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float InheritPullVelocityFactor { get; set; } = 0.65f;

    /// <summary>
    /// Максимальная итоговая скорость slingshot launch.
    /// </summary>
    [Export(PropertyHint.Range, "1,120,0.5,suffix:m/s")] public float MaxLaunchVelocity { get; set; } = 36.0f;

    /// <summary>
    /// Скорость лёгкого выстрела из лука.
    /// </summary>
    [ExportGroup("Bow")]
    [Export(PropertyHint.Range, "0,220,0.5,suffix:m/s")] public float LightShotSpeed { get; set; } = 50.0f;

    /// <summary>
    /// Скорость заряженного выстрела из лука.
    /// </summary>
    [Export(PropertyHint.Range, "0,240,0.5,suffix:m/s")] public float ChargedShotSpeed { get; set; } = 100.0f;

    /// <summary>
    /// Скорость precision shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,320,1,suffix:m/s")] public float PrecisionShotSpeed { get; set; } = 180.0f;

    /// <summary>
    /// Гравитация projectile-стрелы для ballistic shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s^2")] public float ProjectileGravity { get; set; } = 18.0f;

    /// <summary>
    /// Обычный FOV камеры игрока.
    /// </summary>
    [ExportGroup("Camera")]
    [Export(PropertyHint.Range, "50,120,1,suffix:deg")] public float PlayerFov { get; set; } = 100.0f;

    /// <summary>
    /// FOV камеры в режиме precision aiming.
    /// </summary>
    [Export(PropertyHint.Range, "20,100,0.5,suffix:deg")] public float PrecisionFov { get; set; } = 45.0f;

    /// <summary>
    /// Скорость плавного перехода FOV.
    /// </summary>
    [Export(PropertyHint.Range, "1,300,1,suffix:deg/s")] public float FovTransitionSpeed { get; set; } = 240.0f;
}
