using Godot;

public partial class TargetHitbox : Area3D
{
    [Export] public NodePath TargetMeshPath { get; set; } = new("");
    [Export] public bool FlashOnHit { get; set; } = true;
    [Export] public Color HitColor { get; set; } = new(1.0f, 0.85f, 0.15f, 1.0f);
    [Export] public float FlashDuration { get; set; } = 0.12f;

    private MeshInstance3D _targetMesh;
    private StandardMaterial3D _runtimeMaterial;
    private Color _defaultColor;
    private float _flashTimeRemaining;

    public override void _Ready()
    {
        _targetMesh = GetNodeOrNull<MeshInstance3D>(TargetMeshPath);

        if (_targetMesh == null)
        {
            return;
        }

        Material material = _targetMesh.GetSurfaceOverrideMaterial(0) ?? _targetMesh.Mesh?.SurfaceGetMaterial(0);
        _runtimeMaterial = material?.Duplicate() as StandardMaterial3D ?? new StandardMaterial3D();
        _defaultColor = _runtimeMaterial.AlbedoColor;
        _targetMesh.SetSurfaceOverrideMaterial(0, _runtimeMaterial);
    }

    public override void _Process(double delta)
    {
        if (_runtimeMaterial == null || _flashTimeRemaining <= 0.0f)
        {
            return;
        }

        _flashTimeRemaining -= (float)delta;
        if (_flashTimeRemaining <= 0.0f)
        {
            _runtimeMaterial.AlbedoColor = _defaultColor;
        }
    }

    public void OnHit(float damage)
    {
        GD.Print("Target hit");

        if (!FlashOnHit || _runtimeMaterial == null)
        {
            return;
        }

        _runtimeMaterial.AlbedoColor = HitColor;
        _flashTimeRemaining = FlashDuration;
    }
}
