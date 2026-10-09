using Godot;

// Populate the two explicit FP mesh slots by name, without baking generated GLB
// subresource IDs into a second asset. Runs in the editor as well as in the game.
[Tool]
public partial class FirstPersonBodySource : Node3D
{
    [Export] public PackedScene SourceScene { get; set; }

    public override void _Ready() => Populate(SourceScene);

    public void Populate(PackedScene sourceScene)
    {
        if (sourceScene == null) return;
        var source = sourceScene.Instantiate<Node3D>();
        var original = source.GetNode<Skeleton3D>("Skeleton3D");
        var target = GetNode<Skeleton3D>("Skeleton3D");
        target.ClearBones();
        target.Transform = original.Transform;
        // Keep joint names/indices compatible with the existing skin and clips.
        // Only TORSO and ARMS geometry enters this presentation scene.
        for (int i = 0; i < original.GetBoneCount(); i++)
        {
            target.AddBone(original.GetBoneName(i));
            target.SetBoneParent(i, original.GetBoneParent(i));
            target.SetBoneRest(i, original.GetBoneRest(i));
            target.SetBonePose(i, original.GetBonePose(i));
        }
        foreach (string name in new[] { "TORSO", "ARMS" })
        {
            var from = original.GetNode<MeshInstance3D>(name);
            var to = target.GetNode<MeshInstance3D>(name);
            to.Transform = from.Transform;
            to.Mesh = from.Mesh;
            to.Skin = from.Skin;
        }
        var animations = GetNode<AnimationPlayer>("AnimationPlayer");
        if (animations.HasAnimationLibrary("")) animations.RemoveAnimationLibrary("");
        animations.AddAnimationLibrary("", (AnimationLibrary)source.GetNode<AnimationPlayer>("AnimationPlayer")
            .GetAnimationLibrary("").Duplicate());
        animations.CallbackModeProcess = AnimationMixer.AnimationCallbackModeProcess.Manual;
        animations.Play("BH01_IDLE", 0);
        animations.Advance(0);
        var grip = target.GetNode<BoneAttachment3D>("FP_LeftHandGrip");
        grip.BoneIdx = target.FindBone(grip.BoneName);
        uint layer = target.GetNode<MeshInstance3D>("TORSO").Layers;
        foreach (Node node in grip.FindChildren("*", "VisualInstance3D", true, false))
        {
            ((VisualInstance3D)node).Layers = layer;
            if (node is GeometryInstance3D geometry) geometry.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
        source.Free();
    }
}
