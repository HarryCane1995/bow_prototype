using Godot;

public partial class PlayerBowShootModule : Node
{
    private enum BowShotState
    {
        Idle,
        Drawing,
        Charged,
        PrecisionAiming,
        Released
    }

    /// <summary>
    /// Сцена projectile-стрелы, создаваемая при выстреле. Если не назначить сцену, модуль не сможет выпустить стрелу.
    /// </summary>
    [ExportGroup("Ссылки")]
    [Export] public PackedScene ArrowProjectileScene { get; set; }

    /// <summary>
    /// Путь к камере, задающей направление выстрела. Смена пути меняет источник направления; неверный путь заставит модуль использовать камеру игрока как fallback.
    /// </summary>
    [Export] public NodePath CameraPath { get; set; } = new("../CameraPivot/Camera3D");

    /// <summary>
    /// Путь к точке появления projectile-стрелы. Смена пути меняет место спавна; неверный путь заставит модуль использовать камеру.
    /// </summary>
    [Export] public NodePath ShootPointPath { get; set; } = new("../CameraPivot/Camera3D/ShootPoint");

    /// <summary>
    /// Скорость лёгкого выстрела без полного натяжения. Увеличение делает быструю стрелу быстрее и прямее; уменьшение делает её медленнее.
    /// </summary>
    [ExportGroup("Лёгкий выстрел")]
    [Export(PropertyHint.Range, "0,200,0.5,suffix:m/s")] public float LightShotSpeed { get; set; } = 50.0f;

    /// <summary>
    /// Урон лёгкого выстрела. Увеличение усиливает быстрый выстрел; уменьшение делает его слабее относительно заряженного.
    /// </summary>
    [Export(PropertyHint.Range, "0,100,1")] public float LightShotDamage { get; set; } = 8.0f;

    /// <summary>
    /// Скорость полностью заряженного выстрела. Увеличение делает charged shot быстрее и мощнее по ощущению; уменьшение сближает его с лёгким выстрелом.
    /// </summary>
    [ExportGroup("Заряженный выстрел")]
    [Export(PropertyHint.Range, "0,200,0.5,suffix:m/s")] public float ChargedShotSpeed { get; set; } = 100.0f;

    /// <summary>
    /// Урон полностью заряженного выстрела. Увеличение сильнее награждает полное натяжение; уменьшение снижает разницу между типами выстрела.
    /// </summary>
    [Export(PropertyHint.Range, "0,200,1")] public float ChargedShotDamage { get; set; } = 24.0f;

    /// <summary>
    /// Время до полного натяжения лука. Увеличение делает зарядку дольше; уменьшение быстрее переводит выстрел в charged shot.
    /// </summary>
    [ExportGroup("Тайминги")]
    [Export(PropertyHint.Range, "0.05,5,0.01,suffix:s")] public float ChargeTime { get; set; } = 0.8f;

    /// <summary>
    /// Включает третий режим precision shot. Если выключить, удержание ЛКМ дольше PrecisionChargeTime останется обычным charged shot.
    /// </summary>
    [ExportGroup("Precision Shot")]
    [Export] public bool EnablePrecisionShot { get; set; } = true;

    /// <summary>
    /// Время удержания ЛКМ до входа в precision aiming. Увеличение делает sniper shot более долгим; уменьшение быстрее включает прямой выстрел.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,6,0.05,suffix:s")] public float PrecisionChargeTime { get; set; } = 2.0f;

    /// <summary>
    /// Скорость precision straight shot. Увеличение делает выстрел ещё более мгновенным; уменьшение сильнее отличает его от charged shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,300,1,suffix:m/s")] public float PrecisionShotSpeed { get; set; } = 180.0f;

    /// <summary>
    /// Урон precision straight shot. Увеличение делает sniper shot мощнее; уменьшение снижает награду за долгое удержание.
    /// </summary>
    [Export(PropertyHint.Range, "0,400,1")] public float PrecisionShotDamage { get; set; } = 60.0f;

    /// <summary>
    /// Помечает precision shot как бронебойный. Если выключить, precision projectile остаётся прямым, но без armor-piercing метки.
    /// </summary>
    [Export] public bool PrecisionShotArmorPiercing { get; set; } = true;

    /// <summary>
    /// Минимальная пауза между выстрелами. Увеличение снижает скорострельность; уменьшение позволяет стрелять чаще.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.01,suffix:s")] public float FireCooldown { get; set; } = 0.2f;

    /// <summary>
    /// Время жизни созданной projectile-стрелы. Увеличение позволяет стреле лететь дольше; уменьшение быстрее удаляет её из сцены.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1,suffix:s")] public float ProjectileLifetime { get; set; } = 5.0f;

    /// <summary>
    /// Смещение точки появления стрелы вперёд по направлению выстрела. Увеличение отодвигает спавн от камеры; уменьшение приближает его к ShootPoint.
    /// </summary>
    [ExportGroup("Спавн projectile")]
    [Export(PropertyHint.Range, "0,2,0.01,suffix:m")] public float SpawnForwardOffset { get; set; } = 0.35f;

    private PlayerController _player;
    private Camera3D _camera;
    private Node3D _shootPoint;
    private PlayerBowVisualModule _bowVisualModule;
    private PlayerCameraFovModule _cameraFovModule;
    private BowShotState _shotState = BowShotState.Idle;
    private bool _isHoldingFire;
    private float _holdTime;
    private float _cooldownRemaining;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _camera = GetNodeOrNull<Camera3D>(CameraPath) ?? _player.Camera;
        _shootPoint = GetNodeOrNull<Node3D>(ShootPointPath) ?? _camera;
        _bowVisualModule = _player.BowVisualModule;
        _cameraFovModule = _player.CameraFovModule;
    }

    public override void _Process(double delta)
    {
        float deltaTime = (float)delta;
        _cooldownRemaining = Mathf.Max(0.0f, _cooldownRemaining - deltaTime);

        if (_isHoldingFire && Input.MouseMode != Input.MouseModeEnum.Captured)
        {
            CancelShot();
            return;
        }

        if (Input.IsActionJustPressed("fire"))
        {
            BeginDraw();
        }

        if (_isHoldingFire && Input.IsActionPressed("fire"))
        {
            UpdateDraw(deltaTime);
        }

        if (_isHoldingFire && Input.IsActionJustReleased("fire"))
        {
            ReleaseShot();
        }
    }

    private void BeginDraw()
    {
        _isHoldingFire = true;
        _holdTime = 0.0f;
        _shotState = BowShotState.Drawing;
        _bowVisualModule?.SetPrecisionAiming(false);
        _cameraFovModule?.SetPrecisionAiming(false);
    }

    private void UpdateDraw(float deltaTime)
    {
        _holdTime += deltaTime;
        float chargeDuration = Mathf.Max(0.001f, ChargeTime);
        float drawAmount = Mathf.Clamp(_holdTime / chargeDuration, 0.0f, 1.0f);
        _bowVisualModule?.SetDrawAmount(drawAmount);

        if (EnablePrecisionShot && _holdTime >= PrecisionChargeTime)
        {
            EnterPrecisionAiming();
            return;
        }

        if (_holdTime >= ChargeTime && _shotState == BowShotState.Drawing)
        {
            _shotState = BowShotState.Charged;
        }
    }

    private void EnterPrecisionAiming()
    {
        if (_shotState == BowShotState.PrecisionAiming)
        {
            return;
        }

        _shotState = BowShotState.PrecisionAiming;
        _bowVisualModule?.SetPrecisionAiming(true);
        _cameraFovModule?.SetPrecisionAiming(true);
    }

    private void ReleaseShot()
    {
        BowShotState releasedState = _shotState;
        _shotState = BowShotState.Released;

        bool precisionShot = releasedState == BowShotState.PrecisionAiming;
        bool chargedShot = precisionShot || _holdTime >= ChargeTime;
        bool shotFired = Fire(GetShotConfig(chargedShot, precisionShot));

        if (shotFired)
        {
            _bowVisualModule?.HandleShotVisual();
        }
        else
        {
            _bowVisualModule?.ResetDraw();
        }

        ResetShotState();
    }

    private void CancelShot()
    {
        _bowVisualModule?.ResetDraw();
        ResetShotState();
    }

    private ShotConfig GetShotConfig(bool chargedShot, bool precisionShot)
    {
        if (precisionShot)
        {
            return new ShotConfig(PrecisionShotSpeed, PrecisionShotDamage, ArrowFlightMode.Straight, PrecisionShotArmorPiercing);
        }

        if (chargedShot)
        {
            return new ShotConfig(ChargedShotSpeed, ChargedShotDamage, ArrowFlightMode.Ballistic, false);
        }

        return new ShotConfig(LightShotSpeed, LightShotDamage, ArrowFlightMode.Ballistic, false);
    }

    private bool Fire(ShotConfig shotConfig)
    {
        if (_cooldownRemaining > 0.0f || ArrowProjectileScene == null || _camera == null)
        {
            return false;
        }

        ArrowProjectile projectile = ArrowProjectileScene.Instantiate<ArrowProjectile>();
        Vector3 shootDirection = -_camera.GlobalTransform.Basis.Z.Normalized();
        Vector3 origin = (_shootPoint ?? _camera).GlobalPosition + shootDirection * SpawnForwardOffset;

        GetTree().CurrentScene.AddChild(projectile);
        projectile.GlobalPosition = origin;

        // Gameplay rule: arrows use only aim direction and shot speed, never player velocity.
        projectile.Initialize(
            shootDirection,
            shotConfig.Speed,
            shotConfig.Damage,
            ProjectileLifetime,
            shotConfig.FlightMode,
            shotConfig.ArmorPiercing
        );

        _cooldownRemaining = FireCooldown;
        return true;
    }

    private void ResetShotState()
    {
        _isHoldingFire = false;
        _holdTime = 0.0f;
        _shotState = BowShotState.Idle;
        _cameraFovModule?.SetPrecisionAiming(false);
        _bowVisualModule?.SetPrecisionAiming(false);
    }

    private readonly struct ShotConfig
    {
        public ShotConfig(float speed, float damage, ArrowFlightMode flightMode, bool armorPiercing)
        {
            Speed = speed;
            Damage = damage;
            FlightMode = flightMode;
            ArmorPiercing = armorPiercing;
        }

        public float Speed { get; }
        public float Damage { get; }
        public ArrowFlightMode FlightMode { get; }
        public bool ArmorPiercing { get; }
    }
}
