using Godot;
using System.Collections.Generic;

// Owns RMB intent only. No motor channels, bone writes, FOV or projectile writes.
public partial class PlayerRmbCombat : Node
{
    public enum CombatState { Idle, RmbAnticipation, Melee, ParrySuccess, PowerShotPrep, PowerShotReady, PowerShotRelease, Recovery }

    [ExportGroup("RMB Input")]
    [Export] public StringName InputAction { get; set; } = "rmb_combat";
    [Export] public bool ShowDebugReadout { get; set; } = true;
    [Export(PropertyHint.Range, "0.01,1,0.01,suffix:s")] public float TapHoldThreshold { get; set; } = 0.17f;
    [Export(PropertyHint.Range, "0.01,1,0.01,suffix:s")] public float ParryWindow { get; set; } = 0.14f;

    [ExportGroup("Melee / Parry Timing")]
    [Export(PropertyHint.Range, "0,1,0.01,suffix:s")] public float MeleeActiveDelay { get; set; } = 0.08f;
    [Export(PropertyHint.Range, "0.01,1,0.01,suffix:s")] public float MeleeActiveDuration { get; set; } = 0.12f;
    [Export(PropertyHint.Range, "0.01,2,0.01,suffix:s")] public float MeleeDuration { get; set; } = 0.30f;
    [Export(PropertyHint.Range, "0.01,2,0.01,suffix:s")] public float ParrySuccessDuration { get; set; } = 0.20f;
    [Export(PropertyHint.Range, "0,2,0.01,suffix:s")] public float RecoveryDuration { get; set; } = 0.18f;

    [ExportGroup("Logical Power Shot")]
    [Export(PropertyHint.Range, "0.01,5,0.01,suffix:s")] public float PowerChargeTime { get; set; } = 0.75f;
    [Export(PropertyHint.Range, "0,1,0.01,suffix:s")] public float BowReadyLeadTime { get; set; } = 0.08f;
    [Export(PropertyHint.Range, "0,1,0.01,suffix:s")] public float PowerReleasePoseTime { get; set; } = 0.06f;
    [Export(PropertyHint.Range, "0.01,2,0.01,suffix:s")] public float PowerReleaseDuration { get; set; } = 0.20f;
    [ExportGroup("Animation Mapping")]
    [Export] public RmbCombatAnimationSlots AnimationSlots { get; set; } = new();

    [Signal] public delegate void StateChangedEventHandler(string previous, string current);
    [Signal] public delegate void ParryWindowChangedEventHandler(bool active);
    [Signal] public delegate void ParrySucceededEventHandler(Node projectile);
    [Signal] public delegate void MeleeCommittedEventHandler();
    [Signal] public delegate void MeleeActiveWindowChangedEventHandler(bool active);
    [Signal] public delegate void MeleeHitReportedEventHandler(Node target, Vector3 worldPosition);
    [Signal] public delegate void PowerShotStartedEventHandler();
    [Signal] public delegate void PowerReadyEnteredEventHandler();
    [Signal] public delegate void PowerChargeUpdatedEventHandler(float charge);
    [Signal] public delegate void PowerShotReleasedEventHandler(Vector3 aimOrigin, Vector3 aimDirection, float charge, bool fullyCharged);

    public CombatState State { get; private set; }
    public string StateName => State.ToString();
    public float HeldTime => _gestureActive ? (float)(Now - _pressedAt) : _lastHeldTime;
    public float ChargeAmount { get; private set; }
    public bool PowerReady => State == CombatState.PowerShotReady;
    public bool IsParryWindowOpen => _gestureActive && _rmbHeld
        && (State == CombatState.RmbAnticipation || State == CombatState.PowerShotPrep)
        && HeldTime < Mathf.Max(0, ParryWindow);
    public bool IsMeleeActive => State == CombatState.Melee
        && StateTime >= Mathf.Max(0, MeleeActiveDelay)
        && StateTime < Mathf.Min(Mathf.Max(0, MeleeDuration), Mathf.Max(0, MeleeActiveDelay) + Mathf.Max(0, MeleeActiveDuration));
    public Vector3 AimOrigin => _player?.Camera?.GlobalPosition ?? Vector3.Zero;
    public Vector3 AimDirection => -(_player?.Camera?.GlobalBasis.Z ?? Vector3.Back).Normalized();

    public StringName RequestedAnimation => State switch
    {
        CombatState.RmbAnticipation => AnimationSlots.Anticipation,
        CombatState.Melee => AnimationSlots.Melee,
        CombatState.ParrySuccess => AnimationSlots.ParrySuccess,
        CombatState.PowerShotPrep => StateTime < BowReadyLeadTime ? AnimationSlots.BowReady : AnimationSlots.BowDrawStart,
        CombatState.PowerShotReady => AnimationSlots.BowFullDraw,
        CombatState.PowerShotRelease => StateTime < PowerReleasePoseTime ? AnimationSlots.BowRelease : AnimationSlots.BowFollowThrough,
        CombatState.Recovery => _powerRecovery ? AnimationSlots.BowRecovery : AnimationSlots.MeleeRecovery,
        _ => new StringName()
    };

    public string DebugReadout => $"RMB STATE: {StateName}  HELD: {HeldTime:0.000} s\n"
        + $"PARRY WINDOW: {(IsParryWindowOpen ? "ON" : "OFF")}  POWER READY: {(PowerReady ? "ON" : "OFF")}  CHARGE: {ChargeAmount:0%}\n"
        + $"MELEE ACTIVE: {(IsMeleeActive ? "ON" : "OFF")}  |  RMB tap: melee / hold: power (stub)";

    private PlayerController _player;
    private bool _rmbHeld, _gestureActive, _powerRecovery, _parryPublished, _meleePublished, _pendingPowerRelease, _releaseWasReady;
    private double _pressedAt, _stateStarted;
    private float _lastHeldTime;
    private readonly HashSet<ulong> _meleeTargets = new();
    private static double Now => Time.GetTicksUsec() / 1_000_000.0;
    private double StateTime => Now - _stateStarted;
    private bool CanUseInput => _player?.Camera != null && Input.MouseMode == Input.MouseModeEnum.Captured && !GetTree().Paused;

    public override void _Ready()
    {
        _player = GetParent() as PlayerController;
        // Release payload samples the gameplay camera after V2's -10 render pass.
        ProcessPriority = -5;
        AnimationSlots ??= new RmbCombatAnimationSlots();
        _stateStarted = Now;
    }

    public override void _Input(InputEvent input)
    {
        if (!input.IsAction(InputAction)) return;
        if (input.IsEcho()) return;
        if (!CanUseInput) { CancelGesture(); return; }
        AdvanceState();
        if (input.IsActionPressed(InputAction))
        {
            if (!_rmbHeld)
            {
                _rmbHeld = true;
                // Busy presses are discarded, never queued into the next attack.
                if (State == CombatState.Idle)
                {
                    _gestureActive = true;
                    _pressedAt = Now;
                    _lastHeldTime = 0;
                    ChargeAmount = 0;
                    _powerRecovery = false;
                    ChangeState(CombatState.RmbAnticipation);
                }
            }
        }
        else if (input.IsActionReleased(InputAction))
        {
            _rmbHeld = false;
            if (_gestureActive)
            {
                _lastHeldTime = HeldTime;
                _gestureActive = false;
                if (State == CombatState.RmbAnticipation)
                {
                    _meleeTargets.Clear();
                    ChangeState(CombatState.Melee);
                    EmitSignal(SignalName.MeleeCommitted);
                }
                else if (State == CombatState.PowerShotPrep || State == CombatState.PowerShotReady)
                {
                    _releaseWasReady = PowerReady;
                    _pendingPowerRelease = true;
                    _powerRecovery = true;
                    ChangeState(CombatState.PowerShotRelease);
                }
            }
        }
        PublishWindows();
        GetViewport().SetInputAsHandled();
    }

    public override void _Process(double delta)
    {
        if (!CanUseInput) { CancelGesture(); return; }
        if (_pendingPowerRelease)
        {
            _pendingPowerRelease = false;
            // A request only: no projectile, damage, Nock or existing LMB writer here.
            EmitSignal(SignalName.PowerShotReleased, AimOrigin, AimDirection, ChargeAmount, _releaseWasReady);
        }
        AdvanceState();
        if (State == CombatState.PowerShotPrep || State == CombatState.PowerShotReady)
            EmitSignal(SignalName.PowerChargeUpdated, ChargeAmount);
    }

    private void AdvanceState()
    {
        if (_gestureActive && State == CombatState.RmbAnticipation && HeldTime >= Mathf.Max(0.001f, TapHoldThreshold))
        {
            ChangeState(CombatState.PowerShotPrep);
            EmitSignal(SignalName.PowerShotStarted);
        }
        if (_gestureActive && (State == CombatState.PowerShotPrep || State == CombatState.PowerShotReady))
        {
            ChargeAmount = Mathf.Clamp((HeldTime - Mathf.Max(0.001f, TapHoldThreshold)) / Mathf.Max(0.001f, PowerChargeTime), 0, 1);
            if (ChargeAmount >= 1 && State == CombatState.PowerShotPrep)
            {
                ChangeState(CombatState.PowerShotReady);
                EmitSignal(SignalName.PowerReadyEntered);
            }
        }
        if ((State == CombatState.Melee && StateTime >= Mathf.Max(0, MeleeDuration))
            || (State == CombatState.ParrySuccess && StateTime >= Mathf.Max(0, ParrySuccessDuration))
            || (State == CombatState.PowerShotRelease && StateTime >= Mathf.Max(0, PowerReleaseDuration)))
            ChangeState(CombatState.Recovery);
        else if (State == CombatState.Recovery && StateTime >= Mathf.Max(0, RecoveryDuration))
        {
            ChangeState(CombatState.Idle);
            _lastHeldTime = 0;
            ChargeAmount = 0;
        }
        PublishWindows();
    }

    // The projectile/collision owner decides eligibility and what a successful
    // parry does to the projectile. This foundation only atomically consumes intent.
    public bool TryParryProjectile(Node projectile, bool eligible)
    {
        if (!CanUseInput || !eligible || !IsInstanceValid(projectile)) return false;
        AdvanceState();
        if (!IsParryWindowOpen) return false;
        _lastHeldTime = HeldTime;
        _gestureActive = false;
        _pendingPowerRelease = false;
        ChangeState(CombatState.ParrySuccess);
        EmitSignal(SignalName.ParrySucceeded, projectile);
        return true;
    }

    public bool DebugTryParry() => OS.IsDebugBuild() && TryParryProjectile(this, true);

    // Future hit detection calls this during the window; each target is accepted
    // once per melee. A consumer subscribes to MeleeHitReported to apply damage.
    public bool TryReportMeleeHit(Node target, Vector3 worldPosition)
    {
        if (!CanUseInput || !IsMeleeActive || !IsInstanceValid(target) || !_meleeTargets.Add(target.GetInstanceId())) return false;
        EmitSignal(SignalName.MeleeHitReported, target, worldPosition);
        return true;
    }

    public void CancelGesture()
    {
        _rmbHeld = _gestureActive = _pendingPowerRelease = false;
        _lastHeldTime = ChargeAmount = 0;
        _meleeTargets.Clear();
        if (State != CombatState.Idle) ChangeState(CombatState.Idle);
        PublishWindows();
    }

    public override void _Notification(int what)
    {
        if (what == NotificationWMWindowFocusOut || what == NotificationPaused) CancelGesture();
    }

    private void ChangeState(CombatState next)
    {
        string previous = StateName;
        State = next;
        _stateStarted = Now;
        PublishWindows();
        EmitSignal(SignalName.StateChanged, previous, StateName);
    }

    private void PublishWindows()
    {
        bool parry = IsParryWindowOpen, melee = IsMeleeActive;
        if (_parryPublished != parry) { _parryPublished = parry; EmitSignal(SignalName.ParryWindowChanged, parry); }
        if (_meleePublished != melee) { _meleePublished = melee; EmitSignal(SignalName.MeleeActiveWindowChanged, melee); }
    }
}
