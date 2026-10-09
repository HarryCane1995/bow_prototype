using Godot;

// Clip names live in one resource. Missing/unexported slots never block combat.
[GlobalClass]
public partial class RmbCombatAnimationSlots : Resource
{
    [ExportGroup("Melee / Parry")]
    [Export] public StringName Anticipation { get; set; } = "BH01_RMB_ANTICIPATION";
    [Export] public StringName Melee { get; set; } = "BH01_MELEE";
    [Export] public StringName ParrySuccess { get; set; } = "BH01_PARRY";
    [Export] public StringName MeleeRecovery { get; set; } = "BH01_MELEE_RECOVERY";

    [ExportGroup("Existing Bow Actions")]
    [Export] public StringName BowReady { get; set; } = "BH01_BOW_READY";
    [Export] public StringName BowDrawStart { get; set; } = "BH01_BOW_DRAW_START";
    [Export] public StringName BowFullDraw { get; set; } = "BH01_BOW_FULL_DRAW";
    [Export] public StringName BowRelease { get; set; } = "BH01_BOW_RELEASE";
    [Export] public StringName BowFollowThrough { get; set; } = "BH01_BOW_FOLLOW_THROUGH";
    [Export] public StringName BowRecovery { get; set; } = "BH01_BOW_RECOVERY";
}
