using Godot;

public partial class PlayerCameraFovModule : Node
{
    /// <summary>
    /// Путь к основной FPS-камере. Смена пути выбирает другую камеру для FOV-эффекта; неверный путь заставит модуль использовать камеру игрока.
    /// </summary>
    [ExportGroup("Камера")]
    [Export] public NodePath CameraPath { get; set; } = new("../CameraPivot/Camera3D");

    /// <summary>
    /// Базовый угол обзора игрока в градусах. Увеличение расширяет обзор; уменьшение приближает картинку и служит точкой возврата после precision shot.
    /// </summary>
    [Export(PropertyHint.Range, "50,110,1,suffix:°")] public float PlayerFov { get; set; } = 75.0f;

    /// <summary>
    /// FOV камеры при precision aiming в градусах. Меньшее значение сильнее приближает; большее значение делает sniper-эффект мягче.
    /// </summary>
    [Export(PropertyHint.Range, "20,90,0.5,suffix:deg")] public float PrecisionFov { get; set; } = 45.0f;

    /// <summary>
    /// Скорость плавного перехода FOV в градусах в секунду. Увеличение делает zoom быстрее; уменьшение делает вход и выход мягче.
    /// </summary>
    [Export(PropertyHint.Range, "1,240,1,suffix:deg/s")] public float FovTransitionSpeed { get; set; } = 90.0f;

    private Camera3D _camera;
    private float _targetFov;
    private PlayerController _player;
    private bool _isPrecisionAiming;

    /// <summary>
    /// Инициализирует модуль и выставляет обычный FOV как текущую цель камеры.
    /// </summary>
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

        _targetFov = _isPrecisionAiming ? CurrentPrecisionFov : CurrentPlayerFov;
        _camera.Fov = Mathf.MoveToward(_camera.Fov, _targetFov, CurrentFovTransitionSpeed * (float)delta);
    }

    /// <summary>
    /// Переключает целевой FOV между обычным режимом и precision aiming.
    /// </summary>
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
