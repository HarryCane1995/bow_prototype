using Godot;
using System.Collections.Generic;

// Reusable visual consumer: no Player/input/physics/camera owner. A remote actor
// can instantiate 3POV alone and feed it state, root transform and aim basis.
public partial class SplitBodyVisual : Node3D
{
    [Export] public SplitAnimationSlots Slots { get; set; }
    [Export(PropertyHint.Range,"0,0.3,0.01,suffix:s")] public float BlendSeconds { get; set; } = .08f;
    [Export] public bool FirstPerson { get; set; }
    [Export] public bool StabilizeFpWrist { get; set; } = true;
    [Export(PropertyHint.Range,"0,1,0.05")] public float WorldAimWeight { get; set; } = .3f;
    public Skeleton3D Skeleton { get; private set; }
    public AnimationPlayer Animations { get; private set; }
    public Node3D Bow { get; private set; }
    public string Clip { get; private set; } = "";
    public int AdvanceCount { get; private set; }
    private int _hand, _chest;
    private Transform3D _handCalibration, _authoredHand, _authoredChest;
    private bool _authored;
    private readonly List<(Node3D Source,Node3D Copy)> _parts = new();
    public override void _Ready()
    {
        Skeleton=GetNode<Skeleton3D>("Body/Skeleton3D");
        Animations=GetNode<AnimationPlayer>("Body/AnimationPlayer");
        Animations.CallbackModeProcess=AnimationMixer.AnimationCallbackModeProcess.Manual;
        // Independent containers and clips, even with multiple actors in a scene.
        var lib=(AnimationLibrary)Animations.GetAnimationLibrary("").Duplicate(true);
        Animations.RemoveAnimationLibrary("");Animations.AddAnimationLibrary("",lib);
        _hand=Skeleton.FindBone("hand.L");_chest=Skeleton.FindBone("chest");
        var grip=GetNode<BoneAttachment3D>("Grip");grip.UseExternalSkeleton=true;
        grip.ExternalSkeleton=grip.GetPathTo(Skeleton);grip.BoneName="hand.L";grip.BoneIdx=_hand;
        Bow=grip.GetNode<Node3D>(FirstPerson ? "FP_CyberBow" : "World_CyberBow");
        Bow.ProcessMode=ProcessModeEnum.Disabled;
        SetLayer(FirstPerson ? 19 : 17);
    }
    public void BindBow(Node3D visualSource, Transform3D handCalibration, float scale)
    {
        _handCalibration=handCalibration;
        var mesh=Bow.FindChild("Bow_Visual",true,false) as Node3D;
        var meshInRoot=Bow.GlobalTransform.AffineInverse()*mesh.GlobalTransform;
        Bow.Transform=new Transform3D(Basis.Identity.Scaled(Vector3.One*scale),Vector3.Zero)*handCalibration*meshInRoot.AffineInverse();
        _parts.Clear();
        foreach (Node node in visualSource.FindChildren("*","Node3D",true,false))
        {
            var copy=Bow.GetNodeOrNull<Node3D>(visualSource.GetPathTo(node));
            if (copy!=null) _parts.Add(((Node3D)node,copy));
        }
    }
    public void Present(PresentationState state,double delta,Basis view,bool sliding)
    {
        if (_authored) { Skeleton.SetBonePose(_hand,_authoredHand);Skeleton.SetBonePose(_chest,_authoredChest); }
        string next=Slots.Resolve(state,Animations).ToString();
        if (next!=Clip) { Clip=next;Animations.Play(Clip,BlendSeconds); }
        Animations.Advance(delta);AdvanceCount++;
        _authoredHand=Skeleton.GetBonePose(_hand);_authoredChest=Skeleton.GetBonePose(_chest);_authored=true;
        if (FirstPerson && StabilizeFpWrist)
        {
            Basis desired=Skeleton.GlobalBasis.Inverse()*new Basis(view.Z,view.X,view.Y)*_handCalibration.Basis.Inverse();
            SetGlobalRotation(_hand,desired);
        }
        else if (!FirstPerson && !sliding && WorldAimWeight>0)
        {
            // Bounded anatomical torso response, independent from FP wrist cheats.
            // Keep the hand/bow relationship authored; no camera/socket correction.
            Vector3 dir=GlobalBasis.Inverse()*-view.Z;
            float yaw=Mathf.Clamp(Mathf.Atan2(-dir.X,-dir.Z),-1.13f,1.13f);
            float pitch=Mathf.Clamp(Mathf.Asin(Mathf.Clamp(dir.Y,-1,1)),-.96f,.96f);
            Basis turn=GlobalBasis*new Basis(Vector3.Up,yaw*WorldAimWeight)*new Basis(Vector3.Right,pitch*WorldAimWeight)*GlobalBasis.Inverse();
            SetGlobalRotation(_chest,Skeleton.GlobalBasis.Inverse()*turn*Skeleton.GlobalBasis*Skeleton.GetBoneGlobalPose(_chest).Basis);
        }
        foreach (var (source,copy) in _parts) { copy.Transform=source.Transform;copy.Visible=source.Visible; }
    }
    private void SetGlobalRotation(int bone,Basis desired)
    {
        int parent=Skeleton.GetBoneParent(bone);
        Basis basis=parent<0 ? Basis.Identity : Skeleton.GetBoneGlobalPose(parent).Basis;
        Skeleton.SetBonePoseRotation(bone,(basis.Inverse()*desired).Orthonormalized().GetRotationQuaternion());
    }
    public void SetLayer(int layer)
    {
        uint mask=1u<<(layer-1);
        foreach (Node n in FindChildren("*","VisualInstance3D",true,false))
        {
            ((VisualInstance3D)n).Layers=mask;
            if (FirstPerson && n is GeometryInstance3D g) g.CastShadow=GeometryInstance3D.ShadowCastingSetting.Off;
        }
    }
}
