using Godot;

public partial class ArrowProjectile : Area3D
{
    /// <summary>
    /// Скорость полёта стрелы по направлению движения. Увеличение делает стрелу быстрее и прямее по ощущению; уменьшение делает полёт медленнее.
    /// </summary>
    [ExportGroup("Полёт")]
    [Export(PropertyHint.Range, "0,120,0.5,suffix:m/s")] public float Speed { get; set; } = 24.0f;

    /// <summary>
    /// Поворачивать визуал стрелы по направлению полёта. Если выключить, стрела будет лететь без автоматического выравнивания ориентации.
    /// </summary>
    [Export] public bool AlignToVelocity { get; set; } = true;

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
    /// Максимальное время жизни стрелы до автоудаления. Увеличение позволяет стреле существовать дольше; уменьшение быстрее очищает сцену.
    /// </summary>
    [ExportGroup("Жизненный цикл")]
    [Export(PropertyHint.Range, "0.1,30,0.1,suffix:s")] public float Lifetime { get; set; } = 5.0f;

    private Vector3 _direction = Vector3.Forward;
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
            _direction = -GlobalTransform.Basis.Z.Normalized();
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

        Vector3 startPosition = GlobalPosition;
        Vector3 nextPosition = startPosition + _direction * Speed * deltaTime;

        if (TrySweepHit(startPosition, nextPosition))
        {
            return;
        }

        GlobalPosition = nextPosition;
        _lifetimeRemaining -= deltaTime;

        if (AlignToVelocity)
        {
            AlignWithDirection();
        }

        if (_lifetimeRemaining <= 0.0f)
        {
            QueueFree();
        }
    }

    public void Initialize(Vector3 direction, float speed, float damage, float lifetime)
    {
        _direction = direction.Normalized();
        Speed = speed;
        Damage = damage;
        Lifetime = lifetime;
        _lifetimeRemaining = lifetime;
        _wasInitialized = true;

        if (AlignToVelocity)
        {
            AlignWithDirection();
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

    private void AlignWithDirection()
    {
        if (_direction.LengthSquared() <= 0.0001f)
        {
            return;
        }

        LookAt(GlobalPosition + _direction, Vector3.Up);
    }
}
