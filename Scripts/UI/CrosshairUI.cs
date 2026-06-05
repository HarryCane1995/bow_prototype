using Godot;

public partial class CrosshairUI : Control
{
    /// <summary>
    /// Длина каждого луча прицела в пикселях. Увеличение делает прицел крупнее; уменьшение делает линии короче и менее заметными.
    /// </summary>
    [ExportGroup("Прицел")]
    [Export(PropertyHint.Range, "0,64,1,suffix:px")] public float LineLength { get; set; } = 12.0f;

    /// <summary>
    /// Толщина линий прицела в пикселях. Увеличение делает прицел жирнее; уменьшение делает его тоньше.
    /// </summary>
    [Export(PropertyHint.Range, "1,16,1,suffix:px")] public float LineThickness { get; set; } = 2.0f;

    /// <summary>
    /// Отступ между центром экрана и линиями прицела в пикселях. Увеличение расширяет прицел; уменьшение собирает линии ближе к центру.
    /// </summary>
    [Export(PropertyHint.Range, "0,64,1,suffix:px")] public float Gap { get; set; } = 5.0f;

    /// <summary>
    /// Цвет линий прицела. Более контрастный цвет улучшает читаемость на dev-texture/grid; более мягкий цвет меньше отвлекает.
    /// </summary>
    [Export] public Color CrosshairColor { get; set; } = Colors.White;

    /// <summary>
    /// Показывать прицел на экране. Если выключить, UI-прицел будет скрыт без удаления нод линий.
    /// </summary>
    [Export] public bool ShowCrosshair { get; set; } = true;

    private ColorRect _horizontalLineLeft;
    private ColorRect _horizontalLineRight;
    private ColorRect _verticalLineTop;
    private ColorRect _verticalLineBottom;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore;
        SetFullRect();

        _horizontalLineLeft = GetOrCreateLine("HorizontalLineLeft");
        _horizontalLineRight = GetOrCreateLine("HorizontalLineRight");
        _verticalLineTop = GetOrCreateLine("VerticalLineTop");
        _verticalLineBottom = GetOrCreateLine("VerticalLineBottom");

        UpdateCrosshair();
    }

    public override void _Process(double delta)
    {
        UpdateCrosshair();
    }

    private ColorRect GetOrCreateLine(string nodeName)
    {
        ColorRect line = GetNodeOrNull<ColorRect>(nodeName);
        if (line != null)
        {
            line.MouseFilter = MouseFilterEnum.Ignore;
            return line;
        }

        line = new ColorRect
        {
            Name = nodeName,
            MouseFilter = MouseFilterEnum.Ignore
        };
        AddChild(line);
        return line;
    }

    private void UpdateCrosshair()
    {
        SetFullRect();
        Visible = ShowCrosshair;

        float length = Mathf.Max(0.0f, LineLength);
        float thickness = Mathf.Max(1.0f, LineThickness);
        float gap = Mathf.Max(0.0f, Gap);
        Vector2 center = Size * 0.5f;

        ConfigureLine(_horizontalLineLeft, new Vector2(length, thickness), center + new Vector2(-gap - length, -thickness * 0.5f));
        ConfigureLine(_horizontalLineRight, new Vector2(length, thickness), center + new Vector2(gap, -thickness * 0.5f));
        ConfigureLine(_verticalLineTop, new Vector2(thickness, length), center + new Vector2(-thickness * 0.5f, -gap - length));
        ConfigureLine(_verticalLineBottom, new Vector2(thickness, length), center + new Vector2(-thickness * 0.5f, gap));
    }

    private void ConfigureLine(ColorRect line, Vector2 size, Vector2 position)
    {
        line.Color = CrosshairColor;
        line.Size = size;
        line.Position = position;
        line.Visible = ShowCrosshair;
    }

    private void SetFullRect()
    {
        AnchorLeft = 0.0f;
        AnchorTop = 0.0f;
        AnchorRight = 1.0f;
        AnchorBottom = 1.0f;
        OffsetLeft = 0.0f;
        OffsetTop = 0.0f;
        OffsetRight = 0.0f;
        OffsetBottom = 0.0f;
    }
}
