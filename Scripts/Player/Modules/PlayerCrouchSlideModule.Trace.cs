using Godot;

public partial class PlayerCrouchSlideModule
{
    // Read-only diagnostics, including raw direction after exit (presentation getter returns zero).
    public float TraceTimer => _slideTimer;
    public float TraceBuffer => _airborneSlideBufferTimer;
    public object GetMovementTraceState() => new
    {
        state = _state.ToString(), is_sliding = IsSliding, is_crouching = IsCrouching,
        direction = PlayerMovementTrace.V(_slideDirection), internal_speed = _slideSpeed,
        timer = _slideTimer, duration = CurrentSlideDuration,
        cooldown_timer = _slideCooldownTimer, cooldown = CurrentSlideCooldown,
        exit_speed_grace_timer = _slideExitSpeedGraceTimer, exit_speed_grace = CurrentSlideExitMinSpeedGraceTime,
        airborne_buffer_timer = _airborneSlideBufferTimer, airborne_buffer_time = CurrentAirborneSlideBufferTime,
        enable_slide = EnableSlide, enable_crouch = EnableCrouch,
        min_start_speed = SlideMinStartSpeed, initial_speed = CurrentSlideInitialSpeed,
        friction = CurrentSlideFriction, exit_by_speed = CurrentEnableSlideExitBySpeed,
        exit_min_speed = CurrentSlideExitMinSpeed, airborne_enabled = CurrentEnableAirborneSlideEntry,
        airborne_min_speed = CurrentAirborneSlideMinSpeed,
        gesture_id = _slideGestureId, gesture_state = _slideGestureState.ToString(),
        gesture_consumed = IsSlideGestureConsumed, airborne_intent_armed = _airborneSlideIntentArmed,
        gesture_press_pending = _slideGesturePressPending, jump_consumed_this_tick = JumpConsumedThisTick,
        rearm = "one acquisition per gesture; release then press to rearm; airborne TTL never refreshed by held input",
        slide_jump_enabled = CurrentEnableSlideJump,
        slide_jump_requires_stand_space = CurrentSlideJumpRequiresStandUpSpace
    };

    private void TracePosture(CrouchSlideState previous, string reason, object before = null, Vector3? velocity = null)
        => _player.MovementTrace?.StateChange("POSTURE", previous.ToString(), _state.ToString(), reason, before, velocity);
}
