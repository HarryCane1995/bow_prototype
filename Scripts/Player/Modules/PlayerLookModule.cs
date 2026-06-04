using Godot;

public partial class PlayerLookModule : Node
{
    [Export] public float MouseSensitivity { get; set; } = 0.003f;
    [Export] public float MinPitch { get; set; } = -80.0f;
    [Export] public float MaxPitch { get; set; } = 80.0f;

    private PlayerController _player;
    private float _pitch;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _pitch = _player.CameraPivot.Rotation.X;
        Input.MouseMode = Input.MouseModeEnum.Captured;
    }

    public void HandleInput(InputEvent @event)
    {
        if (@event is not InputEventMouseMotion mouseMotion)
        {
            return;
        }

        _player.RotateY(-mouseMotion.Relative.X * MouseSensitivity);

        float minPitchRadians = Mathf.DegToRad(MinPitch);
        float maxPitchRadians = Mathf.DegToRad(MaxPitch);
        _pitch = Mathf.Clamp(_pitch - mouseMotion.Relative.Y * MouseSensitivity, minPitchRadians, maxPitchRadians);

        Vector3 pivotRotation = _player.CameraPivot.Rotation;
        pivotRotation.X = _pitch;
        pivotRotation.Y = 0.0f;
        pivotRotation.Z = 0.0f;
        _player.CameraPivot.Rotation = pivotRotation;
    }
}
