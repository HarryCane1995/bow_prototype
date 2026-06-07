using Godot;

public partial class PlayerSlingshotGrappleModule : Node
{
    public enum SlingshotGrappleState
    {
        Idle,
        Pulling,
        Launching,
        Cooldown
    }

    /// <summary>
    /// Включает или полностью отключает механику slingshot grapple без удаления модуля из сцены.
    /// </summary>
    [ExportGroup("Grapple Detection")]
    [Export] public bool EnableSlingshotGrapple { get; set; } = true;

    /// <summary>
    /// Максимальная дистанция raycast из основной камеры до специальной точки зацепа.
    /// </summary>
    [Export(PropertyHint.Range, "1,100,0.5,suffix:m")] public float MaxGrappleDistance { get; set; } = 25.0f;

    /// <summary>
    /// Имя группы, элементы которой считаются разрешёнными grapple anchor-точками.
    /// </summary>
    [Export] public string GrappleAnchorGroupName { get; set; } = "grapple_anchor";

    /// <summary>
    /// Physics mask для raycast обнаружения anchor-точек. Должен включать слой Area3D/Collider anchor-объектов.
    /// </summary>
    [Export(PropertyHint.Layers3DPhysics)] public uint GrappleDetectionMask { get; set; } = uint.MaxValue;

    /// <summary>
    /// Если включено, fallback-поиск в конусе принимает anchor только при свободной прямой линии от камеры.
    /// </summary>
    [Export] public bool RequireLineOfSight { get; set; } = true;

    /// <summary>
    /// Угол конуса для мягкого fallback-поиска ближайшего anchor, если прямой raycast не попал в точку.
    /// </summary>
    [Export(PropertyHint.Range, "0,35,0.5,suffix:deg")] public float FallbackConeAngleDegrees { get; set; } = 8.0f;

    /// <summary>
    /// Ускорение, с которым игрок притягивается к выбранной точке зацепа во время Pulling.
    /// </summary>
    [ExportGroup("Pull")]
    [Export(PropertyHint.Range, "0,120,0.5,suffix:m/s^2")] public float PullAcceleration { get; set; } = 45.0f;

    /// <summary>
    /// Максимальная скорость притяжения к anchor-точке до slingshot launch.
    /// </summary>
    [Export(PropertyHint.Range, "1,80,0.5,suffix:m/s")] public float MaxPullSpeed { get; set; } = 24.0f;

    /// <summary>
    /// Дистанция до anchor-точки, на которой Pulling завершается и начинается slingshot launch.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,5,0.05,suffix:m")] public float GrappleArriveDistance { get; set; } = 1.25f;

    /// <summary>
    /// Если включено, launch сработает и при пролёте игрока за anchor, даже если точная дистанция не успела попасть в arrive window.
    /// </summary>
    [Export] public bool StopPullWhenPassedAnchor { get; set; } = true;

    /// <summary>
    /// Базовая скорость выстрела игрока по направлению от стартовой позиции через anchor-точку.
    /// </summary>
    [ExportGroup("Launch")]
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s")] public float LaunchSpeed { get; set; } = 28.0f;

    /// <summary>
    /// Дополнительный множитель итоговой launch velocity для быстрой настройки силы рогатки.
    /// </summary>
    [Export(PropertyHint.Range, "0,3,0.05")] public float LaunchForce { get; set; } = 1.0f;

    /// <summary>
    /// Доля текущей скорости притяжения, наследуемая launch velocity вдоль сохранённого направления выстрела.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.05")] public float InheritPullVelocityFactor { get; set; } = 0.65f;

    /// <summary>
    /// Максимальная итоговая скорость после slingshot launch.
    /// </summary>
    [Export(PropertyHint.Range, "1,120,0.5,suffix:m/s")] public float MaxLaunchVelocity { get; set; } = 36.0f;

    /// <summary>
    /// Минимальная итоговая скорость после slingshot launch, если рассчитанная скорость оказалась слишком слабой.
    /// </summary>
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s")] public float MinLaunchVelocity { get; set; } = 18.0f;

    /// <summary>
    /// Блокирует обычное горизонтальное движение во время Pulling и короткого post-launch окна.
    /// </summary>
    [ExportGroup("Control")]
    [Export] public bool DisableNormalMovementWhilePulling { get; set; } = true;

    /// <summary>
    /// Блокирует запуск и продолжение slide, пока игрок притягивается к anchor-точке.
    /// </summary>
    [Export] public bool DisableSlideWhilePulling { get; set; } = true;

    /// <summary>
    /// Разрешает обычный air control после короткой задержки PostLaunchControlDelay.
    /// </summary>
    [Export] public bool AllowAirControlAfterLaunch { get; set; } = true;

    /// <summary>
    /// Сколько секунд после launch обычное horizontal movement не может сразу погасить скорость выстрела.
    /// </summary>
    [Export(PropertyHint.Range, "0,1,0.01,suffix:s")] public float PostLaunchControlDelay { get; set; } = 0.12f;

    /// <summary>
    /// Задержка перед следующим slingshot grapple после launch или отмены.
    /// </summary>
    [Export(PropertyHint.Range, "0,5,0.01,suffix:s")] public float Cooldown { get; set; } = 0.45f;

    /// <summary>
    /// Имя Input Map action для запуска slingshot grapple.
    /// </summary>
    [Export] public string GrappleAction { get; set; } = "slingshot_grapple";

    /// <summary>
    /// Показывает debug-линии: от стартовой позиции к anchor и направление launch после выстрела.
    /// </summary>
    [ExportGroup("Debug")]
    [Export] public bool DrawDebugTrajectory { get; set; } = true;

    /// <summary>
    /// Печатает переходы состояния slingshot grapple в Output Godot.
    /// </summary>
    [Export] public bool DebugPrintStateChanges { get; set; } = false;

    public SlingshotGrappleState CurrentState { get; private set; } = SlingshotGrappleState.Idle;
    public bool IsSlingshotActive => CurrentState is SlingshotGrappleState.Pulling or SlingshotGrappleState.Launching;
    public bool BlocksJump => CurrentState == SlingshotGrappleState.Pulling;
    public bool BlocksSlide => DisableSlideWhilePulling && CurrentState == SlingshotGrappleState.Pulling;
    public bool IsNormalMovementBlocked => (DisableNormalMovementWhilePulling && CurrentState == SlingshotGrappleState.Pulling) || _postLaunchControlTimer > 0.0f;

    private const float MinimumGrappleVectorLength = 0.2f;
    private PlayerController _player;
    private Vector3 _initialPlayerPosition;
    private Vector3 _grapplePointPosition;
    private Vector3 _storedLaunchDirection = Vector3.Forward;
    private float _cooldownTimer;
    private float _postLaunchControlTimer;
    private MeshInstance3D _debugMeshInstance;
    private StandardMaterial3D _debugMaterial;

    /// <summary>
    /// Инициализирует модуль, сохраняет ссылку на игрока и гарантирует наличие input action для grapple.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
        EnsureInputAction();
        EnsureDebugMesh();
    }

    /// <summary>
    /// Обрабатывает нажатие grapple action и пытается выбрать специальную anchor-точку перед камерой.
    /// </summary>
    public void ProcessSlingshotInput()
    {
        if (!EnableSlingshotGrapple || _player == null || _cooldownTimer > 0.0f || CurrentState != SlingshotGrappleState.Idle)
        {
            return;
        }

        if (!Input.IsActionJustPressed(GrappleAction))
        {
            return;
        }

        if (TryFindGrappleAnchor(out Node3D anchor))
        {
            TryStartGrappleAt(anchor.GlobalPosition);
        }
    }

    /// <summary>
    /// Обновляет состояние slingshot grapple, применяет Pulling velocity и выполняет launch при достижении anchor-точки.
    /// </summary>
    public void UpdateSlingshot(double delta)
    {
        float deltaTime = (float)delta;
        _cooldownTimer = Mathf.Max(0.0f, _cooldownTimer - deltaTime);
        _postLaunchControlTimer = Mathf.Max(0.0f, _postLaunchControlTimer - deltaTime);

        if (CurrentState == SlingshotGrappleState.Pulling)
        {
            UpdatePulling(deltaTime);
        }
        else if (CurrentState == SlingshotGrappleState.Launching)
        {
            LaunchPlayer();
        }

        if (CurrentState == SlingshotGrappleState.Cooldown && _cooldownTimer <= 0.0f && _postLaunchControlTimer <= 0.0f)
        {
            SetState(SlingshotGrappleState.Idle);
        }

        UpdateDebugTrajectory();
    }

    /// <summary>
    /// Принудительно начинает slingshot grapple к указанной мировой позиции, если направление выстрела достаточно длинное.
    /// </summary>
    public bool TryStartGrappleAt(Vector3 grapplePointPosition)
    {
        Vector3 startToAnchor = grapplePointPosition - _player.GlobalPosition;
        if (startToAnchor.Length() < MinimumGrappleVectorLength)
        {
            return false;
        }

        _initialPlayerPosition = _player.GlobalPosition;
        _grapplePointPosition = grapplePointPosition;
        _storedLaunchDirection = startToAnchor.Normalized();

        _player.CrouchSlideModule?.CancelSlide();
        _player.JumpModule?.RestoreAirJumpChargeFromGrapple();
        SetState(SlingshotGrappleState.Pulling);

        if (DebugPrintStateChanges)
        {
            GD.Print($"Slingshot grapple start: initial={_initialPlayerPosition}, anchor={_grapplePointPosition}, launchDir={_storedLaunchDirection}");
        }

        return true;
    }

    /// <summary>
    /// Отменяет текущий slingshot grapple и переводит модуль в cooldown.
    /// </summary>
    public void CancelGrapple()
    {
        if (CurrentState == SlingshotGrappleState.Idle)
        {
            return;
        }

        _cooldownTimer = Mathf.Max(_cooldownTimer, Cooldown);
        SetState(SlingshotGrappleState.Cooldown);
    }

    private void UpdatePulling(float deltaTime)
    {
        Vector3 toAnchor = _grapplePointPosition - _player.GlobalPosition;
        float distanceToAnchor = toAnchor.Length();

        if (distanceToAnchor <= GrappleArriveDistance || HasPassedAnchor())
        {
            SetState(SlingshotGrappleState.Launching);
            return;
        }

        Vector3 pullDirection = toAnchor / distanceToAnchor;
        Vector3 velocity = _player.Velocity + pullDirection * CurrentPullAcceleration * deltaTime;
        float maxPullSpeed = Mathf.Max(0.1f, CurrentMaxPullSpeed);

        if (velocity.Length() > maxPullSpeed)
        {
            velocity = velocity.Normalized() * maxPullSpeed;
        }

        _player.Velocity = velocity;
    }

    private bool HasPassedAnchor()
    {
        if (!StopPullWhenPassedAnchor)
        {
            return false;
        }

        Vector3 fromStartToAnchor = _grapplePointPosition - _initialPlayerPosition;
        Vector3 fromAnchorToPlayer = _player.GlobalPosition - _grapplePointPosition;

        if (fromStartToAnchor.LengthSquared() <= 0.0001f || fromAnchorToPlayer.LengthSquared() <= 0.0001f)
        {
            return false;
        }

        return fromStartToAnchor.Normalized().Dot(fromAnchorToPlayer.Normalized()) > 0.0f;
    }

    private void LaunchPlayer()
    {
        Vector3 currentVelocity = _player.Velocity;
        float inheritedAlongDirection = currentVelocity.Dot(_storedLaunchDirection);
        Vector3 inheritedDirectionalVelocity = _storedLaunchDirection * Mathf.Max(0.0f, inheritedAlongDirection) * CurrentInheritPullVelocityFactor;
        Vector3 launchVelocity = (_storedLaunchDirection * CurrentLaunchSpeed + inheritedDirectionalVelocity) * LaunchForce;

        float launchSpeed = launchVelocity.Length();
        if (launchSpeed < MinLaunchVelocity)
        {
            launchVelocity = _storedLaunchDirection * MinLaunchVelocity;
        }
        else if (launchSpeed > CurrentMaxLaunchVelocity)
        {
            launchVelocity = launchVelocity.Normalized() * CurrentMaxLaunchVelocity;
        }

        _player.Velocity = launchVelocity;
        _postLaunchControlTimer = AllowAirControlAfterLaunch ? Mathf.Max(0.0f, PostLaunchControlDelay) : Cooldown;
        _cooldownTimer = Cooldown;

        if (DebugPrintStateChanges)
        {
            GD.Print($"Slingshot grapple launch: velocity={launchVelocity}, speed={launchVelocity.Length():0.00}");
        }

        SetState(SlingshotGrappleState.Cooldown);
    }

    private bool TryFindGrappleAnchor(out Node3D anchor)
    {
        anchor = null;

        if (_player.Camera == null)
        {
            return false;
        }

        Vector3 rayOrigin = _player.Camera.GlobalPosition;
        Vector3 rayDirection = -_player.Camera.GlobalTransform.Basis.Z.Normalized();
        Vector3 rayEnd = rayOrigin + rayDirection * CurrentMaxGrappleDistance;

        PhysicsRayQueryParameters3D query = PhysicsRayQueryParameters3D.Create(rayOrigin, rayEnd);
        query.CollisionMask = GrappleDetectionMask;
        query.CollideWithAreas = true;
        query.CollideWithBodies = true;
        query.Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() };

        Godot.Collections.Dictionary result = _player.GetWorld3D().DirectSpaceState.IntersectRay(query);
        if (result.Count > 0 && TryGetAnchorFromRayResult(result, out anchor))
        {
            return true;
        }

        return TryFindAnchorInFallbackCone(rayOrigin, rayDirection, out anchor);
    }

    private bool TryGetAnchorFromRayResult(Godot.Collections.Dictionary result, out Node3D anchor)
    {
        anchor = null;

        if (!result.TryGetValue("collider", out Variant colliderVariant))
        {
            return false;
        }

        Node collider = colliderVariant.AsGodotObject() as Node;
        anchor = FindAnchorNode(collider);
        return anchor != null;
    }

    private bool TryFindAnchorInFallbackCone(Vector3 rayOrigin, Vector3 rayDirection, out Node3D bestAnchor)
    {
        bestAnchor = null;

        if (FallbackConeAngleDegrees <= 0.0f || string.IsNullOrWhiteSpace(GrappleAnchorGroupName))
        {
            return false;
        }

        float bestDistance = float.MaxValue;
        float minDot = Mathf.Cos(Mathf.DegToRad(FallbackConeAngleDegrees));

        foreach (Node node in GetTree().GetNodesInGroup(GrappleAnchorGroupName))
        {
            if (node is not Node3D candidate)
            {
                continue;
            }

            Vector3 toCandidate = candidate.GlobalPosition - rayOrigin;
            float distance = toCandidate.Length();
            if (distance <= 0.0f || distance > CurrentMaxGrappleDistance)
            {
                continue;
            }

            float dot = rayDirection.Dot(toCandidate / distance);
            if (dot < minDot || distance >= bestDistance)
            {
                continue;
            }

            if (RequireLineOfSight && !HasLineOfSightToAnchor(rayOrigin, candidate))
            {
                continue;
            }

            bestAnchor = candidate;
            bestDistance = distance;
        }

        return bestAnchor != null;
    }

    private bool HasLineOfSightToAnchor(Vector3 rayOrigin, Node3D candidate)
    {
        PhysicsRayQueryParameters3D query = PhysicsRayQueryParameters3D.Create(rayOrigin, candidate.GlobalPosition);
        query.CollisionMask = GrappleDetectionMask;
        query.CollideWithAreas = true;
        query.CollideWithBodies = true;
        query.Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() };

        Godot.Collections.Dictionary result = _player.GetWorld3D().DirectSpaceState.IntersectRay(query);
        return result.Count > 0 && TryGetAnchorFromRayResult(result, out Node3D hitAnchor) && hitAnchor == candidate;
    }

    private Node3D FindAnchorNode(Node node)
    {
        while (node != null)
        {
            if (node is Node3D node3D && (node is GrappleAnchor || node.IsInGroup(GrappleAnchorGroupName)))
            {
                return node3D;
            }

            node = node.GetParent();
        }

        return null;
    }

    private void SetState(SlingshotGrappleState state)
    {
        CurrentState = state;

        if (state == SlingshotGrappleState.Cooldown && _cooldownTimer <= 0.0f && _postLaunchControlTimer <= 0.0f)
        {
            CurrentState = SlingshotGrappleState.Idle;
        }
    }

    private void UpdateDebugTrajectory()
    {
        if (!DrawDebugTrajectory || _debugMeshInstance?.Mesh is not ImmediateMesh immediateMesh)
        {
            return;
        }

        immediateMesh.ClearSurfaces();
        _debugMeshInstance.Visible = CurrentState != SlingshotGrappleState.Idle || _postLaunchControlTimer > 0.0f;

        if (!_debugMeshInstance.Visible)
        {
            return;
        }

        immediateMesh.SurfaceBegin(Mesh.PrimitiveType.Lines, _debugMaterial);
        immediateMesh.SurfaceSetColor(new Color(0.1f, 0.85f, 1.0f));
        immediateMesh.SurfaceAddVertex(_initialPlayerPosition);
        immediateMesh.SurfaceAddVertex(_grapplePointPosition);
        immediateMesh.SurfaceSetColor(new Color(1.0f, 0.75f, 0.15f));
        immediateMesh.SurfaceAddVertex(_grapplePointPosition);
        immediateMesh.SurfaceAddVertex(_grapplePointPosition + _storedLaunchDirection * 4.0f);
        immediateMesh.SurfaceEnd();
    }

    private void EnsureDebugMesh()
    {
        if (_debugMeshInstance != null || _player == null)
        {
            return;
        }

        _debugMaterial = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
            VertexColorUseAsAlbedo = true,
            NoDepthTest = true
        };

        _debugMeshInstance = new MeshInstance3D
        {
            Name = "SlingshotGrappleDebugLines",
            Mesh = new ImmediateMesh(),
            TopLevel = true,
            Visible = false,
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off
        };

        _player.AddChild(_debugMeshInstance);
    }

    private void EnsureInputAction()
    {
        if (!InputMap.HasAction(GrappleAction))
        {
            InputMap.AddAction(GrappleAction);
        }

        InputEventKey keyEvent = new()
        {
            Keycode = Key.E,
            PhysicalKeycode = Key.E
        };

        if (!InputMap.ActionHasEvent(GrappleAction, keyEvent))
        {
            InputMap.ActionAddEvent(GrappleAction, keyEvent);
        }
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private float CurrentMaxGrappleDistance => TuningProfile?.MaxGrappleDistance ?? MaxGrappleDistance;
    private float CurrentPullAcceleration => TuningProfile?.PullAcceleration ?? PullAcceleration;
    private float CurrentMaxPullSpeed => TuningProfile?.MaxPullSpeed ?? MaxPullSpeed;
    private float CurrentLaunchSpeed => TuningProfile?.LaunchSpeed ?? LaunchSpeed;
    private float CurrentInheritPullVelocityFactor => TuningProfile?.InheritPullVelocityFactor ?? InheritPullVelocityFactor;
    private float CurrentMaxLaunchVelocity => TuningProfile?.MaxLaunchVelocity ?? MaxLaunchVelocity;
}
