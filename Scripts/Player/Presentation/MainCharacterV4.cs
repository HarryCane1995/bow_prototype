using Godot;
using System.Collections.Generic;
using System.Text.Json;

// Local presentation host only. State comes from the existing Player; visual
// consumers never create physics bodies, weapons, projectiles or combat systems.
public partial class MainCharacterV4 : Node
{
    [Export] public bool StartSplit { get; set; } = true;
    [Export] public Key ToggleSplitKey { get; set; } = Key.F12;
    [Export] public Key ExternalViewKey { get; set; } = Key.F10;
    [Export(PropertyHint.File,"*.json")] public string FpCalibration { get; set; } = "res://Assets/Characters/BaseHumanoid/Exports/BH01_1POV.presentation.json";
    [Export(PropertyHint.Range,"0.1,2,0.01")] public float FpBowScale { get; set; } = .62f;
    [Export] public Vector3 ExternalCameraOffset { get; set; } = new(2.2f,1.6f,3.2f);
    public bool Active { get; private set; }
    public bool ExternalView { get; private set; }
    public bool FpVisible => Active && !ExternalView;
    public string StateName => _observer.State.ToString();
    public string LocomotionName => _observer.Locomotion.ToString();
    public SplitBodyVisual FirstPerson { get; private set; }
    public SplitBodyVisual ThirdPerson { get; private set; }
    public Camera3D FpCamera { get; private set; }
    private PlayerController _player;
    private PlayerRmbCombat _combat;
    private MainCharacterV2 _v2;
    private MainCharacterV3 _v3;
    private CanvasLayer _canvas, _legacyCanvas;
    private SubViewport _viewport;
    private Camera3D _external;
    private SplitGameplayCamera _cameraLayer;
    private Label _readout;
    private SplitStateObserver _observer = new();
    private readonly Dictionary<Node,ProcessModeEnum> _processes=new();
    private readonly Dictionary<CanvasLayer,bool> _canvases=new();
    private Transform3D _savedCameraTransform;
    private bool _savedTopLevel, _ready, _savedArrowOwner;
    private float _savedFov;
    private uint _savedMask;
    private PhysicsInterpolationModeEnum _savedInterpolation;
    private int _savedLookPriority,_savedWallPriority;
    private const uint WorldMask=1u<<16, FpMask=1u<<18, LegacyMask=1u<<19;
    public override void _Ready()
    {
        _player=GetParent<PlayerController>();_combat=_player.GetNode<PlayerRmbCombat>("PlayerRmbCombat");
        _v2=_player.GetNode<MainCharacterV2>("MainCharacterV2");_v3=_player.GetNode<MainCharacterV3>("MainCharacterV3");
        ProcessPriority=20;ProcessPhysicsPriority=50;
        CallDeferred(nameof(Initialize));
    }
    private void Initialize()
    {
        if (!_v2.PresentationReady || _v3.FpSkeleton==null) { CallDeferred(nameof(Initialize));return; }
        _canvas=GetNode<CanvasLayer>("FirstPerson");_viewport=_canvas.GetNode<SubViewport>("FPContainer/FPViewport");
        var space=_viewport.GetNode<Node3D>("FPSpace");FpCamera=space.GetNode<Camera3D>("FPViewCamera");
        FPDriftRoot=space.GetNode<Node3D>("FPPresentationBase/FPDriftRoot");
        FirstPerson=FPDriftRoot.GetNode<SplitBodyVisual>("FPArms");
        ThirdPerson=GetNode<SplitBodyVisual>("ThirdPerson");ThirdPerson.TopLevel=true;
        _external=GetNode<Camera3D>("ExternalCamera");_external.TopLevel=true;
        _external.CullMask=(_player.Camera.CullMask|WorldMask)&~(FpMask|LegacyMask);
        _cameraLayer=GetNode<SplitGameplayCamera>("GameplayCameraLayer");_cameraLayer.Player=_player;
        _legacyCanvas=_player.GetNode<CanvasLayer>("CanvasLayer_ViewModel");
        _readout=GetNode<Label>("Readout/Label");
        using var json=JsonDocument.Parse(FileAccess.GetFileAsString(FpCalibration));
        var m=json.RootElement.GetProperty("fp_model_rows");
        Vector3 Col(int c)=>new(m[0][c].GetSingle(),m[1][c].GetSingle(),m[2][c].GetSingle());
        FirstPerson.Transform=new Transform3D(new Basis(Col(0),Col(1),Col(2)),Col(3));
        FpCamera.Fov=json.RootElement.GetProperty("fov").GetSingle();
        _ready=true;SetSplitEnabled(StartSplit);
    }
    public void SetSplitEnabled(bool enabled)
    {
        if (!_ready || Active==enabled) return;
        if (enabled)
        {
            // Restore the existing bow to its gameplay visual source before
            // suspending fallback presentation; visual modules keep updating it.
            _v2.SetV2Enabled(false);
            _savedArrowOwner=_player.BowVisualModule.ArrowPresentationOwnedByHands;
            _player.BowVisualModule.ArrowPresentationOwnedByHands=false;
            _processes.Clear();_canvases.Clear();
            foreach (Node n in new Node[]{_v2,_v3,_player.ViewModelSwayModule,_player.CameraFovModule})
            { _processes[n]=n.ProcessMode;n.ProcessMode=ProcessModeEnum.Disabled; }
            string root="CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot";
            foreach (string path in new[]{root+"/ViewModelSwayRoot/FirstPersonHands",root+"/FirstPersonSlideLegs"})
            { var n=_player.GetNode(path);_processes[n]=n.ProcessMode;n.ProcessMode=ProcessModeEnum.Disabled; }
            foreach (Node holder in new Node[]{_v2,_v3,_player.ViewModelSwayModule})
                foreach (Node n in holder.FindChildren("*","CanvasLayer",true,false))
                { _canvases[(CanvasLayer)n]=((CanvasLayer)n).Visible;((CanvasLayer)n).Visible=false; }
            _canvases[_legacyCanvas]=_legacyCanvas.Visible;_legacyCanvas.Visible=false;
            var camera=_player.Camera;_savedCameraTransform=camera.Transform;_savedTopLevel=camera.TopLevel;
            _savedFov=camera.Fov;_savedMask=camera.CullMask;_savedInterpolation=camera.PhysicsInterpolationMode;
            camera.TopLevel=true;camera.PhysicsInterpolationMode=Node.PhysicsInterpolationModeEnum.Off;
            camera.CullMask=_savedMask&~(WorldMask|(1u<<17)|FpMask|LegacyMask);
            _savedLookPriority=_player.LookModule.ProcessPriority;_savedWallPriority=_player.WallRunModule.ProcessPriority;
            _player.LookModule.ProcessPriority=-12;_player.WallRunModule.ProcessPriority=-11;
            FirstPerson.BindBow(_v2.PresentationWeapon,_v2.BowMeshInHand,FpBowScale);
            ThirdPerson.BindBow(_v2.PresentationWeapon,_v2.BowMeshInHand,1);
            _observer=new();Active=true;_cameraLayer.Active=true;_cameraLayer._Process(0);
            _observer.Observe(_player,_combat,0);SetExternalView(false);ResetFpDrift();
        }
        else
        {
            Active=false;_cameraLayer.Active=false;SetExternalView(false);
            var camera=_player.Camera;camera.TopLevel=_savedTopLevel;camera.Transform=_savedCameraTransform;
            camera.Fov=_savedFov;camera.CullMask=_savedMask;camera.PhysicsInterpolationMode=_savedInterpolation;
            _player.LookModule.ProcessPriority=_savedLookPriority;_player.WallRunModule.ProcessPriority=_savedWallPriority;
            foreach (var pair in _processes) pair.Key.ProcessMode=pair.Value;
            foreach (var pair in _canvases) pair.Key.Visible=pair.Value;
            _player.BowVisualModule.ArrowPresentationOwnedByHands=_savedArrowOwner;
            _v3.SetHybridSelected(true);
        }
        ThirdPerson.Visible=Active;_canvas.Visible=FpVisible;
        _readout.Visible=Active;_viewport.RenderTargetUpdateMode=FpVisible ? SubViewport.UpdateMode.Always : SubViewport.UpdateMode.Disabled;
        GD.Print("PRESENTATION: "+(Active ? "V4 SPLIT" : "V3 REFERENCE"));
    }
    public void SetExternalView(bool external)
    {
        ExternalView=Active&&external;
        if (ExternalView) _external.MakeCurrent();else _player.Camera.MakeCurrent();
        _canvas.Visible=FpVisible;
        _viewport.RenderTargetUpdateMode=FpVisible ? SubViewport.UpdateMode.Always : SubViewport.UpdateMode.Disabled;
    }
    public override void _Input(InputEvent input)
    {
        if (!_ready || input is not InputEventKey {Pressed:true,Echo:false} key) return;
        bool Is(Key k)=>key.Keycode==k||key.PhysicalKeycode==k;
        if (Is(ToggleSplitKey)) SetSplitEnabled(!Active);
        else if (Active&&Is(ExternalViewKey)) SetExternalView(!ExternalView);
        else if (Active&&Is(FPDriftToggleKey)) { FPDriftEnabled=!FPDriftEnabled;ResetFpDrift(); }
        else return;
        GetViewport().SetInputAsHandled();
    }
    public override void _PhysicsProcess(double delta)
    { if (Active) _observer.Observe(_player,_combat,(float)delta); }
    public override void _Process(double delta)
    {
        if (!Active) return;
        _observer.Observe(_player,_combat,0);
        Vector3 dir=_player.CrouchSlideModule.SlideDirection;
        float yaw=_player.CrouchSlideModule.IsSliding&&!dir.IsZeroApprox() ? Mathf.Atan2(-dir.X,-dir.Z) : _player.GlobalRotation.Y;
        ThirdPerson.GlobalTransform=new Transform3D(new Basis(Vector3.Up,yaw),_player.GetGlobalTransformInterpolated().Origin);
        ThirdPerson.Present(_observer.State,delta,_player.Camera.GlobalBasis,_player.CrouchSlideModule.IsSliding);
        FPDriftRoot.Transform=Transform3D.Identity;
        FirstPerson.Present(_observer.State,delta,FpCamera.GlobalBasis,false);
        UpdateFpDrift(delta);
        Vector3 target=_player.GlobalPosition+Vector3.Up*.85f;
        Basis orbit=new Basis(Vector3.Up,_player.GlobalRotation.Y)*new Basis(Vector3.Right,Mathf.Clamp(_player.CameraPivot.Rotation.X,-1,1));
        _external.GlobalPosition=target+orbit*ExternalCameraOffset;_external.LookAt(target,Vector3.Up);
        _readout.Text=$"V4 SPLIT | {(ExternalView ? "3POV" : "1POV ARMS + BOW")} | {_observer.State}\n"
            +$"FP: {FirstPerson.Clip}\nWORLD: {ThirdPerson.Clip}\nF10: external | F12: V3 reference (then F11: V2 / F9: legacy) | F4: drift {(FPDriftEnabled ? "ON" : "OFF")}";
    }
}
