using Godot;

public partial class EnemyProjectile : Area3D
{
    /// <summary>
    /// Скорость полёта enemy projectile. Увеличение делает выстрел быстрее и опаснее; уменьшение даёт игроку больше времени уклониться.
    /// </summary>
    [ExportGroup("Полёт")]
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s")] public float Speed { get; set; } = 16.0f;

    /// <summary>
    /// Время жизни projectile в секундах. Увеличение позволяет ему лететь дальше; уменьшение быстрее очищает сцену.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,20,0.1,suffix:s")] public float Lifetime { get; set; } = 5.0f;

    /// <summary>
    /// Перезагружать текущую сцену при попадании в игрока. Если выключить, projectile просто исчезает при контакте с игроком.
    /// </summary>
    [ExportGroup("Попадание")]
    [Export] public bool ReloadSceneOnPlayerHit { get; set; } = true;

    /// <summary>
    /// Имя группы игрока. Projectile считает попаданием в игрока объект из этой группы или объект с PlayerController.
    /// </summary>
    [Export] public string PlayerGroupName { get; set; } = "player";

    private Vector3 _velocity = Vector3.Forward;
    private float _lifetimeRemaining;
    private bool _wasInitialized;
    private Rid _ignoredBodyRid;

    public override void _Ready()
    {
        AddToGroup("enemy_projectile");
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
        Vector3 startPosition = GlobalPosition;
        Vector3 nextPosition = startPosition + _velocity * deltaTime;
        if (TrySweepHit(startPosition, nextPosition))
        {
            return;
        }

        GlobalPosition = nextPosition;
        _lifetimeRemaining -= deltaTime;

        if (_lifetimeRemaining <= 0.0f)
        {
            QueueFree();
        }
    }

    /// <summary>
    /// Запускает projectile в заданном направлении с заданной скоростью.
    /// </summary>
    public void Initialize(Vector3 direction, float speed)
    {
        Initialize(direction, speed, null);
    }

    /// <summary>
    /// Запускает projectile и исключает стрелявший объект из sweep-проверки, чтобы projectile не попадал в своего владельца при спавне.
    /// </summary>
    public void Initialize(Vector3 direction, float speed, Node3D shooter)
    {
        Speed = speed;
        _velocity = direction.Normalized() * speed;
        _lifetimeRemaining = Lifetime;
        _wasInitialized = true;
        _ignoredBodyRid = shooter is CollisionObject3D collisionObject ? collisionObject.GetRid() : default;

        if (_velocity.LengthSquared() > 0.0001f)
        {
            LookAt(GlobalPosition + _velocity.Normalized(), Vector3.Up);
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

    private void HandleHit(Node node)
    {
        if (node == null || node == this || IsEnemyNode(node))
        {
            return;
        }

        if (IsPlayerNode(node))
        {
            if (ReloadSceneOnPlayerHit)
            {
                GetTree().ReloadCurrentScene();
            }

            QueueFree();
            return;
        }

        QueueFree();
    }

    private bool TrySweepHit(Vector3 from, Vector3 to)
    {
        PhysicsRayQueryParameters3D query = PhysicsRayQueryParameters3D.Create(from, to);
        query.CollideWithAreas = true;
        query.CollideWithBodies = true;
        query.CollisionMask = CollisionMask;
        Godot.Collections.Array<Rid> excludedRids = new() { GetRid() };
        if (_ignoredBodyRid.IsValid)
        {
            excludedRids.Add(_ignoredBodyRid);
        }

        query.Exclude = excludedRids;

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

    private bool IsPlayerNode(Node node)
    {
        Node current = node;
        while (current != null)
        {
            if (current.IsInGroup(PlayerGroupName) || current is PlayerController)
            {
                return true;
            }

            current = current.GetParent();
        }

        return false;
    }

    private static bool IsEnemyNode(Node node)
    {
        Node current = node;
        while (current != null)
        {
            if (current.IsInGroup("enemy"))
            {
                return true;
            }

            current = current.GetParent();
        }

        return false;
    }
}
