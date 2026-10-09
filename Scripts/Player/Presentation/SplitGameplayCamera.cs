using Godot;

// Independent camera layer. No reference to either presentation skeleton.
public partial class SplitGameplayCamera : Node
{
    [Export] public Vector3 EyeOffsetFromPivot { get; set; } = new(.026536f,-.417539f,-.345794f);
    [Export(PropertyHint.Range,"30,120,0.5,suffix:deg")] public float FieldOfView { get; set; } = 98;
    public PlayerController Player { get; set; }
    public bool Active { get; set; }
    public override void _Ready() => ProcessPriority=-10;
    public override void _Process(double delta)
    {
        if (!Active || Player?.Camera == null) return;
        var effects=Player.CameraPivot.GetNode<Node3D>("CameraEffectsPivot");
        Vector3 origin=Player.GetGlobalTransformInterpolated().Origin
            + Player.GlobalBasis*(Player.CameraPivot.Position+EyeOffsetFromPivot);
        Player.Camera.GlobalTransform=new Transform3D(effects.GlobalBasis.Orthonormalized(),origin);
        Player.Camera.Fov=FieldOfView;
    }
}
