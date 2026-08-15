using Godot;

public partial class StylizedContactDarkening : Node
{
    public enum DisplayMode
    {
        Passthrough = 0,
        LinearDepth = 1,
        OcclusionMask = 2,
        Composite = 3,
    }

    [ExportGroup("Integration")]
    [Export] public bool Enabled { get; set; } = true;
    [Export] public DisplayMode Mode { get; set; } = DisplayMode.Passthrough;
    [Export] public NodePath CameraPath { get; set; } = new("../Player/CameraPivot/CameraEffectsPivot/Camera3D");

    [ExportGroup("Contact Darkening")]
    [Export(PropertyHint.Range, "0,1,0.01")] public float Strength { get; set; } = 0.55f;
    [Export(PropertyHint.Range, "0.05,3,0.05,suffix:m")] public float Radius { get; set; } = 0.8f;
    [Export(PropertyHint.Range, "0,0.35,0.005")] public float Bias { get; set; } = 0.06f;
    [Export(PropertyHint.Range, "0.5,4,0.05")] public float Falloff { get; set; } = 2.0f;

    [ExportGroup("Distance Fade")]
    [Export(PropertyHint.Range, "0,200,1,suffix:m")] public float FadeStart { get; set; } = 25.0f;
    [Export(PropertyHint.Range, "1,500,1,suffix:m")] public float FadeEnd { get; set; } = 70.0f;

    [ExportGroup("Diagnostics")]
    [Export(PropertyHint.Range, "1,500,1,suffix:m")] public float DebugDepthRange { get; set; } = 80.0f;

    private MeshInstance3D _fullscreenQuad;
    private ShaderMaterial _material;
    private Camera3D _attachedCamera;

    public override void _Ready()
    {
        _fullscreenQuad = GetNodeOrNull<MeshInstance3D>("FullscreenQuad");
        ShaderMaterial sourceMaterial = _fullscreenQuad?.MaterialOverride as ShaderMaterial;
        _material = sourceMaterial?.Duplicate() as ShaderMaterial;

        if (_fullscreenQuad == null || _material == null)
        {
            GD.PushError($"{nameof(StylizedContactDarkening)} requires FullscreenQuad with a ShaderMaterial override.");
            SetProcess(false);
            return;
        }

        _fullscreenQuad.MaterialOverride = _material;
        CallDeferred(MethodName.AttachToCurrentCamera);
        ApplyShaderParameters();
    }

    public override void _Process(double delta)
    {
        Camera3D currentCamera = ResolveCamera();
        if (currentCamera != null && currentCamera != _attachedCamera)
        {
            AttachToCamera(currentCamera);
        }

        ApplyShaderParameters();
    }

    public override void _ExitTree()
    {
        if (GodotObject.IsInstanceValid(_fullscreenQuad) && _fullscreenQuad.GetParent() != this)
        {
            _fullscreenQuad.QueueFree();
        }
    }

    private void AttachToCurrentCamera()
    {
        Camera3D camera = ResolveCamera();
        if (camera == null)
        {
            GD.PushWarning($"{nameof(StylizedContactDarkening)} could not find the main Camera3D yet; it will retry.");
            return;
        }

        AttachToCamera(camera);
    }

    private Camera3D ResolveCamera()
    {
        if (!CameraPath.IsEmpty)
        {
            Camera3D configuredCamera = GetNodeOrNull<Camera3D>(CameraPath);
            if (configuredCamera != null)
            {
                return configuredCamera;
            }
        }

        return GetViewport()?.GetCamera3D();
    }

    private void AttachToCamera(Camera3D camera)
    {
        _fullscreenQuad.Reparent(camera, false);
        _fullscreenQuad.Transform = Transform3D.Identity;
        _attachedCamera = camera;
    }

    private void ApplyShaderParameters()
    {
        if (_fullscreenQuad == null || _material == null)
        {
            return;
        }

        _fullscreenQuad.Visible = Enabled;
        _material.SetShaderParameter("effect_enabled", Enabled);
        _material.SetShaderParameter("display_mode", (int)Mode);
        _material.SetShaderParameter("strength", Mathf.Clamp(Strength, 0.0f, 1.0f));
        _material.SetShaderParameter("radius", Mathf.Max(Radius, 0.001f));
        _material.SetShaderParameter("bias", Mathf.Max(Bias, 0.0f));
        _material.SetShaderParameter("falloff", Mathf.Max(Falloff, 0.01f));
        _material.SetShaderParameter("fade_start", Mathf.Max(FadeStart, 0.0f));
        _material.SetShaderParameter("fade_end", Mathf.Max(FadeEnd, FadeStart + 0.001f));
        _material.SetShaderParameter("debug_depth_range", Mathf.Max(DebugDepthRange, 0.001f));
    }
}
