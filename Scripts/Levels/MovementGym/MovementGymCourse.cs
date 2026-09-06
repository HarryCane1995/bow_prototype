using Godot;

// This controller exists only in Level_Movement_Gym. Recovery replaces the
// prefab instance so every ability gets its ordinary, unmodified initial state.
public partial class MovementGymCourse : Node3D
{
    [ExportGroup("Gym Recovery")]
    [Export] public PackedScene PlayerScene { get; set; }
    [Export(PropertyHint.Range, "-100,-5,1,suffix:m")] public float RecoveryY { get; set; } = -18.0f;
    [Export] public Key CheckpointResetKey { get; set; } = Key.R;
    [ExportGroup("Gym Course")]
    [Export] public Godot.Collections.Array<string> SectionNames { get; set; } = new();
    [ExportGroup("Gym Human Runs")]
    [Export] public bool HumanRunLoggingEnabled { get; set; } = true;
    [Export] public bool HumanRunFullscreen { get; set; } = true;
    [Export(PropertyHint.Range, "1,30,1,suffix:Hz")] public int HumanSampleRateHz { get; set; } = 10;
    [Export] public string HumanRunDirectory { get; set; } = "user://MovementGym/HumanRuns";
    [ExportGroup("Gym Wallrun A/B")]
    [Export] public Key WallrunABToggleKey { get; set; } = Key.F2;

    public int CurrentCheckpoint { get; private set; } = -1;
    public int RecoveryCount { get; private set; }
    public bool Finished { get; private set; }
    public double RunSeconds { get; private set; }
    private PlayerController _player;
    private Label _readout;
    private bool _resetPending;
    private bool _resetHeld;
    private MovementGymHumanRunLogger _humanLogger;
    private static bool _canonicalWallrunSelected = true;

    public override void _Ready()
    {
        _player = GetNode<PlayerController>("Player");
        _readout = GetNode<Label>("HUD/Readout");
        // A --script launch belongs to the external autonomous tooling. Ordinary
        // F6/scene launches use real player input and opt into human recording.
        bool scripted = System.Array.Exists(OS.GetCmdlineArgs(), a => a == "--script" || a.StartsWith("--script="));
        bool explicitHuman = System.Array.Exists(OS.GetCmdlineUserArgs(), a => a == "--human-run");
        if (HumanRunLoggingEnabled && (!scripted || explicitHuman))
        {
            _player.WallRunModule.UseCanonicalTrajectory = _canonicalWallrunSelected;
            bool smoke = System.Array.Exists(OS.GetCmdlineUserArgs(), a => a == "--gym-logger-smoke");
            if (HumanRunFullscreen && !smoke) GetWindow().Mode = Window.ModeEnum.Fullscreen;
            _humanLogger = new MovementGymHumanRunLogger { Name = "HumanRunLogger" };
            _humanLogger.Configure(this, HumanSampleRateHz, smoke ? "user://MovementGym/LoggerSmoke" : HumanRunDirectory, smoke);
            AddChild(_humanLogger);
            GD.Print($"GYM_HUMAN_READY fullscreen={GetWindow().Mode} input=real logs={_humanLogger.OutputDirectory}");
        }
        foreach (Node child in GetNode("Checkpoints").GetChildren())
        {
            if (child is not Area3D gate) continue;
            int index = gate.GetMeta("index").AsInt32();
            gate.BodyEntered += body => EnterCheckpoint(index, body);
        }
    }

    public override void _Input(InputEvent @event)
    {
        if (_humanLogger == null || @event is not InputEventKey { Pressed: true, Echo: false } key
            || (key.PhysicalKeycode != WallrunABToggleKey && key.Keycode != WallrunABToggleKey)) return;
        _canonicalWallrunSelected = !_canonicalWallrunSelected;
        _player.WallRunModule.UseCanonicalTrajectory = _canonicalWallrunSelected;
        GD.Print($"GYM_WALLRUN_AB selected={(_canonicalWallrunSelected ? "B_CANONICAL" : "A_LEGACY")} (next entry)");
        GetViewport().SetInputAsHandled();
    }

    public override void _PhysicsProcess(double delta)
    {
        if (CurrentCheckpoint >= 0 && !Finished) RunSeconds += delta;
        bool reset = Input.IsPhysicalKeyPressed(CheckpointResetKey);
        if (!_resetPending && (_player.GlobalPosition.Y < RecoveryY || (reset && !_resetHeld)))
        {
            _resetPending = true;
            CallDeferred(nameof(RecoverPlayer));
        }
        _resetHeld = reset;
        int section = Mathf.Clamp(CurrentCheckpoint, 0, SectionNames.Count - 1);
        string name = SectionNames.Count > 0 ? SectionNames[section] : "MOVEMENT GYM";
        _readout.Text = Finished
            ? $"FINISH  {RunSeconds:0.00}s  |  recoveries {RecoveryCount}  |  F1: new run"
            : $"{section + 1:00}/{SectionNames.Count:00}  {name}   {RunSeconds:0.0}s   |   R: checkpoint  ({RecoveryCount})";
        if (_humanLogger != null)
        {
            string selected = _canonicalWallrunSelected ? "B CANONICAL" : "A LEGACY";
            bool pending = _player.WallRunModule.IsWallRunning && _player.WallRunModule.IsCanonicalRun != _canonicalWallrunSelected;
            _readout.Text += $"\n{WallrunABToggleKey}: WALLRUN {selected}" + (pending ? " (next wall)" : "") + "  | R: retry section";
            _readout.Text += "\n" + _humanLogger.StatusText;
        }
    }

    private void EnterCheckpoint(int index, Node3D body)
    {
        if (body != _player || Finished || index != CurrentCheckpoint + 1) return;
        CurrentCheckpoint = index;
        _humanLogger?.CheckpointEntered(index);
        if (index == 0) GD.Print("GYM_START");
        if (index == SectionNames.Count)
        {
            Finished = true;
            _humanLogger?.CompleteRun();
            GD.Print($"GYM_FINISH seconds={RunSeconds:0.000} recoveries={RecoveryCount}");
        }
        else GD.Print($"GYM_CHECKPOINT index={index} seconds={RunSeconds:0.000}");
    }

    private void RecoverPlayer()
    {
        Marker3D spawn = GetNode<Marker3D>($"Spawns/Spawn{Mathf.Max(0, CurrentCheckpoint)}");
        RemoveChild(_player);
        _player.Free();
        _player = PlayerScene.Instantiate<PlayerController>();
        _player.Name = "Player";
        _player.Position = spawn.Position;
        _player.Rotation = spawn.Rotation;
        AddChild(_player);
        if (_humanLogger != null) _player.WallRunModule.UseCanonicalTrajectory = _canonicalWallrunSelected;
        _player.ResetPhysicsInterpolation();
        RecoveryCount++;
        _humanLogger?.PlayerRecovered();
        _resetPending = false;
        GD.Print($"GYM_RECOVERY checkpoint={CurrentCheckpoint} count={RecoveryCount}");
    }
}
