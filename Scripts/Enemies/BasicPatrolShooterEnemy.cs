using Godot;

public partial class BasicPatrolShooterEnemy : CharacterBody3D, IDamageable
{
    /// <summary>
    /// Путь к игроку. Если путь пустой или неверный, враг попробует найти игрока по группе "player".
    /// </summary>
    [ExportGroup("References")]
    [Export] public NodePath PlayerPath { get; set; } = new("");

    /// <summary>
    /// Сцена projectile, которым враг стреляет по игроку. Если не назначена, враг патрулирует, но не стреляет.
    /// </summary>
    [Export] public PackedScene EnemyProjectileScene { get; set; }

    /// <summary>
    /// Путь к точке выстрела. Неверный путь заставит врага стрелять из своей позиции.
    /// </summary>
    [Export] public NodePath ShootPointPath { get; set; } = new("ShootPoint");

    /// <summary>
    /// Ось патруля в локике мира. Увеличение компоненты X/Z меняет направление маршрута; нулевой вектор отключает движение.
    /// </summary>
    [ExportGroup("Patrol")]
    [Export] public Vector3 PatrolAxis { get; set; } = Vector3.Right;

    /// <summary>
    /// Дистанция патруля в каждую сторону от стартовой позиции. Увеличение делает маршрут длиннее; уменьшение оставляет врага ближе к старту.
    /// </summary>
    [Export(PropertyHint.Range, "0,30,0.1,suffix:m")] public float PatrolDistance { get; set; } = 5.0f;

    /// <summary>
    /// Скорость патруля. Увеличение делает врага быстрее; уменьшение делает его более спокойной движущейся целью.
    /// </summary>
    [Export(PropertyHint.Range, "0,12,0.1,suffix:m/s")] public float PatrolSpeed { get; set; } = 2.5f;

    /// <summary>
    /// Останавливаться ли на краях патруля. Если выключено, враг сразу разворачивается.
    /// </summary>
    [Export] public bool WaitAtPatrolEnds { get; set; } = false;

    /// <summary>
    /// Сколько секунд ждать на краю патруля. Увеличение делает движение более ступенчатым; уменьшение почти убирает паузы.
    /// </summary>
    [Export(PropertyHint.Range, "0,5,0.05,suffix:s")] public float WaitTimeAtEnds { get; set; } = 0.25f;

    /// <summary>
    /// Разрешает врагу стрелять по игроку. Если выключить, враг останется только патрульной целью.
    /// </summary>
    [ExportGroup("Shooting")]
    [Export] public bool CanShoot { get; set; } = true;

    /// <summary>
    /// Интервал между выстрелами в секундах. Увеличение делает врага безопаснее; уменьшение повышает давление на игрока.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,10,0.1,suffix:s")] public float ShootInterval { get; set; } = 2.0f;

    /// <summary>
    /// Скорость projectile врага. Увеличение делает попадания сложнее избежать; уменьшение делает выстрелы более читаемыми.
    /// </summary>
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s")] public float ProjectileSpeed { get; set; } = 16.0f;

    /// <summary>
    /// Смещение точки прицеливания относительно позиции игрока. Увеличение Y заставляет врага целиться выше; уменьшение целится ниже.
    /// </summary>
    [Export] public Vector3 AimAtPlayerCenterOffset { get; set; } = new(0.0f, 1.0f, 0.0f);

    /// <summary>
    /// Поворачивать врага лицом к игроку по горизонтали. Если выключить, патруль и стрельба работают без визуального разворота.
    /// </summary>
    [Export] public bool RotateToFacePlayer { get; set; } = true;

    /// <summary>
    /// Максимальное здоровье врага. Увеличение требует больше попаданий; уменьшение делает врага одноразовой целью.
    /// </summary>
    [ExportGroup("Health")]
    [Export(PropertyHint.Range, "1,20,1")] public int MaxHealth { get; set; } = 1;

    /// <summary>
    /// Удалять врага из сцены при смерти. Если выключить, враг отключит коллизии и стрельбу, но останется в сцене.
    /// </summary>
    [Export] public bool DestroyOnDeath { get; set; } = true;

    /// <summary>
    /// Печатать события врага в Output. Включение помогает отлаживать патруль, выстрелы и получение урона.
    /// </summary>
    [ExportGroup("Debug")]
    [Export] public bool DebugPrintEnemyEvents { get; set; } = false;

    private Node3D _player;
    private Marker3D _shootPoint;
    private Vector3 _startPosition;
    private Vector3 _patrolAxis = Vector3.Right;
    private int _patrolDirection = 1;
    private float _waitTimer;
    private float _shootTimer;
    private int _health;
    private float _gravity;
    private bool _isDead;

    public override void _Ready()
    {
        AddToGroup("enemy");
        _startPosition = GlobalPosition;
        _patrolAxis = PatrolAxis.LengthSquared() > 0.0001f ? PatrolAxis.Normalized() : Vector3.Zero;
        _shootPoint = GetNodeOrNull<Marker3D>(ShootPointPath);
        _player = FindPlayer();
        _health = MaxHealth;
        _shootTimer = ShootInterval;
        _gravity = (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_isDead)
        {
            return;
        }

        float deltaTime = (float)delta;
        UpdatePatrol(deltaTime);
        UpdateFacing();
        UpdateShooting(deltaTime);
    }

    /// <summary>
    /// Применяет урон к врагу. Если здоровье падает до нуля, враг умирает или исчезает.
    /// </summary>
    public void ApplyDamage(int amount)
    {
        if (_isDead)
        {
            return;
        }

        _health -= Mathf.Max(0, amount);
        if (DebugPrintEnemyEvents)
        {
            GD.Print($"{Name} took {amount} damage. Health: {_health}");
        }

        if (_health <= 0)
        {
            Die();
        }
    }

    private void UpdatePatrol(float delta)
    {
        Vector3 velocity = Velocity;
        velocity.X = 0.0f;
        velocity.Z = 0.0f;

        if (!IsOnFloor())
        {
            velocity.Y -= _gravity * delta;
        }
        else if (velocity.Y < 0.0f)
        {
            velocity.Y = 0.0f;
        }

        if (_patrolAxis != Vector3.Zero && PatrolDistance > 0.0f && PatrolSpeed > 0.0f)
        {
            if (_waitTimer > 0.0f)
            {
                _waitTimer = Mathf.Max(0.0f, _waitTimer - delta);
            }
            else
            {
                float currentOffset = (GlobalPosition - _startPosition).Dot(_patrolAxis);
                float targetOffset = _patrolDirection * PatrolDistance;

                if (Mathf.Abs(targetOffset - currentOffset) <= 0.1f)
                {
                    _patrolDirection *= -1;
                    _waitTimer = WaitAtPatrolEnds ? WaitTimeAtEnds : 0.0f;
                }

                velocity += _patrolAxis * _patrolDirection * PatrolSpeed;
            }
        }

        Velocity = velocity;
        MoveAndSlide();
    }

    private void UpdateFacing()
    {
        if (!RotateToFacePlayer || _player == null)
        {
            return;
        }

        Vector3 target = _player.GlobalPosition;
        target.Y = GlobalPosition.Y;
        if ((target - GlobalPosition).LengthSquared() > 0.0001f)
        {
            LookAt(target, Vector3.Up);
        }
    }

    private void UpdateShooting(float delta)
    {
        if (!CanShoot || EnemyProjectileScene == null)
        {
            return;
        }

        _player ??= FindPlayer();
        if (_player == null)
        {
            return;
        }

        _shootTimer -= delta;
        if (_shootTimer > 0.0f)
        {
            return;
        }

        _shootTimer = ShootInterval;
        ShootAtPlayer();
    }

    private void ShootAtPlayer()
    {
        Node3D shootPoint = _shootPoint != null ? _shootPoint : this;
        Vector3 targetPosition = _player.GlobalPosition + AimAtPlayerCenterOffset;
        Vector3 direction = (targetPosition - shootPoint.GlobalPosition).Normalized();
        if (direction.LengthSquared() <= 0.0001f)
        {
            return;
        }

        EnemyProjectile projectile = EnemyProjectileScene.Instantiate<EnemyProjectile>();
        GetTree().CurrentScene.AddChild(projectile);
        projectile.GlobalPosition = shootPoint.GlobalPosition;
        projectile.Initialize(direction, ProjectileSpeed, this);

        if (DebugPrintEnemyEvents)
        {
            GD.Print($"{Name} fired at player.");
        }
    }

    private Node3D FindPlayer()
    {
        Node3D player = GetNodeOrNull<Node3D>(PlayerPath);
        if (player != null)
        {
            return player;
        }

        player = GetTree().GetFirstNodeInGroup("player") as Node3D;
        if (player != null)
        {
            return player;
        }

        return FindFirstDescendant<PlayerController>(GetTree().CurrentScene);
    }

    private static T FindFirstDescendant<T>(Node root) where T : Node
    {
        if (root == null)
        {
            return null;
        }

        if (root is T match)
        {
            return match;
        }

        foreach (Node child in root.GetChildren())
        {
            T nestedMatch = FindFirstDescendant<T>(child);
            if (nestedMatch != null)
            {
                return nestedMatch;
            }
        }

        return null;
    }

    private void Die()
    {
        _isDead = true;
        CanShoot = false;

        if (DebugPrintEnemyEvents)
        {
            GD.Print($"{Name} died.");
        }

        if (DestroyOnDeath)
        {
            QueueFree();
            return;
        }

        CollisionLayer = 0;
        CollisionMask = 0;
        SetPhysicsProcess(false);
    }
}
