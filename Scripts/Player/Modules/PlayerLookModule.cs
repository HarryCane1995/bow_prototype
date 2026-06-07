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

    /// <summary>
    /// Имя Input Map action для освобождения курсора. Esc делает курсор видимым; смена имени требует соответствующей настройки InputMap.
    /// </summary>
    private const string ReleaseMouseAction = "ui_cancel";

    /// <summary>
    /// Имя Input Map action для dev-перезапуска текущей сцены. F1 перезагружает сцену; смена имени требует соответствующей настройки InputMap.
    /// </summary>
    private const string ReloadSceneAction = "reload_scene";

    private PlayerController _player;
    private float _pitch;

    /// <summary>
    /// Накопленный mouse look delta с последнего чтения procedural viewmodel-эффектами.
    /// </summary>
    public Vector2 LastLookDelta { get; private set; }

    /// <summary>
    /// Инициализирует модуль обзора, добавляет dev actions при необходимости и сразу захватывает мышь для FPS-управления.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        _pitch = _player.CameraPivot.Rotation.X;
        EnsureDevInputActions();
        CaptureMouse();
    }

    /// <summary>
    /// Обрабатывает dev hotkeys и mouse look. Esc освобождает курсор, ЛКМ захватывает его обратно, F1 перезапускает текущую сцену.
    /// </summary>
    public void HandleInput(InputEvent @event)
    {
        if (HandleDevInput(@event) || Input.MouseMode != Input.MouseModeEnum.Captured)
        {
            return;
        }

        if (@event is not InputEventMouseMotion mouseMotion)
        {
            return;
        }

        LastLookDelta += mouseMotion.Relative;
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

    /// <summary>
    /// Возвращает накопленный mouse look delta и сбрасывает его, чтобы визуальные эффекты не держали старый input.
    /// </summary>
    public Vector2 ConsumeLookDelta()
    {
        Vector2 lookDelta = LastLookDelta;
        LastLookDelta = Vector2.Zero;
        return lookDelta;
    }

    /// <summary>
    /// Обрабатывает служебные действия для play mode: release/capture мыши и быстрый перезапуск текущей сцены.
    /// </summary>
    private bool HandleDevInput(InputEvent @event)
    {
        if (@event.IsActionPressed(ReloadSceneAction))
        {
            GetTree().ReloadCurrentScene();
            return true;
        }

        if (@event.IsActionPressed(ReleaseMouseAction))
        {
            ReleaseMouse();
            return true;
        }

        if (Input.MouseMode != Input.MouseModeEnum.Captured
            && @event is InputEventMouseButton { ButtonIndex: MouseButton.Left, Pressed: true })
        {
            CaptureMouse();
            return true;
        }

        return false;
    }

    /// <summary>
    /// Захватывает курсор мыши для FPS-управления. После вызова mouse motion снова вращает игрока и камеру.
    /// </summary>
    private static void CaptureMouse()
    {
        Input.MouseMode = Input.MouseModeEnum.Captured;
    }

    /// <summary>
    /// Освобождает курсор мыши для работы с окном и редактором. Пока курсор видим, mouse look не обрабатывается.
    /// </summary>
    private static void ReleaseMouse()
    {
        Input.MouseMode = Input.MouseModeEnum.Visible;
    }

    /// <summary>
    /// Гарантирует наличие dev actions в InputMap, чтобы Esc и F1 работали в play mode даже без ручной настройки проекта.
    /// </summary>
    private static void EnsureDevInputActions()
    {
        EnsureKeyAction(ReleaseMouseAction, Key.Escape);
        EnsureKeyAction(ReloadSceneAction, Key.F1);
    }

    /// <summary>
    /// Добавляет InputMap action и клавишу, если такой action или такая привязка ещё отсутствуют.
    /// </summary>
    private static void EnsureKeyAction(string actionName, Key key)
    {
        if (!InputMap.HasAction(actionName))
        {
            InputMap.AddAction(actionName);
        }

        InputEventKey keyEvent = new()
        {
            Keycode = key,
            PhysicalKeycode = key
        };

        if (!InputMap.ActionHasEvent(actionName, keyEvent))
        {
            InputMap.ActionAddEvent(actionName, keyEvent);
        }
    }
}
