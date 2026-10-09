using Godot;

public partial class MainCharacterV2
{
    [ExportGroup("V2 Locomotion Animation")]
    [Export] public StringName IdleAnimation { get; set; } = "BH01_IDLE";
    [Export] public StringName SlideAnimation { get; set; } = "BH01_SLIDE";
    [Export] public StringName RunAnimation { get; set; } = "BH01_RUN";
    [Export] public StringName WallrunLeftAnimation { get; set; } = "BH01_WALLRUN_LEFT";
    [Export] public StringName WallrunRightAnimation { get; set; } = "BH01_WALLRUN_RIGHT";
    [Export(PropertyHint.Range, "0,15,0.1,suffix:m/s")] public float RunEnterSpeed { get; set; } = 2.0f;
    [Export(PropertyHint.Range, "0,15,0.1,suffix:m/s")] public float RunExitSpeed { get; set; } = 1.0f;
    [Export(PropertyHint.Range, "0.1,3,0.05")] public float RunPlaybackSpeedScale { get; set; } = 1.0f;

    public string LocomotionState { get; private set; } = "Idle";
    public float HorizontalSpeed { get; private set; }
    private bool _runningAnimation;

    private StringName SelectLocomotionAnimation()
    {
        Vector3 velocity = _player.Velocity;
        HorizontalSpeed = new Vector2(velocity.X, velocity.Z).Length();
        _runningAnimation = !_sliding && _player.WallRunModule?.IsWallRunning != true
            && _player.IsGrounded
            && HorizontalSpeed >= (_runningAnimation ? Mathf.Min(RunExitSpeed, RunEnterSpeed) : RunEnterSpeed);
        if (_sliding) { LocomotionState = "Slide"; return SlideAnimation; }
        var wall = _player.WallRunModule;
        if (wall?.IsWallRunning == true)
        {
            if (wall.ActiveWallSide == PlayerWallRunModule.WallSide.Left)
            { LocomotionState = "WallrunLeft"; return WallrunLeftAnimation; }
            if (wall.ActiveWallSide == PlayerWallRunModule.WallSide.Right)
            { LocomotionState = "WallrunRight"; return WallrunRightAnimation; }
        }
        LocomotionState = _runningAnimation ? "Run" : "Idle";
        return _runningAnimation ? RunAnimation : IdleAnimation;
    }
}
