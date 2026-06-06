using Godot;

public partial class GrappleAnchor : Area3D
{
    /// <summary>
    /// Имя группы, по которой PlayerSlingshotGrappleModule распознаёт специальные точки зацепа.
    /// </summary>
    [ExportGroup("Grapple Anchor")]
    [Export] public string AnchorGroupName { get; set; } = "grapple_anchor";

    /// <summary>
    /// Радиус служебного Area3D-коллайдера, по которому raycast камеры может попасть в точку зацепа.
    /// </summary>
    [Export(PropertyHint.Range, "0.05,3,0.05,suffix:m")] public float DetectionRadius { get; set; } = 0.6f;

    /// <summary>
    /// Включает простую видимую debug-сферу, чтобы точку зацепа было легко найти в прототипной сцене.
    /// </summary>
    [Export] public bool CreateDebugVisual { get; set; } = true;

    /// <summary>
    /// Радиус видимой debug-сферы. Не влияет на gameplay-радиус обнаружения.
    /// </summary>
    [Export(PropertyHint.Range, "0.05,1,0.05,suffix:m")] public float DebugVisualRadius { get; set; } = 0.25f;

    /// <summary>
    /// Цвет debug-сферы, создаваемой для прототипной визуализации точки зацепа.
    /// </summary>
    [Export] public Color DebugVisualColor { get; set; } = new(0.1f, 0.85f, 1.0f, 0.9f);

    /// <summary>
    /// Гарантирует, что anchor состоит в группе, имеет Area3D-коллайдер и, при необходимости, видимую debug-сферу.
    /// </summary>
    public override void _Ready()
    {
        if (!string.IsNullOrWhiteSpace(AnchorGroupName))
        {
            AddToGroup(AnchorGroupName);
        }

        EnsureCollisionShape();

        if (CreateDebugVisual)
        {
            EnsureDebugVisual();
        }
    }

    private void EnsureCollisionShape()
    {
        foreach (Node child in GetChildren())
        {
            if (child is CollisionShape3D)
            {
                return;
            }
        }

        CollisionShape3D collisionShape = new()
        {
            Name = "DetectionShape",
            Shape = new SphereShape3D
            {
                Radius = DetectionRadius
            }
        };

        AddChild(collisionShape);
    }

    private void EnsureDebugVisual()
    {
        foreach (Node child in GetChildren())
        {
            if (child.Name == "DebugVisual")
            {
                return;
            }
        }

        StandardMaterial3D material = new()
        {
            AlbedoColor = DebugVisualColor,
            EmissionEnabled = true,
            Emission = DebugVisualColor,
            Roughness = 0.35f,
            Transparency = BaseMaterial3D.TransparencyEnum.Alpha
        };

        MeshInstance3D debugVisual = new()
        {
            Name = "DebugVisual",
            Mesh = new SphereMesh
            {
                Radius = DebugVisualRadius,
                Height = DebugVisualRadius * 2.0f,
                RadialSegments = 16,
                Rings = 8
            },
            MaterialOverride = material,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off
        };

        AddChild(debugVisual);
    }
}
