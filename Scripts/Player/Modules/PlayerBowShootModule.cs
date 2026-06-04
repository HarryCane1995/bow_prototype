using Godot;

public partial class PlayerBowShootModule : Node
{
    [Export] public PackedScene ArrowProjectileScene { get; set; }
    [Export] public NodePath CameraPath { get; set; } = new("../CameraPivot/Camera3D");
    [Export] public NodePath ShootPointPath { get; set; } = new("../CameraPivot/Camera3D/ShootPoint");
    [Export] public float LightShotSpeed { get; set; } = 24.0f;
    [Export] public float ChargedShotSpeed { get; set; } = 46.0f;
    [Export] public float LightShotDamage { get; set; } = 8.0f;
    [Export] public float ChargedShotDamage { get; set; } = 24.0f;
    [Export] public float ChargeTime { get; set; } = 0.8f;
    [Export] public float FireCooldown { get; set; } = 0.2f;
    [Export] public float ProjectileLifetime { get; set; } = 5.0f;
    [Export] public float SpawnForwardOffset { get; set; } = 0.35f;

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
