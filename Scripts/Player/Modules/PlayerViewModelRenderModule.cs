using Godot;

public partial class PlayerViewModelRenderModule : Node
{
    /// <summary>
    /// Путь к основной FPS-камере игрока. Эта камера рендерит мир и используется стрельбой; неверный путь не позволит исключить viewmodel layer из её cull mask.
    /// </summary>
    [ExportGroup("Камеры")]
    [Export] public NodePath MainCameraPath { get; set; } = new("../CameraPivot/Camera3D");

    /// <summary>
    /// Путь к камере отдельного SubViewport для лука. Эта камера рендерит только viewmodel layer; неверный путь отключит отдельный рендер лука.
    /// </summary>
    [Export] public NodePath ViewModelCameraPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelCamera3D");

    /// <summary>
    /// Путь к корню viewmodel-объектов внутри SubViewport. Все MeshInstance3D внутри этого узла могут быть принудительно переведены на viewmodel visual layer.
    /// </summary>
    [ExportGroup("Viewmodel")]
    [Export] public NodePath ViewModelRootPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot");

    /// <summary>
    /// Путь к light rig внутри viewmodel SubViewport. Модуль настраивает только свет внутри этого узла; неверный путь оставит освещение viewmodel как настроено в сцене.
    /// </summary>
    [Export] public NodePath ViewModelLightRigPath { get; set; } = new("../../CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelLightRig");

    /// <summary>
    /// Номер visual layer для FPS viewmodel. Увеличение выбирает другой слой; значение должно совпадать с cull mask viewmodel-камеры и не использоваться миром.
    /// </summary>
    [Export(PropertyHint.Range, "1,20,1")] public int ViewModelVisualLayer { get; set; } = 20;

    /// <summary>
    /// Исключать viewmodel layer из основной камеры. Если выключить, основная камера сможет снова видеть объекты на этом слое.
    /// </summary>
    [Export] public bool ExcludeViewModelLayerFromMainCamera { get; set; } = true;

    /// <summary>
    /// Принудительно назначать viewmodel layer всем MeshInstance3D внутри ViewModelRootPath. Если выключить, слои нужно настроить вручную в сцене или ассете.
    /// </summary>
    [Export] public bool ForceViewModelLayerOnMeshes { get; set; } = true;

    /// <summary>
    /// Использовать отдельный FOV для viewmodel-камеры. Если выключить, viewmodel-камера будет копировать FOV основной камеры.
    /// </summary>
    [ExportGroup("FOV")]
    [Export] public bool UseSeparateViewModelFov { get; set; } = true;

    /// <summary>
    /// FOV viewmodel-камеры в градусах. Увеличение делает лук визуально шире/дальше; уменьшение делает его крупнее и ближе.
    /// </summary>
    [Export(PropertyHint.Range, "30,100,0.5,suffix:deg")] public float ViewModelFov { get; set; } = 65.0f;

    /// <summary>
    /// Включает отдельный light rig для viewmodel. Если выключить, свет внутри ViewModelLightRig будет скрыт и лук может стать темнее.
    /// </summary>
    [ExportGroup("Освещение viewmodel")]
    [Export] public bool LightRigEnabled { get; set; } = true;

    /// <summary>
    /// Энергия основного направленного света viewmodel. Увеличение делает лук ярче и читабельнее; уменьшение делает основной свет мягче и темнее.
    /// </summary>
    [Export(PropertyHint.Range, "0,8,0.05")] public float MainLightEnergy { get; set; } = 1.8f;

    /// <summary>
    /// Энергия дополнительного fill-света viewmodel. Увеличение подсвечивает тени на луке; уменьшение оставляет больше контраста от основного света.
    /// </summary>
    [Export(PropertyHint.Range, "0,4,0.05")] public float FillLightEnergy { get; set; } = 0.45f;

    private Camera3D _mainCamera;
    private Camera3D _viewModelCamera;
    private Node _viewModelRoot;
    private Node3D _viewModelLightRig;

    public void Initialize(PlayerController player)
    {
        _mainCamera = GetNodeOrNull<Camera3D>(MainCameraPath) ?? player.Camera;
        _viewModelCamera = GetNodeOrNull<Camera3D>(ViewModelCameraPath);
        _viewModelRoot = GetNodeOrNull<Node>(ViewModelRootPath);
        _viewModelLightRig = GetNodeOrNull<Node3D>(ViewModelLightRigPath);

        ConfigureCameraMasks();
        ConfigureViewModelFov();
        ConfigureViewModelLights();

        if (ForceViewModelLayerOnMeshes && _viewModelRoot != null)
        {
            ApplyViewModelLayerRecursive(_viewModelRoot, GetLayerMask());
        }
    }

    public override void _Process(double delta)
    {
        if (_viewModelCamera == null || _mainCamera == null || UseSeparateViewModelFov)
        {
            return;
        }

        _viewModelCamera.Fov = _mainCamera.Fov;
    }

    private void ConfigureCameraMasks()
    {
        uint layerMask = GetLayerMask();

        if (_mainCamera != null && ExcludeViewModelLayerFromMainCamera)
        {
            _mainCamera.CullMask &= ~layerMask;
        }

        if (_viewModelCamera != null)
        {
            _viewModelCamera.CullMask = layerMask;
            _viewModelCamera.Current = true;
        }
    }

    private void ConfigureViewModelFov()
    {
        if (_viewModelCamera == null)
        {
            return;
        }

        _viewModelCamera.Fov = UseSeparateViewModelFov || _mainCamera == null ? ViewModelFov : _mainCamera.Fov;
    }

    private void ConfigureViewModelLights()
    {
        if (_viewModelLightRig == null)
        {
            return;
        }

        uint layerMask = GetLayerMask();
        _viewModelLightRig.Visible = LightRigEnabled;

        ConfigureLightsRecursive(_viewModelLightRig, layerMask);
    }

    private void ConfigureLightsRecursive(Node node, uint layerMask)
    {
        if (node is Light3D light)
        {
            light.LightCullMask = layerMask;

            if (light is DirectionalLight3D)
            {
                light.LightEnergy = MainLightEnergy;
            }
            else if (light is OmniLight3D or SpotLight3D)
            {
                light.LightEnergy = FillLightEnergy;
            }
        }

        foreach (Node child in node.GetChildren())
        {
            ConfigureLightsRecursive(child, layerMask);
        }
    }

    private void ApplyViewModelLayerRecursive(Node node, uint layerMask)
    {
        if (node is VisualInstance3D visualInstance)
        {
            visualInstance.Layers = layerMask;
        }

        foreach (Node child in node.GetChildren())
        {
            ApplyViewModelLayerRecursive(child, layerMask);
        }
    }

    private uint GetLayerMask()
    {
        int layerIndex = Mathf.Clamp(ViewModelVisualLayer, 1, 20) - 1;
        return 1u << layerIndex;
    }

}
