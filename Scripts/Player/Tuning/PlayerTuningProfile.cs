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
    /// Если включено, успешный Slingshot Grapple восстанавливает один air jump charge без ground reset.
    /// </summary>
    [Export] public bool RestoreDoubleJumpOnGrapple { get; set; } = true;

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
    /// Включает автоматический выход из slide при падении горизонтальной скорости ниже порога.
    /// </summary>
    [Export] public bool EnableSlideExitBySpeed { get; set; } = true;

    /// <summary>
    /// Минимальная горизонтальная скорость, ниже которой slide завершается после grace-времени.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.1,suffix:m/s")] public float SlideExitMinSpeed { get; set; } = 3.0f;

    /// <summary>
    /// Короткая задержка после старта slide перед проверкой выхода по скорости.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.5,0.01,suffix:s")] public float SlideExitMinSpeedGraceTime { get; set; } = 0.08f;

    /// <summary>
    /// Включает буфер подката в воздухе для автоматического входа в slide при приземлении.
    /// </summary>
    [Export] public bool EnableAirborneSlideEntry { get; set; } = true;

    /// <summary>
    /// Минимальная горизонтальная скорость в воздухе, при которой удержание crouch_slide буферит landing slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float AirborneSlideMinSpeed { get; set; } = 7.0f;

    /// <summary>
    /// Время жизни airborne-запроса на slide до следующего касания земли.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05,suffix:s")] public float AirborneSlideBufferTime { get; set; } = 0.25f;

    /// <summary>
    /// Разрешает landing slide брать направление из текущей горизонтальной velocity, если input-направление не выбрано.
    /// </summary>
    [Export] public bool AirborneSlideUseCurrentVelocityDirection { get; set; } = true;

    /// <summary>
    /// Если включено, WASD-ввод при приземлении может переопределить направление landing slide относительно камеры.
    /// </summary>
    [Export] public bool AirborneSlideUseInputDirectionIfAny { get; set; } = true;

    /// <summary>
    /// Минимальная сила WASD-ввода для выбора input-направления airborne landing slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05")] public float AirborneSlideInputMin { get; set; } = 0.1f;

    /// <summary>
    /// Включает прыжок из slide с сохранением части горизонтальной инерции.
    /// </summary>
    [Export] public bool EnableSlideJump { get; set; } = true;

    /// <summary>
    /// Дополнительный горизонтальный boost при прыжке из slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.25,suffix:m/s")] public float SlideJumpHorizontalBoost { get; set; } = 3.0f;

    /// <summary>
    /// Доля текущей горизонтальной velocity, сохраняемая при slide jump.
    /// </summary>
    [Export(PropertyHint.Range, "0,1.5,0.05")] public float SlideJumpVelocityCarryFactor { get; set; } = 0.75f;

    /// <summary>
    /// Максимальная горизонтальная скорость после slide jump.
    /// </summary>
    [Export(PropertyHint.Range, "0,35,0.5,suffix:m/s")] public float SlideJumpMaxHorizontalSpeed { get; set; } = 16.0f;

    /// <summary>
    /// Если включено, slide jump требует свободное место для вставания.
    /// </summary>
    [Export] public bool SlideJumpRequiresStandUpSpace { get; set; } = true;

    /// <summary>
    /// Максимальная дистанция поиска grapple anchor из камеры.
    /// </summary>
    [ExportGroup("Slingshot Grapple")]
    [Export(PropertyHint.Range, "1,100,0.5,suffix:m")] public float MaxGrappleDistance { get; set; } = 25.0f;

    /// <summary>
    /// Включает screen-space помощь выбора grapple anchor около центра экрана.
    /// </summary>
    [ExportGroup("Slingshot Grapple / Aim Assist")]
    [Export] public bool EnableScreenSpaceGrappleAssist { get; set; } = true;

    /// <summary>
    /// Радиус screen-space помощи в пикселях вокруг центра экрана.
    /// </summary>
    [Export(PropertyHint.Range, "0,240,4,suffix:px")] public float GrappleScreenAssistRadiusPixels { get; set; } = 96.0f;

    /// <summary>
    /// Если включено, прямое попадание raycast в anchor имеет приоритет над screen-space выбором.
    /// </summary>
    [Export] public bool PreferDirectRaycastHit { get; set; } = true;

    /// <summary>
    /// Максимальный угол от направления камеры до anchor для screen-space assist.
    /// </summary>
    [Export(PropertyHint.Range, "0,45,1,suffix:deg")] public float GrappleAssistMaxAngleDegrees { get; set; } = 18.0f;

    /// <summary>
    /// Требует прямую видимость до anchor для screen-space assist.
    /// </summary>
    [Export] public bool GrappleAssistRequireLineOfSight { get; set; } = true;

    /// <summary>
    /// Вес мировой дистанции в score выбора anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float GrappleAssistDistanceWeight { get; set; } = 0.25f;

    /// <summary>
    /// Вес экранной дистанции от центра в score выбора anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0,3,0.05")] public float GrappleAssistScreenDistanceWeight { get; set; } = 1.0f;

    /// <summary>
    /// Включает короткий camera snap к выбранному anchor после успешного grapple.
    /// </summary>
    [ExportGroup("Slingshot Grapple / Camera Assist")]
    [Export] public bool EnableGrappleCameraSnap { get; set; } = true;

    /// <summary>
    /// Длительность camera snap в секундах.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.5,0.01,suffix:s")] public float GrappleCameraSnapDuration { get; set; } = 0.16f;

    /// <summary>
    /// Сила доводки камеры к anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05")] public float GrappleCameraSnapStrength { get; set; } = 1.0f;

    /// <summary>
    /// Скорость сглаживания camera snap.
    /// </summary>
    [Export(PropertyHint.Range, "1,40,0.5")] public float GrappleCameraSnapSpeed { get; set; } = 18.0f;

    /// <summary>
    /// Если включено, mouse look временно игнорируется во время camera snap.
    /// </summary>
    [Export] public bool LockLookInputDuringGrappleSnap { get; set; } = true;

    /// <summary>
    /// Максимальный pitch camera snap в градусах.
    /// </summary>
    [Export(PropertyHint.Range, "0,89,1,suffix:deg")] public float GrappleCameraSnapMaxPitchDegrees { get; set; } = 85.0f;

    /// <summary>
    /// Включает жёлтый debug-highlight у лучшего GrappleAnchor, который прямо сейчас доступен для зацепа.
    /// </summary>
    [ExportGroup("Slingshot Grapple / Debug")]
    [Export] public bool EnableGrappleAvailableHighlight { get; set; } = true;

    /// <summary>
    /// Если включено, подсвечивается только лучший доступный anchor. Выключение зарезервировано для будущего режима подсветки нескольких точек.
    /// </summary>
    [Export] public bool GrappleHighlightOnlyBestAnchor { get; set; } = true;

    /// <summary>
    /// Ускорение притяжения к grapple anchor.
    /// </summary>
    [ExportGroup("Slingshot Grapple")]
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
    /// Включает мгновенный precision shot по Alt + ЛКМ. Если выключить, модификатор не создаёт straight projectile.
    /// </summary>
    [Export] public bool EnablePrecisionShot { get; set; } = true;

    /// <summary>
    /// Скорость мгновенного precision shot. Увеличение делает Alt + ЛКМ быстрее и прямее; уменьшение сближает его с charged shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,320,1,suffix:m/s")] public float PrecisionShotSpeed { get; set; } = 180.0f;

    /// <summary>
    /// Урон мгновенного precision shot. Увеличение делает Alt + ЛКМ мощнее; уменьшение приближает его к charged shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,400,1")] public float PrecisionShotDamage { get; set; } = 60.0f;

    /// <summary>
    /// Помечает precision shot как бронебойный. Если выключить, projectile остаётся прямым, но без armor-piercing метки.
    /// </summary>
    [Export] public bool PrecisionShotArmorPiercing { get; set; } = true;

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

    /// <summary>
    /// Включает расширение FOV от скорости движения игрока.
    /// </summary>
    [ExportGroup("Camera / Speed FOV")]
    [Export] public bool EnableSpeedFov { get; set; } = true;

    /// <summary>
    /// Главная сила speed FOV: насколько скорость сверх MinSpeedForFov расширяет FOV.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float SpeedFovMultiplier { get; set; } = 0.45f;

    /// <summary>
    /// Скорость, ниже которой FOV не расширяется от движения.
    /// </summary>
    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float MinSpeedForFov { get; set; } = 5.0f;

    /// <summary>
    /// Максимальный FOV-бонус от скорости.
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
    /// Если включено, speed FOV учитывает полную скорость Vector3, включая вертикальный slingshot launch.
    /// </summary>
    [Export] public bool UseFullVelocityForSpeedFov { get; set; } = true;

    /// <summary>
    /// Если включено, speed FOV не применяется во время precision aiming.
    /// </summary>
    [Export] public bool DisableSpeedFovDuringPrecisionAim { get; set; } = true;

    /// <summary>
    /// Включает viewmodel lag от движения мыши.
    /// </summary>
    [ExportGroup("ViewModel Sway")]
    [Export] public bool EnableMouseLag { get; set; } = true;

    /// <summary>
    /// Сила позиционного сдвига лука от mouse look delta.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.08,0.001,suffix:m")] public float MouseLagPositionAmount { get; set; } = 0.015f;

    /// <summary>
    /// Сила поворота лука от mouse look delta.
    /// </summary>
    [Export(PropertyHint.Range, "0,8,0.1,suffix:deg")] public float MouseLagRotationAmount { get; set; } = 1.5f;

    /// <summary>
    /// Включает инерцию viewmodel от ускорения игрока.
    /// </summary>
    [Export] public bool EnableMovementInertia { get; set; } = true;

    /// <summary>
    /// Сила позиционного сдвига viewmodel от ускорения игрока.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.03,0.001,suffix:m")] public float MovementInertiaPositionAmount { get; set; } = 0.004f;

    /// <summary>
    /// Сила поворота viewmodel от ускорения игрока.
    /// </summary>
    [Export(PropertyHint.Range, "0,4,0.05,suffix:deg")] public float MovementInertiaRotationAmount { get; set; } = 0.35f;

    /// <summary>
    /// Включает краткую просадку viewmodel при приземлении.
    /// </summary>
    [Export] public bool EnableLandingSway { get; set; } = true;

    /// <summary>
    /// Сила позиционной просадки viewmodel при приземлении.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.1,0.001,suffix:m")] public float LandingPositionAmount { get; set; } = 0.025f;

    /// <summary>
    /// Сила поворота viewmodel при приземлении.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.1,suffix:deg")] public float LandingRotationAmount { get; set; } = 2.0f;

    /// <summary>
    /// Скорость следования viewmodel к активному sway offset.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float SwayFollowSpeed { get; set; } = 12.0f;

    /// <summary>
    /// Скорость возврата viewmodel к базовому transform.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float SwayReturnSpeed { get; set; } = 10.0f;

    /// <summary>
    /// Скорость затухания landing impulse.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float ImpulseReturnSpeed { get; set; } = 14.0f;
}
