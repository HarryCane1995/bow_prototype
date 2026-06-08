using Godot;

public partial class RuntimeTuningPanel : Window
{
    /// <summary>
    /// Путь к игроку, из которого панель берёт активный PlayerTuningProfile, если профиль не назначен напрямую.
    /// </summary>
    [ExportGroup("References")]
    [Export] public NodePath PlayerPath { get; set; } = new("../Player");

    /// <summary>
    /// Профиль runtime-настроек. Если пустой, панель попробует взять профиль из PlayerController.
    /// </summary>
    [Export] public PlayerTuningProfile TuningProfile { get; set; }

    /// <summary>
    /// Путь к default-профилю, используемому кнопкой Reset To Defaults.
    /// </summary>
    [Export(PropertyHint.File, "*.tres,*.res")] public string DefaultProfilePath { get; set; } = "res://Resources/Tuning/DefaultPlayerTuningProfile.tres";

    /// <summary>
    /// Путь к JSON-файлу с runtime-настройками пользователя.
    /// </summary>
    [Export] public string RuntimeSavePath { get; set; } = "user://player_tuning_runtime.json";

    private VBoxContainer _content;
    private bool _wasTogglePressed;
    private PlayerController _player;
    private readonly System.Collections.Generic.List<System.Action> _readoutUpdaters = new();

    public override void _Ready()
    {
        Title = "Bow Prototype Runtime Tuning";
        Size = new Vector2I(520, 760);
        MinSize = new Vector2I(420, 480);
        Visible = false;
        CloseRequested += Hide;

        ResolveTuningProfile();
        BuildUi();
    }

    public override void _Process(double delta)
    {
        bool togglePressed = Input.IsKeyPressed(Key.F2);
        if (togglePressed && !_wasTogglePressed)
        {
            Visible = !Visible;
        }

        _wasTogglePressed = togglePressed;

        foreach (System.Action updateReadout in _readoutUpdaters)
        {
            updateReadout();
        }
    }

    private void ResolveTuningProfile()
    {
        _player = GetNodeOrNull<PlayerController>(PlayerPath);
        if (TuningProfile != null)
        {
            return;
        }

        TuningProfile = _player?.TuningProfile;
    }

    private void BuildUi()
    {
        ScrollContainer scrollContainer = new()
        {
            Name = "ScrollContainer",
            HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled,
            VerticalScrollMode = ScrollContainer.ScrollMode.Auto,
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill,
            SizeFlagsVertical = Control.SizeFlags.ExpandFill
        };
        scrollContainer.SetAnchorsPreset(Control.LayoutPreset.FullRect);

        _content = new VBoxContainer
        {
            Name = "Content",
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };

        scrollContainer.AddChild(_content);
        AddChild(scrollContainer);

        AddToolbar();

        if (TuningProfile == null)
        {
            Label missingProfileLabel = new()
            {
                Text = "No PlayerTuningProfile assigned.",
                AutowrapMode = TextServer.AutowrapMode.WordSmart
            };
            _content.AddChild(missingProfileLabel);
            return;
        }

        AddMovementSection();
        AddJumpSection();
        AddCrouchSlideSection();
        AddSlingshotGrappleSection();
        AddBowSection();
        AddCameraSection();
        AddSpeedFovSection();
        AddFramePhysicsDebugSection();
        AddViewModelSwaySection();
        AddViewModelAimStabilizationSection();
    }

    private void AddToolbar()
    {
        HBoxContainer toolbar = new()
        {
            Name = "Toolbar"
        };

        Button resetButton = new()
        {
            Text = "Reset To Defaults"
        };
        resetButton.Pressed += ResetToDefaults;

        Button saveButton = new()
        {
            Text = "Save Runtime Values"
        };
        saveButton.Pressed += SaveRuntimeValues;

        Button saveDefaultsButton = new()
        {
            Text = "Save As Project Defaults"
        };
        saveDefaultsButton.Pressed += SaveAsProjectDefaults;

        Button loadButton = new()
        {
            Text = "Load Saved Values"
        };
        loadButton.Pressed += LoadRuntimeValues;

        toolbar.AddChild(resetButton);
        toolbar.AddChild(saveButton);
        toolbar.AddChild(saveDefaultsButton);
        toolbar.AddChild(loadButton);
        _content.AddChild(toolbar);
    }

    private void AddMovementSection()
    {
        AddSection("Movement");
        AddFloatControl("Move Speed", 0.0, 30.0, 0.1, () => TuningProfile.MoveSpeed, value => TuningProfile.MoveSpeed = value);
        AddFloatControl("Ground Acceleration", 0.0, 160.0, 0.5, () => TuningProfile.GroundAcceleration, value => TuningProfile.GroundAcceleration = value);
        AddFloatControl("Ground Deceleration", 0.0, 160.0, 0.5, () => TuningProfile.GroundDeceleration, value => TuningProfile.GroundDeceleration = value);
        AddBoolControl("Enable Direction Change Accel", () => TuningProfile.EnableDirectionChangeAcceleration, value => TuningProfile.EnableDirectionChangeAcceleration = value);
        AddFloatControl("Ground Direction Change", 0.0, 180.0, 0.5, () => TuningProfile.GroundDirectionChangeAcceleration, value => TuningProfile.GroundDirectionChangeAcceleration = value);
        AddBoolControl("Enable Counter Strafe Boost", () => TuningProfile.EnableCounterStrafeBoost, value => TuningProfile.EnableCounterStrafeBoost = value);
        AddFloatControl("Counter Strafe Boost", 1.0, 4.0, 0.05, () => TuningProfile.CounterStrafeBoost, value => TuningProfile.CounterStrafeBoost = value);
    }

    private void AddJumpSection()
    {
        AddSection("Jump");
        AddFloatControl("Jump Velocity", 0.0, 30.0, 0.1, () => TuningProfile.JumpVelocity, value => TuningProfile.JumpVelocity = value);
        AddBoolControl("Enable Double Jump", () => TuningProfile.EnableDoubleJump, value => TuningProfile.EnableDoubleJump = value);
        AddFloatControl("Double Jump Multiplier", 0.1, 3.0, 0.05, () => TuningProfile.DoubleJumpVelocityMultiplier, value => TuningProfile.DoubleJumpVelocityMultiplier = value);
        AddBoolControl("Enable Double Jump Redirect", () => TuningProfile.EnableDoubleJumpRedirect, value => TuningProfile.EnableDoubleJumpRedirect = value);
        AddFloatControl("Double Jump Redirect Speed", 0.0, 40.0, 0.1, () => TuningProfile.DoubleJumpRedirectSpeed, value => TuningProfile.DoubleJumpRedirectSpeed = value);
        AddBoolControl("Restore Double Jump On Grapple", () => TuningProfile.RestoreDoubleJumpOnGrapple, value => TuningProfile.RestoreDoubleJumpOnGrapple = value);
    }

    private void AddCrouchSlideSection()
    {
        AddSection("Crouch / Slide");
        AddFloatControl("Crouch Speed Multiplier", 0.1, 1.0, 0.05, () => TuningProfile.CrouchSpeedMultiplier, value => TuningProfile.CrouchSpeedMultiplier = value);
        AddFloatControl("Slide Initial Speed", 0.0, 40.0, 0.1, () => TuningProfile.SlideInitialSpeed, value => TuningProfile.SlideInitialSpeed = value);
        AddFloatControl("Slide Duration", 0.05, 3.0, 0.01, () => TuningProfile.SlideDuration, value => TuningProfile.SlideDuration = value);
        AddFloatControl("Slide Cooldown", 0.0, 3.0, 0.01, () => TuningProfile.SlideCooldown, value => TuningProfile.SlideCooldown = value);
        AddFloatControl("Slide Friction", 0.0, 60.0, 0.5, () => TuningProfile.SlideFriction, value => TuningProfile.SlideFriction = value);
        AddFloatControl("Slide Steering", 0.0, 3.0, 0.05, () => TuningProfile.SlideSteeringStrength, value => TuningProfile.SlideSteeringStrength = value);
        AddBoolControl("Exit Slide By Speed", () => TuningProfile.EnableSlideExitBySpeed, value => TuningProfile.EnableSlideExitBySpeed = value);
        AddFloatControl("Slide Exit Min Speed", 0.0, 10.0, 0.1, () => TuningProfile.SlideExitMinSpeed, value => TuningProfile.SlideExitMinSpeed = value);
        AddFloatControl("Slide Exit Grace", 0.0, 0.5, 0.01, () => TuningProfile.SlideExitMinSpeedGraceTime, value => TuningProfile.SlideExitMinSpeedGraceTime = value);
        AddBoolControl("Airborne Slide Entry", () => TuningProfile.EnableAirborneSlideEntry, value => TuningProfile.EnableAirborneSlideEntry = value);
        AddFloatControl("Airborne Slide Min Speed", 0.0, 25.0, 0.5, () => TuningProfile.AirborneSlideMinSpeed, value => TuningProfile.AirborneSlideMinSpeed = value);
        AddFloatControl("Airborne Slide Buffer", 0.0, 1.0, 0.05, () => TuningProfile.AirborneSlideBufferTime, value => TuningProfile.AirborneSlideBufferTime = value);
        AddBoolControl("Airborne Uses Velocity", () => TuningProfile.AirborneSlideUseCurrentVelocityDirection, value => TuningProfile.AirborneSlideUseCurrentVelocityDirection = value);
        AddBoolControl("Airborne Uses Input", () => TuningProfile.AirborneSlideUseInputDirectionIfAny, value => TuningProfile.AirborneSlideUseInputDirectionIfAny = value);
        AddFloatControl("Airborne Input Min", 0.0, 1.0, 0.05, () => TuningProfile.AirborneSlideInputMin, value => TuningProfile.AirborneSlideInputMin = value);
        AddBoolControl("Enable Slide Jump", () => TuningProfile.EnableSlideJump, value => TuningProfile.EnableSlideJump = value);
        AddFloatControl("Slide Jump Boost", 0.0, 10.0, 0.25, () => TuningProfile.SlideJumpHorizontalBoost, value => TuningProfile.SlideJumpHorizontalBoost = value);
        AddFloatControl("Slide Jump Carry", 0.0, 1.5, 0.05, () => TuningProfile.SlideJumpVelocityCarryFactor, value => TuningProfile.SlideJumpVelocityCarryFactor = value);
        AddFloatControl("Slide Jump Max Speed", 0.0, 35.0, 0.5, () => TuningProfile.SlideJumpMaxHorizontalSpeed, value => TuningProfile.SlideJumpMaxHorizontalSpeed = value);
        AddBoolControl("Slide Jump Needs Headroom", () => TuningProfile.SlideJumpRequiresStandUpSpace, value => TuningProfile.SlideJumpRequiresStandUpSpace = value);
    }

    private void AddSlingshotGrappleSection()
    {
        AddSection("Slingshot Grapple");
        AddFloatControl("Max Grapple Distance", 1.0, 100.0, 0.5, () => TuningProfile.MaxGrappleDistance, value => TuningProfile.MaxGrappleDistance = value);
        AddBoolControl("Enable Screen Assist", () => TuningProfile.EnableScreenSpaceGrappleAssist, value => TuningProfile.EnableScreenSpaceGrappleAssist = value);
        AddFloatControl("Screen Assist Radius", 0.0, 240.0, 4.0, () => TuningProfile.GrappleScreenAssistRadiusPixels, value => TuningProfile.GrappleScreenAssistRadiusPixels = value);
        AddBoolControl("Prefer Direct Hit", () => TuningProfile.PreferDirectRaycastHit, value => TuningProfile.PreferDirectRaycastHit = value);
        AddFloatControl("Assist Max Angle", 0.0, 45.0, 1.0, () => TuningProfile.GrappleAssistMaxAngleDegrees, value => TuningProfile.GrappleAssistMaxAngleDegrees = value);
        AddBoolControl("Assist Line Of Sight", () => TuningProfile.GrappleAssistRequireLineOfSight, value => TuningProfile.GrappleAssistRequireLineOfSight = value);
        AddFloatControl("Assist Distance Weight", 0.0, 2.0, 0.05, () => TuningProfile.GrappleAssistDistanceWeight, value => TuningProfile.GrappleAssistDistanceWeight = value);
        AddFloatControl("Assist Screen Weight", 0.0, 3.0, 0.05, () => TuningProfile.GrappleAssistScreenDistanceWeight, value => TuningProfile.GrappleAssistScreenDistanceWeight = value);
        AddBoolControl("Enable Camera Snap", () => TuningProfile.EnableGrappleCameraSnap, value => TuningProfile.EnableGrappleCameraSnap = value);
        AddFloatControl("Camera Snap Duration", 0.0, 0.5, 0.01, () => TuningProfile.GrappleCameraSnapDuration, value => TuningProfile.GrappleCameraSnapDuration = value);
        AddFloatControl("Camera Snap Strength", 0.0, 1.0, 0.05, () => TuningProfile.GrappleCameraSnapStrength, value => TuningProfile.GrappleCameraSnapStrength = value);
        AddFloatControl("Camera Snap Speed", 1.0, 40.0, 0.5, () => TuningProfile.GrappleCameraSnapSpeed, value => TuningProfile.GrappleCameraSnapSpeed = value);
        AddBoolControl("Lock Look During Snap", () => TuningProfile.LockLookInputDuringGrappleSnap, value => TuningProfile.LockLookInputDuringGrappleSnap = value);
        AddFloatControl("Camera Snap Max Pitch", 0.0, 89.0, 1.0, () => TuningProfile.GrappleCameraSnapMaxPitchDegrees, value => TuningProfile.GrappleCameraSnapMaxPitchDegrees = value);
        AddBoolControl("Enable Available Highlight", () => TuningProfile.EnableGrappleAvailableHighlight, value => TuningProfile.EnableGrappleAvailableHighlight = value);
        AddFloatControl("Pull Acceleration", 0.0, 140.0, 0.5, () => TuningProfile.PullAcceleration, value => TuningProfile.PullAcceleration = value);
        AddFloatControl("Max Pull Speed", 1.0, 100.0, 0.5, () => TuningProfile.MaxPullSpeed, value => TuningProfile.MaxPullSpeed = value);
        AddFloatControl("Launch Speed", 0.0, 100.0, 0.5, () => TuningProfile.LaunchSpeed, value => TuningProfile.LaunchSpeed = value);
        AddFloatControl("Inherit Pull Velocity", 0.0, 2.0, 0.05, () => TuningProfile.InheritPullVelocityFactor, value => TuningProfile.InheritPullVelocityFactor = value);
        AddFloatControl("Max Launch Velocity", 1.0, 120.0, 0.5, () => TuningProfile.MaxLaunchVelocity, value => TuningProfile.MaxLaunchVelocity = value);
    }

    private void AddBowSection()
    {
        AddSection("Bow / Projectiles");
        AddFloatControl("Light Shot Speed", 0.0, 220.0, 0.5, () => TuningProfile.LightShotSpeed, value => TuningProfile.LightShotSpeed = value);
        AddFloatControl("Charged Shot Speed", 0.0, 240.0, 0.5, () => TuningProfile.ChargedShotSpeed, value => TuningProfile.ChargedShotSpeed = value);
        AddBoolControl("Enable Precision Shot", () => TuningProfile.EnablePrecisionShot, value => TuningProfile.EnablePrecisionShot = value);
        AddFloatControl("Precision Shot Speed", 0.0, 320.0, 1.0, () => TuningProfile.PrecisionShotSpeed, value => TuningProfile.PrecisionShotSpeed = value);
        AddFloatControl("Precision Shot Damage", 0.0, 400.0, 1.0, () => TuningProfile.PrecisionShotDamage, value => TuningProfile.PrecisionShotDamage = value);
        AddBoolControl("Precision Armor Piercing", () => TuningProfile.PrecisionShotArmorPiercing, value => TuningProfile.PrecisionShotArmorPiercing = value);
        AddFloatControl("Projectile Gravity", 0.0, 80.0, 0.5, () => TuningProfile.ProjectileGravity, value => TuningProfile.ProjectileGravity = value);
    }

    private void AddCameraSection()
    {
        AddSection("Camera");
        AddFloatControl("Player FOV", 50.0, 120.0, 1.0, () => TuningProfile.PlayerFov, value => TuningProfile.PlayerFov = value);
        AddFloatControl("Precision FOV", 20.0, 100.0, 0.5, () => TuningProfile.PrecisionFov, value => TuningProfile.PrecisionFov = value);
        AddFloatControl("FOV Transition Speed", 1.0, 300.0, 1.0, () => TuningProfile.FovTransitionSpeed, value => TuningProfile.FovTransitionSpeed = value);
    }

    private void AddSpeedFovSection()
    {
        AddSection("Camera / Speed FOV");
        AddBoolControl("Enable Speed FOV", () => TuningProfile.EnableSpeedFov, value => TuningProfile.EnableSpeedFov = value);
        AddFloatControl("Speed FOV Multiplier", 0.0, 2.0, 0.05, () => TuningProfile.SpeedFovMultiplier, value => TuningProfile.SpeedFovMultiplier = value);
        AddFloatControl("Min Speed For FOV", 0.0, 25.0, 0.5, () => TuningProfile.MinSpeedForFov, value => TuningProfile.MinSpeedForFov = value);
        AddFloatControl("Max Speed FOV Bonus", 0.0, 40.0, 1.0, () => TuningProfile.MaxSpeedFovBonus, value => TuningProfile.MaxSpeedFovBonus = value);
        AddFloatControl("Speed FOV Smooth Up", 0.1, 25.0, 0.1, () => TuningProfile.SpeedFovSmoothUp, value => TuningProfile.SpeedFovSmoothUp = value);
        AddFloatControl("Speed FOV Smooth Down", 0.1, 25.0, 0.1, () => TuningProfile.SpeedFovSmoothDown, value => TuningProfile.SpeedFovSmoothDown = value);
        AddBoolControl("Use Full Velocity", () => TuningProfile.UseFullVelocityForSpeedFov, value => TuningProfile.UseFullVelocityForSpeedFov = value);
        AddBoolControl("Disable During Precision Aim", () => TuningProfile.DisableSpeedFovDuringPrecisionAim, value => TuningProfile.DisableSpeedFovDuringPrecisionAim = value);
        AddBoolControl("Use Axis Based Speed FOV", () => TuningProfile.UseAxisBasedSpeedFov, value => TuningProfile.UseAxisBasedSpeedFov = value);
        AddFloatControl("Strafe Speed FOV Multiplier", 0.0, 2.0, 0.05, () => TuningProfile.StrafeSpeedFovMultiplier, value => TuningProfile.StrafeSpeedFovMultiplier = value);
        AddFloatControl("Min Strafe Speed For FOV", 0.0, 25.0, 0.5, () => TuningProfile.MinStrafeSpeedForFov, value => TuningProfile.MinStrafeSpeedForFov = value);
        AddBoolControl("Include Backward Speed", () => TuningProfile.IncludeBackwardSpeedInForwardFov, value => TuningProfile.IncludeBackwardSpeedInForwardFov = value);
        AddReadout("Speed FOV Debug", GetSpeedFovDebugText);
    }

    private void AddFramePhysicsDebugSection()
    {
        AddSection("Frame / Physics Debug");
        AddReadout("Cadence Debug", GetFramePhysicsDebugText);
    }

    private void AddViewModelSwaySection()
    {
        AddSection("ViewModel / Sway");
        AddBoolControl("Enable ViewModel Sway", () => TuningProfile.EnableViewModelSway, value => TuningProfile.EnableViewModelSway = value);
        AddBoolControl("Enable Mouse Lag", () => TuningProfile.EnableMouseLag, value => TuningProfile.EnableMouseLag = value);
        AddFloatControl("Mouse Lag Position", 0.0, 0.08, 0.001, () => TuningProfile.MouseLagPositionAmount, value => TuningProfile.MouseLagPositionAmount = value);
        AddFloatControl("Mouse Lag Rotation", 0.0, 8.0, 0.1, () => TuningProfile.MouseLagRotationAmount, value => TuningProfile.MouseLagRotationAmount = value);
        AddBoolControl("Enable Mouse Lag Smoothing", () => TuningProfile.EnableMouseLagSmoothing, value => TuningProfile.EnableMouseLagSmoothing = value);
        AddFloatControl("Mouse Lag Input Smooth", 0.1, 40.0, 0.1, () => TuningProfile.MouseLagInputSmoothSpeed, value => TuningProfile.MouseLagInputSmoothSpeed = value);
        AddFloatControl("Mouse Lag Output Smooth", 0.1, 40.0, 0.1, () => TuningProfile.MouseLagOutputSmoothSpeed, value => TuningProfile.MouseLagOutputSmoothSpeed = value);
        AddBoolControl("Enable Movement Inertia", () => TuningProfile.EnableMovementInertia, value => TuningProfile.EnableMovementInertia = value);
        AddFloatControl("Movement Inertia Position", 0.0, 0.03, 0.001, () => TuningProfile.MovementInertiaPositionAmount, value => TuningProfile.MovementInertiaPositionAmount = value);
        AddFloatControl("Movement Inertia Rotation", 0.0, 4.0, 0.05, () => TuningProfile.MovementInertiaRotationAmount, value => TuningProfile.MovementInertiaRotationAmount = value);
        AddBoolControl("Enable Landing Sway", () => TuningProfile.EnableLandingSway, value => TuningProfile.EnableLandingSway = value);
        AddFloatControl("Landing Position", 0.0, 0.10, 0.001, () => TuningProfile.LandingPositionAmount, value => TuningProfile.LandingPositionAmount = value);
        AddFloatControl("Landing Rotation", 0.0, 10.0, 0.1, () => TuningProfile.LandingRotationAmount, value => TuningProfile.LandingRotationAmount = value);
        AddFloatControl("Sway Follow Speed", 0.1, 30.0, 0.1, () => TuningProfile.SwayFollowSpeed, value => TuningProfile.SwayFollowSpeed = value);
        AddFloatControl("Sway Return Speed", 0.1, 30.0, 0.1, () => TuningProfile.SwayReturnSpeed, value => TuningProfile.SwayReturnSpeed = value);
        AddFloatControl("Impulse Return Speed", 0.1, 30.0, 0.1, () => TuningProfile.ImpulseReturnSpeed, value => TuningProfile.ImpulseReturnSpeed = value);
        AddBoolControl("Enable Rotation Smoothing", () => TuningProfile.EnableRotationSmoothing, value => TuningProfile.EnableRotationSmoothing = value);
        AddFloatControl("Rotation Smooth Speed", 0.1, 40.0, 0.1, () => TuningProfile.RotationSmoothSpeed, value => TuningProfile.RotationSmoothSpeed = value);
        AddFloatControl("Position Smooth Speed", 0.1, 40.0, 0.1, () => TuningProfile.PositionSmoothSpeed, value => TuningProfile.PositionSmoothSpeed = value);
    }

    private void AddViewModelAimStabilizationSection()
    {
        AddSection("ViewModel / Aim Stabilization");
        AddBoolControl("Enable Aim Stabilization", () => TuningProfile.EnableAimStabilization, value => TuningProfile.EnableAimStabilization = value);
        AddFloatControl("Aim Stabilization Strength", 0.0, 1.0, 0.01, () => TuningProfile.AimStabilizationStrength, value => TuningProfile.AimStabilizationStrength = value);
        AddFloatControl("Aim Stabilization Smooth", 0.1, 40.0, 0.1, () => TuningProfile.AimStabilizationSmoothSpeed, value => TuningProfile.AimStabilizationSmoothSpeed = value);
        AddFloatControl("Max Aim Correction", 0.0, 30.0, 0.5, () => TuningProfile.MaxAimCorrectionDegrees, value => TuningProfile.MaxAimCorrectionDegrees = value);
        AddFloatControl("Aim Stabilization Dead Zone", 0.0, 0.2, 0.005, () => TuningProfile.AimStabilizationDeadZone, value => TuningProfile.AimStabilizationDeadZone = value);
        AddBoolControl("Only When Aiming", () => TuningProfile.StabilizeOnlyWhenAiming, value => TuningProfile.StabilizeOnlyWhenAiming = value);
    }

    private void AddSection(string title)
    {
        Label label = new()
        {
            Text = title,
            ThemeTypeVariation = "HeaderSmall"
        };
        _content.AddChild(label);
    }

    private void AddFloatControl(string labelText, double min, double max, double step, System.Func<float> getter, System.Action<float> setter)
    {
        HBoxContainer row = new();
        Label label = new()
        {
            Text = labelText,
            CustomMinimumSize = new Vector2(190.0f, 0.0f)
        };

        HSlider slider = new()
        {
            MinValue = min,
            MaxValue = max,
            Step = step,
            Value = getter(),
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };

        SpinBox spinBox = new()
        {
            MinValue = min,
            MaxValue = max,
            Step = step,
            Value = getter(),
            CustomMinimumSize = new Vector2(95.0f, 0.0f)
        };

        slider.ValueChanged += value =>
        {
            setter((float)value);
            spinBox.SetValueNoSignal(value);
        };

        spinBox.ValueChanged += value =>
        {
            setter((float)value);
            slider.SetValueNoSignal(value);
        };

        row.AddChild(label);
        row.AddChild(slider);
        row.AddChild(spinBox);
        _content.AddChild(row);
    }

    private void AddBoolControl(string labelText, System.Func<bool> getter, System.Action<bool> setter)
    {
        CheckBox checkBox = new()
        {
            Text = labelText,
            ButtonPressed = getter()
        };

        checkBox.Toggled += pressed => setter(pressed);
        _content.AddChild(checkBox);
    }

    private void AddReadout(string labelText, System.Func<string> getter)
    {
        Label label = new()
        {
            Text = $"{labelText}: {getter()}",
            AutowrapMode = TextServer.AutowrapMode.WordSmart
        };

        _readoutUpdaters.Add(() => label.Text = $"{labelText}: {getter()}");
        _content.AddChild(label);
    }

    private string GetSpeedFovDebugText()
    {
        PlayerSpeedFovModule speedFov = _player?.SpeedFovModule;
        PlayerCameraFovModule cameraFov = _player?.CameraFovModule;
        if (speedFov == null || cameraFov == null)
        {
            return "player modules unavailable";
        }

        return $"speed={speedFov.CurrentSpeed:0.00}, forward={speedFov.CurrentForwardSpeed:0.00}, strafe={speedFov.CurrentStrafeSpeed:0.00}, bonus={speedFov.CurrentSpeedFovBonus:0.00}/{speedFov.CurrentTargetSpeedFovBonus:0.00}, targetFov={cameraFov.FinalTargetFov:0.00}, cameraFov={cameraFov.CurrentCameraFov:0.00}";
    }

    private string GetFramePhysicsDebugText()
    {
        Vector3 velocity = _player?.Velocity ?? Vector3.Zero;
        float horizontalSpeed = new Vector3(velocity.X, 0.0f, velocity.Z).Length();
        PlayerSpeedFovModule speedFov = _player?.SpeedFovModule;
        PlayerCameraFovModule cameraFov = _player?.CameraFovModule;
        string physicsInterpolation = GetProjectSettingBoolText("physics/common/physics_interpolation");
        bool speedFovEnabled = TuningProfile?.EnableSpeedFov ?? false;
        float speedFovBonus = speedFov?.CurrentSpeedFovBonus ?? 0.0f;
        float cameraFovValue = cameraFov?.CurrentCameraFov ?? _player?.Camera?.Fov ?? 0.0f;

        return $"fps={Engine.GetFramesPerSecond():0}, physicsTicks={Engine.PhysicsTicksPerSecond}, physicsInterpolation={physicsInterpolation}, velocityXZ=({velocity.X:0.00}, {velocity.Z:0.00}), horizontalSpeed={horizontalSpeed:0.00}, cameraFov={cameraFovValue:0.00}, speedFovEnabled={speedFovEnabled}, speedFovBonus={speedFovBonus:0.00}";
    }

    private static string GetProjectSettingBoolText(string settingName)
    {
        if (!ProjectSettings.HasSetting(settingName))
        {
            return "unavailable";
        }

        return ProjectSettings.GetSetting(settingName).AsBool() ? "true" : "false";
    }

    private void ResetToDefaults()
    {
        PlayerTuningProfile defaults = ResourceLoader.Load<PlayerTuningProfile>(DefaultProfilePath, null, ResourceLoader.CacheMode.Ignore);
        if (defaults == null)
        {
            GD.PushWarning($"Could not load default tuning profile: {DefaultProfilePath}");
            return;
        }

        CopyProfile(defaults, TuningProfile);
        RebuildUi();
    }

    private void SaveRuntimeValues()
    {
        if (TuningProfile == null)
        {
            return;
        }

        Godot.Collections.Dictionary values = ProfileToDictionary(TuningProfile);
        using FileAccess file = FileAccess.Open(RuntimeSavePath, FileAccess.ModeFlags.Write);
        file.StoreString(Json.Stringify(values, "\t"));
    }

    private void SaveAsProjectDefaults()
    {
        if (TuningProfile == null)
        {
            return;
        }

        PlayerTuningProfile defaults = TuningProfile.Duplicate() as PlayerTuningProfile;
        if (defaults == null)
        {
            GD.PushWarning("Could not duplicate current tuning profile for project defaults.");
            return;
        }

        Error saveError = ResourceSaver.Save(defaults, DefaultProfilePath);
        if (saveError != Error.Ok)
        {
            GD.PushWarning($"Could not save project tuning defaults to {DefaultProfilePath}: {saveError}");
        }
    }

    private void LoadRuntimeValues()
    {
        if (!FileAccess.FileExists(RuntimeSavePath))
        {
            GD.PushWarning($"No runtime tuning save found: {RuntimeSavePath}");
            return;
        }

        using FileAccess file = FileAccess.Open(RuntimeSavePath, FileAccess.ModeFlags.Read);
        Variant parsed = Json.ParseString(file.GetAsText());
        if (parsed.VariantType != Variant.Type.Dictionary)
        {
            GD.PushWarning($"Runtime tuning save is not a JSON object: {RuntimeSavePath}");
            return;
        }

        DictionaryToProfile(parsed.AsGodotDictionary(), TuningProfile);
        RebuildUi();
    }

    private void RebuildUi()
    {
        _readoutUpdaters.Clear();
        foreach (Node child in GetChildren())
        {
            RemoveChild(child);
            child.QueueFree();
        }

        BuildUi();
    }

    private static Godot.Collections.Dictionary ProfileToDictionary(PlayerTuningProfile profile)
    {
        return new Godot.Collections.Dictionary
        {
            ["MoveSpeed"] = profile.MoveSpeed,
            ["GroundAcceleration"] = profile.GroundAcceleration,
            ["GroundDeceleration"] = profile.GroundDeceleration,
            ["EnableDirectionChangeAcceleration"] = profile.EnableDirectionChangeAcceleration,
            ["GroundDirectionChangeAcceleration"] = profile.GroundDirectionChangeAcceleration,
            ["EnableCounterStrafeBoost"] = profile.EnableCounterStrafeBoost,
            ["CounterStrafeBoost"] = profile.CounterStrafeBoost,
            ["JumpVelocity"] = profile.JumpVelocity,
            ["EnableDoubleJump"] = profile.EnableDoubleJump,
            ["DoubleJumpVelocityMultiplier"] = profile.DoubleJumpVelocityMultiplier,
            ["EnableDoubleJumpRedirect"] = profile.EnableDoubleJumpRedirect,
            ["DoubleJumpRedirectSpeed"] = profile.DoubleJumpRedirectSpeed,
            ["RestoreDoubleJumpOnGrapple"] = profile.RestoreDoubleJumpOnGrapple,
            ["CrouchSpeedMultiplier"] = profile.CrouchSpeedMultiplier,
            ["SlideInitialSpeed"] = profile.SlideInitialSpeed,
            ["SlideDuration"] = profile.SlideDuration,
            ["SlideCooldown"] = profile.SlideCooldown,
            ["SlideFriction"] = profile.SlideFriction,
            ["SlideSteeringStrength"] = profile.SlideSteeringStrength,
            ["EnableSlideExitBySpeed"] = profile.EnableSlideExitBySpeed,
            ["SlideExitMinSpeed"] = profile.SlideExitMinSpeed,
            ["SlideExitMinSpeedGraceTime"] = profile.SlideExitMinSpeedGraceTime,
            ["EnableAirborneSlideEntry"] = profile.EnableAirborneSlideEntry,
            ["AirborneSlideMinSpeed"] = profile.AirborneSlideMinSpeed,
            ["AirborneSlideBufferTime"] = profile.AirborneSlideBufferTime,
            ["AirborneSlideUseCurrentVelocityDirection"] = profile.AirborneSlideUseCurrentVelocityDirection,
            ["AirborneSlideUseInputDirectionIfAny"] = profile.AirborneSlideUseInputDirectionIfAny,
            ["AirborneSlideInputMin"] = profile.AirborneSlideInputMin,
            ["EnableSlideJump"] = profile.EnableSlideJump,
            ["SlideJumpHorizontalBoost"] = profile.SlideJumpHorizontalBoost,
            ["SlideJumpVelocityCarryFactor"] = profile.SlideJumpVelocityCarryFactor,
            ["SlideJumpMaxHorizontalSpeed"] = profile.SlideJumpMaxHorizontalSpeed,
            ["SlideJumpRequiresStandUpSpace"] = profile.SlideJumpRequiresStandUpSpace,
            ["MaxGrappleDistance"] = profile.MaxGrappleDistance,
            ["EnableScreenSpaceGrappleAssist"] = profile.EnableScreenSpaceGrappleAssist,
            ["GrappleScreenAssistRadiusPixels"] = profile.GrappleScreenAssistRadiusPixels,
            ["PreferDirectRaycastHit"] = profile.PreferDirectRaycastHit,
            ["GrappleAssistMaxAngleDegrees"] = profile.GrappleAssistMaxAngleDegrees,
            ["GrappleAssistRequireLineOfSight"] = profile.GrappleAssistRequireLineOfSight,
            ["GrappleAssistDistanceWeight"] = profile.GrappleAssistDistanceWeight,
            ["GrappleAssistScreenDistanceWeight"] = profile.GrappleAssistScreenDistanceWeight,
            ["EnableGrappleCameraSnap"] = profile.EnableGrappleCameraSnap,
            ["GrappleCameraSnapDuration"] = profile.GrappleCameraSnapDuration,
            ["GrappleCameraSnapStrength"] = profile.GrappleCameraSnapStrength,
            ["GrappleCameraSnapSpeed"] = profile.GrappleCameraSnapSpeed,
            ["LockLookInputDuringGrappleSnap"] = profile.LockLookInputDuringGrappleSnap,
            ["GrappleCameraSnapMaxPitchDegrees"] = profile.GrappleCameraSnapMaxPitchDegrees,
            ["EnableGrappleAvailableHighlight"] = profile.EnableGrappleAvailableHighlight,
            ["GrappleHighlightOnlyBestAnchor"] = profile.GrappleHighlightOnlyBestAnchor,
            ["PullAcceleration"] = profile.PullAcceleration,
            ["MaxPullSpeed"] = profile.MaxPullSpeed,
            ["LaunchSpeed"] = profile.LaunchSpeed,
            ["InheritPullVelocityFactor"] = profile.InheritPullVelocityFactor,
            ["MaxLaunchVelocity"] = profile.MaxLaunchVelocity,
            ["LightShotSpeed"] = profile.LightShotSpeed,
            ["ChargedShotSpeed"] = profile.ChargedShotSpeed,
            ["EnablePrecisionShot"] = profile.EnablePrecisionShot,
            ["PrecisionShotSpeed"] = profile.PrecisionShotSpeed,
            ["PrecisionShotDamage"] = profile.PrecisionShotDamage,
            ["PrecisionShotArmorPiercing"] = profile.PrecisionShotArmorPiercing,
            ["ProjectileGravity"] = profile.ProjectileGravity,
            ["PlayerFov"] = profile.PlayerFov,
            ["PrecisionFov"] = profile.PrecisionFov,
            ["FovTransitionSpeed"] = profile.FovTransitionSpeed,
            ["EnableSpeedFov"] = profile.EnableSpeedFov,
            ["SpeedFovMultiplier"] = profile.SpeedFovMultiplier,
            ["MinSpeedForFov"] = profile.MinSpeedForFov,
            ["MaxSpeedFovBonus"] = profile.MaxSpeedFovBonus,
            ["SpeedFovSmoothUp"] = profile.SpeedFovSmoothUp,
            ["SpeedFovSmoothDown"] = profile.SpeedFovSmoothDown,
            ["UseFullVelocityForSpeedFov"] = profile.UseFullVelocityForSpeedFov,
            ["DisableSpeedFovDuringPrecisionAim"] = profile.DisableSpeedFovDuringPrecisionAim,
            ["UseAxisBasedSpeedFov"] = profile.UseAxisBasedSpeedFov,
            ["StrafeSpeedFovMultiplier"] = profile.StrafeSpeedFovMultiplier,
            ["MinStrafeSpeedForFov"] = profile.MinStrafeSpeedForFov,
            ["IncludeBackwardSpeedInForwardFov"] = profile.IncludeBackwardSpeedInForwardFov,
            ["EnableViewModelSway"] = profile.EnableViewModelSway,
            ["EnableMouseLag"] = profile.EnableMouseLag,
            ["MouseLagPositionAmount"] = profile.MouseLagPositionAmount,
            ["MouseLagRotationAmount"] = profile.MouseLagRotationAmount,
            ["EnableMouseLagSmoothing"] = profile.EnableMouseLagSmoothing,
            ["MouseLagInputSmoothSpeed"] = profile.MouseLagInputSmoothSpeed,
            ["MouseLagOutputSmoothSpeed"] = profile.MouseLagOutputSmoothSpeed,
            ["EnableMovementInertia"] = profile.EnableMovementInertia,
            ["MovementInertiaPositionAmount"] = profile.MovementInertiaPositionAmount,
            ["MovementInertiaRotationAmount"] = profile.MovementInertiaRotationAmount,
            ["EnableLandingSway"] = profile.EnableLandingSway,
            ["LandingPositionAmount"] = profile.LandingPositionAmount,
            ["LandingRotationAmount"] = profile.LandingRotationAmount,
            ["SwayFollowSpeed"] = profile.SwayFollowSpeed,
            ["SwayReturnSpeed"] = profile.SwayReturnSpeed,
            ["ImpulseReturnSpeed"] = profile.ImpulseReturnSpeed,
            ["EnableRotationSmoothing"] = profile.EnableRotationSmoothing,
            ["RotationSmoothSpeed"] = profile.RotationSmoothSpeed,
            ["PositionSmoothSpeed"] = profile.PositionSmoothSpeed,
            ["EnableAimStabilization"] = profile.EnableAimStabilization,
            ["AimStabilizationStrength"] = profile.AimStabilizationStrength,
            ["AimStabilizationSmoothSpeed"] = profile.AimStabilizationSmoothSpeed,
            ["MaxAimCorrectionDegrees"] = profile.MaxAimCorrectionDegrees,
            ["AimStabilizationDeadZone"] = profile.AimStabilizationDeadZone,
            ["StabilizeOnlyWhenAiming"] = profile.StabilizeOnlyWhenAiming
        };
    }

    private static void DictionaryToProfile(Godot.Collections.Dictionary values, PlayerTuningProfile profile)
    {
        if (profile == null)
        {
            return;
        }

        profile.MoveSpeed = GetFloat(values, "MoveSpeed", profile.MoveSpeed);
        profile.GroundAcceleration = GetFloat(values, "GroundAcceleration", profile.GroundAcceleration);
        profile.GroundDeceleration = GetFloat(values, "GroundDeceleration", profile.GroundDeceleration);
        profile.EnableDirectionChangeAcceleration = GetBool(values, "EnableDirectionChangeAcceleration", profile.EnableDirectionChangeAcceleration);
        profile.GroundDirectionChangeAcceleration = GetFloat(values, "GroundDirectionChangeAcceleration", profile.GroundDirectionChangeAcceleration);
        profile.EnableCounterStrafeBoost = GetBool(values, "EnableCounterStrafeBoost", profile.EnableCounterStrafeBoost);
        profile.CounterStrafeBoost = GetFloat(values, "CounterStrafeBoost", profile.CounterStrafeBoost);
        profile.JumpVelocity = GetFloat(values, "JumpVelocity", profile.JumpVelocity);
        profile.EnableDoubleJump = GetBool(values, "EnableDoubleJump", profile.EnableDoubleJump);
        profile.DoubleJumpVelocityMultiplier = GetFloat(values, "DoubleJumpVelocityMultiplier", profile.DoubleJumpVelocityMultiplier);
        profile.EnableDoubleJumpRedirect = GetBool(values, "EnableDoubleJumpRedirect", profile.EnableDoubleJumpRedirect);
        profile.DoubleJumpRedirectSpeed = GetFloat(values, "DoubleJumpRedirectSpeed", profile.DoubleJumpRedirectSpeed);
        profile.RestoreDoubleJumpOnGrapple = GetBool(values, "RestoreDoubleJumpOnGrapple", profile.RestoreDoubleJumpOnGrapple);
        profile.CrouchSpeedMultiplier = GetFloat(values, "CrouchSpeedMultiplier", profile.CrouchSpeedMultiplier);
        profile.SlideInitialSpeed = GetFloat(values, "SlideInitialSpeed", profile.SlideInitialSpeed);
        profile.SlideDuration = GetFloat(values, "SlideDuration", profile.SlideDuration);
        profile.SlideCooldown = GetFloat(values, "SlideCooldown", profile.SlideCooldown);
        profile.SlideFriction = GetFloat(values, "SlideFriction", profile.SlideFriction);
        profile.SlideSteeringStrength = GetFloat(values, "SlideSteeringStrength", profile.SlideSteeringStrength);
        profile.EnableSlideExitBySpeed = GetBool(values, "EnableSlideExitBySpeed", profile.EnableSlideExitBySpeed);
        profile.SlideExitMinSpeed = GetFloat(values, "SlideExitMinSpeed", profile.SlideExitMinSpeed);
        profile.SlideExitMinSpeedGraceTime = GetFloat(values, "SlideExitMinSpeedGraceTime", profile.SlideExitMinSpeedGraceTime);
        profile.EnableAirborneSlideEntry = GetBool(values, "EnableAirborneSlideEntry", profile.EnableAirborneSlideEntry);
        profile.AirborneSlideMinSpeed = GetFloat(values, "AirborneSlideMinSpeed", profile.AirborneSlideMinSpeed);
        profile.AirborneSlideBufferTime = GetFloat(values, "AirborneSlideBufferTime", profile.AirborneSlideBufferTime);
        profile.AirborneSlideUseCurrentVelocityDirection = GetBool(values, "AirborneSlideUseCurrentVelocityDirection", profile.AirborneSlideUseCurrentVelocityDirection);
        profile.AirborneSlideUseInputDirectionIfAny = GetBool(values, "AirborneSlideUseInputDirectionIfAny", profile.AirborneSlideUseInputDirectionIfAny);
        profile.AirborneSlideInputMin = GetFloat(values, "AirborneSlideInputMin", profile.AirborneSlideInputMin);
        profile.EnableSlideJump = GetBool(values, "EnableSlideJump", profile.EnableSlideJump);
        profile.SlideJumpHorizontalBoost = GetFloat(values, "SlideJumpHorizontalBoost", profile.SlideJumpHorizontalBoost);
        profile.SlideJumpVelocityCarryFactor = GetFloat(values, "SlideJumpVelocityCarryFactor", profile.SlideJumpVelocityCarryFactor);
        profile.SlideJumpMaxHorizontalSpeed = GetFloat(values, "SlideJumpMaxHorizontalSpeed", profile.SlideJumpMaxHorizontalSpeed);
        profile.SlideJumpRequiresStandUpSpace = GetBool(values, "SlideJumpRequiresStandUpSpace", profile.SlideJumpRequiresStandUpSpace);
        profile.MaxGrappleDistance = GetFloat(values, "MaxGrappleDistance", profile.MaxGrappleDistance);
        profile.EnableScreenSpaceGrappleAssist = GetBool(values, "EnableScreenSpaceGrappleAssist", profile.EnableScreenSpaceGrappleAssist);
        profile.GrappleScreenAssistRadiusPixels = GetFloat(values, "GrappleScreenAssistRadiusPixels", profile.GrappleScreenAssistRadiusPixels);
        profile.PreferDirectRaycastHit = GetBool(values, "PreferDirectRaycastHit", profile.PreferDirectRaycastHit);
        profile.GrappleAssistMaxAngleDegrees = GetFloat(values, "GrappleAssistMaxAngleDegrees", profile.GrappleAssistMaxAngleDegrees);
        profile.GrappleAssistRequireLineOfSight = GetBool(values, "GrappleAssistRequireLineOfSight", profile.GrappleAssistRequireLineOfSight);
        profile.GrappleAssistDistanceWeight = GetFloat(values, "GrappleAssistDistanceWeight", profile.GrappleAssistDistanceWeight);
        profile.GrappleAssistScreenDistanceWeight = GetFloat(values, "GrappleAssistScreenDistanceWeight", profile.GrappleAssistScreenDistanceWeight);
        profile.EnableGrappleCameraSnap = GetBool(values, "EnableGrappleCameraSnap", profile.EnableGrappleCameraSnap);
        profile.GrappleCameraSnapDuration = GetFloat(values, "GrappleCameraSnapDuration", profile.GrappleCameraSnapDuration);
        profile.GrappleCameraSnapStrength = GetFloat(values, "GrappleCameraSnapStrength", profile.GrappleCameraSnapStrength);
        profile.GrappleCameraSnapSpeed = GetFloat(values, "GrappleCameraSnapSpeed", profile.GrappleCameraSnapSpeed);
        profile.LockLookInputDuringGrappleSnap = GetBool(values, "LockLookInputDuringGrappleSnap", profile.LockLookInputDuringGrappleSnap);
        profile.GrappleCameraSnapMaxPitchDegrees = GetFloat(values, "GrappleCameraSnapMaxPitchDegrees", profile.GrappleCameraSnapMaxPitchDegrees);
        profile.EnableGrappleAvailableHighlight = GetBool(values, "EnableGrappleAvailableHighlight", profile.EnableGrappleAvailableHighlight);
        profile.GrappleHighlightOnlyBestAnchor = GetBool(values, "GrappleHighlightOnlyBestAnchor", profile.GrappleHighlightOnlyBestAnchor);
        profile.PullAcceleration = GetFloat(values, "PullAcceleration", profile.PullAcceleration);
        profile.MaxPullSpeed = GetFloat(values, "MaxPullSpeed", profile.MaxPullSpeed);
        profile.LaunchSpeed = GetFloat(values, "LaunchSpeed", profile.LaunchSpeed);
        profile.InheritPullVelocityFactor = GetFloat(values, "InheritPullVelocityFactor", profile.InheritPullVelocityFactor);
        profile.MaxLaunchVelocity = GetFloat(values, "MaxLaunchVelocity", profile.MaxLaunchVelocity);
        profile.LightShotSpeed = GetFloat(values, "LightShotSpeed", profile.LightShotSpeed);
        profile.ChargedShotSpeed = GetFloat(values, "ChargedShotSpeed", profile.ChargedShotSpeed);
        profile.EnablePrecisionShot = GetBool(values, "EnablePrecisionShot", profile.EnablePrecisionShot);
        profile.PrecisionShotSpeed = GetFloat(values, "PrecisionShotSpeed", profile.PrecisionShotSpeed);
        profile.PrecisionShotDamage = GetFloat(values, "PrecisionShotDamage", profile.PrecisionShotDamage);
        profile.PrecisionShotArmorPiercing = GetBool(values, "PrecisionShotArmorPiercing", profile.PrecisionShotArmorPiercing);
        profile.ProjectileGravity = GetFloat(values, "ProjectileGravity", profile.ProjectileGravity);
        profile.PlayerFov = GetFloat(values, "PlayerFov", profile.PlayerFov);
        profile.PrecisionFov = GetFloat(values, "PrecisionFov", profile.PrecisionFov);
        profile.FovTransitionSpeed = GetFloat(values, "FovTransitionSpeed", profile.FovTransitionSpeed);
        profile.EnableSpeedFov = GetBool(values, "EnableSpeedFov", profile.EnableSpeedFov);
        profile.SpeedFovMultiplier = GetFloat(values, "SpeedFovMultiplier", profile.SpeedFovMultiplier);
        profile.MinSpeedForFov = GetFloat(values, "MinSpeedForFov", profile.MinSpeedForFov);
        profile.MaxSpeedFovBonus = GetFloat(values, "MaxSpeedFovBonus", profile.MaxSpeedFovBonus);
        profile.SpeedFovSmoothUp = GetFloat(values, "SpeedFovSmoothUp", profile.SpeedFovSmoothUp);
        profile.SpeedFovSmoothDown = GetFloat(values, "SpeedFovSmoothDown", profile.SpeedFovSmoothDown);
        profile.UseFullVelocityForSpeedFov = GetBool(values, "UseFullVelocityForSpeedFov", profile.UseFullVelocityForSpeedFov);
        profile.DisableSpeedFovDuringPrecisionAim = GetBool(values, "DisableSpeedFovDuringPrecisionAim", profile.DisableSpeedFovDuringPrecisionAim);
        profile.UseAxisBasedSpeedFov = GetBool(values, "UseAxisBasedSpeedFov", profile.UseAxisBasedSpeedFov);
        profile.StrafeSpeedFovMultiplier = GetFloat(values, "StrafeSpeedFovMultiplier", profile.StrafeSpeedFovMultiplier);
        profile.MinStrafeSpeedForFov = GetFloat(values, "MinStrafeSpeedForFov", profile.MinStrafeSpeedForFov);
        profile.IncludeBackwardSpeedInForwardFov = GetBool(values, "IncludeBackwardSpeedInForwardFov", profile.IncludeBackwardSpeedInForwardFov);
        profile.EnableViewModelSway = GetBool(values, "EnableViewModelSway", profile.EnableViewModelSway);
        profile.EnableMouseLag = GetBool(values, "EnableMouseLag", profile.EnableMouseLag);
        profile.MouseLagPositionAmount = GetFloat(values, "MouseLagPositionAmount", profile.MouseLagPositionAmount);
        profile.MouseLagRotationAmount = GetFloat(values, "MouseLagRotationAmount", profile.MouseLagRotationAmount);
        profile.EnableMouseLagSmoothing = GetBool(values, "EnableMouseLagSmoothing", profile.EnableMouseLagSmoothing);
        profile.MouseLagInputSmoothSpeed = GetFloat(values, "MouseLagInputSmoothSpeed", profile.MouseLagInputSmoothSpeed);
        profile.MouseLagOutputSmoothSpeed = GetFloat(values, "MouseLagOutputSmoothSpeed", profile.MouseLagOutputSmoothSpeed);
        profile.EnableMovementInertia = GetBool(values, "EnableMovementInertia", profile.EnableMovementInertia);
        profile.MovementInertiaPositionAmount = GetFloat(values, "MovementInertiaPositionAmount", profile.MovementInertiaPositionAmount);
        profile.MovementInertiaRotationAmount = GetFloat(values, "MovementInertiaRotationAmount", profile.MovementInertiaRotationAmount);
        profile.EnableLandingSway = GetBool(values, "EnableLandingSway", profile.EnableLandingSway);
        profile.LandingPositionAmount = GetFloat(values, "LandingPositionAmount", profile.LandingPositionAmount);
        profile.LandingRotationAmount = GetFloat(values, "LandingRotationAmount", profile.LandingRotationAmount);
        profile.SwayFollowSpeed = GetFloat(values, "SwayFollowSpeed", profile.SwayFollowSpeed);
        profile.SwayReturnSpeed = GetFloat(values, "SwayReturnSpeed", profile.SwayReturnSpeed);
        profile.ImpulseReturnSpeed = GetFloat(values, "ImpulseReturnSpeed", profile.ImpulseReturnSpeed);
        profile.EnableRotationSmoothing = GetBool(values, "EnableRotationSmoothing", profile.EnableRotationSmoothing);
        profile.RotationSmoothSpeed = GetFloat(values, "RotationSmoothSpeed", profile.RotationSmoothSpeed);
        profile.PositionSmoothSpeed = GetFloat(values, "PositionSmoothSpeed", profile.PositionSmoothSpeed);
        profile.EnableAimStabilization = GetBool(values, "EnableAimStabilization", profile.EnableAimStabilization);
        profile.AimStabilizationStrength = GetFloat(values, "AimStabilizationStrength", profile.AimStabilizationStrength);
        profile.AimStabilizationSmoothSpeed = GetFloat(values, "AimStabilizationSmoothSpeed", profile.AimStabilizationSmoothSpeed);
        profile.MaxAimCorrectionDegrees = GetFloat(values, "MaxAimCorrectionDegrees", profile.MaxAimCorrectionDegrees);
        profile.AimStabilizationDeadZone = GetFloat(values, "AimStabilizationDeadZone", profile.AimStabilizationDeadZone);
        profile.StabilizeOnlyWhenAiming = GetBool(values, "StabilizeOnlyWhenAiming", profile.StabilizeOnlyWhenAiming);
    }

    private static void CopyProfile(PlayerTuningProfile source, PlayerTuningProfile target)
    {
        DictionaryToProfile(ProfileToDictionary(source), target);
    }

    private static float GetFloat(Godot.Collections.Dictionary values, string key, float fallback)
    {
        return values.TryGetValue(key, out Variant value) ? (float)value.AsDouble() : fallback;
    }

    private static bool GetBool(Godot.Collections.Dictionary values, string key, bool fallback)
    {
        return values.TryGetValue(key, out Variant value) ? value.AsBool() : fallback;
    }
}
