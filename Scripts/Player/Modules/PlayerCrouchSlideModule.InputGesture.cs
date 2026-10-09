using Godot;

public partial class PlayerCrouchSlideModule
{
    private enum SlideGestureState { Released, Available, Consumed }

    private SlideGestureState _slideGestureState;
    private long _slideGestureId;
    private bool _slideGesturePressPending;
    private bool _airborneSlideIntentArmed;

    public long SlideGestureId => _slideGestureId;
    public bool IsSlideGestureConsumed => _slideGestureState == SlideGestureState.Consumed;
    public bool IsAirborneSlideIntentArmed => _airborneSlideIntentArmed;
    private bool HasAvailableSlideGesture => _slideGestureState == SlideGestureState.Available;
    private bool JumpConsumedThisTick => _player.JumpModule?.JumpConsumedThisTick == true;

    // Observe edges without consuming the event. This also preserves release/press pairs
    // arriving between physics ticks; keyboard repeat cannot create another gesture.
    public override void _Input(InputEvent input)
    {
        if (_player == null || input is InputEventKey { Echo: true }) return;
        if (input.IsActionReleased(CrouchSlideAction) && !Input.IsActionPressed(CrouchSlideAction))
            EndSlideGesture();
        else if (input.IsActionPressed(CrouchSlideAction) && _slideGestureState == SlideGestureState.Released)
            BeginSlideGesture();
    }

    private bool UpdateSlideGesture(bool held, bool justPressed)
    {
        if (!held) EndSlideGesture();
        // Input.ActionPress has no InputEvent callback; use the same edge semantics.
        else if (justPressed && _slideGestureState == SlideGestureState.Released) BeginSlideGesture();
        bool freshPress = _slideGesturePressPending && held;
        _slideGesturePressPending = false;
        return freshPress;
    }

    private void BeginSlideGesture()
    {
        _slideGestureState = SlideGestureState.Available;
        _slideGestureId++;
        _slideGesturePressPending = true;
        ClearAirborneSlideIntent();
        _player.MovementTrace?.Emit("SLIDE_GESTURE_BEGIN", "slide action DOWN: new available gesture");
    }

    private void EndSlideGesture()
    {
        if (_slideGestureState == SlideGestureState.Released) return;
        _slideGestureState = SlideGestureState.Released;
        _slideGesturePressPending = false;
        ClearAirborneSlideIntent();
        _player.MovementTrace?.Emit("SLIDE_GESTURE_END", "slide action released: pending intent cleared");
    }

    private void ConsumeSlideGesture()
    {
        _slideGestureState = SlideGestureState.Consumed;
        _slideGesturePressPending = false;
        ClearAirborneSlideIntent();
    }

    private void ClearAirborneSlideIntent()
    {
        _airborneSlideIntentArmed = false;
        _airborneSlideBufferTimer = 0.0f;
    }
}
