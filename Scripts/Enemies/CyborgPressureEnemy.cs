using Godot;

// Stationary pressure proxy: no navigation or predictive aim.
public partial class CyborgPressureEnemy : StaticBody3D, IDamageable
{
    [ExportGroup("Scene Links")]
    [Export] public PackedScene ProjectileScene { get; set; }
    [Export] public NodePath MuzzlePath { get; set; } = new("Muzzle");
    [Export] public NodePath SensorPath { get; set; } = new("Sensor");
    [Export] public NodePath FlashPath { get; set; } = new("Muzzle/Flash");

    [ExportGroup("Pressure")]
    [Export(PropertyHint.Range, "5,80,1,suffix:m")] public float DetectionRange { get; set; } = 34;
    [Export(PropertyHint.Range, "0.8,5,0.05,suffix:s")] public float FireInterval { get; set; } = 1.4f;
    [Export(PropertyHint.Range, "0.1,0.8,0.01,suffix:s")] public float ChargeSeconds { get; set; } = 0.25f;
    [Export(PropertyHint.Range, "0,4,0.05,suffix:s")] public float InitialDelay { get; set; } = 0.7f;
    [Export(PropertyHint.Range, "5,30,0.5,suffix:m/s")] public float ProjectileSpeed { get; set; } = 12;
    [Export(PropertyHint.Layers3DPhysics)] public uint SightMask { get; set; } = 1;
    [Export] public bool CanShoot { get; set; } = true;

    [ExportGroup("Health")]
    [Export(PropertyHint.Range, "1,200,1")] public int MaxHealth { get; set; } = 8;

    [ExportGroup("Death VFX")]
    [Export] public PackedScene DeathEffectScene { get; set; }
    [Export(PropertyHint.Range, "0.1,4,0.05")] public float DeathEffectScale { get; set; } = 1.0f;
    [Export] public Vector3 DeathEffectOffset { get; set; } = Vector3.Zero;

    public int CurrentHealth { get; private set; }
    public bool IsDead { get; private set; }
    public bool PlayerVisible { get; private set; }
    public int ShotsFired { get; private set; }
    public Vector3 LastShotOrigin { get; private set; }
    public Vector3 LastShotTarget { get; private set; }

    private PlayerController _player;
    private CollisionShape3D _playerShape;
    private Node3D _muzzle;
    private Node3D _flash;
    private StandardMaterial3D _sensorMaterial;
    private float _cooldown;
    private float _charge = -1;
    private float _flashRemaining;

    public override void _Ready()
    {
        AddToGroup("enemy");
        _muzzle = GetNode<Node3D>(MuzzlePath);
        _flash = GetNode<Node3D>(FlashPath);
        var sensor = GetNode<MeshInstance3D>(SensorPath);
        // Each proxy owns its charge feedback; the shared scene material stays immutable.
        _sensorMaterial = (StandardMaterial3D)sensor.GetActiveMaterial(0).Duplicate();
        sensor.MaterialOverride = _sensorMaterial;
        _cooldown = InitialDelay;
        CurrentHealth = Mathf.Max(1, MaxHealth);
    }

    public override void _PhysicsProcess(double delta)
    {
        if (IsDead) return;
        float dt = (float)delta;
        _cooldown = Mathf.Max(0, _cooldown - dt);
        _flashRemaining = Mathf.Max(0, _flashRemaining - dt);
        _flash.Visible = _flashRemaining > 0;
        if (!GodotObject.IsInstanceValid(_player))
        {
            _player = GetTree().GetFirstNodeInGroup("player") as PlayerController;
            _playerShape = _player?.GetNodeOrNull<CollisionShape3D>("CollisionShape3D");
        }
        PlayerVisible = false;
        if (_player != null)
        {
            var facing = _player.GlobalPosition;
            facing.Y = GlobalPosition.Y;
            if (GlobalPosition.DistanceSquaredTo(facing) > 0.01f) LookAt(facing);
            PlayerVisible = HasLineOfSight(AimPoint());
        }
        if (!CanShoot || !PlayerVisible || ProjectileScene == null)
        {
            _charge = -1;
            _sensorMaterial.EmissionEnergyMultiplier = 0.65f;
            return;
        }
        if (_cooldown > 0) return;
        if (_charge < 0) _charge = Mathf.Max(0.1f, ChargeSeconds);
        _charge -= dt;
        _sensorMaterial.EmissionEnergyMultiplier = Mathf.Lerp(0.65f, 2.0f,
            1 - Mathf.Clamp(_charge / Mathf.Max(ChargeSeconds, 0.1f), 0, 1));
        if (_charge > 0) return;

        // Aim and LOS are sampled again at release, not predicted or updated in flight.
        Vector3 target = AimPoint();
        if (HasLineOfSight(target))
        {
            var projectile = ProjectileScene.Instantiate<EnemyProjectile>();
            GetTree().CurrentScene.AddChild(projectile);
            projectile.GlobalPosition = _muzzle.GlobalPosition;
            projectile.Initialize(target - _muzzle.GlobalPosition, ProjectileSpeed, this);
            projectile.ResetPhysicsInterpolation();
            LastShotOrigin = _muzzle.GlobalPosition;
            LastShotTarget = target;
            ShotsFired++;
            _flashRemaining = 0.075f;
            _flash.Visible = true;
        }
        _sensorMaterial.EmissionEnergyMultiplier = 0.65f;
        _cooldown = Mathf.Max(0.1f, FireInterval - ChargeSeconds);
        _charge = -1;
    }

    public void ApplyDamage(int amount)
    {
        if (IsDead || amount <= 0) return;
        CurrentHealth = Mathf.Max(0, CurrentHealth - amount);
        if (CurrentHealth > 0) return;

        IsDead = true;
        CanShoot = false;
        PlayerVisible = false;
        Hide();
        SetPhysicsProcess(false);
        // Arrow overlap callbacks can arrive during a physics query flush.
        Callable.From(FinishDeath).CallDeferred();
    }

    private void FinishDeath()
    {
        CollisionLayer = 0;
        CollisionMask = 0;
        if (DeathEffectScene != null)
        {
            var effect = DeathEffectScene.Instantiate<Node3D>();
            effect.Set("autoplay", true);
            effect.Set("loop", false);
            effect.Connect("finished", Callable.From(effect.QueueFree), (uint)ConnectFlags.OneShot);
            // Keep the ground ring upright and let the effect outlive the enemy.
            Node parent = GetTree().CurrentScene ?? (Node)GetTree().Root;
            parent.AddChild(effect);
            effect.GlobalTransform = new Transform3D(
                Basis.Identity.Scaled(Vector3.One * Mathf.Max(0.1f, DeathEffectScale)),
                ToGlobal(DeathEffectOffset));
            effect.ResetPhysicsInterpolation();
        }
        QueueFree();
    }

    private Vector3 AimPoint()
    {
        // A point just below the actual capsule top makes low cover posture-sensitive.
        // It follows crouch/slide collision shape, not camera shake or screen visibility.
        if (_playerShape?.Shape is CapsuleShape3D capsule)
            return _playerShape.GlobalTransform * (Vector3.Up * (capsule.Height * 0.5f - 0.16f));
        return _player.GlobalPosition + Vector3.Up;
    }

    private bool HasLineOfSight(Vector3 target)
    {
        if (_muzzle.GlobalPosition.DistanceSquaredTo(target) > DetectionRange * DetectionRange) return false;
        var query = PhysicsRayQueryParameters3D.Create(_muzzle.GlobalPosition, target, SightMask);
        query.Exclude = new Godot.Collections.Array<Rid> { GetRid() };
        query.CollideWithAreas = false;
        query.HitFromInside = true;
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(query);
        // Require the actual player collider; an empty ray is not visibility proof.
        return hit.Count > 0 && hit["collider"].AsGodotObject() == _player;
    }
}
