using Godot;
using System.Reflection;

// Disposable test fixture only. Freeze the motor and inject module states to
// compare identical left/right camera effects without route/timing variation.
public partial class V2AimProof : Node
{
    public PlayerController Player;
    public MainCharacterV2 V2;
    // Reconstruct the authored chain from the solver's saved locals, without
    // touching the live skeleton or depending on its procedural global cache.
    public Transform3D AuthoredWorld(string name)
    {
        var saved = (System.Collections.Generic.Dictionary<int, Transform3D>)typeof(MainCharacterV2)
            .GetField("_authoredBones", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(V2);
        var chain = new System.Collections.Generic.Stack<int>();
        for (int b = V2.Skeleton.FindBone(name); b >= 0; b = V2.Skeleton.GetBoneParent(b)) chain.Push(b);
        Transform3D pose = V2.Skeleton.GlobalTransform;
        foreach (int b in chain) pose *= saved.TryGetValue(b, out var original) ? original : V2.Skeleton.GetBonePose(b);
        return pose;
    }
    public void SolveFrozenBody()
    {
        foreach (string method in new[] { "RestoreAuthoredBones", "CacheAuthoredCamera", "UpdateAimPresentation", "ApplyCameraCalibration" })
            typeof(MainCharacterV2).GetMethod(method, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic).Invoke(V2, null);
    }
    public void Setup(Node gym)
    {
        Player = gym.GetNode<PlayerController>("Player");
        V2 = Player.GetNode<MainCharacterV2>("MainCharacterV2");
        Player.SetPhysicsProcess(false);
        Player.WallRunModule.SetProcess(false);
    }
    public void Wall(string side)
    {
        var module = Player.WallRunModule;
        typeof(PlayerWallRunModule).GetProperty("IsWallRunning").SetValue(module, side != "None");
        var field = typeof(PlayerWallRunModule).GetField("_wallSide", BindingFlags.Instance | BindingFlags.NonPublic);
        field.SetValue(module, System.Enum.Parse(field.FieldType, side));
        module._Process(1.0);
    }
    public void Pose(bool slide)
    {
        var module = Player.CrouchSlideModule;
        var field = module.GetType().GetField("_state", BindingFlags.Instance | BindingFlags.NonPublic);
        field.SetValue(module, System.Enum.Parse(field.FieldType, slide ? "Sliding" : "Standing"));
        module.GetType().GetField("_slideDirection", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(module, Vector3.Forward);
        V2._PhysicsProcess(0);
    }
}
