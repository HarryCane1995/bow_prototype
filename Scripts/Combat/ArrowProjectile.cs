using Godot;

public enum ArrowFlightMode
{
    Ballistic,
    Straight
}

public partial class ArrowProjectile : Area3D
{
    /// <summary>
    /// Скорость полёта стрелы по направлению движения. Увеличение делает стрелу быстрее и прямее по ощущению; уменьшение делает полёт медленнее.
    /// </summary>
    [ExportGroup("Полёт")]
    [Export(PropertyHint.Range, "0,200,0.5,suffix:m/s")] public float Speed { get; set; } = 50.0f;

    /// <summary>
    /// Ручная гравитация projectile-стрелы. Увеличение делает дугу падения заметнее и короче; уменьшение делает траекторию прямее.
    /// </summary>
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s^2")] public float ProjectileGravity { get; set; } = 18.0f;

    /// <summary>
    /// Режим полёта стрелы. Ballistic применяет gravity и даёт дугу; Straight сохраняет velocity без падения для precision shot.
    /// </summary>
    [Export] public ArrowFlightMode FlightMode { get; set; } = ArrowFlightMode.Ballistic;

    /// <summary>
    /// Поворачивать визуал стрелы по направлению полёта. Если выключить, стрела будет лететь без автоматического выравнивания ориентации.
    /// </summary>
    [Export] public bool AlignToVelocity { get; set; } = true;

    /// <summary>
    /// Дополнительный локальный поворот модели после выравнивания по velocity. Используется, если импортированная модель стрелы смотрит не вдоль стандартной оси; изменение позволяет исправить ориентацию из Inspector.
    /// </summary>
    [Export] public Vector3 RotationOffsetDegrees { get; set; } = Vector3.Zero;

    /// <summary>
    /// Удалять стрелу сразу при попадании. Если выключить, стрела остановится и проживёт HitStickTime перед удалением.
    /// </summary>
    [ExportGroup("Попадание")]
    [Export] public bool DestroyOnHit { get; set; } = true;

    /// <summary>
    /// Сколько секунд остановленная стрела остаётся на месте после попадания, если DestroyOnHit выключен. Увеличение дольше показывает попадание; уменьшение быстрее удаляет стрелу.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.1,suffix:s")] public float HitStickTime { get; set; } = 0.3f;

    /// <summary>
    /// Урон, передаваемый TargetHitbox при попадании. Увеличение усиливает стрелу; уменьшение делает попадание слабее.
    /// </summary>
    [Export(PropertyHint.Range, "0,200,1")] public float Damage { get; set; } = 8.0f;

    /// <summary>
    /// Помечает стрелу как бронебойную. Сейчас это метка для precision shot и будущей логики брони; включение не меняет движение projectile.
    /// </summary>
    [Export] public bool ArmorPiercing { get; set; } = false;

    /// <summary>
    /// Максимальное время жизни стрелы до автоудаления. Увеличение позволяет стреле существовать дольше; уменьшение быстрее очищает сцену.
    /// </summary>
    [ExportGroup("Жизненный цикл")]
    [Export(PropertyHint.Range, "0.1,30,0.1,suffix:s")] public float Lifetime { get; set; } = 5.0f;

    private Vector3 _velocity = Vector3.Forward;
    private bool _isStopped;
    private float _lifetimeRemaining;
    private float _stickTimeRemaining;
    private bool _wasInitialized;

    public override void _Ready()
    {
        BodyEntered += OnBodyEntered;
        AreaEntered += OnAreaEntered;

        if (!_wasInitialized)
        {
            _lifetimeRemaining = Lifetime;
            _velocity = -GlobalTransform.Basis.Z.Normalized() * Speed;
        }
    }

    public override void _PhysicsProcess(double delta)
    {
        float deltaTime = (float)delta;

        if (_isStopped)
        {
            _stickTimeRemaining -= deltaTime;
            if (_stickTimeRemaining <= 0.0f)
            {
                QueueFree();
            }

            return;
        }

        if (FlightMode == ArrowFlightMode.Ballistic)
        {
            _velocity += Vector3.Down * ProjectileGravity * deltaTime;
        }

        Vector3 startPosition = GlobalPosition;
        Vector3 nextPosition = startPosition + _velocity * deltaTime;
        if (TrySweepHit(startPosition, nextPosition))
        {
            return;
        }

        GlobalPosition = nextPosition;
        _lifetimeRemaining -= deltaTime;

        if (AlignToVelocity)
        {
            AlignWithVelocity();
        }

        if (_lifetimeRemaining <= 0.0f)
        {
            QueueFree();
        }
    }

    public void Initialize(Vector3 direction, float speed, float damage, float lifetime)
    {
        Initialize(direction, speed, damage, lifetime, FlightMode, ArmorPiercing);
    }

    public void Initialize(Vector3 direction, float speed, float damage, float lifetime, ArrowFlightMode flightMode, bool armorPiercing)
    {
        Speed = speed;
        Damage = damage;
        Lifetime = lifetime;
        FlightMode = flightMode;
        ArmorPiercing = armorPiercing;
        _lifetimeRemaining = lifetime;

        // Do not inherit shooter/player velocity: aim direction must fully define the initial projectile velocity.
        _velocity = direction.Normalized() * speed;
        _wasInitialized = true;

        if (AlignToVelocity)
        {
            AlignWithVelocity();
        }
    }

    private void OnBodyEntered(Node3D body)
    {
        HandleHit(body);
    }

    private void OnAreaEntered(Area3D area)
    {
        HandleHit(area);
    }

    private bool TrySweepHit(Vector3 from, Vector3 to)
    {
        PhysicsRayQueryParameters3D query = PhysicsRayQueryParameters3D.Create(from, to);
        query.CollideWithAreas = true;
        query.CollideWithBodies = true;
        query.CollisionMask = CollisionMask;
        query.Exclude = new Godot.Collections.Array<Rid> { GetRid() };

        Godot.Collections.Dictionary hit = GetWorld3D().DirectSpaceState.IntersectRay(query);
        if (hit.Count == 0)
        {
            return false;
        }

        GlobalPosition = hit["position"].AsVector3();
        if (AlignToVelocity)
        {
            AlignWithVelocity();
        }

        Node hitNode = hit["collider"].AsGodotObject() as Node;
        HandleHit(hitNode);
        return true;
    }

    private void HandleHit(Node hitNode)
    {
        if (_isStopped)
        {
            return;
        }

        TargetHitbox targetHitbox = FindTargetHitbox(hitNode);
        targetHitbox?.OnHit(Damage);

        if (DestroyOnHit)
        {
            QueueFree();
            return;
        }

        _isStopped = true;
        Monitoring = false;
        Monitorable = false;
        _stickTimeRemaining = HitStickTime;
    }

    private static TargetHitbox FindTargetHitbox(Node node)
    {
        Node current = node;
        while (current != null)
        {
            if (current is TargetHitbox targetHitbox)
            {
                return targetHitbox;
            }

            current = current.GetParent();
        }

        return null;
    }

    private void AlignWithVelocity()
    {
        if (_velocity.LengthSquared() <= 0.0001f)
        {
            return;
        }

        LookAt(GlobalPosition + _velocity.Normalized(), Vector3.Up);

        RotateObjectLocal(Vector3.Right, Mathf.DegToRad(RotationOffsetDegrees.X));
        RotateObjectLocal(Vector3.Up, Mathf.DegToRad(RotationOffsetDegrees.Y));
        RotateObjectLocal(Vector3.Back, Mathf.DegToRad(RotationOffsetDegrees.Z));
    }
}
