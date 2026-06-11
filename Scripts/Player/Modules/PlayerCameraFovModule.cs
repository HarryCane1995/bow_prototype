using Godot;

public partial class PlayerCameraFovModule : Node
{
    // Owns the final gameplay Camera3D.Fov value; other modules feed inputs, not camera writes.
    [ExportGroup("Камера")]
    [Export] public NodePath CameraPath { get; set; } = new("../CameraPivot/Camera3D");

    [Export(PropertyHint.Range, "50,110,1,suffix:°")] public float PlayerFov { get; set; } = 75.0f;

    [Export(PropertyHint.Range, "20,90,0.5,suffix:deg")] public float PrecisionFov { get; set; } = 45.0f;

    [Export(PropertyHint.Range, "1,240,1,suffix:deg/s")] public float FovTransitionSpeed { get; set; } = 90.0f;

    private Camera3D _camera;
    private float _targetFov;
    private PlayerController _player;
    private bool _isPrecisionAiming;

    public bool IsPrecisionAiming => _isPrecisionAiming;

    public float FinalTargetFov => _targetFov;

    public float CurrentCameraFov => _camera?.Fov ?? 0.0f;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _camera = GetNodeOrNull<Camera3D>(CameraPath) ?? player.Camera;
        _targetFov = CurrentPlayerFov;

        if (_camera != null)
        {
            _camera.Fov = CurrentPlayerFov;
        }
    }

    public override void _Process(double delta)
    {
        if (_camera == null)
        {
            return;
        }

        float baseTargetFov = _isPrecisionAiming ? CurrentPrecisionFov : CurrentPlayerFov;
        float speedFovBonus = _player.SpeedFovModule?.UpdateSpeedFovBonus(delta, _isPrecisionAiming) ?? 0.0f;
        _targetFov = Mathf.Min(baseTargetFov + speedFovBonus, 140.0f);
        _camera.Fov = Mathf.MoveToward(_camera.Fov, _targetFov, CurrentFovTransitionSpeed * (float)delta);
    }

    public void SetPrecisionAiming(bool isPrecisionAiming)
    {
        _isPrecisionAiming = isPrecisionAiming;
        _targetFov = isPrecisionAiming ? CurrentPrecisionFov : CurrentPlayerFov;
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private float CurrentPlayerFov => TuningProfile?.PlayerFov ?? PlayerFov;
    private float CurrentPrecisionFov => TuningProfile?.PrecisionFov ?? PrecisionFov;
    private float CurrentFovTransitionSpeed => TuningProfile?.FovTransitionSpeed ?? FovTransitionSpeed;
}
