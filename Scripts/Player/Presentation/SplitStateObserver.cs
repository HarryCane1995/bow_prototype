using Godot;

// One read-only snapshot routes BOTH branches. Presentation holds never block
// gameplay, and clip lengths never determine gameplay or observer transitions.
public sealed class SplitStateObserver
{
    public PresentationState State { get; private set; }
    public PresentationState Locomotion { get; private set; }
    private bool _grounded, _wall, _wallJump, _grappleFlight, _running, _initialized;
    private float _jumpAge = 10, _landingAge = 10, _launchAge = 10, _shotAge = 10;
    private uint _shot;
    private PlayerSlingshotGrappleModule.SlingshotGrappleState _grapple;
    public void Observe(PlayerController p, PlayerRmbCombat combat, float dt)
    {
        _jumpAge += dt; _landingAge += dt; _launchAge += dt; _shotAge += dt;
        bool ground = p.IsGrounded, wall = p.WallRunModule.IsWallRunning;
        var grapple = p.SlingshotGrappleModule.CurrentState;
        if (_initialized)
        {
            if (_grounded && !ground && p.Velocity.Y > 0) { _jumpAge = 0; _wallJump = false; }
            if (!_grounded && ground) _landingAge = 0;
            if (_wall && !wall && p.Velocity.Y > 0 && Input.IsActionJustPressed(p.JumpModule.JumpAction)) { _jumpAge = 0; _wallJump = true; }
            if (grapple == PlayerSlingshotGrappleModule.SlingshotGrappleState.Launching && grapple != _grapple
                || _grapple == PlayerSlingshotGrappleModule.SlingshotGrappleState.Pulling && grapple == PlayerSlingshotGrappleModule.SlingshotGrappleState.Cooldown)
            { _launchAge = 0; _grappleFlight = true; }
            if (_shot != p.BowVisualModule.ShotVisualSequence) _shotAge = 0;
        }
        if (ground || wall || p.CrouchSlideModule.IsSliding) _grappleFlight = false;
        float speed = new Vector2(p.Velocity.X,p.Velocity.Z).Length();
        _running = ground && speed >= (_running ? 1 : 2);
        if (p.CrouchSlideModule.IsSliding) Locomotion = PresentationState.Slide;
        else if (wall) Locomotion = p.WallRunModule.ActiveWallSide == PlayerWallRunModule.WallSide.Left ? PresentationState.WallrunLeft : PresentationState.WallrunRight;
        else if (grapple == PlayerSlingshotGrappleModule.SlingshotGrappleState.Pulling) Locomotion = PresentationState.GrapplePull;
        else if (_launchAge < .14f) Locomotion = PresentationState.GrappleLaunch;
        else if (_grappleFlight && !ground) Locomotion = PresentationState.GrappleFlight;
        else if (_jumpAge < .12f) Locomotion = _wallJump ? PresentationState.WallJump : PresentationState.JumpTakeoff;
        else if (!ground) Locomotion = p.Velocity.Y > 0 ? PresentationState.JumpAir : PresentationState.Fall;
        else if (_landingAge < .12f) Locomotion = PresentationState.Landing;
        else Locomotion = p.CrouchSlideModule.IsCrouching ? PresentationState.Crouch : _running ? PresentationState.Run : PresentationState.Idle;
        State = CombatState(combat) ?? (_shotAge < .06f ? PresentationState.BowRelease
            : _shotAge < .16f ? PresentationState.BowFollowThrough : _shotAge < .30f ? PresentationState.BowRecovery
            : p.BowVisualModule.IsDrawing ? (p.BowVisualModule.DrawAmount >= .99f ? PresentationState.BowFullDraw : PresentationState.BowDrawStart)
            : p.BowVisualModule.IsPrecisionAiming ? PresentationState.BowReady : Locomotion);
        _grounded=ground;_wall=wall;_grapple=grapple;_shot=p.BowVisualModule.ShotVisualSequence;_initialized=true;
    }
    private static PresentationState? CombatState(PlayerRmbCombat combat)
    {
        if (combat == null) return null;
        var name = combat.RequestedAnimation;var map = combat.AnimationSlots;
        if (name == null || name.IsEmpty) return null;
        // Existing combat API returns named slots. Translate at this ONE boundary.
        if (name==map.Anticipation) return PresentationState.RmbAnticipation;
        if (name==map.Melee) return PresentationState.Melee;
        if (name==map.ParrySuccess) return PresentationState.Parry;
        if (name==map.MeleeRecovery) return PresentationState.MeleeRecovery;
        if (name==map.BowReady) return PresentationState.BowReady;
        if (name==map.BowDrawStart) return PresentationState.BowDrawStart;
        if (name==map.BowFullDraw) return PresentationState.BowFullDraw;
        if (name==map.BowRelease) return PresentationState.BowRelease;
        if (name==map.BowFollowThrough) return PresentationState.BowFollowThrough;
        if (name==map.BowRecovery) return PresentationState.BowRecovery;
        return null;
    }
}
