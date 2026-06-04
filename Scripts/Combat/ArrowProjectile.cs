using Godot;

public partial class ArrowProjectile : Area3D
{
    [Export] public float Speed { get; set; } = 24.0f;
    [Export] public float Damage { get; set; } = 8.0f;
    [Export] public float Lifetime { get; set; } = 5.0f;
    [Export] public bool DestroyOnHit { get; set; } = true;
    [Export] public float HitStickTime { get; set; } = 0.3f;
    [Export] public bool AlignToVelocity { get; set; } = true;

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

        GlobalPosition += _direction * Speed * deltaTime;
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
        HandleHit();
    }

    private void OnAreaEntered(Area3D area)
    {
        HandleHit();
    }

    private void HandleHit()
    {
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

    private void AlignWithDirection()
    {
        if (_direction.LengthSquared() <= 0.0001f)
        {
            return;
        }

        LookAt(GlobalPosition + _direction, Vector3.Up);
    }
}
