using Godot;

// Presentation only. The bow visual module owns draw/release; this node owns the
// imported blocking rig and follows the existing holder/sway without input or physics.
public partial class FirstPersonHands : Node3D
{
    [ExportGroup("Scene Links")]
    [Export] public NodePath SkeletonPath { get; set; } = new("Arms/HandsRig/Skeleton3D");
    [Export] public NodePath BowHolderPath { get; set; } = new("../BowViewModelHolder");
    [Export] public NodePath ArrowFromHolderPath { get; set; } = new("CyberBowAxisCorrection/CyberBow_ViewModel/Arrow_Visual");
    [Export] public NodePath BowPresentationFromHolderPath { get; set; } = new("CyberBowAxisCorrection");

    [ExportGroup("Blocking")]
    [Export(PropertyHint.Range, "0,1,0.05")] public float HeavyProportions { get; set; }
    [Export] public Vector3 DrawOffset { get; set; } = new(0, 0, 0.18f);
    [Export] public Vector3 SupportWristOffset { get; set; } = new(0.00674f, 0.01846f, -0.01229f);
    [Export] public Vector3 DrawingWristOffset { get; set; } = new(-0.005f, -0.08f, -0.07f);
    [Export(PropertyHint.Range, "0,0.3,0.01,suffix:m")] public float PrecisionHandLift { get; set; } = 0.20f;
    [Export(PropertyHint.Range, "5,40,1,suffix:/s")] public float PoseResponse { get; set; } = 22;
    [Export(PropertyHint.Range, "0.05,0.4,0.01,suffix:s")] public float ReleaseSeconds { get; set; } = 0.18f;
    [Export] public Vector3 NockIdle { get; set; } = new(0.02f, -0.30f, -0.65f);
    [Export] public Vector3 StringTipLeft { get; set; } = new(-0.74605f, -0.32f, -0.68038f);
    [Export] public Vector3 StringTipRight { get; set; } = new(0.76803f, -0.32f, -0.68036f);

    public float CurrentDraw { get; private set; }
    public float MaxGripError { get; private set; }

    private Skeleton3D _skeleton;
    private MeshInstance3D _mesh;
    private Node3D _holder;
    private Node3D _arrow;
    private Transform3D _holderRest;
    private Transform3D _arrowRest;
    private PlayerBowVisualModule _visual;
    private ViewModelMotionPrototype _motionPrototype;
    private CyberBowShotMotion _shotMotion;
    private Node3D _bowPresentation;
    private Transform3D _bowRest;
    private Arm _left;
    private Arm _right;
    private MeshInstance3D _stringLeft;
    private MeshInstance3D _stringRight;
    private uint _lastShot;
    private float _releaseAge = 10;
    private int _heavyShape = -1;

    private sealed class Arm
    {
        public int Upper, Forearm, Hand, Fingers;
        public Transform3D UpperRest, ForearmRest, HandRest;
        public Quaternion FingersRest;
    }

    public override void _Ready()
    {
        // Run after the existing visual and sway presentation updates.
        ProcessPriority = 20;
        _skeleton = GetNode<Skeleton3D>(SkeletonPath);
        _mesh = _skeleton.GetNode<MeshInstance3D>("Hands_Blocking");
        _heavyShape = _mesh.FindBlendShapeByName("Heavy");
        _holder = GetNode<Node3D>(BowHolderPath);
        _holderRest = _holder.Transform;
        _arrow = _holder.GetNode<Node3D>(ArrowFromHolderPath);
        _arrowRest = GetParent<Node3D>().GlobalTransform.AffineInverse() * _arrow.GlobalTransform;
        _bowPresentation = _holder.GetNode<Node3D>(BowPresentationFromHolderPath);
        _bowRest = _bowPresentation.Transform;
        _left = BindArm("L");
        _right = BindArm("R");
        _stringLeft = GetNode<MeshInstance3D>("StringLeft");
        _stringRight = GetNode<MeshInstance3D>("StringRight");
    }

    private Arm BindArm(string side)
    {
        var arm = new Arm
        {
            Upper = _skeleton.FindBone("Upper." + side),
            Forearm = _skeleton.FindBone("Forearm." + side),
            Hand = _skeleton.FindBone("Hand." + side),
            Fingers = _skeleton.FindBone("Fingers." + side)
        };
        arm.UpperRest = _skeleton.GetBoneGlobalRest(arm.Upper);
        arm.ForearmRest = _skeleton.GetBoneGlobalRest(arm.Forearm);
        arm.HandRest = _skeleton.GetBoneGlobalRest(arm.Hand);
        arm.FingersRest = _skeleton.GetBonePoseRotation(arm.Fingers);
        return arm;
    }

    public override void _Process(double delta)
    {
        if (_visual == null)
        {
            var player = GetTree().GetFirstNodeInGroup("player") as PlayerController;
            _visual = player?.BowVisualModule;
            _motionPrototype = player?.GetNodeOrNull<ViewModelMotionPrototype>("PlayerViewModelSwayModule/MotionPrototype");
            _shotMotion = _motionPrototype?.GetNodeOrNull<CyberBowShotMotion>("ShotMotion");
        }
        if (_visual == null) return;
        bool useShot = _motionPrototype?.UseNewMotion == true && _shotMotion?.Enabled == true;
        // Hand back a ready arrow when switching to the legacy presentation;
        // its old timer was deliberately inactive during procedural recovery.
        if (_visual.ArrowPresentationOwnedByHands && !useShot) _arrow.Visible = true;
        _visual.ArrowPresentationOwnedByHands = useShot;

        float dt = (float)delta;
        _releaseAge += dt;
        if (_lastShot != _visual.ShotVisualSequence)
        {
            _lastShot = _visual.ShotVisualSequence;
            _releaseAge = 0;
        }
        float target = _visual.IsPrecisionAiming ? 1 : _visual.DrawAmount;
        bool releasing = _releaseAge < ReleaseSeconds;
        if (releasing) target = 0;
        CurrentDraw = Mathf.Lerp(CurrentDraw, target, 1 - Mathf.Exp(-(releasing ? 38 : PoseResponse) * dt));
        if (useShot) CurrentDraw = _shotMotion.StringDraw;
        float release = releasing ? Mathf.Sin(Mathf.Pi * _releaseAge / ReleaseSeconds) : 0;
        if (_heavyShape >= 0) _mesh.SetBlendShapeValue(_heavyShape, HeavyProportions);

        // Both nodes share SwayRoot. Remove the bind holder transform so metre-space
        // guide positions follow its precision rotation, not its legacy asset scale.
        Transform3D motion = _holder.Transform * _holderRest.AffineInverse();
        Transform3D shotPose = useShot ? _shotMotion.BowPose : Transform3D.Identity;
        // Conjugate the metre-space grip pivot into the scaled asset's parent.
        // This is the only writer of this decorative body transform. Precision
        // still belongs to Holder; the support wrist follows the very same pose.
        _bowPresentation.Transform = _holderRest.AffineInverse() * shotPose * _holderRest * _bowRest;
        Transform3D bowMotion = motion * shotPose;
        Basis wristRotation = motion.Basis.Orthonormalized();
        Vector3 fullPull = DrawOffset + (useShot ? _shotMotion.ExtraDrawPull : Vector3.Zero);
        Vector3 pull = fullPull * CurrentDraw;
        Vector3 handPull = useShot ? fullPull * _shotMotion.HandDraw + _shotMotion.HandOffset
            : pull + new Vector3(0.035f, -0.012f, 0.015f) * release;
        // The bow rolls vertical, while the drawing hand stays in the lower-right
        // camera space. Follow the actual roll so entering/leaving aim stays smooth.
        float roll = Mathf.Abs(wristRotation.GetEuler().Z);
        Vector3 precisionLift = Vector3.Up * (PrecisionHandLift * Mathf.Clamp(roll / Mathf.DegToRad(65), 0, 1));
        PoseArm(_left, bowMotion * (_left.HandRest.Origin + SupportWristOffset), bowMotion.Basis.Orthonormalized());
        PoseArm(_right, motion * (_right.HandRest.Origin + DrawingWristOffset + handPull) + precisionLift, wristRotation);
        _skeleton.SetBonePoseRotation(_right.Fingers, _right.FingersRest * new Quaternion(Vector3.Right, (useShot ? _shotMotion.FingerOpen : release) * 0.4f));

        float straight = useShot ? _shotMotion.StringStraighten : 0;
        Vector3 nock = bowMotion * NockIdle.Lerp((StringTipLeft + StringTipRight) * 0.5f, straight)
            + motion.Basis * pull + precisionLift * (1 - straight);
        UpdateString(_stringLeft, bowMotion * StringTipLeft, nock);
        UpdateString(_stringRight, bowMotion * StringTipRight, nock);
        if (useShot)
        {
            _arrow.Visible = _shotMotion.ArrowVisible;
        }
        // Arrow retrieval follows the drawing hand, separately from the already
        // straight string. Neither decorative transform feeds projectile aim.
        var sway = GetParent<Node3D>();
        Transform3D oldArrow = bowMotion * _arrowRest;
        Vector3 restGuide = bowMotion * (NockIdle + _arrowRest.Basis.Y.Normalized() * 0.30f);
        Basis aim = new(new Quaternion(oldArrow.Basis.Y.Normalized(), (restGuide - nock).Normalized()));
        Transform3D arrowPose = new(aim * oldArrow.Basis, nock + aim * (oldArrow.Origin - bowMotion * NockIdle));
        // Carry the whole arrow from below. Aiming its shaft through the grip
        // during retrieval would swing the tip across the reticle.
        if (useShot) arrowPose.Origin += motion.Basis * _shotMotion.ArrowLoadOffset;
        _arrow.Transform = _arrow.GetParent<Node3D>().GlobalTransform.AffineInverse() * sway.GlobalTransform * arrowPose;
    }

    private void PoseArm(Arm arm, Vector3 wrist, Basis wristRotation)
    {
        Vector3 shoulder = arm.UpperRest.Origin;
        Vector3 oldElbow = arm.ForearmRest.Origin;
        float upperLength = shoulder.DistanceTo(oldElbow);
        float foreLength = oldElbow.DistanceTo(arm.HandRest.Origin);
        Vector3 direction = (wrist - shoulder).Normalized();
        float distance = Mathf.Clamp(shoulder.DistanceTo(wrist), Mathf.Abs(upperLength - foreLength) + 0.001f, upperLength + foreLength - 0.001f);
        Vector3 pole = oldElbow - shoulder;
        pole = (pole - direction * pole.Dot(direction)).Normalized();
        float along = (upperLength * upperLength - foreLength * foreLength + distance * distance) / (2 * distance);
        Vector3 elbow = shoulder + direction * along + pole * Mathf.Sqrt(Mathf.Max(0, upperLength * upperLength - along * along));
        SetGlobalBone(arm.Upper, new Transform3D(RotateToward(arm.UpperRest.Basis, oldElbow - shoulder, elbow - shoulder), shoulder));
        SetGlobalBone(arm.Forearm, new Transform3D(RotateToward(arm.ForearmRest.Basis, arm.HandRest.Origin - oldElbow, wrist - elbow), elbow));
        SetGlobalBone(arm.Hand, new Transform3D(wristRotation * arm.HandRest.Basis, wrist));
        MaxGripError = Mathf.Max(MaxGripError, _skeleton.GetBoneGlobalPose(arm.Hand).Origin.DistanceTo(wrist));
    }

    private static Basis RotateToward(Basis rest, Vector3 from, Vector3 to)
        => new Basis(new Quaternion(from.Normalized(), to.Normalized())) * rest;

    private void SetGlobalBone(int index, Transform3D pose)
    {
        int parent = _skeleton.GetBoneParent(index);
        Transform3D local = parent >= 0 ? _skeleton.GetBoneGlobalPose(parent).AffineInverse() * pose : pose;
        _skeleton.SetBonePosePosition(index, local.Origin);
        _skeleton.SetBonePoseRotation(index, local.Basis.GetRotationQuaternion().Normalized());
    }

    private static void UpdateString(MeshInstance3D segment, Vector3 start, Vector3 end)
    {
        Vector3 direction = end - start;
        segment.Position = (start + end) * 0.5f;
        Basis rotation = new(new Quaternion(Vector3.Up, direction.Normalized()));
        segment.Basis = new Basis(rotation.X, rotation.Y * direction.Length(), rotation.Z);
    }
}
