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
    private Vector3 _lookAssistTarget;
    private float _lookAssistTimer;
    private float _lookAssistDuration;
    private float _lookAssistStrength = 1.0f;
    private float _lookAssistSpeed = 18.0f;
    private float _lookAssistMaxPitchRadians = Mathf.DegToRad(85.0f);
    private bool _lockLookInputDuringAssist;
    private bool _isTemporaryLookAssistActive;

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

    public override void _Process(double delta)
    {
        UpdateTemporaryLookAssist((float)delta);
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

        if (_isTemporaryLookAssistActive && _lockLookInputDuringAssist)
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
    /// Запускает временную доводку взгляда к мировой точке. Увеличение duration/speed/strength делает assist дольше, быстрее или сильнее; после окончания обычный mouse look возвращается.
    /// </summary>
    public void RequestTemporaryLookAt(Vector3 worldTarget, float duration, float strength, float speed, bool lockPlayerInput, float maxPitchDegrees)
    {
        if (_player == null || duration <= 0.0f || strength <= 0.0f)
        {
            return;
        }

        _lookAssistTarget = worldTarget;
        _lookAssistDuration = duration;
        _lookAssistTimer = duration;
        _lookAssistStrength = Mathf.Clamp(strength, 0.0f, 1.0f);
        _lookAssistSpeed = Mathf.Max(0.01f, speed);
        _lockLookInputDuringAssist = lockPlayerInput;
        _lookAssistMaxPitchRadians = Mathf.DegToRad(Mathf.Clamp(maxPitchDegrees, 0.0f, 89.0f));
        _isTemporaryLookAssistActive = true;
    }

    /// <summary>
    /// Запускает короткую доводку взгляда к grapple anchor с параметрами, переданными slingshot grapple-модулем.
    /// </summary>
    public void RequestGrappleLookAssist(Vector3 worldTarget, float duration, float strength, float speed, bool lockPlayerInput, float maxPitchDegrees)
    {
        RequestTemporaryLookAt(worldTarget, duration, strength, speed, lockPlayerInput, maxPitchDegrees);
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

    private void UpdateTemporaryLookAssist(float delta)
    {
        if (!_isTemporaryLookAssistActive || _player == null)
        {
            return;
        }

        if (Input.MouseMode != Input.MouseModeEnum.Captured)
        {
            StopTemporaryLookAssist();
            return;
        }

        _lookAssistTimer -= delta;

        Vector3 lookOrigin = _player.CameraPivot?.GlobalPosition ?? _player.GlobalPosition;
        Vector3 direction = _lookAssistTarget - lookOrigin;
        if (direction.LengthSquared() <= 0.0001f)
        {
            StopTemporaryLookAssist();
            return;
        }

        direction = direction.Normalized();
        float targetYaw = Mathf.Atan2(-direction.X, -direction.Z);
        float targetPitch = Mathf.Clamp(Mathf.Asin(direction.Y), -_lookAssistMaxPitchRadians, _lookAssistMaxPitchRadians);
        float progress = _lookAssistDuration > 0.0f ? 1.0f - Mathf.Clamp(_lookAssistTimer / _lookAssistDuration, 0.0f, 1.0f) : 1.0f;
        float strength = _lookAssistStrength * progress;
        float t = (1.0f - Mathf.Exp(-_lookAssistSpeed * delta)) * strength;

        Vector3 playerRotation = _player.Rotation;
        playerRotation.Y = Mathf.LerpAngle(playerRotation.Y, targetYaw, t);
        _player.Rotation = playerRotation;

        _pitch = Mathf.Lerp(_pitch, targetPitch, t);
        _pitch = Mathf.Clamp(_pitch, Mathf.DegToRad(MinPitch), Mathf.DegToRad(MaxPitch));

        Vector3 pivotRotation = _player.CameraPivot.Rotation;
        pivotRotation.X = _pitch;
        pivotRotation.Y = 0.0f;
        pivotRotation.Z = 0.0f;
        _player.CameraPivot.Rotation = pivotRotation;

        if (_lookAssistTimer <= 0.0f)
        {
            StopTemporaryLookAssist();
        }
    }

    private void StopTemporaryLookAssist()
    {
        _lookAssistTimer = 0.0f;
        _isTemporaryLookAssistActive = false;
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
