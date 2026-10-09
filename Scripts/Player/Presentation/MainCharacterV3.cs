using Godot;
using System.Collections.Generic;

// Hybrid companion to the existing world character. No motor, weapon or input owner.
public partial class MainCharacterV3 : Node
{
    [ExportGroup("V3 Hybrid")]
    [Export] public bool StartHybrid { get; set; } = true;
    [Export] public Key ToggleKey { get; set; } = Key.F11;
    [Export] public PackedScene FpModelScene { get; set; }
    [Export] public V3FpAnimationSlots AnimationSlots { get; set; } = new();
    [Export] public AnimationLibrary FpAnimationLibrary { get; set; }
    [ExportGroup("Render Layers")]
    [Export(PropertyHint.Range, "1,20,1")] public int WorldUpperLayer { get; set; } = 17;
    [Export(PropertyHint.Range, "1,20,1")] public int WorldLowerLayer { get; set; } = 18;
    [Export(PropertyHint.Range, "1,20,1")] public int FirstPersonLayer { get; set; } = 19;

    public bool HybridSelected { get; private set; }
    public bool Active => _ready && HybridSelected && _world.Enabled;
    public bool FpVisible => Active && !_world.ExternalView;
    public bool SlideLegsVisible => FpVisible && _player.CrouchSlideModule.IsSliding;
    public string FpSlot { get; private set; } = "FP_IDLE";
    public string FpClip { get; private set; } = "BH01_IDLE";
    public Skeleton3D FpSkeleton { get; private set; }
    public Camera3D FpCamera { get; private set; }
    public Node3D FpBow { get; private set; }
    public float FpBowAimErrorDegrees { get; private set; }
    public uint UpperMask => Mask(WorldUpperLayer);
    public uint LowerMask => Mask(WorldLowerLayer);
    public uint FpMask => Mask(FirstPersonLayer);

    private PlayerController _player;
    private MainCharacterV2 _world;
    private PlayerRmbCombat _combat;
    private Camera3D _external;
    private CanvasLayer _canvas;
    private SubViewport _viewport;
    private readonly Dictionary<VisualInstance3D,uint> _worldLayers = new();
    private uint _mainMask, _externalMask, _legacyFpMask;
    private bool _ready, _layersOwned;
    private uint _lastShot;
    private float _shotAge = 10;
    private readonly List<(Node3D Source, Node3D Copy)> _bowParts = new();
    private static uint Mask(int layer) => 1u << (Mathf.Clamp(layer,1,20)-1);

    public override void _Ready()
    {
        _player = GetParent<PlayerController>();
        _world = _player.GetNode<MainCharacterV2>("MainCharacterV2");
        _combat = _player.GetNodeOrNull<PlayerRmbCombat>("PlayerRmbCombat");
        HybridSelected = StartHybrid;
        _world.HybridPresentationActive = HybridSelected;
        // Read the finished camera and the single gameplay bow visual state.
        ProcessPriority = 20;
        CallDeferred(nameof(Initialize));
    }

    private void Initialize()
    {
        if (!_world.PresentationReady) { CallDeferred(nameof(Initialize)); return; }
        _external = _world.GetNode<Camera3D>("ExternalCamera");
        _mainMask = _player.Camera.CullMask;
        _externalMask = _external.CullMask;
        _legacyFpMask = Mask(_player.GetNode<PlayerViewModelRenderModule>("PlayerViewModelRenderModule").ViewModelVisualLayer);
        foreach (Node node in _world.GetNode("Body").FindChildren("*","VisualInstance3D",true,false))
            _worldLayers[(VisualInstance3D)node] = ((VisualInstance3D)node).Layers;
        BuildFirstPerson();
        _ready = true;
        // Also update synchronously for debug keys arriving after _Process.
        _world.PresentationVisibilityChanged += ApplyVisibility;
        ApplyVisibility();
        UpdateFirstPerson(0);
        GD.Print("PRESENTATION: " + (HybridSelected ? "V3 HYBRID" : "V2 TRUE BODY"));
    }

    public void SetHybridSelected(bool hybrid)
    {
        HybridSelected = hybrid;
        _world.HybridPresentationActive = hybrid;
        if (!_world.Enabled) _world.SetV2Enabled(true);
        if (_ready) ApplyVisibility();
        GD.Print("PRESENTATION: " + (hybrid ? "V3 HYBRID" : "V2 TRUE BODY"));
    }

    public override void _Input(InputEvent input)
    {
        if (input is not InputEventKey { Pressed: true, Echo: false } key) return;
        if (FpVisible && (key.Keycode == FPDriftToggleKey || key.PhysicalKeycode == FPDriftToggleKey))
        {
            FPDriftEnabled = !FPDriftEnabled;
            ResetFpDrift();
            GD.Print($"FP_DRIFT {(FPDriftEnabled ? "ON" : "OFF")}");
            GetViewport().SetInputAsHandled();
            return;
        }
        if (key.Keycode != ToggleKey && key.PhysicalKeycode != ToggleKey) return;
        SetHybridSelected(!HybridSelected);
        GetViewport().SetInputAsHandled();
    }

    public override void _Process(double delta)
    {
        if (!_ready) return;
        ApplyVisibility();
        if (Active) UpdateFirstPerson(delta);
        // Apply above the finished neutral rig: wrist stabilization cannot undo
        // the common torso/arms/bow drift or chase last frame's drift transform.
        UpdateFpDrift(delta);
        _world.AppendPresentationReadout($"PRESENTATION: {(HybridSelected ? "V3 HYBRID" : "V2 TRUE BODY")}  |  {ToggleKey}: V2 / V3\n"
            + $"FP WORLD BODY: {(!Active ? "V2 / FALLBACK" : SlideLegsVisible ? "SLIDE LEGS" : "HIDDEN")}  |  FP RIG: {(FpVisible ? "ON" : "OFF")}"
            + (Active ? $"  |  {FpSlot} → {FpClip}\nDRIFT: {(FPDriftEnabled && FPDriftWeight > 0 ? "ON" : "OFF")}  |  {FPDriftToggleKey}: A/B  |  weight {FPDriftWeight:0.00}" : ""));
    }

    private void ApplyVisibility()
    {
        if (Active)
        {
            foreach (var pair in _worldLayers)
                pair.Key.Layers = pair.Key.Name == "LEGS" ? LowerMask : UpperMask;
            // Head stays renderable for the external camera. Main camera masks
            // exclude it rather than toggling it at every slide transition.
            _world.Skeleton.GetNode<MeshInstance3D>("HEAD").Visible = true;
            _player.Camera.CullMask = (_mainMask & ~(UpperMask|LowerMask|FpMask)) | (SlideLegsVisible ? LowerMask : 0);
            _external.CullMask = (_externalMask & ~(FpMask|_legacyFpMask)) | UpperMask | LowerMask;
            _layersOwned = true;
        }
        else if (_layersOwned)
        {
            foreach (var pair in _worldLayers)
                if (_world.IsAncestorOf(pair.Key)) pair.Key.Layers = pair.Value;
            _world.Skeleton.GetNode<MeshInstance3D>("HEAD").Visible = _world.ExternalView;
            _player.Camera.CullMask = _mainMask;
            _external.CullMask = _externalMask;
            _layersOwned = false;
        }
        _canvas.Visible = FpVisible;
        _viewport.RenderTargetUpdateMode = FpVisible ? SubViewport.UpdateMode.Always : SubViewport.UpdateMode.Disabled;
    }

    private string SelectFpSlot(float delta)
    {
        var slots = AnimationSlots;
        var bow = _player.BowVisualModule;
        if (_lastShot != bow.ShotVisualSequence) { _lastShot = bow.ShotVisualSequence; _shotAge = 0; }
        else _shotAge += delta;
        if (_combat != null)
        {
            var requested = _combat.RequestedAnimation;
            var map = _combat.AnimationSlots;
            if (requested == map.Anticipation) return slots.Anticipation;
            if (requested == map.Melee) return slots.Melee;
            if (requested == map.ParrySuccess) return slots.Parry;
            if (requested == map.BowReady) return slots.BowReady;
            if (requested == map.BowDrawStart) return slots.BowDrawStart;
            if (requested == map.BowFullDraw) return slots.BowFullDraw;
            if (requested == map.BowRelease) return slots.BowRelease;
            if (requested == map.BowFollowThrough) return slots.BowFollowThrough;
            if (requested == map.BowRecovery || requested == map.MeleeRecovery) return slots.BowRecovery;
        }
        if (_shotAge < 0.06f) return slots.BowRelease;
        if (_shotAge < 0.16f) return slots.BowFollowThrough;
        if (_shotAge < 0.30f) return slots.BowRecovery;
        if (bow.IsDrawing) return bow.DrawAmount >= 0.99f ? slots.BowFullDraw : slots.BowDrawStart;
        if (bow.IsPrecisionAiming) return slots.BowReady;
        return _world.LocomotionState switch
        {
            "Slide" => slots.Slide, "Run" => slots.Run,
            "WallrunLeft" => slots.WallrunLeft, "WallrunRight" => slots.WallrunRight,
            _ => slots.Idle
        };
    }

    public override void _ExitTree()
    {
        if (IsInstanceValid(_world))
        {
            _world.PresentationVisibilityChanged -= ApplyVisibility;
            _world.HybridPresentationActive = false;
        }
    }
}
