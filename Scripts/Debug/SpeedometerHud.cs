using System.Globalization;
using Godot;

public partial class SpeedometerHud : Label
{
    [Export] public NodePath PlayerPath { get; set; } = new("");
    [Export] public string PlayerGroupName { get; set; } = "player";
    [Export(PropertyHint.Range, "0,200,1,suffix:px")] public float BottomOffset { get; set; } = 48.0f;
    [Export(PropertyHint.Range, "80,320,1,suffix:px")] public float Width { get; set; } = 160.0f;
    [Export(PropertyHint.Range, "16,80,1,suffix:px")] public float Height { get; set; } = 28.0f;

    private CharacterBody3D _player;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore;
        HorizontalAlignment = HorizontalAlignment.Center;
        VerticalAlignment = VerticalAlignment.Center;
        AddThemeColorOverride("font_color", Colors.White);
        AddThemeColorOverride("font_outline_color", Colors.Black);
        AddThemeConstantOverride("outline_size", 4);

        ConfigureLayout();
        ResolvePlayer();
        UpdateText();
    }

    public override void _Process(double delta)
    {
        if (_player == null || !IsInstanceValid(_player))
        {
            ResolvePlayer();
        }

        ConfigureLayout();
        UpdateText();
    }

    private void ConfigureLayout()
    {
        float halfWidth = Mathf.Max(1.0f, Width) * 0.5f;
        float height = Mathf.Max(1.0f, Height);
        float bottomOffset = Mathf.Max(0.0f, BottomOffset);

        AnchorLeft = 0.5f;
        AnchorRight = 0.5f;
        AnchorTop = 1.0f;
        AnchorBottom = 1.0f;
        OffsetLeft = -halfWidth;
        OffsetRight = halfWidth;
        OffsetTop = -bottomOffset - height;
        OffsetBottom = -bottomOffset;
    }

    private void ResolvePlayer()
    {
        if (!PlayerPath.IsEmpty)
        {
            _player = GetNodeOrNull<CharacterBody3D>(PlayerPath);
            if (_player != null)
            {
                return;
            }
        }

        _player = GetTree()?.GetFirstNodeInGroup(PlayerGroupName) as CharacterBody3D;
    }

    private void UpdateText()
    {
        Vector3 velocity = _player?.Velocity ?? Vector3.Zero;
        float horizontalSpeed = new Vector2(velocity.X, velocity.Z).Length();
        Text = $"{horizontalSpeed.ToString("0.0", CultureInfo.InvariantCulture)} m/s";
    }
}
