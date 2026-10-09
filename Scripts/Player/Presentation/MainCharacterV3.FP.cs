using Godot;
using System.Text.Json;

public partial class MainCharacterV3
{
    [ExportGroup("FP Composition")]
    [Export(PropertyHint.Range,"30,110,0.5,suffix:deg")] public float FpFov { get; set; } = 65;
    [Export] public Vector3 FpCompositionOffset { get; set; } = new(0.003062f,-0.141082f,-0.388422f);
    [Export(PropertyHint.Range,"0.3,1.2,0.01")] public float FpBowScale { get; set; } = 0.62f;
    [Export(PropertyHint.Range,"0,0.3,0.01,suffix:s")] public float FpBlendSeconds { get; set; } = 0.08f;
    [Export] public bool StabilizeBowWrist { get; set; } = true;

    private Node3D _fpModel;
    private AnimationPlayer _fpAnimations;
    private Vector3 _fpBaseOrigin;
    private int _fpLeftHand;
    private Transform3D _fpAuthoredWrist;
    private bool _hasAuthoredWrist;
    private Transform3D _fpBowAttachment;

    private void BuildFirstPerson()
    {
        // The presentation hierarchy now lives in its own editable scene.
        // This companion only binds gameplay observations and FP animation state.
        _canvas = GetNode<CanvasLayer>("FirstPerson");
        _viewport = _canvas.GetNode<SubViewport>("FPContainer/FPViewport");
        var space = _viewport.GetNode<Node3D>("FPSpace");
        FpCamera = space.GetNode<Camera3D>("FPViewCamera");
        FPDriftRoot = space.GetNode<Node3D>("FPPresentationBase/FPDriftRoot");
        var source = FPDriftRoot.GetNode<FirstPersonBodySource>("FPUpperBody");
        // Preserve the earlier Inspector override; normally the FP scene owns
        // its source. The adapter exposes only the named upper-body meshes.
        if (FpModelScene != null) source.Populate(FpModelScene);
        _fpModel = source;
        FpSkeleton = source.GetNode<Skeleton3D>("Skeleton3D");
        _fpAnimations = source.GetNode<AnimationPlayer>("AnimationPlayer");
        foreach (Node node in space.FindChildren("*","VisualInstance3D",true,false))
        {
            ((VisualInstance3D)node).Layers = FpMask;
            if (node is Light3D light) light.LightCullMask = FpMask;
            if (node is GeometryInstance3D geometry) geometry.CastShadow = GeometryInstance3D.ShadowCastingSetting.Off;
        }
        _fpAnimations.CallbackModeProcess = AnimationMixer.AnimationCallbackModeProcess.Manual;
        AnimationSlots ??= new V3FpAnimationSlots();
        // The FP scene's source adapter already owns a private library container.
        var library = _fpAnimations.GetAnimationLibrary("");
        if (FpAnimationLibrary != null)
        {
            // Clone the container only; future FP clips must never mutate the
            // cached world AnimationLibrary shared by other scene instances.
            foreach (StringName name in FpAnimationLibrary.GetAnimationList())
            {
                if (library.HasAnimation(name)) library.RemoveAnimation(name);
                library.AddAnimation(name,FpAnimationLibrary.GetAnimation(name));
            }
        }
        _fpAnimations.Play(AnimationSlots.FallbackClip,0); _fpAnimations.Advance(0);
        // Calibrate once from the Idle reference, never from the animated world
        // body and never feed the FP skeleton/socket back into a gameplay camera.
        using var json = JsonDocument.Parse(FileAccess.GetFileAsString(_world.CameraCalibrationPath));
        var m = json.RootElement.GetProperty("cameras").GetProperty("CAM_FP_VIEWMODEL").GetProperty("socket_offset_transform");
        var offset = new Vector3(m[0][3].GetSingle(),m[1][3].GetSingle(),m[2][3].GetSingle());
        Vector3 socket = FpSkeleton.GetBoneGlobalPose(FpSkeleton.FindBone("FP_CAMERA_SOCKET")).Origin;
        _fpBaseOrigin = -(_fpModel.Basis * (socket+offset));
        _fpModel.Position = _fpBaseOrigin + FpCompositionOffset;

        _fpLeftHand = FpSkeleton.FindBone("hand.L");
        var grip = FpSkeleton.GetNode<BoneAttachment3D>("FP_LeftHandGrip");
        grip.BoneIdx = _fpLeftHand;
        // A real instance of the existing CyberBow art is authored in 1POV.
        // It has no scripts/input/gameplay owner; the original bow drives state.
        FpBow = grip.GetNode<Node3D>("FP_CyberBow");
        FpBow.Transform = _world.PresentationWeapon.Transform;
        _fpBowAttachment = FpBow.Transform;
        FpBow.ProcessMode = ProcessModeEnum.Disabled;
        foreach (Node node in _world.PresentationWeapon.FindChildren("*","Node3D",true,false))
        {
            var counterpart = FpBow.GetNodeOrNull<Node3D>(_world.PresentationWeapon.GetPathTo(node));
            if (counterpart != null) _bowParts.Add(((Node3D)node,counterpart));
        }
    }

    private void UpdateFirstPerson(double delta)
    {
        FPDriftRoot.Transform = Transform3D.Identity;
        FpSlot = SelectFpSlot((float)delta);
        string next = _fpAnimations.HasAnimation(FpSlot) ? FpSlot : AnimationSlots.FallbackClip.ToString();
        if (_hasAuthoredWrist) FpSkeleton.SetBonePose(_fpLeftHand,_fpAuthoredWrist);
        if (next != FpClip) { FpClip=next; _fpAnimations.Play(FpClip,FpBlendSeconds); }
        _fpAnimations.Advance(delta);
        _fpAuthoredWrist = FpSkeleton.GetBonePose(_fpLeftHand); _hasAuthoredWrist=true;
        _fpModel.Position = _fpBaseOrigin + FpCompositionOffset;
        FpCamera.Fov = FpFov;
        FpCamera.CullMask = FpMask;
        FpBow.Transform = new Transform3D(Basis.Identity.Scaled(Vector3.One*FpBowScale),Vector3.Zero) * _fpBowAttachment;
        // The FP world is camera-local. A wrist-only correction is sufficient
        // for the POC and remains independent of world hand.L and torso yaw.
        if (StabilizeBowWrist)
        {
            Basis view = FpCamera.GlobalBasis;
            Basis bow = new(view.Z,view.X,view.Y);
            Basis desired = FpSkeleton.GlobalBasis.Inverse() * bow * _world.BowMeshInHand.Basis.Inverse();
            int parent = FpSkeleton.GetBoneParent(_fpLeftHand);
            Basis parentBasis = FpSkeleton.GetBoneGlobalPose(parent).Basis;
            FpSkeleton.SetBonePoseRotation(_fpLeftHand,(parentBasis.Inverse()*desired).Orthonormalized().GetRotationQuaternion());
        }
        // Mirror only local bow-part state/arrow visibility. Never copy world
        // hand/bow global transforms: the FP grip is owned exclusively here.
        foreach (var pair in _bowParts) { pair.Copy.Transform=pair.Source.Transform; pair.Copy.Visible=pair.Source.Visible; }
        Transform3D solvedBow = FpSkeleton.GlobalTransform * FpSkeleton.GetBoneGlobalPose(_fpLeftHand) * _world.BowMeshInHand;
        // Neutral wrist diagnostic. The cosmetic common-root drift is applied
        // afterwards, so it intentionally adds a screen-space aiming deviation.
        FpBowAimErrorDegrees = Mathf.RadToDeg((-solvedBow.Basis.X).Normalized().AngleTo(-FpCamera.GlobalBasis.Z));
    }
}
