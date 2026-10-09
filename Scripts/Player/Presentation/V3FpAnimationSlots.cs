using Godot;

[GlobalClass]
public partial class V3FpAnimationSlots : Resource
{
    [ExportGroup("Locomotion")]
    [Export] public StringName Idle { get; set; } = "FP_IDLE";
    [Export] public StringName Run { get; set; } = "FP_RUN";
    [Export] public StringName Slide { get; set; } = "FP_SLIDE";
    [Export] public StringName WallrunLeft { get; set; } = "FP_WALLRUN_LEFT";
    [Export] public StringName WallrunRight { get; set; } = "FP_WALLRUN_RIGHT";
    [ExportGroup("Combat")]
    [Export] public StringName Anticipation { get; set; } = "FP_RMB_ANTICIPATION";
    [Export] public StringName Melee { get; set; } = "FP_MELEE";
    [Export] public StringName Parry { get; set; } = "FP_PARRY";
    [ExportGroup("Bow")]
    [Export] public StringName BowReady { get; set; } = "FP_BOW_READY";
    [Export] public StringName BowDrawStart { get; set; } = "FP_BOW_DRAW_START";
    [Export] public StringName BowFullDraw { get; set; } = "FP_BOW_FULL_DRAW";
    [Export] public StringName BowRelease { get; set; } = "FP_BOW_RELEASE";
    [Export] public StringName BowFollowThrough { get; set; } = "FP_BOW_FOLLOW_THROUGH";
    [Export] public StringName BowRecovery { get; set; } = "FP_BOW_RECOVERY";
    [ExportGroup("Placeholder")]
    [Export] public StringName FallbackClip { get; set; } = "BH01_IDLE";
}
