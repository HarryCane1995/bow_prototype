using Godot;

public partial class PlayerController : CharacterBody3D
{
    [Export] public NodePath CameraPivotPath { get; set; } = new("CameraPivot");
    [Export] public NodePath CameraPath { get; set; } = new("CameraPivot/Camera3D");
    [Export] public NodePath GroundCheckPath { get; set; } = new("GroundCheck");
    [Export] public NodePath MovementModulePath { get; set; } = new("PlayerMovementModule");
    [Export] public NodePath JumpModulePath { get; set; } = new("PlayerJumpModule");
    [Export] public NodePath LookModulePath { get; set; } = new("PlayerLookModule");
    [Export] public NodePath BowShootModulePath { get; set; } = new("PlayerBowShootModule");
    [Export] public NodePath BowVisualModulePath { get; set; } = new("PlayerBowVisualModule");

    public Node3D CameraPivot { get; private set; }
    public Camera3D Camera { get; private set; }
    public RayCast3D GroundCheck { get; private set; }
    public PlayerMovementModule MovementModule { get; private set; }
    public PlayerJumpModule JumpModule { get; private set; }
    public PlayerLookModule LookModule { get; private set; }
    public PlayerBowShootModule BowShootModule { get; private set; }
    public PlayerBowVisualModule BowVisualModule { get; private set; }

    public bool IsGrounded => IsOnFloor() || (Velocity.Y <= 0.0f && GroundCheck?.IsColliding() == true);

    public override void _Ready()
    {
        CameraPivot = GetNode<Node3D>(CameraPivotPath);
        Camera = GetNode<Camera3D>(CameraPath);
        GroundCheck = GetNode<RayCast3D>(GroundCheckPath);
        MovementModule = GetNode<PlayerMovementModule>(MovementModulePath);
        JumpModule = GetNode<PlayerJumpModule>(JumpModulePath);
        LookModule = GetNode<PlayerLookModule>(LookModulePath);
        BowShootModule = GetNode<PlayerBowShootModule>(BowShootModulePath);
        BowVisualModule = GetNode<PlayerBowVisualModule>(BowVisualModulePath);

        MovementModule.Initialize(this);
        JumpModule.Initialize(this);
        LookModule.Initialize(this);
        BowVisualModule.Initialize(this);
        BowShootModule.Initialize(this);
    }

    public override void _PhysicsProcess(double delta)
    {
        JumpModule.UpdateVerticalVelocity(delta);
        MovementModule.UpdateHorizontalVelocity(delta);
        MoveAndSlide();
    }

    public override void _Input(InputEvent @event)
    {
        LookModule.HandleInput(@event);
    }
}
