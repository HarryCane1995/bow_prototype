using Godot;
using System.Collections.Generic;

public partial class MainCharacterV2
{
    [ExportGroup("V2 Runtime Aim")]
    [Export(PropertyHint.Range, "0,1,0.05")] public float UpperBodyAimWeight { get; set; } = 0.3f;
    [Export(PropertyHint.Range, "0,1,0.05")] public float LeftArmIKWeight { get; set; } = 1;
    [Export(PropertyHint.Range, "0,1,0.05")] public float RightArmIKWeight { get; set; } = 1;
    [Export(PropertyHint.Range, "0,80,1,suffix:deg")] public float AimYawLimit { get; set; } = 65;
    [Export(PropertyHint.Range, "0,75,1,suffix:deg")] public float AimPitchLimit { get; set; } = 55;

    public float BowAimErrorDegrees { get; private set; }
    public float LeftGripError { get; private set; }
    public float RightGripError { get; private set; }
    public Vector2 ClampedAimDegrees { get; private set; }
    public bool Slide360Active => Enabled && _sliding && !HybridPresentationActive;
    private bool SlideTurretEnabled => Slide360Active && (UpperBodyAimWeight > 0 || LeftArmIKWeight > 0 || RightArmIKWeight > 0);

    private Vector3 PresentationCameraOffset(Basis view)
    {
        if (!SlideTurretEnabled) return _worldCamera.Offset;
        Vector3 forward = GlobalBasis.Inverse() * -view.Z;
        float yaw = Mathf.Atan2(-forward.X, -forward.Z);
        // The eye's composition offset travels with the rotary upper body too;
        // leaving it in the lower-body frame places the camera behind the torso
        // when looking backwards. This changes position only, never mouse look.
        Vector3 axis = Skeleton.GlobalBasis.Inverse() * Vector3.Up;
        return new Basis(axis.Normalized(), yaw) * _worldCamera.Offset;
    }
    private Node3D _bowAimTarget;
    private MeshInstance3D _aimBowMesh;
    private ArmChain _aimLeft, _aimRight;
    private int _aimSpine, _aimChest;
    private readonly Dictionary<int, Transform3D> _authoredBones = new();

    private sealed record ArmChain(int Upper, int Forearm, int Hand);
    private ArmChain Arm(string side) => new(Skeleton.FindBone("upper_arm." + side),
        Skeleton.FindBone("forearm." + side), Skeleton.FindBone("hand." + side));

    private void InitializeAimLayer()
    {
        _aimLeft = Arm("L"); _aimRight = Arm("R");
        _aimSpine = Skeleton.FindBone("spine_02"); _aimChest = Skeleton.FindBone("chest");
        _aimBowMesh = _weapon?.FindChild("Bow_Visual", true, false) as MeshInstance3D;
        _bowAimTarget = new Node3D { Name = "V2_BowAimTarget", TopLevel = true };
        AddChild(_bowAimTarget);
    }

    private void RestoreAuthoredBones()
    {
        // Static clips stop at their endpoint; Advance then need not rewrite bones.
        // Restore the exact pre-IK locals before evaluating the next frame/blend.
        foreach (var entry in _authoredBones)
            Skeleton.SetBonePose(entry.Key, entry.Value);
        _authoredBones.Clear();
    }

    private void RememberBone(int bone)
    {
        if (!_authoredBones.ContainsKey(bone)) _authoredBones[bone] = Skeleton.GetBonePose(bone);
    }

    public void UpdateAimPresentation()
    {
        if (!_ready || !Enabled || _aimBowMesh == null) return;
        // Hybrid FP has its own wrists/bow. World slide remains exactly authored.
        if (HybridPresentationActive && _sliding) return;
        Basis body = GlobalBasis.Orthonormalized();
        Basis view = _frameViewBasis;
        Vector3 forward = body.Inverse() * -view.Z;
        float rawYaw = Mathf.Atan2(-forward.X, -forward.Z);
        float rawPitch = Mathf.Asin(Mathf.Clamp(forward.Y, -1, 1));
        float yaw = _sliding ? rawYaw : Mathf.Clamp(rawYaw, -Mathf.DegToRad(AimYawLimit), Mathf.DegToRad(AimYawLimit));
        float pitch = Mathf.Clamp(rawPitch, -Mathf.DegToRad(AimPitchLimit), Mathf.DegToRad(AimPitchLimit));
        ClampedAimDegrees = new Vector2(Mathf.RadToDeg(yaw), Mathf.RadToDeg(pitch));
        Basis aimNoRoll = body * new Basis(Vector3.Up, yaw) * new Basis(Vector3.Right, pitch);
        // Match camera screen horizontal, including canonical wallrun roll; this
        // avoids the apparent opposite lean of a world-horizontal attached bow.
        Basis rawNoRoll = body * new Basis(Vector3.Up, rawYaw) * new Basis(Vector3.Right, rawPitch);
        Vector3 viewRight = rawNoRoll.Inverse() * view.X;
        float roll = Mathf.Atan2(viewRight.Y, viewRight.X);
        Basis aim = aimNoRoll * new Basis(Vector3.Back, roll);
        _bowAimTarget.GlobalTransform = new Transform3D(aim, _frameCameraOrigin - aim.Z * 10);

        Transform3D skWorld = Skeleton.GlobalTransform;
        Basis skInverse = skWorld.Basis.Inverse();
        Basis motion = skInverse * aim * body.Inverse() * skWorld.Basis;
        // Authoring reference, before this frame's turret/IK. It must not include
        // last frame's camera offset or corrected bones (no target feedback).
        Vector3 pivot = skWorld.AffineInverse() * _preAimSocketWorld + _worldCamera.Offset;
        Transform3D leftBase = Skeleton.GetBoneGlobalPose(_aimLeft.Hand);
        Transform3D rightBase = Skeleton.GetBoneGlobalPose(_aimRight.Hand);

        float support = Mathf.Clamp(UpperBodyAimWeight, 0, 1);
        bool turret = SlideTurretEnabled;
        // A full periodic rotation on ONE upper-body joint has no branch cut at
        // +/-180. Splitting a wrapped angle into fractional spine rotations would
        // jump those fractions at the seam. Pelvis/root stay authored and locked.
        float spineYaw = turret ? yaw : yaw * support * 0.4f;
        float chestYaw = turret ? 0 : yaw * support * 0.6f;
        RotateGlobal(_aimSpine, skInverse * body * new Basis(Vector3.Up, spineYaw)
            * new Basis(Vector3.Right, pitch * support * 0.4f) * body.Inverse() * skWorld.Basis);
        RotateGlobal(_aimChest, skInverse * body * new Basis(Vector3.Up, chestYaw)
            * new Basis(Vector3.Right, pitch * support * 0.6f) * body.Inverse() * skWorld.Basis);
        Vector3 finalEye = skWorld.AffineInverse() * _frameCameraOrigin;
        // Keep the authored grip vicinity in the bounded eye frame; orbiting
        // around the chest alone swings a low grip across/behind the camera.
        Vector3 leftTarget = finalEye + motion * (leftBase.Origin - pivot);
        Vector3 rightTarget = finalEye + motion * (rightBase.Origin - pivot);

        // CyberBow's measured asset axes: -X shoots, +Y spans the limbs, +Z is up.
        // BowMeshInHand is the existing calibrated attachment, never re-authored.
        Basis bowWorld = new(aim.Z, aim.X, aim.Y);
        Basis wrist = skInverse * bowWorld * BowMeshInHand.Basis.Inverse();
        LeftGripError = SolveArm(_aimLeft, leftTarget, wrist.Orthonormalized(), LeftArmIKWeight);
        // Ready hand follows the same bounded aiming motion. Nock draw integration
        // is kept separate from camera aim and never feeds projectile direction.
        RightGripError = SolveArm(_aimRight, rightTarget, motion * rightBase.Basis, RightArmIKWeight);

        // BoneAttachment alone publishes the final hand on skeleton_updated.
        // The readout can use the solved transform before that notification.
        Transform3D solvedBow = skWorld * Skeleton.GetBoneGlobalPose(_aimLeft.Hand) * BowMeshInHand;
        BowAimErrorDegrees = Mathf.RadToDeg((-solvedBow.Basis.X).Normalized().AngleTo(-view.Z));
        _readout.Text += $"\nAIM YAW: {ClampedAimDegrees.X:0.0}°  |  SLIDE 360: {(Slide360Active ? "ON" : "OFF")}";
    }

    private void RotateGlobal(int bone, Basis delta)
    {
        if (delta.IsEqualApprox(Basis.Identity)) return;
        SetGlobalRotation(bone, delta * Skeleton.GetBoneGlobalPose(bone).Basis, 1);
    }

    private void SetGlobalRotation(int bone, Basis desired, float weight)
    {
        if (weight <= 0) return;
        RememberBone(bone);
        int parent = Skeleton.GetBoneParent(bone);
        Basis parentBasis = parent < 0 ? Basis.Identity : Skeleton.GetBoneGlobalPose(parent).Basis;
        Quaternion local = (parentBasis.Inverse() * desired).Orthonormalized().GetRotationQuaternion();
        Skeleton.SetBonePoseRotation(bone, Skeleton.GetBonePoseRotation(bone).Slerp(local, Mathf.Clamp(weight, 0, 1)).Normalized());
    }

    private float SolveArm(ArmChain arm, Vector3 target, Basis wrist, float weight)
    {
        if (weight <= 0) return 0;
        Vector3 shoulder = Skeleton.GetBoneGlobalPose(arm.Upper).Origin;
        Vector3 elbow = Skeleton.GetBoneGlobalPose(arm.Forearm).Origin;
        Vector3 hand = Skeleton.GetBoneGlobalPose(arm.Hand).Origin;
        float upper = shoulder.DistanceTo(elbow), fore = elbow.DistanceTo(hand);
        Vector3 direction = (target - shoulder).Normalized();
        float distance = Mathf.Clamp(shoulder.DistanceTo(target), Mathf.Abs(upper - fore) + 0.005f, upper + fore - 0.005f);
        Vector3 reachable = shoulder + direction * distance;
        Vector3 pole = elbow - shoulder;
        pole -= direction * pole.Dot(direction);
        if (pole.LengthSquared() < 0.00001f) pole = direction.Cross(Vector3.Forward);
        if (pole.LengthSquared() < 0.00001f) pole = direction.Cross(Vector3.Up);
        float along = (upper * upper - fore * fore + distance * distance) / (2 * distance);
        Vector3 bend = shoulder + direction * along + pole.Normalized() * Mathf.Sqrt(Mathf.Max(0, upper * upper - along * along));
        Basis upperRotation = new Basis(new Quaternion((elbow - shoulder).Normalized(), (bend - shoulder).Normalized())) * Skeleton.GetBoneGlobalPose(arm.Upper).Basis;
        SetGlobalRotation(arm.Upper, upperRotation, weight);
        elbow = Skeleton.GetBoneGlobalPose(arm.Forearm).Origin;
        hand = Skeleton.GetBoneGlobalPose(arm.Hand).Origin;
        Basis foreRotation = new Basis(new Quaternion((hand - elbow).Normalized(), (reachable - elbow).Normalized())) * Skeleton.GetBoneGlobalPose(arm.Forearm).Basis;
        SetGlobalRotation(arm.Forearm, foreRotation, weight);
        SetGlobalRotation(arm.Hand, wrist, weight);
        return Skeleton.GetBoneGlobalPose(arm.Hand).Origin.DistanceTo(target);
    }
}
