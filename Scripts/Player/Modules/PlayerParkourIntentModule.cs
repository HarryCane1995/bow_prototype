using Godot;

// Shared intent gate for contextual traversal. No physics or ability ownership.
public partial class PlayerParkourIntentModule : Node
{
    [ExportGroup("Input")]
    [Export] public StringName ParkourAction { get; set; } = "parkour_mode";

    public bool IsActive => Input.IsActionPressed(ParkourAction);
}
