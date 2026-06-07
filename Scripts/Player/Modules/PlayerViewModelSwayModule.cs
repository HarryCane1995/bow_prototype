using Godot;

public partial class PlayerViewModelSwayModule : Node
{
    /// <summary>
    /// Путь к визуальному pivot-узлу viewmodel. Модуль двигает только этот Node3D и не меняет игровые камеры или направление стрельбы.
    /// </summary>
    [ExportGroup("References")]
    [Export] public NodePath ViewModelSwayRootPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelSwayRoot");

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
    /// Печатает landing impulse и debug-данные sway в Output Godot.
    /// </summary>
    [ExportGroup("Debug")]
    [Export] public bool DebugPrintSway { get; set; } = false;

    private PlayerController _player;
    private Node3D _viewModelSwayRoot;
    private Vector3 _basePosition;
    private Vector3 _baseRotationDegrees;
    private Vector3 _previousVelocity;
    private bool _previousIsOnFloor;
    private Vector3 _currentPositionOffset;
    private Vector3 _currentRotationOffsetDegrees;
    private Vector3 _landingPositionImpulse;
    private Vector3 _landingRotationImpulseDegrees;

    /// <summary>
    /// Инициализирует sway-модуль, сохраняет базовый transform ViewModelSwayRoot и стартовое состояние игрока.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        _viewModelSwayRoot = GetNodeOrNull<Node3D>(ViewModelSwayRootPath) ?? FindNode3DByName(GetTree().CurrentScene, "ViewModelSwayRoot");

        if (_viewModelSwayRoot == null)
        {
            GD.PushWarning($"{nameof(PlayerViewModelSwayModule)} could not find ViewModelSwayRoot at '{ViewModelSwayRootPath}'. Viewmodel sway is disabled.");
            return;
        }

        _basePosition = _viewModelSwayRoot.Position;
        _baseRotationDegrees = _viewModelSwayRoot.RotationDegrees;
        _previousVelocity = _player.Velocity;
        _previousIsOnFloor = _player.IsGrounded;
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

        Vector3 targetPositionOffset = Vector3.Zero;
        Vector3 targetRotationOffsetDegrees = Vector3.Zero;

        AddMouseLag(ref targetPositionOffset, ref targetRotationOffsetDegrees);
        AddMovementInertia(deltaFloat, currentVelocity, ref targetPositionOffset, ref targetRotationOffsetDegrees);
        AddLandingImpulse(currentVelocity, currentIsOnFloor);

        float positionSpeed = targetPositionOffset.LengthSquared() > _currentPositionOffset.LengthSquared() ? CurrentSwayFollowSpeed : CurrentSwayReturnSpeed;
        float rotationSpeed = targetRotationOffsetDegrees.LengthSquared() > _currentRotationOffsetDegrees.LengthSquared() ? CurrentSwayFollowSpeed : CurrentSwayReturnSpeed;

        _currentPositionOffset = SmoothVector(_currentPositionOffset, targetPositionOffset, positionSpeed, deltaFloat);
        _currentRotationOffsetDegrees = SmoothVector(_currentRotationOffsetDegrees, targetRotationOffsetDegrees, rotationSpeed, deltaFloat);
        _landingPositionImpulse = SmoothVector(_landingPositionImpulse, Vector3.Zero, CurrentImpulseReturnSpeed, deltaFloat);
        _landingRotationImpulseDegrees = SmoothVector(_landingRotationImpulseDegrees, Vector3.Zero, CurrentImpulseReturnSpeed, deltaFloat);

        float maxPositionOffset = Mathf.Max(Mathf.Max(MouseLagMaxPositionOffset, MovementInertiaMaxPositionOffset), LandingMaxPositionOffset);
        float maxRotationDegrees = Mathf.Max(Mathf.Max(MouseLagMaxRotationDegrees, MovementInertiaMaxRotationDegrees), LandingMaxRotationDegrees);
        Vector3 finalPositionOffset = ClampVectorLength(_currentPositionOffset + _landingPositionImpulse, maxPositionOffset);
        Vector3 finalRotationOffset = ClampVectorLength(_currentRotationOffsetDegrees + _landingRotationImpulseDegrees, maxRotationDegrees);

        _viewModelSwayRoot.Position = _basePosition + finalPositionOffset;
        _viewModelSwayRoot.RotationDegrees = _baseRotationDegrees + finalRotationOffset;

        _previousVelocity = currentVelocity;
        _previousIsOnFloor = currentIsOnFloor;
    }

    private void AddMouseLag(ref Vector3 positionOffset, ref Vector3 rotationOffsetDegrees)
    {
        Vector2 lookDelta = _player.LookModule?.ConsumeLookDelta() ?? Vector2.Zero;
        if (!CurrentEnableMouseLag || lookDelta == Vector2.Zero)
        {
            return;
        }

        Vector3 mousePosition = new(
            -lookDelta.X * CurrentMouseLagPositionAmount,
            lookDelta.Y * CurrentMouseLagPositionAmount,
            0.0f);
        Vector3 mouseRotation = new(
            -lookDelta.Y * CurrentMouseLagRotationAmount,
            -lookDelta.X * CurrentMouseLagRotationAmount,
            -lookDelta.X * CurrentMouseLagRotationAmount * 0.35f);

        positionOffset += ClampVectorLength(mousePosition, MouseLagMaxPositionOffset);
        rotationOffsetDegrees += ClampVectorLength(mouseRotation, MouseLagMaxRotationDegrees);
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
        float t = 1.0f - Mathf.Exp(-Mathf.Max(0.0f, speed) * delta);
        return from.Lerp(to, t);
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
    private bool CurrentEnableMouseLag => TuningProfile?.EnableMouseLag ?? EnableMouseLag;
    private float CurrentMouseLagPositionAmount => TuningProfile?.MouseLagPositionAmount ?? MouseLagPositionAmount;
    private float CurrentMouseLagRotationAmount => TuningProfile?.MouseLagRotationAmount ?? MouseLagRotationAmount;
    private bool CurrentEnableMovementInertia => TuningProfile?.EnableMovementInertia ?? EnableMovementInertia;
    private float CurrentMovementInertiaPositionAmount => TuningProfile?.MovementInertiaPositionAmount ?? MovementInertiaPositionAmount;
    private float CurrentMovementInertiaRotationAmount => TuningProfile?.MovementInertiaRotationAmount ?? MovementInertiaRotationAmount;
    private bool CurrentEnableLandingSway => TuningProfile?.EnableLandingSway ?? EnableLandingSway;
    private float CurrentLandingPositionAmount => TuningProfile?.LandingPositionAmount ?? LandingPositionAmount;
    private float CurrentLandingRotationAmount => TuningProfile?.LandingRotationAmount ?? LandingRotationAmount;
    private float CurrentSwayFollowSpeed => TuningProfile?.SwayFollowSpeed ?? SwayFollowSpeed;
    private float CurrentSwayReturnSpeed => TuningProfile?.SwayReturnSpeed ?? SwayReturnSpeed;
    private float CurrentImpulseReturnSpeed => TuningProfile?.ImpulseReturnSpeed ?? ImpulseReturnSpeed;
}
