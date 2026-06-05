using Godot;

public partial class PlayerBowShootModule : Node
{
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
    [Export(PropertyHint.Range, "0,100,0.5,suffix:m/s")] public float LightShotSpeed { get; set; } = 24.0f;

    /// <summary>
    /// Урон лёгкого выстрела. Увеличение усиливает быстрый выстрел; уменьшение делает его слабее относительно заряженного.
    /// </summary>
    [Export(PropertyHint.Range, "0,100,1")] public float LightShotDamage { get; set; } = 8.0f;

    /// <summary>
    /// Скорость полностью заряженного выстрела. Увеличение делает charged shot быстрее и мощнее по ощущению; уменьшение сближает его с лёгким выстрелом.
    /// </summary>
    [ExportGroup("Заряженный выстрел")]
    [Export(PropertyHint.Range, "0,120,0.5,suffix:m/s")] public float ChargedShotSpeed { get; set; } = 46.0f;

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
    private bool _isHoldingFire;
    private float _holdTime;
    private float _cooldownRemaining;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _camera = GetNodeOrNull<Camera3D>(CameraPath) ?? _player.Camera;
        _shootPoint = GetNodeOrNull<Node3D>(ShootPointPath) ?? _camera;
        _bowVisualModule = _player.BowVisualModule;
    }

    public override void _Process(double delta)
    {
        float deltaTime = (float)delta;
        _cooldownRemaining = Mathf.Max(0.0f, _cooldownRemaining - deltaTime);

        if (Input.IsActionJustPressed("fire"))
        {
            _isHoldingFire = true;
            _holdTime = 0.0f;
        }

        if (_isHoldingFire && Input.IsActionPressed("fire"))
        {
            _holdTime += deltaTime;
            float chargeDuration = Mathf.Max(0.001f, ChargeTime);
            float drawAmount = Mathf.Clamp(_holdTime / chargeDuration, 0.0f, 1.0f);
            _bowVisualModule?.SetDrawAmount(drawAmount);
        }

        if (_isHoldingFire && Input.IsActionJustReleased("fire"))
        {
            bool shotFired = Fire(_holdTime >= ChargeTime);
            if (shotFired)
            {
                _bowVisualModule?.HandleShotVisual();
            }
            else
            {
                _bowVisualModule?.ResetDraw();
            }

            _isHoldingFire = false;
            _holdTime = 0.0f;
        }
    }

    private bool Fire(bool chargedShot)
    {
        if (_cooldownRemaining > 0.0f || ArrowProjectileScene == null || _camera == null)
        {
            return false;
        }

        ArrowProjectile projectile = ArrowProjectileScene.Instantiate<ArrowProjectile>();
        Vector3 direction = -_camera.GlobalTransform.Basis.Z.Normalized();
        Vector3 origin = (_shootPoint ?? _camera).GlobalPosition + direction * SpawnForwardOffset;

        GetTree().CurrentScene.AddChild(projectile);
        projectile.GlobalPosition = origin;
        projectile.Initialize(
            direction,
            chargedShot ? ChargedShotSpeed : LightShotSpeed,
            chargedShot ? ChargedShotDamage : LightShotDamage,
            ProjectileLifetime
        );

        _cooldownRemaining = FireCooldown;
        return true;
    }
}
