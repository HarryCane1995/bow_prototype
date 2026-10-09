using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

// Opt-in observer. Never writes input, velocity, collision, ability state or tuning.
public partial class PlayerMovementTrace : Node
{
    private static PlayerMovementTrace _activeSession;
    private PlayerController _player;
    private TraceWriter _writer;
    private Label _marker;
    private string _sessionId, _stopPath, _phase = "ready", _mode;
    private string _lastExitReason;
    private double _seconds, _lastEnter = -1, _lastExit = -1, _nextSample, _nextHeld, _nextPoll;
    private bool _recording, _held, _onFloor, _grounded, _captureRequested, _captureStarted;
    private object _lastContact;
    private Vector3 _beforeMoveVelocity;
    private long _sequence;
    private readonly Queue<RingSample> _ring = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.AllowNamedFloatingPointLiterals
    };

    public static PlayerMovementTrace AttachIfRequested(PlayerController player)
    {
        string mode = OS.GetCmdlineUserArgs().FirstOrDefault(a => a.StartsWith("--movement-trace="));
        if (mode == null) return null;
        if (IsInstanceValid(_activeSession))
        {
            var active = _activeSession;
            active._player = player;
            active._onFloor = player.IsOnFloor();
            active._grounded = player.IsGrounded;
            active._lastContact = active.Contact();
            active._mode = null;
            active._ring.Clear();
            active.Emit("PLAYER_REBIND", "new player instance after scene reload; same human session");
            return active;
        }
        var trace = new PlayerMovementTrace { Name = "MovementSessionTrace", _player = player };
        string requestedMode = mode["--movement-trace=".Length..];
        trace.Start(requestedMode is "human" or "human_fixed" or "regression" ? requestedMode : "smoke");
        _activeSession = trace;
        // Root-owned so a normal respawn / scene reload does not truncate latest_human_session.
        player.GetTree().Root.CallDeferred(Node.MethodName.AddChild, trace);
        return trace;
    }

    private void Start(string mode)
    {
        string directory = ProjectSettings.GlobalizePath("res://.godot/movement-traces");
        _sessionId = $"{mode}_{DateTimeOffset.UtcNow:yyyyMMdd_HHmmss_fff}Z_{Guid.NewGuid():N}";
        _stopPath = Path.Combine(directory, $"stop_{_sessionId}.request");
        _writer = new TraceWriter(directory, $"latest_{mode}_session.jsonl", _sessionId + ".jsonl");
        _recording = _writer.Error == null;
        _captureRequested = OS.GetCmdlineUserArgs().Contains("--movement-trace-capture");
        _onFloor = _player.IsOnFloor();
        _grounded = _player.IsGrounded;
        _lastContact = Contact();
        Emit("SESSION_START", mode == "regression" ? "controlled regression: synthetic key input" : "opt-in command line; human input", details: new
        {
            mode, session_id = _sessionId, latest_path = _writer.LatestPath,
            archive_path = _writer.ArchivePath, stop_request_path = _stopPath,
            scene = _player.GetTree().CurrentScene?.SceneFilePath ?? _player.GetParent().SceneFilePath,
            player_path = _player.GetPath().ToString(), physics_hz = Engine.PhysicsTicksPerSecond,
            rapid_reentry_seconds = 0.5, ring_seconds = 2.0, periodic_sample_hz = 2,
            flush_seconds = 0.5, schema_version = 2,
            state_contract = "Separate authoritative posture, ability requests, wallrun and grapple states; locomotion_mode is derived. No separate RUN authority exists: GROUND_MOVE is running/walking at the configured MoveSpeed.",
            floor_contract = "IsOnFloor is last MoveAndSlide result; IsGrounded also uses existing GroundCheck and velocity.Y <= 0. No extra physics queries. Floor contact is a matching collision normal candidate; ray contact is separately identified."
        });
    }

    public override void _Ready()
    {
        ProcessMode = ProcessModeEnum.Always;
        var canvas = new CanvasLayer { Name = "MovementTraceReadout", Layer = 128 };
        AddChild(canvas);
        _marker = new Label
        {
            Name = "MovementTraceStatus", Text = "MOVEMENT TRACE: REC",
            MouseFilter = Control.MouseFilterEnum.Ignore,
            Position = new Vector2(18, 90)
        };
        _marker.AddThemeFontSizeOverride("font_size", 17);
        _marker.AddThemeColorOverride("font_color", new Color(0.5f, 1, 0.65f));
        _marker.AddThemeColorOverride("font_outline_color", Colors.Black);
        _marker.AddThemeConstantOverride("outline_size", 5);
        canvas.AddChild(_marker);
        UpdateMarker();
        GD.Print($"MOVEMENT_TRACE_READY latest={_writer.LatestPath} archive={_writer.ArchivePath} stop={_stopPath}");
    }

    public override void _Input(InputEvent input)
    {
        if (!_recording || !IsInstanceValid(_player) || input is InputEventKey { Echo: true }) return;
        string action = _player.CrouchSlideModule.CrouchSlideAction;
        if (input.IsActionPressed(action) || input.IsActionReleased(action))
            Emit(input.IsActionPressed(action) ? "SLIDE_INPUT_DOWN" : "SLIDE_INPUT_UP",
                "raw InputEvent action edge (does not consume input)", details: new
                {
                    source = "raw_event", physical_key = input is InputEventKey key ? key.PhysicalKeycode.ToString() : null,
                    logical_key = input is InputEventKey key2 ? key2.Keycode.ToString() : null
                });
    }

    public void BeginTick(double delta)
    {
        if (!_recording) return;
        _seconds += delta;
        _phase = "physics_begin";
        string action = _player.CrouchSlideModule.CrouchSlideAction;
        bool held = Input.IsActionPressed(action);
        if (held != _held)
            Emit(held ? "SLIDE_INPUT_DOWN" : "SLIDE_INPUT_UP", "physics action state changed", details: new { source = "physics_poll" });
        if (held && (_seconds >= _nextHeld || !_held))
        {
            Emit("SLIDE_INPUT_HELD", "IsActionPressed at physics begin (maximum 1 Hz)");
            _nextHeld = _seconds + 1;
        }
        _held = held;
        ObserveFloor();
    }

    public void BeforeMove()
    {
        if (!_recording) return;
        _phase = "before_MoveAndSlide";
        _beforeMoveVelocity = _player.Velocity;
        ObserveFloor();
    }

    public void AfterMove()
    {
        if (!_recording) return;
        _phase = "after_MoveAndSlide";
        ObserveFloor();
        string mode = LocomotionMode();
        if (_mode != mode)
        {
            Emit("LOCOMOTION_MODE_CHANGE", "derived from live module flags, grounded and horizontal velocity after MoveAndSlide",
                _mode ?? "INITIAL", mode, new { authoritative = false });
            _mode = mode;
        }
        _ring.Enqueue(new RingSample(_seconds, Engine.GetPhysicsFrames(), Engine.GetProcessFrames(),
            _player.GlobalPosition, _player.Velocity, _beforeMoveVelocity, _player.IsOnFloor(), _player.IsGrounded,
            _player.CrouchSlideModule.IsSliding, _held, MovementInput(),
            _player.CrouchSlideModule.TraceTimer, _player.CrouchSlideModule.TraceBuffer));
        while (_ring.Count > 0 && _seconds - _ring.Peek().Seconds > 2) _ring.Dequeue();
        if (_seconds >= _nextSample)
        {
            _nextSample = _seconds + 0.5;
            Emit("TELEMETRY", "2 Hz passive sample", details: new { pre_move_velocity = V(_beforeMoveVelocity) });
        }
    }

    private void ObserveFloor()
    {
        bool floor = _player.IsOnFloor(), grounded = _player.IsGrounded;
        if (floor != _onFloor || grounded != _grounded)
        {
            object currentContact = Contact();
            if (floor != _onFloor)
                Emit(floor ? "FLOOR_ACQUIRE" : "FLOOR_LOST", "CharacterBody3D.IsOnFloor changed",
                    _onFloor ? "ON_FLOOR" : "AIRBORNE", floor ? "ON_FLOOR" : "AIRBORNE",
                    new { previous_contact = _lastContact, current_contact = currentContact, pre_move_velocity = V(_beforeMoveVelocity) });
            if (grounded != _grounded)
                Emit(grounded ? "GROUNDED_ACQUIRE" : "GROUNDED_LOST", "PlayerController.IsGrounded changed (IsOnFloor OR ray with velocity.Y <= 0)",
                    _grounded ? "GROUNDED" : "AIR", grounded ? "GROUNDED" : "AIR",
                    new { previous_contact = _lastContact, current_contact = currentContact });
            _onFloor = floor;
            _grounded = grounded;
        }
        // Keep previous contact while airborne so the departure collider is not lost.
        if (floor || grounded) _lastContact = Contact();
    }

    public object Snapshot(Vector3? branchVelocity = null)
    {
        if (!_recording || !IsInstanceValid(_player) || !_player.IsInsideTree()) return null;
        Vector3 velocity = branchVelocity ?? _player.Velocity;
        var slide = _player.CrouchSlideModule;
        string action = slide.CrouchSlideAction;
        var input = MovementInput();
        return new
        {
            player_instance_id = _player.GetInstanceId(),
            position = V(_player.GlobalPosition), velocity = V(velocity), player_velocity = V(_player.Velocity),
            velocity_source = branchVelocity.HasValue ? "branch_local_ref" : "Player.Velocity",
            horizontal_speed = new Vector2(velocity.X, velocity.Z).Length(),
            on_floor = _player.IsOnFloor(), grounded = _player.IsGrounded, contact = Contact(),
            slide = slide.GetMovementTraceState(), time_since_slide_enter = _lastEnter >= 0 ? (double?)(_seconds - _lastEnter) : null,
            input = new { action, just_pressed = Input.IsActionJustPressed(action), held = Input.IsActionPressed(action),
                just_released = Input.IsActionJustReleased(action), ctrl_physical = Input.IsPhysicalKeyPressed(Key.Ctrl),
                c_physical = Input.IsPhysicalKeyPressed(Key.C), movement = new[] { input.X, input.Y },
                jump_pressed = Input.IsActionJustPressed(_player.JumpModule.JumpAction),
                parkour = _player.ParkourIntentModule?.IsActive ?? false, shift_physical = Input.IsPhysicalKeyPressed(Key.Shift),
                mouse_mode = Input.MouseMode.ToString() },
            selected_ability = _player.AbilityStateModule?.GetHighestPriorityAbility().ToString(),
            ability_requests = _player.AbilityStateModule?.GetDebugState(),
            wallrun = _player.WallRunModule?.IsWallRunning ?? false,
            grapple_state = _player.SlingshotGrappleModule?.CurrentState.ToString(),
            locomotion_mode = LocomotionMode(), paused = _player.GetTree().Paused
        };
    }

    public void StateChange(string domain, string from, string to, string reason, object before = null, Vector3? velocity = null)
    {
        if (!_recording || from == to) return;
        string kind = domain + "_TRANSITION";
        if (domain == "POSTURE" && to == "Sliding")
        {
            _lastEnter = _seconds;
            kind = "SLIDE_ENTER";
        }
        if (domain == "POSTURE" && from == "Sliding")
        {
            _lastExit = _seconds;
            _lastExitReason = reason;
            kind = "SLIDE_EXIT";
        }
        Emit(kind, reason, from, to, new { domain, before }, velocity);
        if (kind == "SLIDE_ENTER" && _lastExit >= 0 && _seconds - _lastExit < 0.5)
        {
            Emit("SLIDE_RAPID_REENTRY", reason, from, to, new
            {
                time_since_exit = _seconds - _lastExit, exit_reason = _lastExitReason, new_enter_reason = reason,
                context = _ring.Select(s => new
                {
                    seconds = s.Seconds, physics_tick = s.Tick, frame = s.Frame, position = V(s.Position),
                    velocity = V(s.Velocity), pre_move_velocity = V(s.PreMoveVelocity), on_floor = s.Floor,
                    grounded = s.Grounded, is_sliding = s.Sliding, input_held = s.Held,
                    movement_input = new[] { s.Input.X, s.Input.Y }, slide_timer = s.Timer, airborne_buffer = s.Buffer
                }).ToArray()
            }, velocity);
        }
    }

    public void Emit(string kind, string reason, string from = null, string to = null, object details = null, Vector3? velocity = null)
    {
        if (!_recording || _writer.Error != null) return;
        try
        {
            _writer.Enqueue(JsonSerializer.Serialize(new
            {
                sequence = ++_sequence, session_id = _sessionId, timestamp_utc = DateTimeOffset.UtcNow,
                monotonic_us = Time.GetTicksUsec(), physics_seconds = _seconds,
                frame = Engine.GetProcessFrames(), physics_tick = Engine.GetPhysicsFrames(),
                phase = _phase, kind, from_state = from, to_state = to, reason, details, snapshot = Snapshot(velocity)
            }, JsonOptions));
        }
        catch (Exception error)
        {
            // A diagnostic failure must never abort the caller's movement branch.
            _writer.Error = "Serialization failed: " + error.Message;
            GD.PushError("Movement trace disabled: " + _writer.Error);
        }
    }

    private object Contact()
    {
        var contacts = new List<object>();
        object floorCandidate = null;
        float bestDot = -1;
        Vector3 normal = _player.IsOnFloor() ? _player.GetFloorNormal() : Vector3.Zero;
        for (int i = 0; i < _player.GetSlideCollisionCount(); i++)
        {
            var collision = _player.GetSlideCollision(i);
            contacts.Add(new { collider = Identity(collision.GetCollider()), normal = V(collision.GetNormal()),
                position = V(collision.GetPosition()), shape_index = collision.GetColliderShapeIndex() });
            float dot = collision.GetNormal().Dot(normal);
            if (_player.IsOnFloor() && dot > 0.99f && dot > bestDot)
            {
                bestDot = dot;
                floorCandidate = new { collider = Identity(collision.GetCollider()), normal = V(collision.GetNormal()),
                    position = V(collision.GetPosition()), collision_index = i, shape_index = collision.GetColliderShapeIndex() };
            }
        }
        var ray = _player.GroundCheck;
        bool rayHit = ray?.IsColliding() == true;
        return new { floor_normal = V(normal), floor_collision_candidate = floorCandidate, move_and_slide_contacts = contacts,
            ray_colliding = rayHit, ray_grounds_player = rayHit && _player.Velocity.Y <= 0,
            ray_collider = rayHit ? Identity(ray.GetCollider()) : null,
            ray_normal = rayHit ? V(ray.GetCollisionNormal()) : null,
            ray_position = rayHit ? V(ray.GetCollisionPoint()) : null };
    }

    private static object Identity(GodotObject value) => value == null ? null : new
    {
        id = value.GetInstanceId(), name = (value as Node)?.Name.ToString(),
        path = value is Node node && node.IsInsideTree() ? node.GetPath().ToString() : null
    };

    private Vector2 MovementInput()
    {
        var m = _player.MovementModule;
        var input = new Vector2(Input.GetActionStrength(m.MoveRightAction) - Input.GetActionStrength(m.MoveLeftAction),
            Input.GetActionStrength(m.MoveForwardAction) - Input.GetActionStrength(m.MoveBackAction));
        return input.LengthSquared() > 1 ? input.Normalized() : input;
    }

    private string LocomotionMode()
    {
        if (_player.SlingshotGrappleModule?.IsSlingshotActive == true) return "GRAPPLE_" + _player.SlingshotGrappleModule.CurrentState;
        if (_player.WallRunModule?.IsWallRunning == true) return "WALLRUN";
        if (_player.CrouchSlideModule.IsSliding) return "SLIDE";
        if (!_player.IsGrounded) return "AIR";
        if (_player.CrouchSlideModule.IsCrouching) return "CROUCH";
        return new Vector2(_player.Velocity.X, _player.Velocity.Z).LengthSquared() > 0.0025f ? "GROUND_MOVE" : "IDLE";
    }

    public override void _Process(double delta)
    {
        UpdateMarker();
        double now = Time.GetTicksMsec() / 1000.0;
        if (_recording && now >= _nextPoll)
        {
            _nextPoll = now + 0.5;
            if (System.IO.File.Exists(_stopPath)) StopRecording("explicit session stop request file");
        }
        if (_captureRequested && !_captureStarted && _seconds >= 2 && DisplayServer.GetName() != "headless")
        {
            _captureStarted = true;
            CaptureReadout();
        }
    }

    private async void CaptureReadout()
    {
        await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
        string path = ProjectSettings.GlobalizePath("res://.godot/movement-traces/handoff.png");
        Error result = GetViewport().GetTexture().GetImage().SavePng(path);
        Emit("TRACE_READOUT", "rendered startup readout; no input injected", details: new
            { marker = _marker.Text, visible = _marker.IsVisibleInTree(), path, result = result.ToString() });
        GD.Print($"MOVEMENT_TRACE_READOUT {_marker.Text} visible={_marker.IsVisibleInTree()} capture={result}");
    }

    private void UpdateMarker()
    {
        if (_marker == null) return;
        _marker.Text = _writer.Error != null ? "MOVEMENT TRACE: ERROR" : _recording ? "MOVEMENT TRACE: REC" : "MOVEMENT TRACE: SAVED";
    }

    public void StopRecording(string reason)
    {
        if (!_recording) return;
        Emit("SESSION_END", reason);
        _recording = false;
        _writer.Finish();
        UpdateMarker();
        GD.Print($"MOVEMENT_TRACE_SAVED {_writer.ArchivePath} error={_writer.Error ?? "none"}");
    }

    public void MarkRegressionCase(string name) => Emit("REGRESSION_CASE", name);

    public override void _ExitTree()
    {
        StopRecording("trace node exiting tree / game closed");
        if (_activeSession == this) _activeSession = null;
    }
    public static float[] V(Vector3 v) => new[] { v.X, v.Y, v.Z };
    private readonly record struct RingSample(double Seconds, ulong Tick, ulong Frame, Vector3 Position,
        Vector3 Velocity, Vector3 PreMoveVelocity, bool Floor, bool Grounded, bool Sliding, bool Held, Vector2 Input,
        float Timer, float Buffer);
}
