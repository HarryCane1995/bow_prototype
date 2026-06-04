using Godot;

public partial class PlayerMovementModule : Node
{
    [Export] public float MoveSpeed { get; set; } = 6.0f;
    [Export] public float Acceleration { get; set; } = 18.0f;
    [Export(PropertyHint.Range, "0,1,0.05")] public float AirControlMultiplier { get; set; } = 0.35f;
    [Export] public string MoveForwardAction { get; set; } = "move_forward";
    [Export] public string MoveBackAction { get; set; } = "move_back";
    [Export] public string MoveLeftAction { get; set; } = "move_left";
    [Export] public string MoveRightAction { get; set; } = "move_right";

    private PlayerController _player;

    public void Initialize(PlayerController player)
    {
        _player = player;
    }

    public void UpdateHorizontalVelocity(double delta)
    {
        Vector2 input = GetMovementInput();
        Vector3 direction = GetMovementDirection(input);
        Vector3 velocity = _player.Velocity;

        Vector3 targetVelocity = direction * MoveSpeed;
        float control = _player.IsGrounded ? 1.0f : AirControlMultiplier;
        float step = Acceleration * control * (float)delta;

        velocity.X = Mathf.MoveToward(velocity.X, targetVelocity.X, step);
        velocity.Z = Mathf.MoveToward(velocity.Z, targetVelocity.Z, step);

        _player.Velocity = velocity;
    }

    private Vector2 GetMovementInput()
    {
        Vector2 input = new(
            Input.GetActionStrength(MoveRightAction) - Input.GetActionStrength(MoveLeftAction),
            Input.GetActionStrength(MoveForwardAction) - Input.GetActionStrength(MoveBackAction)
        );

        return input.LengthSquared() > 1.0f ? input.Normalized() : input;
    }

    private Vector3 GetMovementDirection(Vector2 input)
    {
        if (input == Vector2.Zero)
        {
            return Vector3.Zero;
        }

        Basis playerBasis = _player.GlobalTransform.Basis;
        Vector3 forward = -playerBasis.Z;
        Vector3 right = playerBasis.X;

        forward.Y = 0.0f;
        right.Y = 0.0f;

        return (forward.Normalized() * input.Y + right.Normalized() * input.X).Normalized();
    }
}
