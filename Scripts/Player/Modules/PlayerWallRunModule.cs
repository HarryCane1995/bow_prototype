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
    private WallSide _lastWallSide = WallSide.None;
    private float _cameraRoll;
    private float _cameraPitchOffset;
    private float _currentFovBoost;
    private string _lastExitReason = "none";

    public bool IsWallRunning { get; private set; }
    public bool BlocksNormalJumpAndGravity => IsWallRunning || _blockNormalJumpThisFrame;
    public float CurrentFovBoost => _currentFovBoost;

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
        return $"{state}, timer={_wallRunTimer:0.00}, normal=({_wallNormal.X:0.00},{_wallNormal.Y:0.00},{_wallNormal.Z:0.00}), cooldown={_reattachCooldownTimer:0.00}, sameCooldown={_sameWallCooldownTimer:0.00}, fovBoost={_currentFovBoost:0.00}, lastExit={_lastExitReason}";
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

        if (!TryGetWallRunDirection(hit.Normal, out Vector3 runDirection))
        {
            return;
        }

        if (!PassesForwardDot(runDirection))
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
        if (!hasAirState)
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

        return _player.AbilityStateModule == null
            || _player.AbilityStateModule.CanStart(PlayerAbilityLock.HorizontalVelocity | PlayerAbilityLock.VerticalVelocity | PlayerAbilityLock.Slide);
    }

    private void BeginWallRun(WallHit hit, Vector3 runDirection)
    {
        IsWallRunning = true;
        _wallRunTimer = 0.0f;
        _wallSide = hit.Side;
        _wallNormal = hit.Normal;
        _wallRunDirection = runDirection;
        _lastExitReason = "running";

        _player.CrouchSlideModule?.CancelSlide();
        _player.JumpModule?.RestoreAirJumpChargeFromWallRun();
        _player.AbilityStateModule?.BeginAbility(
            PlayerAbilityTag.WallRun,
            PlayerAbilityStateModule.PriorityWallRun,
            PlayerAbilityLock.HorizontalVelocity | PlayerAbilityLock.VerticalVelocity | PlayerAbilityLock.Slide,
            nameof(PlayerWallRunModule)
        );

        Vector3 velocity = _player.Velocity;
        float carriedSpeed = Mathf.Abs(GetHorizontalVelocity(velocity).Dot(_wallRunDirection)) * CurrentEntrySpeedRetention;
        float entrySpeed = Mathf.Max(CurrentWallRunSpeed, carriedSpeed);
        velocity.X = _wallRunDirection.X * entrySpeed;
        velocity.Z = _wallRunDirection.Z * entrySpeed;
        velocity.Y = Mathf.Max(velocity.Y * (1.0f - CurrentWallVerticalDamping), -CurrentWallFallSpeedClamp);
        _player.Velocity = velocity;

        if (CurrentDebugWallRun)
        {
            GD.Print($"WallRun enter side={_wallSide} normal={_wallNormal} direction={_wallRunDirection}");
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

        if (CurrentRequireForwardInput && !HasForwardIntent())
        {
            EndWallRun("input_released", true);
            return;
        }

        if (!TryFindBestWall(_wallSide, out WallHit hit))
        {
            EndWallRun("lost_wall", true);
            return;
        }

        if (!TryGetWallRunDirection(hit.Normal, out Vector3 runDirection))
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

        ApplyWallRunVelocity(delta);
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
        _lastWallSide = _wallSide;
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
        hit = default;
        Vector3 origin = _player.GlobalPosition + Vector3.Up * CurrentWallDetectionHeightOffset;
        Vector3 sideDirection = GetSideDirection(side);
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
        return _sameWallCooldownTimer > 0.0f
            && hit.Side == _lastWallSide
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
        if (_player?.CameraPivot == null)
        {
            return;
        }

        float targetRoll = 0.0f;
        float targetPitchOffset = 0.0f;
        if (IsWallRunning && CurrentEnableCameraRoll)
        {
            float sideSign = _wallSide == WallSide.Left ? -1.0f : 1.0f;
            targetRoll = Mathf.DegToRad(CurrentWallRunCameraRollAngle) * sideSign;
            targetPitchOffset = Mathf.DegToRad(CurrentWallRunCameraPitchOffset);
        }

        float rollSpeed = Mathf.DegToRad(Mathf.Max(0.0f, IsWallRunning ? CurrentWallRunCameraRollEnterSpeed : CurrentWallRunCameraRollExitSpeed));
        _cameraRoll = Mathf.MoveToward(_cameraRoll, targetRoll, rollSpeed * delta);
        _cameraPitchOffset = Mathf.MoveToward(_cameraPitchOffset, targetPitchOffset, rollSpeed * delta);

        Vector3 pivotRotation = _player.CameraPivot.Rotation;
        pivotRotation.Z = _cameraRoll;
        _player.CameraPivot.Rotation = pivotRotation;

        if (_player.Camera != null)
        {
            Vector3 cameraRotation = _player.Camera.Rotation;
            cameraRotation.X = _cameraPitchOffset;
            _player.Camera.Rotation = cameraRotation;
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
