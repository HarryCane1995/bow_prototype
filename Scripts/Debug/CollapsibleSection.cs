using Godot;

public partial class CollapsibleSection : VBoxContainer
{
    public event System.Action<bool> ExpandedChanged;

    public Button HeaderButton { get; private set; }
    public VBoxContainer Content { get; private set; }
    public string SectionTitle { get; private set; } = string.Empty;
    public bool Expanded { get; private set; }

    public void Initialize(string title, bool expanded)
    {
        SectionTitle = title;
        SizeFlagsHorizontal = Control.SizeFlags.ExpandFill;

        HeaderButton = new Button
        {
            Name = "Header",
            Alignment = HorizontalAlignment.Left,
            CustomMinimumSize = new Vector2(0.0f, 34.0f),
            FocusMode = FocusModeEnum.All,
            MouseDefaultCursorShape = CursorShape.PointingHand,
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };
        HeaderButton.Pressed += ToggleExpanded;

        MarginContainer contentMargin = new()
        {
            Name = "ContentMargin",
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };
        contentMargin.AddThemeConstantOverride("margin_left", 12);
        contentMargin.AddThemeConstantOverride("margin_right", 4);
        contentMargin.AddThemeConstantOverride("margin_top", 4);
        contentMargin.AddThemeConstantOverride("margin_bottom", 8);

        Content = new VBoxContainer
        {
            Name = "Content",
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };

        contentMargin.AddChild(Content);
        AddChild(HeaderButton);
        AddChild(contentMargin);

        Expanded = expanded;
        contentMargin.Visible = expanded;
        UpdateHeaderText();
    }

    public void SetExpanded(bool expanded)
    {
        if (Expanded == expanded)
        {
            return;
        }

        Expanded = expanded;
        GetNode<MarginContainer>("ContentMargin").Visible = expanded;
        UpdateHeaderText();
        ExpandedChanged?.Invoke(expanded);
    }

    private void ToggleExpanded()
    {
        SetExpanded(!Expanded);
    }

    private void UpdateHeaderText()
    {
        HeaderButton.Text = $"{(Expanded ? "▼" : "▶")} {SectionTitle}";
        HeaderButton.TooltipText = Expanded ? $"Collapse {SectionTitle}" : $"Expand {SectionTitle}";
    }
}
