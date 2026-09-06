using Godot;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;

// A passive Gym observer: no synthetic events and no writes to player state.
// Splits use the course's existing timer, including recovery time.
public partial class MovementGymHumanRunLogger : Node
{
    public const double NormalSeconds = 95.78;
    public const double FastSeconds = 92.65;
    public string OutputDirectory { get; private set; }
    public string StatusText { get; private set; } = "HUMAN RUN | timer starts at green start gate";
    private MovementGymCourse _course;
    private PlayerController _player;
    private StreamWriter _samples;
    private StreamWriter _events;
    private readonly List<Split> _splits = new();
    private readonly Dictionary<string, int> _eventCounts = new();
    private readonly List<string> _wallrunVariants = new();
    private string _initialWallrunVariant;
    private string _selectedWallrunVariant;
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    private string _runId;
    private DateTimeOffset _startedUtc;
    private bool _smoke, _active, _completed, _ioFailed, _wasWall, _wasSlide, _wasGrounded;
    private int _grappleState, _sectionRecoveries, _sampleRate, _sampleCount;
    private double _sectionStarted, _nextSample, _nextFlush, _lastGrounded = double.NegativeInfinity;
    private Vector3 _lastVelocity;
    private record Split(int Index, string Name, double Seconds, double CumulativeSeconds, int Recoveries);

    public void Configure(MovementGymCourse course, int sampleRate, string directory, bool smoke)
    {
        _course = course;
        _sampleRate = Math.Clamp(sampleRate, 1, 30);
        OutputDirectory = ProjectSettings.GlobalizePath(directory);
        _smoke = smoke;
        ProcessPhysicsPriority = 100; // Read after the unchanged Player's physics.
    }

    public override void _Ready() => BindPlayer();

    private void BindPlayer()
    {
        _player = _course.GetNode<PlayerController>("Player");
        _wasWall = _player.WallRunModule.IsWallRunning;
        _wasSlide = _player.CrouchSlideModule.IsSliding;
        _wasGrounded = _player.IsGrounded;
        _grappleState = (int)_player.SlingshotGrappleModule.CurrentState;
        _lastVelocity = _player.Velocity;
        _lastGrounded = double.NegativeInfinity;
    }

    public void CheckpointEntered(int index)
    {
        if (index == 0)
        {
            _startedUtc = DateTimeOffset.UtcNow;
            _runId = $"{(_smoke ? "LOGGER_SMOKE" : "HUMAN")}_{_startedUtc:yyyyMMdd_HHmmss_fff}Z_{Guid.NewGuid().ToString("N")[..8]}";
            _active = true;
            _initialWallrunVariant = _selectedWallrunVariant = SelectedWallrunVariant;
            _wallrunVariants.Add(_initialWallrunVariant);
            _sectionStarted = _course.RunSeconds;
            _sectionRecoveries = _course.RecoveryCount;
            TryIo(() =>
            {
                Directory.CreateDirectory(OutputDirectory);
                _samples = CreateCsv("samples.csv");
                _samples.WriteLine("seconds,section,recoveries,x,y,z,vx,vy,vz,yaw,pitch,grounded,slide,wallrun,grapple,forward,back,left,right,jump,crouch,grapple_button");
                _events = CreateCsv("events.csv");
                _events.WriteLine("seconds,section,event,detail");
            });
            StatusText = "HUMAN RUN | recording  | A refs: NORMAL 95.78s / FAST 92.65s";
            RecordEvent("run_start", "human player input");
            if (_ioFailed) StatusText = "HUMAN RUN | LOG WRITE FAILED (see console)";
            return;
        }
        if (!_active) return;
        int section = index - 1;
        _splits.Add(new Split(section + 1, _course.SectionNames[section],
            _course.RunSeconds - _sectionStarted, _course.RunSeconds, _course.RecoveryCount - _sectionRecoveries));
        RecordEvent("section_finish", $"{section + 1}: {_course.SectionNames[section]}", section + 1);
        _sectionStarted = _course.RunSeconds;
        _sectionRecoveries = _course.RecoveryCount;
        TryIo(Flush);
    }

    public void PlayerRecovered()
    {
        BindPlayer();
        RecordEvent("recovery", $"count={_course.RecoveryCount}");
    }

    public override void _PhysicsProcess(double delta)
    {
        if (!_active || _completed || !IsInstanceValid(_player)) return;
        double now = _course.RunSeconds;
        bool wall = _player.WallRunModule.IsWallRunning;
        bool slide = _player.CrouchSlideModule.IsSliding;
        bool grounded = _player.IsGrounded;
        int grapple = (int)_player.SlingshotGrappleModule.CurrentState;
        if (_selectedWallrunVariant != SelectedWallrunVariant)
        {
            _selectedWallrunVariant = SelectedWallrunVariant;
            if (!_wallrunVariants.Contains(_selectedWallrunVariant)) _wallrunVariants.Add(_selectedWallrunVariant);
            RecordEvent("wallrun_variant_selected", _selectedWallrunVariant + " (applies on next entry)");
        }
        bool jumpPressed = Input.IsActionJustPressed(_player.JumpModule.JumpAction);
        if (wall != _wasWall)
        {
            string reason = wall ? (_player.WallRunModule.IsCanonicalRun ? "B_CANONICAL" : "A_LEGACY") : _player.WallRunModule.GetDebugText();
            RecordEvent(wall ? "wallrun_enter" : "wallrun_exit", reason);
            if (!wall && reason.Contains("lastExit=wall_jump")) RecordEvent("wall_jump", "observed wallrun exit reason");
        }
        if (slide != _wasSlide) RecordEvent(slide ? "slide_start" : "slide_finish", "observed state transition");
        if (grapple != _grappleState)
        {
            if (grapple == 1) RecordEvent("grapple_start", "Pulling");
            if (grapple == 2) RecordEvent("grapple_launch", "Launching");
            if (grapple == 0) RecordEvent("grapple_finish", "Idle (including cooldown end or cancellation)");
        }
        if (jumpPressed)
        {
            RecordEvent("jump_input", "pressed");
            // No hooks/private-field changes in Player. These two labels are
            // inferred from input + observed vertical impulse; raw input remains.
            if (!_wasWall && !wall && grapple != 1 && _player.Velocity.Y > _lastVelocity.Y + 0.1f)
            {
                bool groundJump = _wasGrounded || (_player.JumpModule.UseCoyoteTime && now - _lastGrounded <= _player.JumpModule.CoyoteTime);
                RecordEvent(groundJump ? "jump" : "air_jump", "inferred: jump input plus vertical impulse");
            }
        }
        if (grounded && !_wasGrounded) RecordEvent("landing", "observed grounded transition");
        if (grounded) _lastGrounded = now;
        _wasWall = wall; _wasSlide = slide; _wasGrounded = grounded; _grappleState = grapple; _lastVelocity = _player.Velocity;
        if (now + 1e-9 >= _nextSample)
        {
            _nextSample = now + 1.0 / _sampleRate;
            WriteSample();
        }
        if (now >= _nextFlush) { _nextFlush = now + 2.0; TryIo(Flush); }
    }

    private void WriteSample()
    {
        Vector3 p = _player.GlobalPosition, v = _player.Velocity;
        TryIo(() => _samples?.WriteLine(FormattableString.Invariant(
            $"{_course.RunSeconds:F4},{CurrentSection},{_course.RecoveryCount},{p.X:F4},{p.Y:F4},{p.Z:F4},{v.X:F4},{v.Y:F4},{v.Z:F4},{_player.Rotation.Y:F4},{_player.CameraPivot.Rotation.X:F4},{(_player.IsGrounded ? 1 : 0)},{(_player.CrouchSlideModule.IsSliding ? 1 : 0)},{(_player.WallRunModule.IsWallRunning ? 1 : 0)},{(int)_player.SlingshotGrappleModule.CurrentState},{Input.GetActionStrength("move_forward"):F3},{Input.GetActionStrength("move_back"):F3},{Input.GetActionStrength("move_left"):F3},{Input.GetActionStrength("move_right"):F3},{Input.GetActionStrength("jump"):F3},{Input.GetActionStrength("crouch_slide"):F3},{Input.GetActionStrength("slingshot_grapple"):F3}")));
        _sampleCount++;
    }

    private int CurrentSection => Math.Clamp(_course.CurrentCheckpoint + 1, 1, Math.Max(1, _course.SectionNames.Count));
    private string SelectedWallrunVariant => _player.WallRunModule.UseCanonicalTrajectory ? "B_CANONICAL" : "A_LEGACY";
    private void RecordEvent(string name, string detail, int? section = null)
    {
        if (!_active || _completed) return;
        _eventCounts[name] = _eventCounts.GetValueOrDefault(name) + 1;
        TryIo(() => _events?.WriteLine($"{_course.RunSeconds.ToString("F4", CultureInfo.InvariantCulture)},{section ?? CurrentSection},{name},{Csv(detail)}"));
    }

    public void CompleteRun()
    {
        if (!_active || _completed) return;
        RecordEvent("run_finish", "all section gates crossed");
        WriteSample();
        _completed = true;
        double normalDelta = _course.RunSeconds - NormalSeconds, fastDelta = _course.RunSeconds - FastSeconds;
        string comparison = $"NORMAL {normalDelta:+0.00;-0.00;0.00}s  |  FAST {fastDelta:+0.00;-0.00;0.00}s";
        TryIo(() =>
        {
            CloseStreams();
            using (var sections = CreateCsv("sections.csv"))
            {
                sections.WriteLine("section,name,seconds,cumulative_seconds,recoveries");
                foreach (var s in _splits) sections.WriteLine(FormattableString.Invariant($"{s.Index},{Csv(s.Name)},{s.Seconds:F4},{s.CumulativeSeconds:F4},{s.Recoveries}"));
            }
            var summary = new
            {
                schema_version = 1, run_type = _smoke ? "LOGGER_SMOKE" : "HUMAN", run_id = _runId,
                started_utc = _startedUtc, finished_utc = DateTimeOffset.UtcNow,
                scene = _course.SceneFilePath, status = "FINISHED", total_seconds = _course.RunSeconds,
                recovery_count = _course.RecoveryCount, clean_run = _course.RecoveryCount == 0,
                wallrun_variant_at_start = _initialWallrunVariant, wallrun_variants_selected = _wallrunVariants,
                mixed_wallrun_variants = _wallrunVariants.Count > 1,
                timing = "Existing Gym simulation timer: start gate to finish gate, recovery time included",
                sections = _splits, event_counts = _eventCounts, sample_count = _sampleCount, requested_sample_hz = _sampleRate,
                event_detection = "State transitions observed after physics; jump/air_jump inferred from input and vertical impulse; jump_input is also retained",
                comparison = new { normal_seconds = NormalSeconds, fast_seconds = FastSeconds,
                    baseline_wallrun_variant = "A_LEGACY",
                    same_wallrun_model = _wallrunVariants.Count == 1 && _wallrunVariants[0] == "A_LEGACY",
                    delta_vs_normal_seconds = normalDelta, delta_vs_fast_seconds = fastDelta,
                    delta_sign = "negative = human faster; positive = human slower" },
                files = new { samples = _runId + "_samples.csv", events = _runId + "_events.csv", sections = _runId + "_sections.csv" }
            };
            string path = Path.Combine(OutputDirectory, _runId + ".json");
            System.IO.File.WriteAllText(path + ".tmp", JsonSerializer.Serialize(summary, JsonOptions), new UTF8Encoding(false));
            System.IO.File.Move(path + ".tmp", path);
            GD.Print($"GYM_HUMAN_SAVED path={path} seconds={_course.RunSeconds:F4} recoveries={_course.RecoveryCount} {comparison}");
        });
        StatusText = _ioFailed ? "HUMAN RUN | LOG SAVE FAILED (see console)"
            : $"HUMAN RUN SAVED | {comparison}\n{_runId}.json";
    }

    private StreamWriter CreateCsv(string suffix) => new(new FileStream(Path.Combine(OutputDirectory, _runId + "_" + suffix), FileMode.CreateNew, System.IO.FileAccess.Write, FileShare.Read), new UTF8Encoding(false));
    private static string Csv(string text) => "\"" + text.Replace("\"", "\"\"") + "\"";
    private void Flush() { _samples?.Flush(); _events?.Flush(); }
    private void CloseStreams() { _samples?.Dispose(); _events?.Dispose(); _samples = null; _events = null; }
    private void TryIo(Action operation)
    {
        if (_ioFailed) return;
        try { operation(); }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            _ioFailed = true;
            StatusText = "HUMAN RUN | LOG WRITE FAILED (see console)";
            GD.PushError($"Gym human logger: {e.Message}");
        }
    }
    public override void _ExitTree()
    {
        // F1/closing an unfinished run leaves its timestamped sample/event CSVs;
        // only a finish creates the summary JSON used for competition.
        try { CloseStreams(); } catch (IOException) { }
    }
}
