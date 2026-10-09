using Godot;

[GlobalClass]
public partial class SplitAnimationSlots : Resource
{
    [Export] public Godot.Collections.Dictionary<PresentationState, StringName> Clips { get; set; } = new();
    [Export] public StringName Fallback { get; set; }
    public StringName Resolve(PresentationState state, AnimationPlayer player)
        => Clips.TryGetValue(state, out var clip) && player.HasAnimation(clip) ? clip : Fallback;
}
