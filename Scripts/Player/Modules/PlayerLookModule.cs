using Godot;

public partial class PlayerLookModule : Node
{
    /// <summary>
    /// Чувствительность обзора мышью. Увеличение ускоряет поворот камеры и игрока; уменьшение делает наведение медленнее и точнее.
    /// </summary>
    [ExportGroup("Обзор")]
    [Export(PropertyHint.Range, "0.0001,0.02,0.0001")] public float MouseSensitivity { get; set; } = 0.003f;

    /// <summary>
    /// Нижний предел вертикального угла камеры в градусах. Более отрицательное значение позволяет сильнее смотреть вниз; значение ближе к 0 ограничивает наклон вниз.
    /// </summary>
    [Export(PropertyHint.Range, "-89,0,1,suffix:deg")] public float MinPitch { get; set; } = -80.0f;

    /// <summary>
    /// Верхний предел вертикального угла камеры в градусах. Большее значение позволяет выше смотреть вверх; значение ближе к 0 ограничивает наклон вверх.
    /// </summary>
    [Export(PropertyHint.Range, "0,89,1,suffix:deg")] public float MaxPitch { get; set; } = 80.0f;

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
