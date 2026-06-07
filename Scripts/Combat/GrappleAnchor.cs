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
    /// Путь к жёлтой debug-сфере доступности grapple. Если путь пустой или неверный, anchor попробует найти узел AvailableHighlightSphere.
    /// </summary>
    [ExportGroup("Available Highlight")]
    [Export] public NodePath HighlightSpherePath { get; set; } = new("AvailableHighlightSphere");

    /// <summary>
    /// Включает debug-highlight доступности anchor. Если выключить, SetGrappleAvailableHighlight не будет показывать сферу.
    /// </summary>
    [Export] public bool EnableDebugHighlight { get; set; } = true;

    /// <summary>
    /// Цвет сферы доступности. Более яркий цвет проще заметить; более тёмный меньше отвлекает от сцены.
    /// </summary>
    [Export] public Color AvailableHighlightColor { get; set; } = Colors.Yellow;

    /// <summary>
    /// Множитель масштаба сферы доступности относительно обычной debug-сферы. Увеличение делает highlight заметнее; уменьшение ближе к размеру anchor.
    /// </summary>
    [Export(PropertyHint.Range, "0.5,4,0.05")] public float HighlightScaleMultiplier { get; set; } = 1.25f;

    private MeshInstance3D _highlightSphere;
    private StandardMaterial3D _highlightMaterial;

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

        EnsureHighlightSphere();
        SetGrappleAvailableHighlight(false);
    }

    /// <summary>
    /// Показывает или скрывает debug-сферу доступности grapple. Видимость означает, что игрок прямо сейчас может зацепиться за этот anchor.
    /// </summary>
    public void SetGrappleAvailableHighlight(bool isVisible)
    {
        SetGrappleAvailableHighlight(isVisible, AvailableHighlightColor);
    }

    /// <summary>
    /// Показывает или скрывает debug-сферу доступности grapple с указанным цветом. Цвет позволяет временно отличать разные состояния отладки.
    /// </summary>
    public void SetGrappleAvailableHighlight(bool isVisible, Color color)
    {
        if (!EnableDebugHighlight)
        {
            isVisible = false;
        }

        if (_highlightSphere == null)
        {
            EnsureHighlightSphere();
        }

        if (_highlightSphere == null)
        {
            return;
        }

        _highlightSphere.Visible = isVisible;
        if (_highlightMaterial != null)
        {
            _highlightMaterial.AlbedoColor = color;
            _highlightMaterial.Emission = color;
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

    private void EnsureHighlightSphere()
    {
        _highlightSphere = GetNodeOrNull<MeshInstance3D>(HighlightSpherePath) ?? FindHighlightSphere();
        if (_highlightSphere == null)
        {
            return;
        }

        _highlightSphere.Visible = false;
        _highlightSphere.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        _highlightSphere.Scale = Vector3.One * HighlightScaleMultiplier;

        Material material = _highlightSphere.MaterialOverride ?? (_highlightSphere.Mesh?.SurfaceGetMaterial(0));
        if (material is StandardMaterial3D standardMaterial)
        {
            _highlightMaterial = standardMaterial.Duplicate() as StandardMaterial3D;
        }
        else
        {
            _highlightMaterial = new StandardMaterial3D();
        }

        _highlightMaterial.ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded;
        _highlightMaterial.AlbedoColor = AvailableHighlightColor;
        _highlightMaterial.EmissionEnabled = true;
        _highlightMaterial.Emission = AvailableHighlightColor;
        _highlightMaterial.Transparency = BaseMaterial3D.TransparencyEnum.Alpha;
        _highlightSphere.MaterialOverride = _highlightMaterial;
    }

    private MeshInstance3D FindHighlightSphere()
    {
        foreach (Node child in GetChildren())
        {
            if (child is MeshInstance3D meshInstance && child.Name == "AvailableHighlightSphere")
            {
                return meshInstance;
            }
        }

        return null;
    }
}
