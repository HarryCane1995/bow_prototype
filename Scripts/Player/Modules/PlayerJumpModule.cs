using Godot;

public partial class PlayerJumpModule : Node
{
    [Export] public float JumpVelocity { get; set; } = 5.0f;
    [Export] public float GravityMultiplier { get; set; } = 1.0f;

    private PlayerController _player;
    private float _gravity;
    private bool _spaceWasPressed;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _gravity = (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble();
    }

    public void UpdateVerticalVelocity(double delta)
    {
        Vector3 velocity = _player.Velocity;

        if (_player.IsGrounded)
        {
            if (velocity.Y < 0.0f)
            {
                velocity.Y = -0.1f;
            }
        }
        else
        {
            velocity.Y -= _gravity * GravityMultiplier * (float)delta;
        }

        bool spacePressed = Input.IsKeyPressed(Key.Space);
        bool jumpRequested = spacePressed && !_spaceWasPressed;
        _spaceWasPressed = spacePressed;

        if (jumpRequested && _player.IsGrounded)
        {
            velocity.Y = JumpVelocity;
        }

        _player.Velocity = velocity;
    }
}
