using Godot;

// Level-local prototype start. Recovery remains the existing scene reload contract.
public partial class Level01CombatDraft : Node3D
{
    [Export] public bool StartAtCombatSpawn { get; set; } = true;
    [Export] public NodePath PlayerPath { get; set; } = new("../Player");

    public override async void _Ready()
    {
        // The original marker binder finishes first; its original spawn is preserved.
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (!IsInsideTree() || !StartAtCombatSpawn) return;
        var player = GetNodeOrNull<Node3D>(PlayerPath);
        var spawn = GetNode<Node3D>("CombatSpawn");
        if (player == null) return;
        player.GlobalTransform = spawn.GlobalTransform;
        player.ResetPhysicsInterpolation();
        GD.Print("COMBAT_DRAFT_READY enemies=8 recovery=scene_reload input=real");
    }
}
