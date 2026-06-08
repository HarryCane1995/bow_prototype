using Godot;

public partial class PlayerCrouchSlideModule : Node
{
    private enum CrouchSlideState
    {
        Standing,
        Crouching,
        Sliding
    }

    /// <summary>
    /// Путь к CollisionShape3D игрока. Неверный путь отключит изменение высоты коллайдера при crouch и slide.
    /// </summary>
    [ExportGroup("Ссылки")]
    [Export] public NodePath CollisionShapePath { get; set; } = new("../CollisionShape3D");

    /// <summary>
    /// Путь к pivot-узлу камеры игрока. Неверный путь отключит плавное опускание камеры при crouch и slide.
    /// </summary>
    [Export] public NodePath CameraPivotPath { get; set; } = new("../CameraPivot");

    /// <summary>
    /// Имя Input Map action для приседа и подката. Смена имени требует такой же action в InputMap; по умолчанию модуль добавляет Ctrl и C.
    /// </summary>
    [ExportGroup("Input")]
    [Export] public string CrouchSlideAction { get; set; } = "crouch_slide";

    /// <summary>
    /// Включает обычный присед. Если выключить, удержание crouch_slide не будет опускать игрока без старта slide.
    /// </summary>
    [ExportGroup("Crouch")]
    [Export] public bool EnableCrouch { get; set; } = true;

    /// <summary>
    /// Высота коллайдера игрока в обычном стоячем состоянии. Увеличение делает игрока выше; уменьшение снижает полный рост.
    /// </summary>
    [Export(PropertyHint.Range, "0.5,3,0.05,suffix:m")] public float StandingColliderHeight { get; set; } = 1.8f;

    /// <summary>
    /// Высота коллайдера игрока в приседе и подкате. Увеличение делает crouch выше; уменьшение позволяет пролезать ниже.
    /// </summary>
    [Export(PropertyHint.Range, "0.4,2,0.05,suffix:m")] public float CrouchingColliderHeight { get; set; } = 1.1f;

    /// <summary>
    /// Высота камеры в обычном стоячем состоянии. Увеличение поднимает взгляд; уменьшение опускает обычную точку обзора.
    /// </summary>
    [Export(PropertyHint.Range, "0.5,3,0.05,suffix:m")] public float StandingCameraHeight { get; set; } = 1.6f;

    /// <summary>
    /// Высота камеры в приседе и подкате. Увеличение делает присед визуально выше; уменьшение сильнее опускает камеру.
    /// </summary>
    [Export(PropertyHint.Range, "0.3,2,0.05,suffix:m")] public float CrouchingCameraHeight { get; set; } = 0.95f;

    /// <summary>
    /// Скорость плавного перехода высоты камеры и коллайдера. Увеличение делает crouch резче; уменьшение делает переход мягче.
    /// </summary>
    [Export(PropertyHint.Range, "1,30,0.5,suffix:m/s")] public float CrouchTransitionSpeed { get; set; } = 10.0f;

    /// <summary>
    /// Множитель скорости обычного движения в приседе. Увеличение ускоряет crouch movement; уменьшение делает присед медленнее.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,1,0.05")] public float CrouchSpeedMultiplier { get; set; } = 0.55f;

    /// <summary>
    /// Включает подкат при нажатии crouch_slide на земле на достаточной скорости. Если выключить, action будет работать только как crouch.
    /// </summary>
    [ExportGroup("Slide")]
    [Export] public bool EnableSlide { get; set; } = true;

    /// <summary>
    /// Минимальная горизонтальная скорость для старта подката. Увеличение требует сильнее разогнаться; уменьшение позволяет скользить почти с места.
    /// </summary>
    [Export(PropertyHint.Range, "0,20,0.1,suffix:m/s")] public float SlideMinStartSpeed { get; set; } = 5.0f;

    /// <summary>
    /// Начальная горизонтальная скорость подката. Увеличение делает старт slide резче; уменьшение делает его спокойнее.
    /// </summary>
    [Export(PropertyHint.Range, "0,30,0.1,suffix:m/s")] public float SlideInitialSpeed { get; set; } = 11.0f;

    /// <summary>
    /// Длительность подката в секундах. Увеличение продлевает скольжение; уменьшение делает slide короче.
    /// </summary>
    [Export(PropertyHint.Range, "0.05,2,0.01,suffix:s")] public float SlideDuration { get; set; } = 0.55f;

    /// <summary>
    /// Задержка перед повторным подкатом. Увеличение сильнее ограничивает спам slide; уменьшение позволяет чаще подкатываться.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.01,suffix:s")] public float SlideCooldown { get; set; } = 0.35f;

    /// <summary>
    /// Скорость затухания подката. Увеличение быстрее гасит slide; уменьшение делает скольжение длиннее и инерционнее.
    /// </summary>
    [Export(PropertyHint.Range, "0,40,0.5,suffix:m/s^2")] public float SlideFriction { get; set; } = 14.0f;

    /// <summary>
    /// Сила лёгкого управления направлением во время подката. Увеличение даёт больше steering; уменьшение делает slide более прямолинейным.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float SlideSteeringStrength { get; set; } = 0.25f;

    /// <summary>
    /// Включает автоматический выход из slide, когда горизонтальная скорость падает ниже SlideExitMinSpeed.
    /// </summary>
    [Export] public bool EnableSlideExitBySpeed { get; set; } = true;

    /// <summary>
    /// Горизонтальная скорость, ниже которой slide завершается после grace-времени.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.1,suffix:m/s")] public float SlideExitMinSpeed { get; set; } = 3.0f;

    /// <summary>
    /// Короткая задержка после старта slide, во время которой выход по скорости игнорируется.
    /// </summary>
    [Export(PropertyHint.Range, "0,0.5,0.01,suffix:s")] public float SlideExitMinSpeedGraceTime { get; set; } = 0.08f;

    /// <summary>
    /// Использует текущий WASD-ввод для направления старта подката. Если выключить, slide всегда стартует по текущей горизонтальной скорости.
    /// </summary>
    [Export] public bool SlideKeepsInputDirection { get; set; } = true;

    /// <summary>
    /// Включает буфер подката в воздухе: удержание crouch_slide при высокой скорости запускает slide сразу после приземления.
    /// </summary>
    [ExportSubgroup("Airborne Slide Entry")]
    [Export] public bool EnableAirborneSlideEntry { get; set; } = true;

    /// <summary>
    /// Минимальная горизонтальная скорость в воздухе, при которой удержание crouch_slide запоминает желание войти в slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,25,0.5,suffix:m/s")] public float AirborneSlideMinSpeed { get; set; } = 7.0f;

    /// <summary>
    /// Сколько секунд после airborne-запроса модуль ждёт приземления для бесшовного входа в slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05,suffix:s")] public float AirborneSlideBufferTime { get; set; } = 0.25f;

    /// <summary>
    /// Разрешает брать направление landing slide из текущей горизонтальной velocity, если input-направление не используется.
    /// </summary>
    [Export] public bool AirborneSlideUseCurrentVelocityDirection { get; set; } = true;

    /// <summary>
    /// Если включено и игрок держит WASD при приземлении, landing slide стартует по input-направлению относительно камеры.
    /// </summary>
    [Export] public bool AirborneSlideUseInputDirectionIfAny { get; set; } = true;

    /// <summary>
    /// Минимальная сила WASD-ввода, при которой airborne landing slide выбирает input-направление.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.05")] public float AirborneSlideInputMin { get; set; } = 0.1f;

    /// <summary>
    /// Включает прыжок из slide с сохранением части горизонтальной инерции и небольшим boost в направлении подката.
    /// </summary>
    [ExportSubgroup("Slide Jump")]
    [Export] public bool EnableSlideJump { get; set; } = true;

    /// <summary>
    /// Дополнительная горизонтальная скорость, добавляемая при прыжке из slide в направлении текущего движения.
    /// </summary>
    [Export(PropertyHint.Range, "0,10,0.25,suffix:m/s")] public float SlideJumpHorizontalBoost { get; set; } = 3.0f;

    /// <summary>
    /// Доля текущей горизонтальной velocity, которая сохраняется при прыжке из slide.
    /// </summary>
    [Export(PropertyHint.Range, "0,1.5,0.05")] public float SlideJumpVelocityCarryFactor { get; set; } = 0.75f;

    /// <summary>
    /// Максимальная горизонтальная скорость после slide jump, чтобы boost не превращался в большой dash.
    /// </summary>
    [Export(PropertyHint.Range, "0,35,0.5,suffix:m/s")] public float SlideJumpMaxHorizontalSpeed { get; set; } = 16.0f;

    /// <summary>
    /// Если включено, slide jump требует свободное место для вставания, чтобы коллайдер не застревал в потолке.
    /// </summary>
    [Export] public bool SlideJumpRequiresStandUpSpace { get; set; } = true;

    /// <summary>
    /// Дополнительный зазор над стоячим коллайдером при проверке возможности встать. Увеличение делает проверку осторожнее; уменьшение допускает вставание ближе к потолку.
    /// </summary>
    [ExportGroup("Ceiling Check")]
    [Export(PropertyHint.Range, "0,1,0.01,suffix:m")] public float StandUpCheckDistance { get; set; } = 0.05f;

    /// <summary>
    /// Радиус capsule shape для проверки возможности встать. Увеличение требует больше места по сторонам; уменьшение делает проверку мягче.
    /// </summary>
    [Export(PropertyHint.Range, "0.05,1,0.01,suffix:m")] public float StandUpCheckRadius { get; set; } = 0.45f;

    /// <summary>
    /// Collision mask препятствий над головой. Увеличение набора слоёв учитывает больше объектов; уменьшение игнорирует лишние слои.
    /// </summary>
    [Export(PropertyHint.Layers3DPhysics)] public uint StandUpBlockedMask { get; set; } = uint.MaxValue;

    public bool IsCrouching => _state is CrouchSlideState.Crouching or CrouchSlideState.Sliding;
    public bool IsSliding => _state == CrouchSlideState.Sliding;
    public float CurrentSpeedMultiplier => IsCrouching ? CurrentCrouchSpeedMultiplier : 1.0f;

    private PlayerController _player;
    private CollisionShape3D _collisionShape;
    private CapsuleShape3D _capsuleShape;
    private Node3D _cameraPivot;
    private CrouchSlideState _state = CrouchSlideState.Standing;
    private float _slideTimer;
    private float _slideCooldownTimer;
    private float _slideExitSpeedGraceTimer;
    private float _airborneSlideBufferTimer;
    private float _slideSpeed;
    private Vector3 _slideDirection = Vector3.Forward;

    /// <summary>
    /// Инициализирует модуль crouch/slide, находит коллайдер и камеру, а также добавляет input action при необходимости.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        _collisionShape = GetNodeOrNull<CollisionShape3D>(CollisionShapePath);
        _capsuleShape = _collisionShape?.Shape as CapsuleShape3D;
        _cameraPivot = GetNodeOrNull<Node3D>(CameraPivotPath) ?? player.CameraPivot;

        EnsureInputAction();

        if (_capsuleShape != null)
        {
            ApplyColliderHeight(StandingColliderHeight);
        }

        if (_cameraPivot != null)
        {
            Vector3 cameraPosition = _cameraPivot.Position;
            cameraPosition.Y = StandingCameraHeight;
            _cameraPivot.Position = cameraPosition;
        }
    }

    /// <summary>
    /// Обновляет crouch/slide state, плавно меняет высоту камеры/коллайдера и при slide управляет горизонтальной velocity игрока.
    /// </summary>
    public void ProcessCrouchSlide(double delta, ref Vector3 velocity)
    {
        float deltaFloat = (float)delta;
        _slideCooldownTimer = Mathf.Max(0.0f, _slideCooldownTimer - deltaFloat);

        if (_player.SlingshotGrappleModule?.BlocksSlide == true)
        {
            CancelSlide();
            UpdateCrouchState(false);
            UpdateHeight(deltaFloat);
            return;
        }

        bool isPressed = Input.IsActionPressed(CrouchSlideAction);
        bool justPressed = Input.IsActionJustPressed(CrouchSlideAction);
        UpdateAirborneSlideBuffer(deltaFloat, isPressed, velocity);

        if (IsSliding)
        {
            ProcessSlide(deltaFloat, isPressed, ref velocity);
        }
        else if (TryStartBufferedLandingSlide(isPressed, ref velocity))
        {
            // Landing slide started from the airborne buffer.
        }
        else if (justPressed && CanStartSlide(velocity))
        {
            StartSlide(ref velocity);
        }
        else
        {
            UpdateCrouchState(isPressed);
        }

        UpdateHeight(deltaFloat);
    }

    private void UpdateCrouchState(bool isPressed)
    {
        if (EnableCrouch && isPressed)
        {
            _state = CrouchSlideState.Crouching;
            return;
        }

        _state = CanStandUp() ? CrouchSlideState.Standing : CrouchSlideState.Crouching;
    }

    private bool CanStartSlide(Vector3 velocity)
    {
        return CanStartSlide(velocity, SlideMinStartSpeed);
    }

    private void StartSlide(ref Vector3 velocity)
    {
        Vector3 horizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        Vector3 direction = GetSlideStartDirection(horizontalVelocity);
        StartSlide(ref velocity, direction);
    }

    private void ProcessSlide(float delta, bool holdCrouch, ref Vector3 velocity)
    {
        _slideTimer = Mathf.Max(0.0f, _slideTimer - delta);
        _slideExitSpeedGraceTimer = Mathf.Max(0.0f, _slideExitSpeedGraceTimer - delta);

        if (TryGetCameraRelativeInputDirection(out Vector3 steeringDirection))
        {
            _slideDirection = _slideDirection.MoveToward(steeringDirection, CurrentSlideSteeringStrength * delta).Normalized();
        }

        _slideSpeed = Mathf.Max(0.0f, _slideSpeed - CurrentSlideFriction * delta);
        velocity.X = _slideDirection.X * _slideSpeed;
        velocity.Z = _slideDirection.Z * _slideSpeed;

        if (_slideTimer <= 0.0f || ShouldExitSlideBySpeed())
        {
            StopSlide(holdCrouch);
        }
    }

    private void StopSlide(bool holdCrouch)
    {
        EndSlideAbility();

        if ((EnableCrouch && holdCrouch) || !CanStandUp())
        {
            _state = CrouchSlideState.Crouching;
            return;
        }

        _state = CrouchSlideState.Standing;
    }

    /// <summary>
    /// Принудительно завершает текущий slide и возвращает модуль в crouch/standing состояние без изменения текущей velocity.
    /// </summary>
    public void CancelSlide()
    {
        StopSlide(false);
        _slideTimer = 0.0f;
        _slideExitSpeedGraceTimer = 0.0f;
        _slideSpeed = 0.0f;
    }

    /// <summary>
    /// Если игрок сейчас скользит, завершает slide и применяет горизонтальный boost к velocity, когда slide jump включён.
    /// </summary>
    public bool TryConsumeSlideJumpBoost(ref Vector3 velocity)
    {
        if (!IsSliding)
        {
            return false;
        }

        if (!CurrentEnableSlideJump)
        {
            StopSlide(Input.IsActionPressed(CrouchSlideAction));
            return true;
        }

        if (CurrentSlideJumpRequiresStandUpSpace && !CanStandUp())
        {
            StopSlide(true);
            return false;
        }

        Vector3 horizontalVelocity = new(velocity.X, 0.0f, velocity.Z);
        if (horizontalVelocity.LengthSquared() <= 0.0001f)
        {
            horizontalVelocity = _slideDirection * _slideSpeed;
        }

        if (horizontalVelocity.LengthSquared() <= 0.0001f)
        {
            StopSlide(Input.IsActionPressed(CrouchSlideAction));
            return false;
        }

        Vector3 direction = horizontalVelocity.Normalized();
        Vector3 newHorizontalVelocity = horizontalVelocity * CurrentSlideJumpVelocityCarryFactor + direction * CurrentSlideJumpHorizontalBoost;
        float maxHorizontalSpeed = Mathf.Max(0.0f, CurrentSlideJumpMaxHorizontalSpeed);
        if (maxHorizontalSpeed > 0.0f && newHorizontalVelocity.Length() > maxHorizontalSpeed)
        {
            newHorizontalVelocity = newHorizontalVelocity.Normalized() * maxHorizontalSpeed;
        }

        velocity.X = newHorizontalVelocity.X;
        velocity.Z = newHorizontalVelocity.Z;
        _slideTimer = 0.0f;
        _slideExitSpeedGraceTimer = 0.0f;
        _slideSpeed = 0.0f;
        EndSlideAbility();
        _state = CrouchSlideState.Standing;
        return true;
    }

    private void UpdateHeight(float delta)
    {
        float targetColliderHeight = IsCrouching ? CrouchingColliderHeight : StandingColliderHeight;
        float targetCameraHeight = IsCrouching ? CrouchingCameraHeight : StandingCameraHeight;
        float step = CrouchTransitionSpeed * delta;

        if (_capsuleShape != null)
        {
            float newHeight = Mathf.MoveToward(_capsuleShape.Height, targetColliderHeight, step);
            ApplyColliderHeight(newHeight);
        }

        if (_cameraPivot != null)
        {
            Vector3 cameraPosition = _cameraPivot.Position;
            cameraPosition.Y = Mathf.MoveToward(cameraPosition.Y, targetCameraHeight, step);
            _cameraPivot.Position = cameraPosition;
        }
    }

    private void ApplyColliderHeight(float height)
    {
        _capsuleShape.Height = height;

        if (_collisionShape != null)
        {
            Vector3 collisionPosition = _collisionShape.Position;
            collisionPosition.Y = height * 0.5f;
            _collisionShape.Position = collisionPosition;
        }
    }

    private bool CanStandUp()
    {
        if (_player == null || _capsuleShape == null)
        {
            return true;
        }

        float checkRadius = StandUpCheckRadius > 0.0f ? StandUpCheckRadius : _capsuleShape.Radius;
        SphereShape3D standUpShape = new()
        {
            Radius = checkRadius
        };

        Transform3D queryTransform = _player.GlobalTransform;
        queryTransform.Origin += Vector3.Up * (StandingColliderHeight + StandUpCheckDistance - checkRadius);

        PhysicsShapeQueryParameters3D query = new()
        {
            Shape = standUpShape,
            Transform = queryTransform,
            CollisionMask = StandUpBlockedMask,
            CollideWithAreas = false,
            CollideWithBodies = true,
            Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() }
        };

        return _player.GetWorld3D().DirectSpaceState.IntersectShape(query, 1).Count == 0;
    }

    private Vector3 GetSlideStartDirection(Vector3 horizontalVelocity)
    {
        if (SlideKeepsInputDirection && TryGetCameraRelativeInputDirection(out Vector3 inputDirection))
        {
            return inputDirection;
        }

        return horizontalVelocity.LengthSquared() > 0.0f ? horizontalVelocity.Normalized() : Vector3.Zero;
    }

    private void UpdateAirborneSlideBuffer(float delta, bool holdCrouch, Vector3 velocity)
    {
        if (_airborneSlideBufferTimer > 0.0f)
        {
            _airborneSlideBufferTimer = Mathf.Max(0.0f, _airborneSlideBufferTimer - delta);
        }

        if (!CurrentEnableAirborneSlideEntry || _player.IsGrounded || !holdCrouch)
        {
            return;
        }

        if (GetHorizontalVelocity(velocity).Length() >= CurrentAirborneSlideMinSpeed)
        {
            _airborneSlideBufferTimer = CurrentAirborneSlideBufferTime;
        }
    }

    private bool TryStartBufferedLandingSlide(bool holdCrouch, ref Vector3 velocity)
    {
        if (!CurrentEnableAirborneSlideEntry || _airborneSlideBufferTimer <= 0.0f || !holdCrouch || !CanStartSlide(velocity, CurrentAirborneSlideMinSpeed))
        {
            return false;
        }

        Vector3 horizontalVelocity = GetHorizontalVelocity(velocity);
        if (!TryGetAirborneSlideDirection(horizontalVelocity, out Vector3 direction))
        {
            return false;
        }

        StartSlide(ref velocity, direction);
        _airborneSlideBufferTimer = 0.0f;
        return true;
    }

    private bool CanStartSlide(Vector3 velocity, float minStartSpeed)
    {
        if (!EnableSlide || !_player.IsGrounded || _slideCooldownTimer > 0.0f)
        {
            return false;
        }

        if (_player.AbilityStateModule != null
            && !_player.AbilityStateModule.CanStart(PlayerAbilityLock.Slide | PlayerAbilityLock.HorizontalVelocity))
        {
            return false;
        }

        return GetHorizontalVelocity(velocity).Length() >= minStartSpeed;
    }

    private void StartSlide(ref Vector3 velocity, Vector3 direction)
    {
        Vector3 horizontalVelocity = GetHorizontalVelocity(velocity);
        if (direction == Vector3.Zero)
        {
            return;
        }

        _state = CrouchSlideState.Sliding;
        _slideTimer = CurrentSlideDuration;
        _slideCooldownTimer = CurrentSlideCooldown;
        _slideExitSpeedGraceTimer = CurrentSlideExitMinSpeedGraceTime;
        _slideDirection = direction;
        _slideSpeed = Mathf.Max(CurrentSlideInitialSpeed, horizontalVelocity.Length());
        BeginSlideAbility();

        velocity.X = _slideDirection.X * _slideSpeed;
        velocity.Z = _slideDirection.Z * _slideSpeed;
    }

    private bool TryGetAirborneSlideDirection(Vector3 horizontalVelocity, out Vector3 direction)
    {
        direction = Vector3.Zero;

        if (CurrentAirborneSlideUseInputDirectionIfAny && TryGetCameraRelativeInputDirection(CurrentAirborneSlideInputMin, out Vector3 inputDirection))
        {
            direction = inputDirection;
            return true;
        }

        if (CurrentAirborneSlideUseCurrentVelocityDirection && horizontalVelocity.LengthSquared() > 0.0001f)
        {
            direction = horizontalVelocity.Normalized();
            return true;
        }

        return false;
    }

    private bool ShouldExitSlideBySpeed()
    {
        return CurrentEnableSlideExitBySpeed && _slideExitSpeedGraceTimer <= 0.0f && _slideSpeed < CurrentSlideExitMinSpeed;
    }

    private void BeginSlideAbility()
    {
        _player.AbilityStateModule?.BeginAbility(
            PlayerAbilityTag.Slide,
            PlayerAbilityStateModule.PrioritySlide,
            PlayerAbilityLock.HorizontalVelocity,
            nameof(PlayerCrouchSlideModule)
        );
    }

    private void EndSlideAbility()
    {
        _player.AbilityStateModule?.EndAbility(PlayerAbilityTag.Slide, nameof(PlayerCrouchSlideModule));
    }

    private static Vector3 GetHorizontalVelocity(Vector3 velocity)
    {
        return new Vector3(velocity.X, 0.0f, velocity.Z);
    }

    private bool TryGetCameraRelativeInputDirection(out Vector3 direction)
    {
        return TryGetCameraRelativeInputDirection(0.0f, out direction);
    }

    private bool TryGetCameraRelativeInputDirection(float minInput, out Vector3 direction)
    {
        direction = Vector3.Zero;

        Vector2 input = GetMovementInput();
        if (input.Length() < minInput || input.LengthSquared() == 0.0f)
        {
            return false;
        }

        Basis basis = _player.Camera?.GlobalTransform.Basis.Orthonormalized() ?? _player.GlobalTransform.Basis.Orthonormalized();
        Vector3 forward = GetHorizontalAxis(-basis.Z, -_player.GlobalTransform.Basis.Z);
        Vector3 right = GetHorizontalAxis(basis.X, _player.GlobalTransform.Basis.X);
        Vector3 desiredDirection = forward * input.Y + right * input.X;

        if (desiredDirection.LengthSquared() == 0.0f)
        {
            return false;
        }

        direction = desiredDirection.Normalized();
        return true;
    }

    private Vector2 GetMovementInput()
    {
        PlayerMovementModule movement = _player.MovementModule;
        string moveRightAction = movement?.MoveRightAction ?? "move_right";
        string moveLeftAction = movement?.MoveLeftAction ?? "move_left";
        string moveForwardAction = movement?.MoveForwardAction ?? "move_forward";
        string moveBackAction = movement?.MoveBackAction ?? "move_back";

        Vector2 input = new(
            Input.GetActionStrength(moveRightAction) - Input.GetActionStrength(moveLeftAction),
            Input.GetActionStrength(moveForwardAction) - Input.GetActionStrength(moveBackAction)
        );

        return input.LengthSquared() > 1.0f ? input.Normalized() : input;
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

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private float CurrentCrouchSpeedMultiplier => TuningProfile?.CrouchSpeedMultiplier ?? CrouchSpeedMultiplier;
    private float CurrentSlideInitialSpeed => TuningProfile?.SlideInitialSpeed ?? SlideInitialSpeed;
    private float CurrentSlideDuration => TuningProfile?.SlideDuration ?? SlideDuration;
    private float CurrentSlideCooldown => TuningProfile?.SlideCooldown ?? SlideCooldown;
    private float CurrentSlideFriction => TuningProfile?.SlideFriction ?? SlideFriction;
    private float CurrentSlideSteeringStrength => TuningProfile?.SlideSteeringStrength ?? SlideSteeringStrength;
    private bool CurrentEnableSlideExitBySpeed => TuningProfile?.EnableSlideExitBySpeed ?? EnableSlideExitBySpeed;
    private float CurrentSlideExitMinSpeed => TuningProfile?.SlideExitMinSpeed ?? SlideExitMinSpeed;
    private float CurrentSlideExitMinSpeedGraceTime => TuningProfile?.SlideExitMinSpeedGraceTime ?? SlideExitMinSpeedGraceTime;
    private bool CurrentEnableAirborneSlideEntry => TuningProfile?.EnableAirborneSlideEntry ?? EnableAirborneSlideEntry;
    private float CurrentAirborneSlideMinSpeed => TuningProfile?.AirborneSlideMinSpeed ?? AirborneSlideMinSpeed;
    private float CurrentAirborneSlideBufferTime => TuningProfile?.AirborneSlideBufferTime ?? AirborneSlideBufferTime;
    private bool CurrentAirborneSlideUseCurrentVelocityDirection => TuningProfile?.AirborneSlideUseCurrentVelocityDirection ?? AirborneSlideUseCurrentVelocityDirection;
    private bool CurrentAirborneSlideUseInputDirectionIfAny => TuningProfile?.AirborneSlideUseInputDirectionIfAny ?? AirborneSlideUseInputDirectionIfAny;
    private float CurrentAirborneSlideInputMin => TuningProfile?.AirborneSlideInputMin ?? AirborneSlideInputMin;
    private bool CurrentEnableSlideJump => TuningProfile?.EnableSlideJump ?? EnableSlideJump;
    private float CurrentSlideJumpHorizontalBoost => TuningProfile?.SlideJumpHorizontalBoost ?? SlideJumpHorizontalBoost;
    private float CurrentSlideJumpVelocityCarryFactor => TuningProfile?.SlideJumpVelocityCarryFactor ?? SlideJumpVelocityCarryFactor;
    private float CurrentSlideJumpMaxHorizontalSpeed => TuningProfile?.SlideJumpMaxHorizontalSpeed ?? SlideJumpMaxHorizontalSpeed;
    private bool CurrentSlideJumpRequiresStandUpSpace => TuningProfile?.SlideJumpRequiresStandUpSpace ?? SlideJumpRequiresStandUpSpace;

    private void EnsureInputAction()
    {
        EnsureKeyAction(CrouchSlideAction, Key.Ctrl);
        EnsureKeyAction(CrouchSlideAction, Key.C);
    }

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
