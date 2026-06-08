using Godot;

public partial class PlayerViewModelSwayModule : Node
{
    /// <summary>
    /// Путь к визуальному pivot-узлу viewmodel. Модуль двигает только этот Node3D и не меняет игровые камеры или направление стрельбы.
    /// </summary>
    [ExportGroup("References")]
    [Export] public NodePath ViewModelSwayRootPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelSwayRoot");

    /// <summary>
    /// Путь к viewmodel-камере, центральный луч которой используется только для визуальной стабилизации наконечника стрелы.
    /// </summary>
    [Export] public NodePath ViewModelCameraPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelCamera3D");

    /// <summary>
    /// Путь к Marker3D на визуальном наконечнике стрелы; если маркер не назначен, aim stabilization отключается без ошибки.
    /// </summary>
    [Export] public NodePath ArrowTipMarkerPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelSwayRoot/BowViewModelHolder/Bow_ViewModel/BowRig/NockPoint_Bone/Arrow_Bone/Arrow_Visual/ArrowTipMarker");

    /// <summary>
    /// Включает процедурный visual sway `ViewModelSwayRoot`; для диагностики jitter можно отключить без влияния на стрельбу.
    /// </summary>
    [ExportGroup("ViewModel Sway")]
    [Export] public bool EnableViewModelSway { get; set; } = true;

    /// <summary>
    /// Включает лёгкое отставание лука от движения мыши.
    /// </summary>
    [ExportGroup("Mouse Lag")]
    [Export] public bool EnableMouseLag { get; set; } = true;

    /// <summary>
    /// Сила позиционного сдвига от mouse look delta.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.08,0.001,suffix:m")] public float MouseLagPositionAmount { get; set; } = 0.015f;

    /// <summary>
    /// Сила поворота лука от mouse look delta.
    /// </summary>
    [Export(PropertyHint.Range, "0,8,0.1,suffix:deg")] public float MouseLagRotationAmount { get; set; } = 1.5f;

    /// <summary>
    /// Максимальный позиционный offset от mouse lag.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.2,0.001,suffix:m")] public float MouseLagMaxPositionOffset { get; set; } = 0.08f;

    /// <summary>
    /// Максимальный поворот от mouse lag в градусах.
    /// </summary>
    [Export(PropertyHint.Range, "0,20,0.1,suffix:deg")] public float MouseLagMaxRotationDegrees { get; set; } = 5.0f;

    /// <summary>
    /// Включает сглаживание mouse delta и итогового mouse lag offset, чтобы сильный mouse sway не дёргался каждый тик.
    /// </summary>
    [ExportGroup("Mouse Lag Smoothing")]
    [Export] public bool EnableMouseLagSmoothing { get; set; } = true;

    /// <summary>
    /// Скорость экспоненциального сглаживания входного mouse delta перед расчётом mouse lag.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,40,0.1")] public float MouseLagInputSmoothSpeed { get; set; } = 18.0f;

    /// <summary>
    /// Скорость экспоненциального сглаживания готового position/rotation offset от mouse lag.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,40,0.1")] public float MouseLagOutputSmoothSpeed { get; set; } = 12.0f;

    /// <summary>
    /// Включает инерцию viewmodel от изменения velocity игрока.
    /// </summary>
    [ExportGroup("Movement Inertia")]
    [Export] public bool EnableMovementInertia { get; set; } = true;

    /// <summary>
    /// Сила позиционного сдвига от горизонтального ускорения игрока.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.03,0.001,suffix:m")] public float MovementInertiaPositionAmount { get; set; } = 0.004f;

    /// <summary>
    /// Сила поворота от горизонтального ускорения игрока.
    /// </summary>
    [Export(PropertyHint.Range, "0,4,0.05,suffix:deg")] public float MovementInertiaRotationAmount { get; set; } = 0.35f;

    /// <summary>
    /// Максимальный позиционный offset от movement inertia.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.2,0.001,suffix:m")] public float MovementInertiaMaxPositionOffset { get; set; } = 0.10f;

    /// <summary>
    /// Максимальный поворот от movement inertia в градусах.
    /// </summary>
    [Export(PropertyHint.Range, "0,20,0.1,suffix:deg")] public float MovementInertiaMaxRotationDegrees { get; set; } = 6.0f;

    /// <summary>
    /// Ограничение величины рассчитанного ускорения, чтобы slide/slingshot не уводили лук за экран.
    /// </summary>
    [Export(PropertyHint.Range, "1,120,0.5")] public float MovementInertiaVelocityClamp { get; set; } = 40.0f;

    /// <summary>
    /// Включает короткую просадку лука при приземлении.
    /// </summary>
    [ExportGroup("Landing")]
    [Export] public bool EnableLandingSway { get; set; } = true;

    /// <summary>
    /// Минимальная вертикальная скорость падения, начиная с которой приземление даёт viewmodel impulse.
    /// </summary>
    [Export(PropertyHint.Range, "0,20,0.1,suffix:m/s")] public float LandingMinImpactSpeed { get; set; } = 4.0f;

    /// <summary>
    /// Сила вертикальной просадки лука при приземлении.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.1,0.001,suffix:m")] public float LandingPositionAmount { get; set; } = 0.025f;

    /// <summary>
    /// Сила кивка/поворота лука при приземлении.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.1,suffix:deg")] public float LandingRotationAmount { get; set; } = 2.0f;

    /// <summary>
    /// Максимальная позиционная просадка от landing impulse.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.2,0.001,suffix:m")] public float LandingMaxPositionOffset { get; set; } = 0.12f;

    /// <summary>
    /// Максимальный поворот от landing impulse.
    /// </summary>
    [Export(PropertyHint.Range, "0,20,0.1,suffix:deg")] public float LandingMaxRotationDegrees { get; set; } = 8.0f;

    /// <summary>
    /// Максимальная скорость падения, учитываемая landing impulse.
    /// </summary>
    [Export(PropertyHint.Range, "1,80,0.5,suffix:m/s")] public float LandingMaxImpactSpeed { get; set; } = 24.0f;

    /// <summary>
    /// Скорость следования к активному sway offset.
    /// </summary>
    [ExportGroup("Smoothing")]
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float SwayFollowSpeed { get; set; } = 12.0f;

    /// <summary>
    /// Скорость возврата viewmodel к базовому transform, когда input/acceleration затухают.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float SwayReturnSpeed { get; set; } = 10.0f;

    /// <summary>
    /// Скорость затухания landing impulse.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1")] public float ImpulseReturnSpeed { get; set; } = 14.0f;

    /// <summary>
    /// Включает отдельное сглаживание итогового rotation offset viewmodel.
    /// </summary>
    [ExportGroup("Rotation Smoothing")]
    [Export] public bool EnableRotationSmoothing { get; set; } = true;

    /// <summary>
    /// Скорость экспоненциального сглаживания итогового поворота viewmodel.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,40,0.1")] public float RotationSmoothSpeed { get; set; } = 14.0f;

    /// <summary>
    /// Скорость экспоненциального сглаживания итогового позиционного offset viewmodel.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,40,0.1")] public float PositionSmoothSpeed { get; set; } = 14.0f;

    /// <summary>
    /// Включает визуальную стабилизацию наконечника стрелы около центра viewmodel-камеры без изменения gameplay aim.
    /// </summary>
    [ExportGroup("Aim Stabilization")]
    [Export] public bool EnableAimStabilization { get; set; } = true;

    /// <summary>
    /// Сила корректирующего поворота: 0 не компенсирует sway, 1 стремится полностью совместить наконечник с center ray.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.01")] public float AimStabilizationStrength { get; set; } = 0.65f;

    /// <summary>
    /// Скорость экспоненциального сглаживания визуальной aim-stabilization correction.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,40,0.1")] public float AimStabilizationSmoothSpeed { get; set; } = 14.0f;

    /// <summary>
    /// Максимальный угол визуальной корректировки, чтобы лук не выворачивался при экстремальном sway.
    /// </summary>
    [Export(PropertyHint.Range, "0,30,0.5,suffix:deg")] public float MaxAimCorrectionDegrees { get; set; } = 12.0f;

    /// <summary>
    /// Минимальная глубина наконечника относительно viewmodel-камеры для стабильного расчёта center ray target.
    /// </summary>
    [Export(PropertyHint.Range, "0.01,10,0.01")] public float MinAimStabilizationDepth { get; set; } = 0.25f;

    /// <summary>
    /// Угловая dead zone в радианах; если наконечник уже почти на center ray, коррекция плавно затухает.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.2,0.005")] public float AimStabilizationDeadZone { get; set; } = 0.02f;

    /// <summary>
    /// Если включено, визуальная стабилизация работает только во время precision aiming.
    /// </summary>
    [Export] public bool StabilizeOnlyWhenAiming { get; set; } = false;

    /// <summary>
    /// Печатает debug-данные aim stabilization в Output Godot.
    /// </summary>
    [Export] public bool DebugDrawAimStabilization { get; set; } = false;

    /// <summary>
    /// Печатает landing impulse и debug-данные sway в Output Godot.
    /// </summary>
    [ExportGroup("Debug")]
    [Export] public bool DebugPrintSway { get; set; } = false;

    private PlayerController _player;
    private Node3D _viewModelSwayRoot;
    private Camera3D _viewModelCamera;
    private Node3D _arrowTipMarker;
    private Vector3 _basePosition;
    private Vector3 _baseRotationDegrees;
    private Vector3 _previousVelocity;
    private bool _previousIsOnFloor;
    private Vector2 _smoothedMouseDelta;
    private Vector3 _currentMouseLagPositionOffset;
    private Vector3 _currentMouseLagRotationOffsetDegrees;
    private Vector3 _currentPositionOffset;
    private Vector3 _currentRotationOffsetDegrees;
    private Vector3 _landingPositionImpulse;
    private Vector3 _landingRotationImpulseDegrees;
    private Vector3 _currentAimCorrectionAxisAngle;
    private bool _warnedMissingAimStabilizationReferences;

    /// <summary>
    /// Инициализирует sway-модуль, сохраняет базовый transform ViewModelSwayRoot и стартовое состояние игрока.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        _viewModelSwayRoot = GetNodeOrNull<Node3D>(ViewModelSwayRootPath) ?? FindNode3DByName(GetTree().CurrentScene, "ViewModelSwayRoot");
        _viewModelCamera = GetNodeOrNull<Camera3D>(ViewModelCameraPath) ?? FindNode3DByName(GetTree().CurrentScene, "ViewModelCamera3D") as Camera3D;
        _arrowTipMarker = GetNodeOrNull<Node3D>(ArrowTipMarkerPath) ?? FindNode3DByName(GetTree().CurrentScene, "ArrowTipMarker");

        if (_viewModelSwayRoot == null)
        {
            GD.PushWarning($"{nameof(PlayerViewModelSwayModule)} could not find ViewModelSwayRoot at '{ViewModelSwayRootPath}'. Viewmodel sway is disabled.");
            return;
        }

        _basePosition = _viewModelSwayRoot.Position;
        _baseRotationDegrees = _viewModelSwayRoot.RotationDegrees;
        _previousVelocity = _player.Velocity;
        _previousIsOnFloor = _player.IsGrounded;

        if (_viewModelCamera == null || _arrowTipMarker == null)
        {
            WarnMissingAimStabilizationReferences();
        }
    }

    public override void _Process(double delta)
    {
        if (_player == null || _viewModelSwayRoot == null)
        {
            return;
        }

        float deltaFloat = Mathf.Max(0.0001f, (float)delta);
        Vector3 currentVelocity = _player.Velocity;
        bool currentIsOnFloor = _player.IsGrounded;

        if (!CurrentEnableViewModelSway)
        {
            ResetViewModelSwayState();
            ApplyAimStabilization(deltaFloat);
            _previousVelocity = currentVelocity;
            _previousIsOnFloor = currentIsOnFloor;
            return;
        }

        Vector3 targetPositionOffset = Vector3.Zero;
        Vector3 targetRotationOffsetDegrees = Vector3.Zero;

        AddMouseLag(deltaFloat, ref targetPositionOffset, ref targetRotationOffsetDegrees);
        AddMovementInertia(deltaFloat, currentVelocity, ref targetPositionOffset, ref targetRotationOffsetDegrees);
        AddLandingImpulse(currentVelocity, currentIsOnFloor);

        float maxPositionOffset = Mathf.Max(Mathf.Max(MouseLagMaxPositionOffset, MovementInertiaMaxPositionOffset), LandingMaxPositionOffset);
        float maxRotationDegrees = Mathf.Max(Mathf.Max(MouseLagMaxRotationDegrees, MovementInertiaMaxRotationDegrees), LandingMaxRotationDegrees);
        targetPositionOffset = ClampVectorLength(targetPositionOffset, maxPositionOffset);
        targetRotationOffsetDegrees = ClampVectorLength(targetRotationOffsetDegrees, maxRotationDegrees);

        float positionSpeed = CurrentEnableRotationSmoothing
            ? CurrentPositionSmoothSpeed
            : (targetPositionOffset.LengthSquared() > _currentPositionOffset.LengthSquared() ? CurrentSwayFollowSpeed : CurrentSwayReturnSpeed);
        float rotationSpeed = CurrentEnableRotationSmoothing
            ? CurrentRotationSmoothSpeed
            : (targetRotationOffsetDegrees.LengthSquared() > _currentRotationOffsetDegrees.LengthSquared() ? CurrentSwayFollowSpeed : CurrentSwayReturnSpeed);

        _currentPositionOffset = ClampVectorLength(SmoothVector(_currentPositionOffset, targetPositionOffset, positionSpeed, deltaFloat), maxPositionOffset);
        _currentRotationOffsetDegrees = ClampVectorLength(SmoothVector(_currentRotationOffsetDegrees, targetRotationOffsetDegrees, rotationSpeed, deltaFloat), maxRotationDegrees);
        _landingPositionImpulse = SmoothVector(_landingPositionImpulse, Vector3.Zero, CurrentImpulseReturnSpeed, deltaFloat);
        _landingRotationImpulseDegrees = SmoothVector(_landingRotationImpulseDegrees, Vector3.Zero, CurrentImpulseReturnSpeed, deltaFloat);

        Vector3 finalPositionOffset = ClampVectorLength(_currentPositionOffset + _landingPositionImpulse, maxPositionOffset);
        Vector3 finalRotationOffset = ClampVectorLength(_currentRotationOffsetDegrees + _landingRotationImpulseDegrees, maxRotationDegrees);

        _viewModelSwayRoot.Position = _basePosition + finalPositionOffset;
        _viewModelSwayRoot.RotationDegrees = _baseRotationDegrees + finalRotationOffset;
        ApplyAimStabilization(deltaFloat);

        _previousVelocity = currentVelocity;
        _previousIsOnFloor = currentIsOnFloor;
    }

    /// <summary>
    /// Сбрасывает процедурные sway offsets к базовому transform для диагностического отключения viewmodel sway.
    /// </summary>
    private void ResetViewModelSwayState()
    {
        _smoothedMouseDelta = Vector2.Zero;
        _currentMouseLagPositionOffset = Vector3.Zero;
        _currentMouseLagRotationOffsetDegrees = Vector3.Zero;
        _currentPositionOffset = Vector3.Zero;
        _currentRotationOffsetDegrees = Vector3.Zero;
        _landingPositionImpulse = Vector3.Zero;
        _landingRotationImpulseDegrees = Vector3.Zero;
        _viewModelSwayRoot.Position = _basePosition;
        _viewModelSwayRoot.RotationDegrees = _baseRotationDegrees;
    }

    private void AddMouseLag(float delta, ref Vector3 positionOffset, ref Vector3 rotationOffsetDegrees)
    {
        Vector2 rawLookDelta = _player.LookModule?.ConsumeLookDelta() ?? Vector2.Zero;
        if (!CurrentEnableMouseLag)
        {
            _smoothedMouseDelta = Vector2.Zero;
            _currentMouseLagPositionOffset = SmoothVector(_currentMouseLagPositionOffset, Vector3.Zero, CurrentMouseLagOutputSmoothSpeed, delta);
            _currentMouseLagRotationOffsetDegrees = SmoothVector(_currentMouseLagRotationOffsetDegrees, Vector3.Zero, CurrentMouseLagOutputSmoothSpeed, delta);
            return;
        }

        _smoothedMouseDelta = CurrentEnableMouseLagSmoothing
            ? _smoothedMouseDelta.Lerp(rawLookDelta, GetExpSmoothingFactor(CurrentMouseLagInputSmoothSpeed, delta))
            : rawLookDelta;

        Vector3 mousePosition = new(
            -_smoothedMouseDelta.X * CurrentMouseLagPositionAmount,
            _smoothedMouseDelta.Y * CurrentMouseLagPositionAmount,
            0.0f);
        Vector3 mouseRotation = new(
            -_smoothedMouseDelta.Y * CurrentMouseLagRotationAmount,
            -_smoothedMouseDelta.X * CurrentMouseLagRotationAmount,
            -_smoothedMouseDelta.X * CurrentMouseLagRotationAmount * 0.35f);

        Vector3 targetMousePositionOffset = ClampVectorLength(mousePosition, MouseLagMaxPositionOffset);
        Vector3 targetMouseRotationOffset = ClampVectorLength(mouseRotation, MouseLagMaxRotationDegrees);

        if (CurrentEnableMouseLagSmoothing)
        {
            float outputFactor = GetExpSmoothingFactor(CurrentMouseLagOutputSmoothSpeed, delta);
            _currentMouseLagPositionOffset = _currentMouseLagPositionOffset.Lerp(targetMousePositionOffset, outputFactor);
            _currentMouseLagRotationOffsetDegrees = _currentMouseLagRotationOffsetDegrees.Lerp(targetMouseRotationOffset, outputFactor);
        }
        else
        {
            _currentMouseLagPositionOffset = targetMousePositionOffset;
            _currentMouseLagRotationOffsetDegrees = targetMouseRotationOffset;
        }

        _currentMouseLagPositionOffset = ClampVectorLength(_currentMouseLagPositionOffset, MouseLagMaxPositionOffset);
        _currentMouseLagRotationOffsetDegrees = ClampVectorLength(_currentMouseLagRotationOffsetDegrees, MouseLagMaxRotationDegrees);

        positionOffset += _currentMouseLagPositionOffset;
        rotationOffsetDegrees += _currentMouseLagRotationOffsetDegrees;
    }

    private void AddMovementInertia(float delta, Vector3 currentVelocity, ref Vector3 positionOffset, ref Vector3 rotationOffsetDegrees)
    {
        if (!CurrentEnableMovementInertia)
        {
            return;
        }

        Vector3 acceleration = (GetHorizontalVelocity(currentVelocity) - GetHorizontalVelocity(_previousVelocity)) / delta;
        acceleration = ClampVectorLength(acceleration, MovementInertiaVelocityClamp);

        if (acceleration.LengthSquared() <= 0.0001f)
        {
            return;
        }

        Vector2 localAcceleration = GetCameraLocalHorizontal(acceleration);
        Vector3 inertiaPosition = new(
            -localAcceleration.X * CurrentMovementInertiaPositionAmount,
            0.0f,
            localAcceleration.Y * CurrentMovementInertiaPositionAmount * 0.4f);
        Vector3 inertiaRotation = new(
            -localAcceleration.Y * CurrentMovementInertiaRotationAmount,
            0.0f,
            localAcceleration.X * CurrentMovementInertiaRotationAmount);

        positionOffset += ClampVectorLength(inertiaPosition, MovementInertiaMaxPositionOffset);
        rotationOffsetDegrees += ClampVectorLength(inertiaRotation, MovementInertiaMaxRotationDegrees);
    }

    private void AddLandingImpulse(Vector3 currentVelocity, bool currentIsOnFloor)
    {
        if (!CurrentEnableLandingSway || _previousIsOnFloor || !currentIsOnFloor)
        {
            return;
        }

        float fallSpeed = Mathf.Abs(_previousVelocity.Y);
        if (fallSpeed < LandingMinImpactSpeed)
        {
            return;
        }

        float impact = Mathf.Clamp(fallSpeed, 0.0f, LandingMaxImpactSpeed);
        _landingPositionImpulse += new Vector3(0.0f, -impact * CurrentLandingPositionAmount, 0.0f);
        _landingRotationImpulseDegrees += new Vector3(-impact * CurrentLandingRotationAmount, 0.0f, 0.0f);
        _landingPositionImpulse = ClampVectorLength(_landingPositionImpulse, LandingMaxPositionOffset);
        _landingRotationImpulseDegrees = ClampVectorLength(_landingRotationImpulseDegrees, LandingMaxRotationDegrees);

        if (DebugPrintSway)
        {
            GD.Print($"Viewmodel landing sway: fallSpeed={fallSpeed:0.00}, impact={impact:0.00}");
        }
    }

    private Vector2 GetCameraLocalHorizontal(Vector3 worldVector)
    {
        Basis basis = _player.Camera?.GlobalTransform.Basis.Orthonormalized() ?? _player.GlobalTransform.Basis.Orthonormalized();
        Vector3 right = GetHorizontalAxis(basis.X, _player.GlobalTransform.Basis.X);
        Vector3 forward = GetHorizontalAxis(-basis.Z, -_player.GlobalTransform.Basis.Z);
        return new Vector2(worldVector.Dot(right), worldVector.Dot(forward));
    }

    private Vector3 GetHorizontalAxis(Vector3 axis, Vector3 fallbackAxis)
    {
        axis.Y = 0.0f;
        if (axis.LengthSquared() == 0.0f)
        {
            axis = fallbackAxis;
            axis.Y = 0.0f;
        }

        return axis.LengthSquared() > 0.0f ? axis.Normalized() : Vector3.Zero;
    }

    private static Vector3 GetHorizontalVelocity(Vector3 velocity)
    {
        return new Vector3(velocity.X, 0.0f, velocity.Z);
    }

    private static Vector3 SmoothVector(Vector3 from, Vector3 to, float speed, float delta)
    {
        return from.Lerp(to, GetExpSmoothingFactor(speed, delta));
    }

    /// <summary>
    /// Добавляет поверх обычного sway мягкий визуальный поворот, который тянет ArrowTipMarker к центральному лучу ViewModelCamera3D.
    /// </summary>
    private void ApplyAimStabilization(float delta)
    {
        if (!ShouldApplyAimStabilization())
        {
            _currentAimCorrectionAxisAngle = SmoothVector(_currentAimCorrectionAxisAngle, Vector3.Zero, CurrentAimStabilizationSmoothSpeed, delta);
            ApplyAimCorrectionAxisAngle(_currentAimCorrectionAxisAngle);
            return;
        }

        Vector3 pivotPosition = _viewModelSwayRoot.GlobalPosition;
        Vector3 tipPosition = _arrowTipMarker.GlobalPosition;
        Vector3 cameraOrigin = _viewModelCamera.GlobalPosition;
        Vector3 cameraForward = -_viewModelCamera.GlobalTransform.Basis.Z.Normalized();
        float depth = Mathf.Max(CurrentMinAimStabilizationDepth, (tipPosition - cameraOrigin).Dot(cameraForward));
        Vector3 targetTipPosition = cameraOrigin + cameraForward * depth;

        Vector3 currentPivotToTip = tipPosition - pivotPosition;
        Vector3 desiredPivotToTip = targetTipPosition - pivotPosition;
        Vector3 targetCorrection = CalculateAimCorrectionAxisAngle(currentPivotToTip, desiredPivotToTip);

        _currentAimCorrectionAxisAngle = SmoothVector(_currentAimCorrectionAxisAngle, targetCorrection, CurrentAimStabilizationSmoothSpeed, delta);
        _currentAimCorrectionAxisAngle = ClampAxisAngle(_currentAimCorrectionAxisAngle, Mathf.DegToRad(CurrentMaxAimCorrectionDegrees));
        ApplyAimCorrectionAxisAngle(_currentAimCorrectionAxisAngle);

        if (DebugDrawAimStabilization)
        {
            GD.Print($"Viewmodel aim stabilization: depth={depth:0.000}, correctionDeg={Mathf.RadToDeg(_currentAimCorrectionAxisAngle.Length()):0.00}");
        }
    }

    /// <summary>
    /// Проверяет, можно ли применять визуальную стабилизацию на текущем кадре.
    /// </summary>
    private bool ShouldApplyAimStabilization()
    {
        if (!CurrentEnableAimStabilization)
        {
            return false;
        }

        if (_viewModelCamera == null || _arrowTipMarker == null)
        {
            WarnMissingAimStabilizationReferences();
            return false;
        }

        return !CurrentStabilizeOnlyWhenAiming || _player.CameraFovModule?.IsPrecisionAiming == true;
    }

    /// <summary>
    /// Рассчитывает axis-angle correction, которая поворачивает вектор pivot->tip к target-вектору с учётом силы и clamp.
    /// </summary>
    private Vector3 CalculateAimCorrectionAxisAngle(Vector3 currentPivotToTip, Vector3 desiredPivotToTip)
    {
        if (currentPivotToTip.LengthSquared() <= 0.000001f || desiredPivotToTip.LengthSquared() <= 0.000001f)
        {
            return Vector3.Zero;
        }

        Vector3 currentDirection = currentPivotToTip.Normalized();
        Vector3 desiredDirection = desiredPivotToTip.Normalized();
        float angle = currentDirection.AngleTo(desiredDirection);
        if (angle <= CurrentAimStabilizationDeadZone)
        {
            return Vector3.Zero;
        }

        Vector3 axis = currentDirection.Cross(desiredDirection);
        if (axis.LengthSquared() <= 0.000001f)
        {
            return Vector3.Zero;
        }

        float correctionAngle = Mathf.Min(
            angle * Mathf.Clamp(CurrentAimStabilizationStrength, 0.0f, 1.0f),
            Mathf.DegToRad(CurrentMaxAimCorrectionDegrees));
        return axis.Normalized() * correctionAngle;
    }

    /// <summary>
    /// Применяет сглаженный axis-angle correction к global basis ViewModelSwayRoot, не меняя gameplay camera или projectile direction.
    /// </summary>
    private void ApplyAimCorrectionAxisAngle(Vector3 axisAngle)
    {
        float angle = axisAngle.Length();
        if (angle <= 0.000001f)
        {
            return;
        }

        Vector3 axis = axisAngle / angle;
        Transform3D transform = _viewModelSwayRoot.GlobalTransform;
        transform.Basis = new Basis(axis, angle) * transform.Basis;
        _viewModelSwayRoot.GlobalTransform = transform;
    }

    /// <summary>
    /// Ограничивает axis-angle вектор максимальным углом коррекции.
    /// </summary>
    private static Vector3 ClampAxisAngle(Vector3 axisAngle, float maxAngleRadians)
    {
        return ClampVectorLength(axisAngle, maxAngleRadians);
    }

    /// <summary>
    /// Один раз предупреждает о недостающих ссылках aim stabilization, чтобы модуль отключался спокойно.
    /// </summary>
    private void WarnMissingAimStabilizationReferences()
    {
        if (_warnedMissingAimStabilizationReferences || !CurrentEnableAimStabilization)
        {
            return;
        }

        _warnedMissingAimStabilizationReferences = true;
        GD.PushWarning($"{nameof(PlayerViewModelSwayModule)} aim stabilization is disabled because ViewModelCamera3D or ArrowTipMarker was not found. ViewModelCameraPath='{ViewModelCameraPath}', ArrowTipMarkerPath='{ArrowTipMarkerPath}'.");
    }

    /// <summary>
    /// Возвращает factor для framerate-independent exponential smoothing.
    /// </summary>
    private static float GetExpSmoothingFactor(float speed, float delta)
    {
        return 1.0f - Mathf.Exp(-Mathf.Max(0.0f, speed) * delta);
    }

    private static Vector3 ClampVectorLength(Vector3 vector, float maxLength)
    {
        maxLength = Mathf.Max(0.0f, maxLength);
        if (maxLength <= 0.0f || vector.LengthSquared() <= maxLength * maxLength)
        {
            return vector;
        }

        return vector.Normalized() * maxLength;
    }

    private static Node3D FindNode3DByName(Node root, string nodeName)
    {
        if (root == null)
        {
            return null;
        }

        foreach (Node child in root.GetChildren())
        {
            if (child is Node3D node3D && child.Name == nodeName)
            {
                return node3D;
            }

            Node3D nestedMatch = FindNode3DByName(child, nodeName);
            if (nestedMatch != null)
            {
                return nestedMatch;
            }
        }

        return null;
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private bool CurrentEnableViewModelSway => TuningProfile?.EnableViewModelSway ?? EnableViewModelSway;
    private bool CurrentEnableMouseLag => TuningProfile?.EnableMouseLag ?? EnableMouseLag;
    private float CurrentMouseLagPositionAmount => TuningProfile?.MouseLagPositionAmount ?? MouseLagPositionAmount;
    private float CurrentMouseLagRotationAmount => TuningProfile?.MouseLagRotationAmount ?? MouseLagRotationAmount;
    private bool CurrentEnableMouseLagSmoothing => TuningProfile?.EnableMouseLagSmoothing ?? EnableMouseLagSmoothing;
    private float CurrentMouseLagInputSmoothSpeed => TuningProfile?.MouseLagInputSmoothSpeed ?? MouseLagInputSmoothSpeed;
    private float CurrentMouseLagOutputSmoothSpeed => TuningProfile?.MouseLagOutputSmoothSpeed ?? MouseLagOutputSmoothSpeed;
    private bool CurrentEnableMovementInertia => TuningProfile?.EnableMovementInertia ?? EnableMovementInertia;
    private float CurrentMovementInertiaPositionAmount => TuningProfile?.MovementInertiaPositionAmount ?? MovementInertiaPositionAmount;
    private float CurrentMovementInertiaRotationAmount => TuningProfile?.MovementInertiaRotationAmount ?? MovementInertiaRotationAmount;
    private bool CurrentEnableLandingSway => TuningProfile?.EnableLandingSway ?? EnableLandingSway;
    private float CurrentLandingPositionAmount => TuningProfile?.LandingPositionAmount ?? LandingPositionAmount;
    private float CurrentLandingRotationAmount => TuningProfile?.LandingRotationAmount ?? LandingRotationAmount;
    private float CurrentSwayFollowSpeed => TuningProfile?.SwayFollowSpeed ?? SwayFollowSpeed;
    private float CurrentSwayReturnSpeed => TuningProfile?.SwayReturnSpeed ?? SwayReturnSpeed;
    private float CurrentImpulseReturnSpeed => TuningProfile?.ImpulseReturnSpeed ?? ImpulseReturnSpeed;
    private bool CurrentEnableRotationSmoothing => TuningProfile?.EnableRotationSmoothing ?? EnableRotationSmoothing;
    private float CurrentRotationSmoothSpeed => TuningProfile?.RotationSmoothSpeed ?? RotationSmoothSpeed;
    private float CurrentPositionSmoothSpeed => TuningProfile?.PositionSmoothSpeed ?? PositionSmoothSpeed;
    private bool CurrentEnableAimStabilization => TuningProfile?.EnableAimStabilization ?? EnableAimStabilization;
    private float CurrentAimStabilizationStrength => TuningProfile?.AimStabilizationStrength ?? AimStabilizationStrength;
    private float CurrentAimStabilizationSmoothSpeed => TuningProfile?.AimStabilizationSmoothSpeed ?? AimStabilizationSmoothSpeed;
    private float CurrentMaxAimCorrectionDegrees => TuningProfile?.MaxAimCorrectionDegrees ?? MaxAimCorrectionDegrees;
    private float CurrentMinAimStabilizationDepth => MinAimStabilizationDepth;
    private float CurrentAimStabilizationDeadZone => TuningProfile?.AimStabilizationDeadZone ?? AimStabilizationDeadZone;
    private bool CurrentStabilizeOnlyWhenAiming => TuningProfile?.StabilizeOnlyWhenAiming ?? StabilizeOnlyWhenAiming;
}
