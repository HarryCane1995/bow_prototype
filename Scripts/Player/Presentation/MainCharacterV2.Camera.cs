using Godot;
using System.Text.Json;

public partial class MainCharacterV2
{
    [ExportGroup("PoseLab Camera Calibration")]
    [Export(PropertyHint.File, "*.json")]
    public string CameraCalibrationPath { get; set; } = "res://Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.camera.json";

    private record CameraCalibration(Vector3 Offset, Basis ViewBasis, float Fov, Camera3D.KeepAspectEnum Aspect, float Near);
    private CameraCalibration _worldCamera;
    private int _cameraSocketIndex;
    private Transform3D _savedCameraTransform;
    private float _savedCameraFov, _savedCameraNear;
    private Camera3D.KeepAspectEnum _savedCameraAspect;
    private PhysicsInterpolationModeEnum _savedCameraInterpolation;
    private ProcessModeEnum _savedFovProcess;
    private int _savedEffectsPriority, _savedLookPriority;
    private bool _savedCameraTopLevel;
    private Node3D _cameraLookParent;
    private Vector3 _preAimSocketWorld, _frameCameraOrigin;
    private Basis _frameViewBasis;

    private void InitializeCameraCalibration()
    {
        using JsonDocument document = JsonDocument.Parse(FileAccess.GetFileAsString(CameraCalibrationPath));
        JsonElement data = document.RootElement;
        if (data.GetProperty("version").GetInt32() != 2)
            throw new System.InvalidOperationException("V2 requires socket calibration; rerun PoseLab capture/export.");
        _cameraSocketIndex = Skeleton.FindBone(data.GetProperty("socket").GetString());
        if (_cameraSocketIndex < 0)
            throw new System.InvalidOperationException("FP_CAMERA_SOCKET is missing from the V2 skeleton.");
        JsonElement camera = data.GetProperty("cameras").GetProperty("CAM_FP_WORLD");
        JsonElement m = camera.GetProperty("socket_offset_transform");
        Vector3 Column(int column) => new(m[0][column].GetSingle(), m[1][column].GetSingle(), m[2][column].GetSingle());
        Basis viewBasis = _model.Transform.Basis * new Basis(Column(0), Column(1), Column(2)).Orthonormalized();
        bool vertical = camera.GetProperty("sensor_fit").GetString() == "VERTICAL";
        _worldCamera = new CameraCalibration(Column(3), viewBasis,
            camera.GetProperty(vertical ? "fov_y_degrees" : "fov_x_degrees").GetSingle(),
            vertical ? Camera3D.KeepAspectEnum.Height : Camera3D.KeepAspectEnum.Width,
            camera.GetProperty("near").GetSingle());
    }

    private void SetCameraCalibrationEnabled(bool enabled)
    {
        Camera3D camera = _player.Camera;
        if (enabled)
        {
            _savedCameraTransform = camera.Transform;
            _savedCameraFov = camera.Fov;
            _savedCameraNear = camera.Near;
            _savedCameraAspect = camera.KeepAspect;
            _savedCameraInterpolation = camera.PhysicsInterpolationMode;
            _savedCameraTopLevel = camera.TopLevel;
            _cameraLookParent = camera.GetParent<Node3D>();
            _savedFovProcess = _player.CameraFovModule.ProcessMode;
            _savedEffectsPriority = _player.WallRunModule.ProcessPriority;
            _savedLookPriority = _player.LookModule.ProcessPriority;
            // Finish look assist and canonical effects before the one V2 pass,
            // which still precedes gameplay weapon consumers at priority zero.
            _player.LookModule.ProcessPriority = ProcessPriority - 2;
            _player.WallRunModule.ProcessPriority = ProcessPriority - 1;
            // OFF alone still inherits Player's interpolated ancestor transform
            // in Godot 4.6's render traversal. Keep the node/path, isolate its
            // transform, and explicitly sample the same MouseLook/effects basis.
            camera.TopLevel = true;
            // A single FOV owner while V2 is active. Speed/precision zoom remains
            // available in fallback; it must not overwrite the authored framing.
            _player.CameraFovModule.ProcessMode = ProcessModeEnum.Disabled;
            camera.PhysicsInterpolationMode = PhysicsInterpolationModeEnum.Off;
            camera.Fov = _worldCamera.Fov;
            camera.KeepAspect = _worldCamera.Aspect;
            camera.Near = _worldCamera.Near;
        }
        else
        {
            camera.TopLevel = _savedCameraTopLevel;
            camera.Transform = _savedCameraTransform;
            camera.Fov = _savedCameraFov;
            camera.Near = _savedCameraNear;
            camera.KeepAspect = _savedCameraAspect;
            camera.PhysicsInterpolationMode = _savedCameraInterpolation;
            _player.CameraFovModule.ProcessMode = _savedFovProcess;
            _player.WallRunModule.ProcessPriority = _savedEffectsPriority;
            _player.LookModule.ProcessPriority = _savedLookPriority;
        }
    }

    private void CacheAuthoredCamera()
    {
        // GetBoneGlobalPose resolves dirty animated parents synchronously. Cache
        // BEFORE torso/arm edits; neither position nor offset reads solved bones.
        _preAimSocketWorld = Skeleton.GlobalTransform * Skeleton.GetBoneGlobalPose(_cameraSocketIndex).Origin;
        _frameViewBasis = (_cameraLookParent.GlobalBasis * _worldCamera.ViewBasis).Orthonormalized();
        _frameCameraOrigin = _preAimSocketWorld + Skeleton.GlobalBasis * PresentationCameraOffset(_frameViewBasis);
    }

    private void ApplyCameraCalibration()
    {
        // The sole per-frame camera writer. Aim consumes this same frame plan,
        // never last frame's camera position or the post-IK socket.
        _player.Camera.GlobalTransform = new Transform3D(_frameViewBasis, _frameCameraOrigin);
    }
}
