using Godot;
using System;

public partial class PlayerBowShootModule : Node
{
    private enum BowShotState
    {
        Idle,
        Drawing,
        Charged,
        Released
    }

    private const string FireAction = "fire";
    private const string PrecisionModifierAction = "precision_modifier";

    /// <summary>
    /// Сцена projectile-стрелы, создаваемая при выстреле. Если не назначить сцену, модуль не сможет выпустить стрелу.
    /// </summary>
    [ExportGroup("Ссылки")]
    [Export] public PackedScene ArrowProjectileScene { get; set; }
    [Export] public PackedScene PresentedArrowScene { get; set; }

    /// <summary>
    /// Путь к камере, задающей направление выстрела. Смена пути меняет источник направления; неверный путь заставит модуль использовать камеру игрока как fallback.
    /// </summary>
    [Export] public NodePath CameraPath { get; set; } = new("../CameraPivot/Camera3D");

    /// <summary>
    /// Путь к точке появления projectile-стрелы. Смена пути меняет место спавна; неверный путь заставит модуль использовать камеру.
    /// </summary>
    [Export] public NodePath ShootPointPath { get; set; } = new("../CameraPivot/Camera3D/ShootPoint");

    [ExportGroup("Управление луком")]
    [Export] public Key ManageBowKey { get; set; } = Key.None;

    /// <summary>
    /// Скорость лёгкого выстрела без полного натяжения. Увеличение делает быструю стрелу быстрее и прямее; уменьшение делает её медленнее.
    /// </summary>
    [ExportGroup("Лёгкий выстрел")]
    [Export(PropertyHint.Range, "0,200,0.5,suffix:m/s")] public float LightShotSpeed { get; set; } = 50.0f;

    /// <summary>
    /// Урон лёгкого выстрела. Увеличение усиливает быстрый выстрел; уменьшение делает его слабее относительно заряженного.
    /// </summary>
    [Export(PropertyHint.Range, "0,100,1")] public float LightShotDamage { get; set; } = 8.0f;

    /// <summary>
    /// Скорость полностью заряженного выстрела. Увеличение делает charged shot быстрее и прямее; уменьшение сближает его с лёгким выстрелом.
    /// </summary>
    [ExportGroup("Заряженный выстрел")]
    [Export(PropertyHint.Range, "0,200,0.5,suffix:m/s")] public float ChargedShotSpeed { get; set; } = 100.0f;

    /// <summary>
    /// Урон полностью заряженного выстрела. Увеличение сильнее награждает полное натяжение; уменьшение снижает разницу между типами выстрела.
    /// </summary>
    [Export(PropertyHint.Range, "0,200,1")] public float ChargedShotDamage { get; set; } = 24.0f;

    /// <summary>
    /// Время до полного натяжения лука для обычного charged shot. Увеличение делает зарядку дольше; уменьшение быстрее переводит выстрел в charged shot.
    /// </summary>
    [ExportGroup("Тайминги")]
    [Export(PropertyHint.Range, "0.05,5,0.01,suffix:s")] public float ChargeTime { get; set; } = 0.8f;

    /// <summary>
    /// Включает мгновенный precision shot по комбинации Alt + ЛКМ. Если выключить, Alt + ЛКМ не создаст straight projectile, а обычная ЛКМ продолжит работать как light/charged shot.
    /// </summary>
    [ExportGroup("Precision Shot")]
    [Export] public bool EnablePrecisionShot { get; set; } = true;

    /// <summary>
    /// Скорость precision straight shot. Увеличение делает Alt + ЛКМ ещё более мгновенным и прямым; уменьшение сильнее отличает его от charged shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,300,1,suffix:m/s")] public float PrecisionShotSpeed { get; set; } = 180.0f;

    /// <summary>
    /// Урон мгновенного precision straight shot. Увеличение делает Alt + ЛКМ мощнее; уменьшение сближает его по силе с обычным charged shot.
    /// </summary>
    [Export(PropertyHint.Range, "0,400,1")] public float PrecisionShotDamage { get; set; } = 60.0f;

    /// <summary>
    /// Помечает precision shot как бронебойный. Если выключить, precision projectile остаётся прямым, но без armor-piercing метки.
    /// </summary>
    [Export] public bool PrecisionShotArmorPiercing { get; set; } = true;

    /// <summary>
    /// Минимальная пауза между выстрелами. Увеличение снижает скорострельность; уменьшение позволяет стрелять чаще.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.01,suffix:s")] public float FireCooldown { get; set; } = 0.2f;

    /// <summary>
    /// Время жизни созданной projectile-стрелы. Увеличение позволяет стреле лететь дольше; уменьшение быстрее удаляет её из сцены.
    /// </summary>
    [Export(PropertyHint.Range, "0.1,30,0.1,suffix:s")] public float ProjectileLifetime { get; set; } = 5.0f;

    /// <summary>
    /// Смещение точки появления стрелы вперёд по направлению выстрела. Увеличение отодвигает спавн от камеры; уменьшение приближает его к ShootPoint.
    /// </summary>
    [ExportGroup("Спавн projectile")]
    [Export(PropertyHint.Range, "0,2,0.01,suffix:m")] public float SpawnForwardOffset { get; set; } = 0.35f;

    /// <summary>
    /// Гравитация созданной ballistic projectile-стрелы. Если активен TuningProfile, значение берётся из профиля; без профиля это локальный fallback.
    /// </summary>
    [ExportGroup("Projectile Tuning")]
    [Export(PropertyHint.Range, "0,80,0.5,suffix:m/s^2")] public float ProjectileGravity { get; set; } = 18.0f;

    private PlayerController _player;
    private Camera3D _camera;
    private Node3D _shootPoint;
    private PlayerBowVisualModule _bowVisualModule;
    private PlayerCameraFovModule _cameraFovModule;
    private BowShotState _shotState = BowShotState.Idle;
    private bool _isHoldingFire;
    private bool _isPrecisionReady;
    private float _holdTime;
    private float _cooldownRemaining;
    private bool _ignoreHeldPress;
    private bool _canceledRelease;
    private PresentedPose? _pressPose;
    private PresentedPose? _releasePose;
    private Func<Transform3D?> _presentedArrowFrame;

    // The optional first-person presenter supplies the last displayed nock pose.
    // It observes these edges and never creates a projectile itself.
    public Func<Transform3D?> PresentedArrowFrame
    {
        get => _presentedArrowFrame;
        set
        {
            _presentedArrowFrame = value;
            ClearInputPoses();
        }
    }
    public event Action DrawBegan;
    public event Action DrawCanceled;
    public event Action<float, bool> ShotReleased;
    public event Action<bool> EquippedChanged;
    public bool IsEquipped { get; private set; } = true;
    public bool IsDrawing => _isHoldingFire;
    public float DrawAmount => _isHoldingFire ? Mathf.Clamp(_holdTime / Mathf.Max(0.001f, ChargeTime), 0f, 1f) : 0f;

    /// <summary>
    /// Активна ли precision-стойка от зажатого Alt. Когда true, визуал лука и FOV переходят в precision-ready состояние, но сам выстрел всё равно требует нового нажатия ЛКМ.
    /// </summary>
    public bool IsPrecisionReady => _isPrecisionReady;

    public void Initialize(PlayerController player)
    {
        EnsureInputActions();

        _player = player;
        _camera = GetNodeOrNull<Camera3D>(CameraPath) ?? _player.Camera;
        _shootPoint = GetNodeOrNull<Node3D>(ShootPointPath) ?? _camera?.GetNodeOrNull<Node3D>("ShootPoint") ?? _camera;
        _bowVisualModule = _player.BowVisualModule;
        _cameraFovModule = _player.CameraFovModule;
        SetProcessInput(ManageBowKey != Key.None || PresentedArrowScene != null);
    }

    public override void _Input(InputEvent input)
        => HandlePresentationInput(input, Input.MouseMode == Input.MouseModeEnum.Captured);

    private void HandlePresentationInput(InputEvent input, bool hasControl)
    {
        if (_ignoreHeldPress && input.IsActionReleased(FireAction))
        {
            // The canceled up-edge and a fresh down-edge can share one poll.
            _canceledRelease = true;
            return;
        }
        if (_ignoreHeldPress && input.IsActionPressed(FireAction))
            _ignoreHeldPress = false;

        if (!hasControl)
            return;
        if (IsEquipped && !_ignoreHeldPress && PresentedArrowScene != null && PresentedArrowFrame != null)
        {
            // Polling still owns acceptance. Keep press and release separately
            // because a quick click can put both edges in a single render tick.
            if (input.IsActionPressed(FireAction))
                _pressPose = ReadPresentedPose();
            else if (input.IsActionReleased(FireAction))
            {
                _canceledRelease = false;
                _releasePose = ReadPresentedPose();
            }
        }
        if (ManageBowKey == Key.None || input is not InputEventKey key || !key.Pressed || key.Echo)
            return;
        Key code = key.PhysicalKeycode != Key.None ? key.PhysicalKeycode : key.Keycode;
        if (code != ManageBowKey)
            return;

        ClearInputPoses();
        bool held = Input.IsActionPressed(FireAction);
        _ignoreHeldPress = held;
        if (IsEquipped && (_isHoldingFire || held))
        {
            if (_isHoldingFire)
                CancelShot();
        }
        else
        {
            IsEquipped = !IsEquipped;
            UpdatePrecisionReadyState(CanUsePrecisionReady(), true);
            EquippedChanged?.Invoke(IsEquipped);
        }
        GetViewport().SetInputAsHandled();
    }

    public override void _Notification(int what)
    {
        if ((what != NotificationWMWindowFocusOut && what != NotificationPaused) ||
            (ManageBowKey == Key.None && PresentedArrowScene == null))
            return;
        ClearInputPoses();
        if (_isHoldingFire)
            CancelShot();
    }

    public override void _Process(double delta)
    {
        AdvanceInput((float)delta, Input.MouseMode == Input.MouseModeEnum.Captured);
        ClearInputPoses();
    }

    private void AdvanceInput(float deltaTime, bool canUseGameplayInput)
    {
        _cooldownRemaining = Mathf.Max(0.0f, _cooldownRemaining - deltaTime);
        UpdatePrecisionReadyState(IsEquipped && canUseGameplayInput && CurrentEnablePrecisionShot && Input.IsActionPressed(PrecisionModifierAction));

        if (_isHoldingFire && !canUseGameplayInput)
        {
            CancelShot();
            return;
        }

        if (!canUseGameplayInput || !IsEquipped)
        {
            return;
        }

        if (_player.AbilityStateModule?.IsLocked(PlayerAbilityLock.Shooting) == true)
        {
            if (_isHoldingFire)
            {
                CancelShot();
            }

            return;
        }

        if (_ignoreHeldPress)
        {
            if (!Input.IsActionPressed(FireAction))
                _ignoreHeldPress = false;
            return;
        }

        bool pressed = Input.IsActionJustPressed(FireAction);
        bool held = Input.IsActionPressed(FireAction);
        bool released = Input.IsActionJustReleased(FireAction) && !_canceledRelease;
        // The previous draw can finish and a new native press arrive between
        // consecutive render ticks. Finish the old charge before resetting it.
        bool releasedBeforePress = _isHoldingFire && pressed && held && released &&
            _releasePose.HasValue && _pressPose.HasValue;
        if (releasedBeforePress)
            ReleaseShot();
        if (pressed)
        {
            if (_isPrecisionReady)
            {
                FireInstantPrecisionShot();
            }
            else
            {
                BeginDraw();
            }
        }

        if (_isHoldingFire && held)
        {
            UpdateDraw(deltaTime);
        }

        if (_isHoldingFire && released && !releasedBeforePress)
        {
            ReleaseShot();
        }
    }

    private void BeginDraw()
    {
        _isHoldingFire = true;
        _holdTime = 0.0f;
        _shotState = BowShotState.Drawing;
        UpdatePrecisionReadyState(CanUsePrecisionReady(), true);
        DrawBegan?.Invoke();
    }

    private void UpdateDraw(float deltaTime)
    {
        _holdTime += deltaTime;
        _bowVisualModule?.SetDrawAmount(DrawAmount);

        if (_holdTime >= ChargeTime && _shotState == BowShotState.Drawing)
        {
            _shotState = BowShotState.Charged;
        }
    }

    private void ReleaseShot()
    {
        _shotState = BowShotState.Released;

        float amount = DrawAmount;
        bool chargedShot = _holdTime >= ChargeTime;
        if (!Fire(GetShotConfig(chargedShot)))
        {
            CancelShot();
            return;
        }

        _bowVisualModule?.HandleShotVisual();
        ResetShotState();
        ShotReleased?.Invoke(amount, false);
    }

    private void FireInstantPrecisionShot()
    {
        _isHoldingFire = false;
        _holdTime = 0.0f;
        _shotState = BowShotState.Released;
        UpdatePrecisionReadyState(CanUsePrecisionReady(), true);

        bool shotFired = Fire(GetPrecisionShotConfig());
        if (shotFired)
        {
            _bowVisualModule?.HandleShotVisual();
        }
        else
        {
            _bowVisualModule?.ResetDraw();
        }

        ResetShotState();
        if (shotFired)
            ShotReleased?.Invoke(1f, true);
    }

    private void CancelShot()
    {
        ClearInputPoses();
        _bowVisualModule?.ResetDraw();
        ResetShotState();
        DrawCanceled?.Invoke();
    }

    private ShotConfig GetShotConfig(bool chargedShot)
    {
        if (chargedShot)
        {
            return new ShotConfig(CurrentChargedShotSpeed, ChargedShotDamage, ArrowFlightMode.Ballistic, false);
        }

        return new ShotConfig(CurrentLightShotSpeed, LightShotDamage, ArrowFlightMode.Ballistic, false);
    }

    private ShotConfig GetPrecisionShotConfig()
    {
        return new ShotConfig(CurrentPrecisionShotSpeed, CurrentPrecisionShotDamage, ArrowFlightMode.Straight, CurrentPrecisionShotArmorPiercing);
    }

    private bool Fire(ShotConfig shotConfig)
    {
        if (_player.AbilityStateModule?.IsLocked(PlayerAbilityLock.Shooting) == true)
        {
            return false;
        }

        if (_cooldownRemaining > 0.0f || _camera == null || !IsEquipped)
        {
            return false;
        }

        // Missing native events (e.g. programmatic Input.ActionPress) sample
        // on acceptance. A native event captured in external view stays there.
        PresentedPose? pose = shotConfig.FlightMode == ArrowFlightMode.Straight ? _pressPose : _releasePose;
        pose ??= ReadPresentedPose();
        Transform3D? displayed = pose?.Nock;
        PackedScene scene = displayed.HasValue ? PresentedArrowScene : ArrowProjectileScene;
        if (scene == null)
            return false;
        ArrowProjectile projectile = scene.Instantiate<ArrowProjectile>();
        projectile.ProjectileGravity = CurrentProjectileGravity;
        GetTree().CurrentScene.AddChild(projectile);

        Vector3 shootDirection;
        if (displayed is Transform3D nock)
        {
            shootDirection = -nock.Basis.Z.Normalized();
            projectile.SetPresentedLaunch(nock, pose.Value.Eye, _player.GetRid());
        }
        else
        {
            shootDirection = -_camera.GlobalTransform.Basis.Z.Normalized();
            projectile.GlobalPosition = (_shootPoint ?? _camera).GlobalPosition + shootDirection * SpawnForwardOffset;
        }

        // Gameplay rule: arrows use only aim direction and shot speed, never player velocity.
        projectile.Initialize(
            shootDirection,
            shotConfig.Speed,
            shotConfig.Damage,
            ProjectileLifetime,
            shotConfig.FlightMode,
            shotConfig.ArmorPiercing
        );

        _cooldownRemaining = FireCooldown;
        return true;
    }

    private PresentedPose? ReadPresentedPose()
    {
        if (PresentedArrowScene == null || PresentedArrowFrame == null || _camera == null)
            return null;
        return new PresentedPose(PresentedArrowFrame(), _camera.GetCameraTransform().Origin);
    }

    private void ClearInputPoses()
    {
        _pressPose = null;
        _releasePose = null;
        _canceledRelease = false;
    }

    private readonly record struct PresentedPose(Transform3D? Nock, Vector3 Eye);

    private void ResetShotState()
    {
        _isHoldingFire = false;
        _holdTime = 0.0f;
        _shotState = BowShotState.Idle;
        UpdatePrecisionReadyState(CanUsePrecisionReady(), true);
    }

    private PlayerTuningProfile TuningProfile => _player?.ActiveTuningProfile;
    private bool CurrentEnablePrecisionShot => TuningProfile?.EnablePrecisionShot ?? EnablePrecisionShot;
    private float CurrentLightShotSpeed => TuningProfile?.LightShotSpeed ?? LightShotSpeed;
    private float CurrentChargedShotSpeed => TuningProfile?.ChargedShotSpeed ?? ChargedShotSpeed;
    private float CurrentPrecisionShotSpeed => TuningProfile?.PrecisionShotSpeed ?? PrecisionShotSpeed;
    private float CurrentPrecisionShotDamage => TuningProfile?.PrecisionShotDamage ?? PrecisionShotDamage;
    private bool CurrentPrecisionShotArmorPiercing => TuningProfile?.PrecisionShotArmorPiercing ?? PrecisionShotArmorPiercing;
    private float CurrentProjectileGravity => TuningProfile?.ProjectileGravity ?? ProjectileGravity;

    private bool CanUsePrecisionReady()
    {
        return IsEquipped && Input.MouseMode == Input.MouseModeEnum.Captured && CurrentEnablePrecisionShot && Input.IsActionPressed(PrecisionModifierAction);
    }

    private void UpdatePrecisionReadyState(bool isPrecisionReady, bool forceApply = false)
    {
        if (!forceApply && _isPrecisionReady == isPrecisionReady)
        {
            return;
        }

        _isPrecisionReady = isPrecisionReady;
        _bowVisualModule?.SetPrecisionAiming(_isPrecisionReady);
        _cameraFovModule?.SetPrecisionAiming(_isPrecisionReady);
    }

    private static void EnsureInputActions()
    {
        EnsureKeyAction(PrecisionModifierAction, Key.Alt);
    }

    private static void EnsureKeyAction(string actionName, Key key)
    {
        if (!InputMap.HasAction(actionName))
        {
            InputMap.AddAction(actionName);
        }

        InputEventKey keyEvent = new()
        {
            Keycode = key,
            PhysicalKeycode = key
        };

        if (!InputMap.ActionHasEvent(actionName, keyEvent))
        {
            InputMap.ActionAddEvent(actionName, keyEvent);
        }
    }

    private readonly struct ShotConfig
    {
        public ShotConfig(float speed, float damage, ArrowFlightMode flightMode, bool armorPiercing)
        {
            Speed = speed;
            Damage = damage;
            FlightMode = flightMode;
            ArmorPiercing = armorPiercing;
        }

        public float Speed { get; }
        public float Damage { get; }
        public ArrowFlightMode FlightMode { get; }
        public bool ArmorPiercing { get; }
    }
}
