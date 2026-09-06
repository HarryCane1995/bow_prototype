using Godot;
using System;
using System.Collections.Generic;

// AUDIO OBSERVES MOVEMENT. This autoload never writes player state, input or tuning.
// It survives R/F1 so old loops can fade naturally while a new prefab is bound.
public partial class PlayerAudioController : Node
{
    [Export] public GameplayAudioSettings Settings { get; set; } = new();
    private PlayerController _player;
    private Node _course;
    private Vector3 _lastVelocity;
    private bool _grounded, _wall, _slide;
    private int _grapple, _checkpoint = -1;
    private double _time, _lastGroundTime = -10, _nextTrace;
    private float _attachDelay = -1, _duck, _wind, _airSeconds, _preContactFallSpeed;
    private Godot.FileAccess _trace;
    private bool _initialized;

    public override void _Ready()
    {
        ProcessPhysicsPriority = 100; // Observe the result of PlayerController.MoveAndSlide.
        ProcessMode = ProcessModeEnum.Always;
        InitializePlayback();
        InitializePanel();
        foreach (string arg in OS.GetCmdlineUserArgs())
            if (arg.StartsWith("--audio-trace="))
                _trace = Godot.FileAccess.Open(arg[14..], Godot.FileAccess.ModeFlags.Write);
        _initialized = true;
    }

    public override void _PhysicsProcess(double delta)
    {
        if (!_initialized) return;
        _time += delta;
        _duck = Mathf.Max(0, _duck - (float)delta);
        var candidate = GetTree().GetFirstNodeInGroup("player") as PlayerController;
        if (!IsInstanceValid(candidate) || !candidate.IsInsideTree()) candidate = null;
        if (_player != candidate) Bind(candidate);
        bool active = IsInstanceValid(_player) && !GetTree().Paused;
        if (active) Observe((float)delta);
        if (_attachDelay >= 0)
        {
            _attachDelay -= (float)delta;
            if (_attachDelay < 0 && active && _grapple == 1) OneShot("grapple_attach", "Grapple", -10);
        }
        UpdateLayers((float)delta, active);
        if (_time >= _nextTrace)
        {
            _nextTrace = _time + .1;
            Trace("sample", new Godot.Collections.Dictionary {
                ["horizontal_speed"] = active ? Horizontal(_player.Velocity) : 0,
                ["vertical_speed"] = active ? _player.Velocity.Y : 0,
                ["wind"] = _wind, ["slide"] = _slide, ["wall"] = _wall,
                ["grapple"] = _grapple, ["voices"] = ActiveVoices(),
                ["loops"] = LoopSnapshot(), ["player_id"] = active ? _player.GetInstanceId() : 0UL });
            _trace?.Flush();
        }
    }

    private void Bind(PlayerController player)
    {
        _player = player;
        _attachDelay = -1;
        _wall = _slide = false;
        _grapple = 0;
        _course = null;
        _checkpoint = -1;
        if (player == null) return;
        _lastVelocity = player.Velocity;
        _grounded = player.IsOnFloor();
        _airSeconds = 0;
        _preContactFallSpeed = 0;
        _lastGroundTime = -10;
        // Optional Gym adapter: read existing public properties. No dependency
        // on the untracked Gym types, no checkpoint hooks or scene modifications.
        Node parent = player.GetParent();
        if (parent.GetScript().AsGodotObject() is Script script &&
            script.ResourcePath.EndsWith("/MovementGymCourse.cs")) _course = parent;
        if (_course != null) _checkpoint = _course.Get("CurrentCheckpoint").AsInt32();
        OneShot("reset", "System", -12);
        Trace("bind", new Godot.Collections.Dictionary { ["player_id"] = player.GetInstanceId() });
    }

    private void Observe(float delta)
    {
        Vector3 velocity = _player.Velocity;
        bool grounded = _player.IsOnFloor();
        if (!grounded) _airSeconds += delta;
        // GroundCheck may make the jump module clamp Y to its snap velocity one
        // tick before IsOnFloor. Retain the last free-flight velocity through
        // that proximity interval instead of mistaking -3.2 m/s for the impact.
        if (!_player.IsGrounded) _preContactFallSpeed = Mathf.Max(0, -velocity.Y);
        bool wall = _player.WallRunModule?.IsWallRunning == true;
        bool slide = _player.CrouchSlideModule?.IsSliding == true;
        int grapple = (int)(_player.SlingshotGrappleModule?.CurrentState ?? 0);
        bool wallJump = _wall && !wall && _player.WallRunModule.GetDebugText().Contains("lastExit=wall_jump");
        if (wall != _wall) OneShot(wall ? "wall_enter" : "wall_exit", "Movement", wall ? -12 : -16, Settings.Wallrun);
        if (wallJump) OneShot("wall_jump", "Movement", -8, Settings.Wallrun);
        if (slide != _slide) OneShot(slide ? "slide_enter" : "slide_exit", "Movement", slide ? -11 : -17, Settings.Slide);
        if (grapple == 1 && _grapple != 1)
        {
            OneShot("grapple_fire", "Grapple", -9);
            _attachDelay = .045f;
        }
        if (_grapple == 1 && grapple != 1)
        {
            _attachDelay = -1;
            OneShot("grapple_release", "Grapple", -9);
        }
        // Successful jump inferred from input + observed impulse; rejected jump
        // spam stays silent. The coyote window is read, never modified.
        if (!wallJump && !_wall && !wall && grapple != 1 &&
            Input.IsActionJustPressed(_player.JumpModule.JumpAction) && velocity.Y > _lastVelocity.Y + .1f)
        {
            bool groundJump = _grounded || (_player.JumpModule.UseCoyoteTime && _time - _lastGroundTime <= _player.JumpModule.CoyoteTime);
            OneShot(groundJump ? "jump" : "air_jump", "Movement", -9);
        }
        if (grounded && !_grounded && _airSeconds >= .06f)
        {
            float impact = Mathf.Max(_preContactFallSpeed, -_lastVelocity.Y);
            if (impact >= Settings.LandingThreshold)
            {
                string family = impact < 8 ? "landing_light" : impact < 19 ? "landing_medium" : "landing_heavy";
                float energy = Mathf.Clamp((impact - Settings.LandingThreshold) / 30f, 0, 1);
                OneShot(family, "Movement", Mathf.Lerp(-16, -6, Mathf.Sqrt(energy)), Settings.Landing,
                    Mathf.Lerp(1.12f, .91f, energy));
                Trace("landing_impact", new Godot.Collections.Dictionary { ["impact"] = impact, ["family"] = family });
            }
        }
        if (_course != null && IsInstanceValid(_course))
        {
            int checkpoint = _course.Get("CurrentCheckpoint").AsInt32();
            if (checkpoint > _checkpoint) OneShot("checkpoint", "System", -10);
            _checkpoint = checkpoint;
        }
        if (grounded) { _lastGroundTime = _time; _airSeconds = 0; _preContactFallSpeed = 0; }
        _grounded = grounded; _wall = wall; _slide = slide; _grapple = grapple; _lastVelocity = velocity;
    }

    private static float Horizontal(Vector3 velocity) => new Vector2(velocity.X, velocity.Z).Length();

    private void UpdateLayers(float delta, bool active)
    {
        float speed = active ? Horizontal(_player.Velocity) : 0;
        float amount = Mathf.Clamp((speed - Settings.WindThreshold) / Mathf.Max(1, Settings.WindFullSpeed - Settings.WindThreshold), 0, 1);
        _wind = Mathf.Lerp(_wind, amount, 1 - Mathf.Exp(-Settings.WindResponse * delta));
        float duck = _duck > 0 ? .64f : 1f;
        SetLoop("wind_low", _wind * _wind * .14f * duck, .85f + .30f * _wind, delta);
        SetLoop("wind_high", Mathf.Pow(_wind, 2.7f) * .10f * duck, .90f + .30f * _wind, delta);
        float contact = Mathf.Clamp(speed / 35, 0, 1);
        SetLoop("slide_loop", active && _slide ? (.04f + .18f * contact) * Settings.Slide : 0, .8f + .4f * contact, delta);
        SetLoop("wall_loop", active && _wall ? (.04f + .14f * contact) * Settings.Wallrun : 0, .85f + .3f * contact, delta);
        SetLoop("grapple_loop", active && _grapple == 1 ? .07f + .13f * contact : 0, .85f + .4f * contact, delta);
        ApplyMix(delta);
    }

    private void Trace(string kind, Godot.Collections.Dictionary details)
    {
        if (_trace == null) return;
        details["time"] = _time; details["kind"] = kind;
        _trace.StoreLine(Json.Stringify(details));
    }

    public override void _ExitTree()
    {
        _trace?.Dispose();
        _trace = null;
    }
}
