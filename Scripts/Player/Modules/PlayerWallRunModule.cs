using Godot;

public partial class PlayerWallRunModule : Node
{
    private enum WallSide
    {
        None,
        Left,
        Right
    }

    private struct WallHit
    {
        public bool HasHit;
        public WallSide Side;
        public Vector3 Normal;
        public Vector3 Position;
    }

    [ExportGroup("Detection")]
    [Export(PropertyHint.Layers3DPhysics)] public uint WallCollisionMask { get; set; } = uint.MaxValue;
    [ExportGroup("Canonical Wallrun Prototype")]
    // Read on entry: switching A/B never splices two models into an active run.
    [Export] public bool UseCanonicalTrajectory { get; set; } = true;
    [Export(PropertyHint.Range, "0,0.2,0.01,suffix:s")] public float CanonicalEntryBlendSeconds { get; set; } = 0.10f;
    [Export(PropertyHint.Range, "0,20,0.25,suffix:m/s")] public float CanonicalInitialUpSpeed { get; set; } = 9.75f;
    [Export(PropertyHint.Range, "0,1,0.05")] public float CanonicalMomentumRetention { get; set; } = 1.0f;
    [Export(PropertyHint.Range, "0.05,0.8,0.05")] public float CanonicalIntentMinAlignment { get; set; } = 0.25f;
    [Export(PropertyHint.Range, "0.1,10,0.1,suffix:m/s")] public float CanonicalMinProjectedSpeed { get; set; } = 2.0f;

    private PlayerController _player;
    private float _gravity;
    private float _wallRunTimer;
    private float _reattachCooldownTimer;
    private float _sameWallCooldownTimer;
    private float _groundGraceTimer;
    private bool _blockNormalJumpThisFrame;
    private WallSide _wallSide = WallSide.None;
    private Vector3 _wallNormal = Vector3.Zero;
    private Vector3 _wallRunDirection = Vector3.Zero;
    private Vector3 _lastWallNormal = Vector3.Zero;
    private float _cameraRoll;
    private float _cameraPitchOffset;
    private float _currentFovBoost;
    private bool _warnedMissingCameraEffectsPivot;
    private string _lastExitReason = "none";
    private bool _activeCanonical;
    private float _canonicalTargetSpeed;
    private float _canonicalEntryAlongSpeed;
    private float _canonicalVertical;
    private string _entryIntent = "none";

    public bool IsWallRunning { get; private set; }
    public bool BlocksNormalJumpAndGravity => IsWallRunning || _blockNormalJumpThisFrame;
    public float CurrentFovBoost => _currentFovBoost;
    public bool IsCanonicalRun => IsWallRunning && _activeCanonical;
    public float EntryHorizontalSpeed { get; private set; }
    public float CanonicalTargetSpeed => _canonicalTargetSpeed;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _gravity = (float)ProjectSettings.GetSetting("physics/3d/default_gravity").AsDouble();
    }

    public override void _Process(double delta)
    {
        UpdateCameraEffects((float)delta);
    }

    public void ProcessWallRun(double delta)
    {
        float deltaFloat = (float)delta;
        _blockNormalJumpThisFrame = false;
        _reattachCooldownTimer = Mathf.Max(0.0f, _reattachCooldownTimer - deltaFloat);
        _sameWallCooldownTimer = Mathf.Max(0.0f, _sameWallCooldownTimer - deltaFloat);

        if (_player.IsGrounded)
        {
            _groundGraceTimer = CurrentEntryGraceTime;
        }
        else
        {
            _groundGraceTimer = Mathf.Max(0.0f, _groundGraceTimer - deltaFloat);
        }

        if (!CurrentEnableWallRun)
        {
            EndWallRun("disabled", false);
            return;
        }

        if (IsWallRunning)
        {
            UpdateActiveWallRun(deltaFloat);
            return;
        }

        TryStartWallRun();
    }

    public string GetDebugText()
    {
        string state = IsWallRunning ? $"active side={_wallSide}" : "inactive";
        string model = (IsWallRunning ? _activeCanonical : UseCanonicalTrajectory) ? "B" : "A";
        return $"{state}, model={model}, intent={_entryIntent}, entrySpeed={EntryHorizontalSpeed:0.00}, timer={_wallRunTimer:0.00}, normal=({_wallNormal.X:0.00},{_wallNormal.Y:0.00},{_wallNormal.Z:0.00}), cooldown={_reattachCooldownTimer:0.00}, sameCooldown={_sameWallCooldownTimer:0.00}, fovBoost={_currentFovBoost:0.00}, lastExit={_lastExitReason}";
    }

    private void TryStartWallRun()
    {
        if (!CanAttemptWallRun())
        {
            return;
        }

        if (!TryFindBestWall(out WallHit hit))
        {
            return;
        }

        Vector3 runDirection;
        bool hasDirection = UseCanonicalTrajectory
            ? TryGetCanonicalEntryDirection(hit.Normal, out runDirection)
            : TryGetWallRunDirection(hit.Normal, out runDirection);
        if (!hasDirection)
        {
            return;
        }

        if (!UseCanonicalTrajectory && !PassesForwardDot(runDirection))
        {
            return;
        }

        if (IsSameWallOnCooldown(hit))
        {
            return;
        }

        BeginWallRun(hit, runDirection);
    }

    private bool CanAttemptWallRun()
    {
        if (_player == null || _reattachCooldownTimer > 0.0f)
        {
            return false;
        }

        if (_player.SlingshotGrappleModule?.IsNormalMovementBlocked == true)
        {
            return false;
        }

        bool hasAirState = !_player.IsGrounded || (CurrentAllowWallRunFromGroundGrace && _groundGraceTimer > 0.0f && _player.Velocity.Y > 0.1f);
        // B can acquire a validated wall directly from a grounded slide.
        // A keeps its original entry behavior for the existing comparison.
        bool canTransferSlide = UseCanonicalTrajectory && _player.CrouchSlideModule?.IsSliding == true;
        if (!hasAirState && !canTransferSlide)
        {
            return false;
        }

        if (GetHorizontalVelocity(_player.Velocity).Length() < CurrentMinEntrySpeed)
        {
            return false;
        }

        if (CurrentRequireForwardInput && !HasForwardIntent())
        {
            return false;
        }

        const PlayerAbilityLock requiredLocks = PlayerAbilityLock.HorizontalVelocity | PlayerAbilityLock.VerticalVelocity | PlayerAbilityLock.Slide;
        return _player.AbilityStateModule == null
            || (UseCanonicalTrajectory
                ? _player.AbilityStateModule.CanStart(requiredLocks, PlayerAbilityStateModule.PriorityWallRun)
                : _player.AbilityStateModule.CanStart(requiredLocks));
    }

    private void BeginWallRun(WallHit hit, Vector3 runDirection)
    {
        IsWallRunning = true;
        _wallRunTimer = 0.0f;
        _wallSide = hit.Side;
        _wallNormal = hit.Normal;
        _wallRunDirection = runDirection;
        _lastExitReason = "running";
        _activeCanonical = UseCanonicalTrajectory;

        // Capture the real incoming momentum before the synchronous ownership handoff.
        Vector3 velocity = _player.Velocity;
        _player.CrouchSlideModule?.CancelSlide();
        _player.JumpModule?.RestoreAirJumpChargeFromWallRun();
        _player.AbilityStateModule?.BeginAbility(
            PlayerAbilityTag.WallRun,
            PlayerAbilityStateModule.PriorityWallRun,
            PlayerAbilityLock.HorizontalVelocity | PlayerAbilityLock.VerticalVelocity | PlayerAbilityLock.Slide,
            nameof(PlayerWallRunModule)
        );

        EntryHorizontalSpeed = GetHorizontalVelocity(velocity).Length();
        if (_activeCanonical)
        {
            _canonicalTargetSpeed = Mathf.Max(CurrentWallRunSpeed, EntryHorizontalSpeed * Mathf.Clamp(CanonicalMomentumRetention, 0.0f, 1.0f));
            _canonicalEntryAlongSpeed = Mathf.Min(_canonicalTargetSpeed,
                Mathf.Max(CurrentMinEntrySpeed, GetHorizontalVelocity(velocity).Dot(_wallRunDirection)));
            _canonicalVertical = CanonicalInitialUpSpeed;
            float speed = CanonicalEntryBlendSeconds > 0.0f ? _canonicalEntryAlongSpeed : _canonicalTargetSpeed;
            velocity = _wallRunDirection * speed + Vector3.Up * _canonicalVertical;
        }
        else
        {
            _entryIntent = "legacy_input_velocity_camera";
            float carriedSpeed = Mathf.Abs(GetHorizontalVelocity(velocity).Dot(_wallRunDirection)) * CurrentEntrySpeedRetention;
            float entrySpeed = Mathf.Max(CurrentWallRunSpeed, carriedSpeed);
            velocity.X = _wallRunDirection.X * entrySpeed;
            velocity.Z = _wallRunDirection.Z * entrySpeed;
            velocity.Y = Mathf.Max(velocity.Y * (1.0f - CurrentWallVerticalDamping), -CurrentWallFallSpeedClamp);
        }
        _player.Velocity = velocity;

        if (CurrentDebugWallRun)
        {
            GD.Print($"WallRun enter model={(_activeCanonical ? "B" : "A")} side={_wallSide} normal={_wallNormal} direction={_wallRunDirection} inputSpeed={EntryHorizontalSpeed:0.00} intent={_entryIntent}");
        }
    }

    private void UpdateActiveWallRun(float delta)
    {
        _blockNormalJumpThisFrame = true;
        _wallRunTimer += delta;

        if (_player.AbilityStateModule != null
            && (!_player.AbilityStateModule.CanWrite(PlayerAbilityTag.WallRun, PlayerAbilityLock.HorizontalVelocity)
                || !_player.AbilityStateModule.CanWrite(PlayerAbilityTag.WallRun, PlayerAbilityLock.VerticalVelocity)))
        {
            EndWallRun("arbitration", true);
            return;
        }

        if (_player.IsGrounded)
        {
            EndWallRun("grounded", true);
            return;
        }

        if (_wallRunTimer >= CurrentWallRunMaxDuration)
        {
            EndWallRun("duration", true);
            return;
        }

        bool canonicalWallJump = _activeCanonical && CurrentEnableWallJump
            && Input.IsActionJustPressed(GetJumpAction());
        if (CurrentRequireForwardInput && !HasForwardIntent() && !canonicalWallJump)
        {
            EndWallRun("input_released", true);
            return;
        }

        WallHit hit;
        bool foundWall = _activeCanonical
            ? TryCastWallDirection(-_wallNormal, _wallSide, out hit)
            : TryFindBestWall(_wallSide, out hit);
        if (!foundWall)
        {
            EndWallRun("lost_wall", true);
            return;
        }

        // Preserve a deliberate look-away jump before checking continuation intent.
        if (canonicalWallJump)
        {
            _wallSide = hit.Side;
            _wallNormal = hit.Normal;
            PerformWallJump();
            return;
        }

        Vector3 runDirection;
        bool hasDirection = _activeCanonical
            ? TryContinueCanonicalDirection(hit.Normal, out runDirection)
            : TryGetWallRunDirection(hit.Normal, out runDirection);
        if (!hasDirection)
        {
            EndWallRun("bad_wall_direction", true);
            return;
        }

        _wallSide = hit.Side;
        _wallNormal = hit.Normal;
        _wallRunDirection = runDirection;

        if (CurrentEnableWallJump && Input.IsActionJustPressed(GetJumpAction()))
        {
            PerformWallJump();
            return;
        }

        if (_activeCanonical) ApplyCanonicalWallRunVelocity(delta);
        else ApplyWallRunVelocity(delta);
    }

    private void ApplyCanonicalWallRunVelocity(float delta)
    {
        float blend = CanonicalEntryBlendSeconds <= 0.0f ? 1.0f
            : Mathf.SmoothStep(0.0f, 1.0f, Mathf.Clamp(_wallRunTimer / CanonicalEntryBlendSeconds, 0.0f, 1.0f));
        float speed = Mathf.Lerp(_canonicalEntryAlongSpeed, _canonicalTargetSpeed, blend);
        // Same wall-specific arc forces as A, integrated from a fixed seed,
        // independently of incoming jump phase and MoveAndSlide's resolved Y.
        _canonicalVertical = Mathf.MoveToward(_canonicalVertical, 0.0f,
            CurrentWallVerticalDamping * delta * Mathf.Max(1.0f, _gravity));
        _canonicalVertical -= CurrentWallGravity * delta;
        float arc = CurrentWallRunMaxDuration > 0.0f ? Mathf.Clamp(_wallRunTimer / CurrentWallRunMaxDuration, 0.0f, 1.0f) : 1.0f;
        _canonicalVertical = Mathf.Max(_canonicalVertical - CurrentWallArcDownForce * arc * delta, -CurrentWallFallSpeedClamp);
        Vector3 stick = -_wallNormal * CurrentWallStickForce * delta;
        Vector3 velocity = _wallRunDirection * speed;
        velocity.X += stick.X;
        velocity.Z += stick.Z;
        velocity.Y = _canonicalVertical;
        _player.Velocity = velocity;
    }

    private void ApplyWallRunVelocity(float delta)
    {
        Vector3 velocity = _player.Velocity;
        Vector3 horizontalVelocity = GetHorizontalVelocity(velocity);
        Vector3 targetHorizontalVelocity = _wallRunDirection * CurrentWallRunSpeed;
        Vector3 newHorizontalVelocity = horizontalVelocity.MoveToward(targetHorizontalVelocity, CurrentWallRunAcceleration * delta);

        float vertical = velocity.Y;
        vertical = Mathf.MoveToward(vertical, 0.0f, CurrentWallVerticalDamping * delta * Mathf.Max(1.0f, _gravity));
        vertical -= CurrentWallGravity * delta;
        float arcProgress = CurrentWallRunMaxDuration > 0.0f ? Mathf.Clamp(_wallRunTimer / CurrentWallRunMaxDuration, 0.0f, 1.0f) : 1.0f;
        vertical -= CurrentWallArcDownForce * arcProgress * delta;
        vertical = Mathf.Max(vertical, -CurrentWallFallSpeedClamp);

        Vector3 stickVelocity = -_wallNormal * CurrentWallStickForce * delta;
        velocity.X = newHorizontalVelocity.X + stickVelocity.X;
        velocity.Y = vertical;
        velocity.Z = newHorizontalVelocity.Z + stickVelocity.Z;
        _player.Velocity = velocity;
    }

    private void PerformWallJump()
    {
        Vector3 forward = GetPreferredForwardDirection();
        Vector3 impulse = _wallNormal * CurrentWallJumpAwayForce
            + Vector3.Up * CurrentWallJumpUpForce
            + forward * CurrentWallJumpForwardForce;

        if (impulse.LengthSquared() > 0.0001f && CurrentWallJumpSpeedClamp > 0.0f && impulse.Length() > CurrentWallJumpSpeedClamp)
        {
            impulse = impulse.Normalized() * CurrentWallJumpSpeedClamp;
        }

        EndWallRun("wall_jump", false);
        _blockNormalJumpThisFrame = true;
        _player.Velocity = impulse;
        _reattachCooldownTimer = Mathf.Max(_reattachCooldownTimer, Mathf.Max(CurrentWallJumpCooldown, CurrentWallJumpLockoutTime));
        _sameWallCooldownTimer = Mathf.Max(_sameWallCooldownTimer, CurrentSameWallReattachCooldown);

        if (CurrentDebugWallRun)
        {
            GD.Print($"WallRun wall jump velocity={impulse}");
        }
    }

    private void EndWallRun(string reason, bool applyExitRetention)
    {
        if (!IsWallRunning)
        {
            _lastExitReason = reason;
            return;
        }

        _lastWallNormal = _wallNormal;
        IsWallRunning = false;
        _wallRunTimer = 0.0f;
        _wallSide = WallSide.None;
        _wallNormal = Vector3.Zero;
        _wallRunDirection = Vector3.Zero;
        _lastExitReason = reason;
        _reattachCooldownTimer = Mathf.Max(_reattachCooldownTimer, CurrentWallReattachCooldown);
        _sameWallCooldownTimer = Mathf.Max(_sameWallCooldownTimer, CurrentSameWallReattachCooldown);
        _player?.AbilityStateModule?.EndAbility(PlayerAbilityTag.WallRun, nameof(PlayerWallRunModule));

        if (applyExitRetention && _player != null)
        {
            Vector3 velocity = _player.Velocity;
            velocity.X *= CurrentWallRunExitSpeedRetention;
            velocity.Z *= CurrentWallRunExitSpeedRetention;
            _player.Velocity = velocity;
        }

        if (CurrentDebugWallRun)
        {
            GD.Print($"WallRun exit reason={reason}");
        }
    }

    private bool TryFindBestWall(out WallHit hit)
    {
        if (TryCastWall(WallSide.Left, out WallHit leftHit) && TryCastWall(WallSide.Right, out WallHit rightHit))
        {
            float leftScore = GetWallAlignmentScore(leftHit);
            float rightScore = GetWallAlignmentScore(rightHit);
            hit = leftScore >= rightScore ? leftHit : rightHit;
            return true;
        }

        if (TryCastWall(WallSide.Left, out hit))
        {
            return true;
        }

        return TryCastWall(WallSide.Right, out hit);
    }

    private bool TryFindBestWall(WallSide preferredSide, out WallHit hit)
    {
        if (preferredSide != WallSide.None && TryCastWall(preferredSide, out hit))
        {
            return true;
        }

        return TryFindBestWall(out hit);
    }

    private bool TryCastWall(WallSide side, out WallHit hit)
    {
        Vector3 sideDirection = GetSideDirection(side);
        return TryCastWallDirection(sideDirection, side, out hit);
    }

    private bool TryCastWallDirection(Vector3 sideDirection, WallSide side, out WallHit hit)
    {
        hit = default;
        Vector3 origin = _player.GlobalPosition + Vector3.Up * CurrentWallDetectionHeightOffset;
        if (sideDirection == Vector3.Zero)
        {
            return false;
        }

        PhysicsRayQueryParameters3D query = new()
        {
            From = origin,
            To = origin + sideDirection * CurrentWallDetectionDistance,
            CollisionMask = WallCollisionMask,
            CollideWithAreas = false,
            CollideWithBodies = true,
            Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() }
        };

        Godot.Collections.Dictionary result = _player.GetWorld3D().DirectSpaceState.IntersectRay(query);
        if (result.Count == 0)
        {
            return false;
        }

        Vector3 normal = result["normal"].AsVector3().Normalized();
        if (Mathf.Abs(normal.Dot(Vector3.Up)) > CurrentMinWallNormalVerticalDot)
        {
            return false;
        }

        hit = new WallHit
        {
            HasHit = true,
            Side = side,
            Normal = normal,
            Position = result["position"].AsVector3()
        };
        return true;
    }

    private bool TryGetWallRunDirection(Vector3 wallNormal, out Vector3 direction)
    {
        direction = wallNormal.Cross(Vector3.Up);
        if (direction.LengthSquared() <= 0.0001f)
        {
            return false;
        }

        direction = direction.Normalized();
        Vector3 preferred = GetPreferredForwardDirection();
        if (direction.Dot(preferred) < 0.0f)
        {
            direction = -direction;
        }

        return true;
    }

    private bool TryGetCanonicalEntryDirection(Vector3 normal, out Vector3 direction)
    {
        direction = normal.Cross(Vector3.Up).Normalized();
        if (direction.IsZeroApprox()) return false;
        Vector3 incoming = GetHorizontalVelocity(_player.Velocity);
        Vector3 intent = GetCanonicalInputDirection();
        float incomingAlong = incoming.Dot(direction);
        float inputAlong = intent.Dot(direction);
        float confidence = Mathf.Clamp(CanonicalIntentMinAlignment, 0.05f, 0.8f);
        bool clearVelocity = Mathf.Abs(incomingAlong) >= Mathf.Max(0.1f, CanonicalMinProjectedSpeed)
            && Mathf.Abs(incomingAlong) >= incoming.Length() * confidence;
        bool clearInput = !intent.IsZeroApprox() && Mathf.Abs(inputAlong) >= confidence;
        float sign;
        if (clearVelocity)
        {
            if (clearInput && incomingAlong * inputAlong < 0.0f)
            {
                _entryIntent = "rejected_conflicting_intent";
                return false;
            }
            sign = Mathf.Sign(incomingAlong);
            _entryIntent = "incoming_tangent";
        }
        else if (clearInput)
        {
            sign = Mathf.Sign(inputAlong);
            _entryIntent = "input_fallback";
        }
        else if (!intent.IsZeroApprox())
        {
            _entryIntent = "rejected_ambiguous_input";
            return false;
        }
        else
        {
            float cameraAlong = GetFlatDirection(-_player.GlobalBasis.Z, Vector3.Forward).Dot(direction);
            if (Mathf.Abs(cameraAlong) < confidence)
            {
                _entryIntent = "rejected_ambiguous_camera";
                return false;
            }
            sign = Mathf.Sign(cameraAlong);
            _entryIntent = "camera_yaw_fallback";
        }
        direction *= sign;
        return true;
    }

    private Vector3 GetCanonicalInputDirection()
    {
        Vector2 input = GetMovementInput();
        if (input.LengthSquared() <= 0.01f) return Vector3.Zero;
        // The player owns yaw; visual camera roll/pitch must not bias intent.
        Basis basis = _player.GlobalBasis.Orthonormalized();
        return (GetFlatDirection(-basis.Z, Vector3.Forward) * input.Y
            + GetFlatDirection(basis.X, Vector3.Right) * input.X).Normalized();
    }

    private bool TryContinueCanonicalDirection(Vector3 normal, out Vector3 direction)
    {
        direction = normal.Cross(Vector3.Up).Normalized();
        float continuity = direction.Dot(_wallRunDirection);
        if (Mathf.Abs(continuity) < 0.5f) return false; // Do not rail around sharp corners.
        if (continuity < 0.0f) direction = -direction;
        Vector3 input = GetCanonicalInputDirection();
        // A deliberate reversal releases the wall instead of flipping velocity.
        return input.IsZeroApprox() || input.Dot(direction) >= -0.35f;
    }

    private bool PassesForwardDot(Vector3 runDirection)
    {
        Vector3 preferred = GetPreferredForwardDirection();
        return runDirection.Dot(preferred) >= CurrentMaxStartAngleForwardDot;
    }

    private bool HasForwardIntent()
    {
        Vector2 input = GetMovementInput();
        if (input.Y > 0.1f)
        {
            return true;
        }

        Vector3 horizontalVelocity = GetHorizontalVelocity(_player.Velocity);
        if (horizontalVelocity.Length() < CurrentMinEntrySpeed)
        {
            return false;
        }

        Vector3 forward = GetFlatCameraForward();
        return !forward.IsZeroApprox() && horizontalVelocity.Normalized().Dot(forward) >= CurrentMaxStartAngleForwardDot;
    }

    private bool IsSameWallOnCooldown(WallHit hit)
    {
        // Left/right changes when the player turns; it must not bypass the
        // cooldown for the same world-space wall surface.
        return _sameWallCooldownTimer > 0.0f
            && !_lastWallNormal.IsZeroApprox()
            && hit.Normal.Dot(_lastWallNormal) > 0.92f;
    }

    private float GetWallAlignmentScore(WallHit hit)
    {
        return Mathf.Max(0.0f, GetPreferredForwardDirection().Dot(hit.Normal.Cross(Vector3.Up).Normalized()));
    }

    private Vector3 GetSideDirection(WallSide side)
    {
        Basis basis = _player.GlobalTransform.Basis.Orthonormalized();
        return side switch
        {
            WallSide.Left => -basis.X.Normalized(),
            WallSide.Right => basis.X.Normalized(),
            _ => Vector3.Zero
        };
    }

    private Vector3 GetPreferredForwardDirection()
    {
        Vector2 input = GetMovementInput();
        if (input.LengthSquared() > 0.01f)
        {
            Basis basis = _player.Camera?.GlobalTransform.Basis.Orthonormalized() ?? _player.GlobalTransform.Basis.Orthonormalized();
            Vector3 forward = GetFlatDirection(-basis.Z, -_player.GlobalTransform.Basis.Z);
            Vector3 right = GetFlatDirection(basis.X, _player.GlobalTransform.Basis.X);
            Vector3 inputDirection = forward * input.Y + right * input.X;
            if (inputDirection.LengthSquared() > 0.0001f)
            {
                return inputDirection.Normalized();
            }
        }

        Vector3 velocity = GetHorizontalVelocity(_player.Velocity);
        if (velocity.LengthSquared() > 0.0001f)
        {
            return velocity.Normalized();
        }

        return GetFlatCameraForward();
    }

    private Vector3 GetFlatCameraForward()
    {
        Basis basis = _player.Camera?.GlobalTransform.Basis.Orthonormalized() ?? _player.GlobalTransform.Basis.Orthonormalized();
        return GetFlatDirection(-basis.Z, -_player.GlobalTransform.Basis.Z);
    }

    private static Vector3 GetFlatDirection(Vector3 axis, Vector3 fallbackAxis)
    {
        axis.Y = 0.0f;
        if (axis.LengthSquared() <= 0.0001f)
        {
            axis = fallbackAxis;
            axis.Y = 0.0f;
        }

        return axis.LengthSquared() > 0.0001f ? axis.Normalized() : Vector3.Forward;
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

    private string GetJumpAction()
    {
        return _player.JumpModule?.JumpAction ?? "jump";
    }

    private void UpdateCameraEffects(float delta)
    {
        Node3D cameraEffectsPivot = _player?.CameraEffectsPivot;
        if (cameraEffectsPivot == null)
        {
            if (!_warnedMissingCameraEffectsPivot)
            {
                GD.PushWarning("PlayerWallRunModule camera roll/pitch effects are disabled because PlayerController.CameraEffectsPivot was not found.");
                _warnedMissingCameraEffectsPivot = true;
            }
        }

        float targetRoll = 0.0f;
        float targetPitchOffset = 0.0f;
        if (cameraEffectsPivot != null && IsWallRunning && CurrentEnableCameraRoll)
        {
            float sideSign = _wallSide == WallSide.Left ? -1.0f : 1.0f;
            targetRoll = Mathf.DegToRad(CurrentWallRunCameraRollAngle) * sideSign;
            targetPitchOffset = Mathf.DegToRad(CurrentWallRunCameraPitchOffset);
        }

        float rollSpeed = Mathf.DegToRad(Mathf.Max(0.0f, IsWallRunning ? CurrentWallRunCameraRollEnterSpeed : CurrentWallRunCameraRollExitSpeed));
        _cameraRoll = Mathf.MoveToward(_cameraRoll, targetRoll, rollSpeed * delta);
        _cameraPitchOffset = Mathf.MoveToward(_cameraPitchOffset, targetPitchOffset, rollSpeed * delta);

        if (cameraEffectsPivot != null)
        {
            Vector3 effectsRotation = cameraEffectsPivot.Rotation;
            effectsRotation.X = _cameraPitchOffset;
            effectsRotation.Z = _cameraRoll;
            cameraEffectsPivot.Rotation = effectsRotation;
        }

        float targetFovBoost = IsWallRunning && CurrentEnableWallRunFovBoost ? CurrentWallRunFovBoost : 0.0f;
        float fovT = 1.0f - Mathf.Exp(-CurrentWallRunFovLerpSpeed * delta);
        _currentFovBoost = Mathf.Lerp(_currentFovBoost, targetFovBoost, fovT);
    }

    private static Vector3 GetHorizontalVelocity(Vector3 velocity)
    {
        return new Vector3(velocity.X, 0.0f, velocity.Z);
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private bool CurrentEnableWallRun => TuningProfile?.EnableWallRun ?? true;
    private bool CurrentRequireForwardInput => TuningProfile?.RequireWallRunForwardInput ?? true;
    private bool CurrentAllowWallRunFromGroundGrace => TuningProfile?.AllowWallRunFromGroundGrace ?? true;
    private bool CurrentEnableWallJump => TuningProfile?.EnableWallJump ?? true;
    private bool CurrentEnableCameraRoll => TuningProfile?.EnableWallRunCameraRoll ?? true;
    private bool CurrentEnableWallRunFovBoost => TuningProfile?.EnableWallRunFovBoost ?? true;
    private bool CurrentDebugWallRun => TuningProfile?.DebugWallRun ?? false;
    private float CurrentWallDetectionDistance => TuningProfile?.WallDetectionDistance ?? 0.9f;
    private float CurrentWallDetectionHeightOffset => TuningProfile?.WallDetectionHeightOffset ?? 1.0f;
    private float CurrentMinWallNormalVerticalDot => TuningProfile?.MinWallNormalVerticalDot ?? 0.25f;
    private float CurrentWallReattachCooldown => TuningProfile?.WallReattachCooldown ?? 0.08f;
    private float CurrentSameWallReattachCooldown => TuningProfile?.SameWallReattachCooldown ?? 0.22f;
    private float CurrentMinEntrySpeed => TuningProfile?.WallRunMinEntrySpeed ?? 7.0f;
    private float CurrentEntrySpeedRetention => TuningProfile?.WallRunEntrySpeedRetention ?? 0.85f;
    private float CurrentEntryGraceTime => TuningProfile?.WallRunEntryGraceTime ?? 0.12f;
    private float CurrentMaxStartAngleForwardDot => TuningProfile?.WallRunMaxStartAngleForwardDot ?? 0.2f;
    private float CurrentWallRunSpeed => TuningProfile?.WallRunSpeed ?? 17.0f;
    private float CurrentWallRunAcceleration => TuningProfile?.WallRunAcceleration ?? 55.0f;
    private float CurrentWallRunMaxDuration => TuningProfile?.WallRunMaxDuration ?? 1.4f;
    private float CurrentWallStickForce => TuningProfile?.WallStickForce ?? 16.0f;
    private float CurrentWallGravity => TuningProfile?.WallGravity ?? 3.5f;
    private float CurrentWallFallSpeedClamp => TuningProfile?.WallFallSpeedClamp ?? 7.0f;
    private float CurrentWallVerticalDamping => TuningProfile?.WallVerticalDamping ?? 0.35f;
    private float CurrentWallArcDownForce => TuningProfile?.WallArcDownForce ?? 7.0f;
    private float CurrentWallRunExitSpeedRetention => TuningProfile?.WallRunExitSpeedRetention ?? 0.9f;
    private float CurrentWallJumpAwayForce => TuningProfile?.WallJumpAwayForce ?? 13.0f;
    private float CurrentWallJumpUpForce => TuningProfile?.WallJumpUpForce ?? 12.0f;
    private float CurrentWallJumpForwardForce => TuningProfile?.WallJumpForwardForce ?? 10.0f;
    private float CurrentWallJumpSpeedClamp => TuningProfile?.WallJumpSpeedClamp ?? 24.0f;
    private float CurrentWallJumpLockoutTime => TuningProfile?.WallJumpLockoutTime ?? 0.08f;
    private float CurrentWallJumpCooldown => TuningProfile?.WallJumpCooldown ?? 0.16f;
    private float CurrentWallRunCameraRollAngle => TuningProfile?.WallRunCameraRollAngle ?? 12.0f;
    private float CurrentWallRunCameraRollEnterSpeed => TuningProfile?.WallRunCameraRollEnterSpeed ?? 120.0f;
    private float CurrentWallRunCameraRollExitSpeed => TuningProfile?.WallRunCameraRollExitSpeed ?? 160.0f;
    private float CurrentWallRunCameraPitchOffset => TuningProfile?.WallRunCameraPitchOffset ?? -1.5f;
    private float CurrentWallRunFovBoost => TuningProfile?.WallRunFovBoost ?? 8.0f;
    private float CurrentWallRunFovLerpSpeed => TuningProfile?.WallRunFovLerpSpeed ?? 10.0f;
}
