using Godot;

public partial class PlayerBowVisualModule : Node
{
    /// <summary>
    /// Путь к AnimationPlayer внутри bow viewmodel. Смена пути выбирает другой источник анимаций; неверный путь заставит модуль искать AnimationPlayer в потомках камеры.
    /// </summary>
    [ExportGroup("Анимации лука")]
    [Export] public NodePath AnimationPlayerPath { get; set; } = new("../CameraPivot/Camera3D/BowViewModelHolder/Bow_ViewModel/AnimationPlayer");

    /// <summary>
    /// Имя анимации натяжения лука. Смена имени позволяет использовать другую Draw-анимацию; неверное имя отключит визуальное натяжение.
    /// </summary>
    [Export] public string DrawAnimationName { get; set; } = "Draw";

    /// <summary>
    /// Имя анимации отпускания тетивы. Смена имени позволяет использовать отдельную Release-анимацию; неверное имя отключит release playback.
    /// </summary>
    [Export] public string ReleaseAnimationName { get; set; } = "Release";

    /// <summary>
    /// Включает проигрывание Release-анимации после выстрела. Если выключить, визуал лука просто плавно вернётся из Draw-состояния.
    /// </summary>
    [Export] public bool UseReleaseAnimation { get; set; } = false;

    /// <summary>
    /// Путь к визуальной стреле в bow viewmodel. Смена пути выбирает другую декоративную стрелу; неверный путь заставит модуль искать узел Arrow_Visual.
    /// </summary>
    [ExportGroup("Визуальная стрела")]
    [Export] public NodePath ArrowVisualPath { get; set; } = new("../CameraPivot/Camera3D/BowViewModelHolder/Bow_ViewModel/BowRig/NockPoint_Bone/Arrow_Bone/Arrow_Visual");

    /// <summary>
    /// Скрывает визуальную стрелу сразу после выстрела. Если выключить, стрела в луке останется видимой даже во время создания projectile-стрелы.
    /// </summary>
    [Export] public bool HideArrowOnShot { get; set; } = true;

    /// <summary>
    /// Задержка перед повторным показом визуальной стрелы после выстрела. Увеличение дольше скрывает стрелу; уменьшение быстрее возвращает её в лук.
    /// </summary>
    [Export(PropertyHint.Range, "0,2,0.01,suffix:s")] public float ArrowShowDelay { get; set; } = 0.15f;

    /// <summary>
    /// Скорость плавного возврата Draw-анимации к ненатянутому состоянию. Увеличение быстрее сбрасывает лук; уменьшение делает возврат мягче и медленнее.
    /// </summary>
    [ExportGroup("Возврат натяжения")]
    [Export(PropertyHint.Range, "0,30,0.1,suffix:/s")] public float DrawResetSpeed { get; set; } = 12.0f;

    private PlayerController _player;
    private AnimationPlayer _animationPlayer;
    private Node3D _arrowVisual;
    private float _drawAmount;
    private float _arrowShowTimer;
    private bool _isResettingDraw;
    private bool _warnedMissingAnimationPlayer;
    private bool _warnedMissingDrawAnimation;
    private bool _warnedMissingReleaseAnimation;

    public void Initialize(PlayerController player)
    {
        _player = player;
        _animationPlayer = GetNodeOrNull<AnimationPlayer>(AnimationPlayerPath) ?? FindFirstDescendant<AnimationPlayer>(_player.Camera);
        _arrowVisual = GetNodeOrNull<Node3D>(ArrowVisualPath) ?? FindNode3DByName(_player.Camera, "Arrow_Visual");

        if (_animationPlayer == null)
        {
            GD.PushWarning($"{nameof(PlayerBowVisualModule)} could not find AnimationPlayer at '{AnimationPlayerPath}'.");
            _warnedMissingAnimationPlayer = true;
        }
    }

    public override void _Process(double delta)
    {
        UpdateArrowVisibility((float)delta);
        UpdateDrawReset((float)delta);
    }

    public void SetDrawAmount(float amount)
    {
        _drawAmount = Mathf.Clamp(amount, 0.0f, 1.0f);
        _isResettingDraw = false;
        ApplyDrawAmount();
    }

    private void ApplyDrawAmount()
    {

        if (!CanUseDrawAnimation())
        {
            return;
        }

        Animation drawAnimation = _animationPlayer.GetAnimation(DrawAnimationName);
        double animationTime = drawAnimation.Length * _drawAmount;

        _animationPlayer.Play(DrawAnimationName);
        _animationPlayer.Seek(animationTime, true);
        _animationPlayer.Pause();
    }

    public void HandleShotVisual()
    {
        HideArrowVisualTemporarily();

        if (UseReleaseAnimation && CanUseReleaseAnimation())
        {
            _animationPlayer.Play(ReleaseAnimationName);
            _isResettingDraw = false;
            _drawAmount = 0.0f;
            return;
        }

        ResetDraw();
    }

    public void ResetDraw()
    {
        _isResettingDraw = true;
    }

    private void UpdateArrowVisibility(float delta)
    {
        if (_arrowShowTimer <= 0.0f)
        {
            return;
        }

        _arrowShowTimer -= delta;
        if (_arrowShowTimer <= 0.0f && _arrowVisual != null)
        {
            _arrowVisual.Visible = true;
        }
    }

    private void UpdateDrawReset(float delta)
    {
        if (!_isResettingDraw)
        {
            return;
        }

        if (DrawResetSpeed <= 0.0f)
        {
            _drawAmount = 0.0f;
            ApplyDrawAmount();
            _isResettingDraw = false;
            return;
        }

        float nextAmount = Mathf.MoveToward(_drawAmount, 0.0f, DrawResetSpeed * delta);
        _drawAmount = nextAmount;
        ApplyDrawAmount();

        if (Mathf.IsEqualApprox(_drawAmount, 0.0f))
        {
            _isResettingDraw = false;
        }
    }

    private void HideArrowVisualTemporarily()
    {
        if (!HideArrowOnShot || _arrowVisual == null)
        {
            return;
        }

        _arrowVisual.Visible = false;
        _arrowShowTimer = Mathf.Max(0.0f, ArrowShowDelay);
    }

    private bool CanUseDrawAnimation()
    {
        if (_animationPlayer == null)
        {
            if (!_warnedMissingAnimationPlayer)
            {
                GD.PushWarning($"{nameof(PlayerBowVisualModule)} cannot set draw amount because AnimationPlayer is missing.");
                _warnedMissingAnimationPlayer = true;
            }

            return false;
        }

        if (_animationPlayer.HasAnimation(DrawAnimationName))
        {
            return true;
        }

        if (!_warnedMissingDrawAnimation)
        {
            GD.PushWarning($"{nameof(PlayerBowVisualModule)} could not find draw animation '{DrawAnimationName}'.");
            _warnedMissingDrawAnimation = true;
        }

        return false;
    }

    private bool CanUseReleaseAnimation()
    {
        if (_animationPlayer == null)
        {
            if (!_warnedMissingAnimationPlayer)
            {
                GD.PushWarning($"{nameof(PlayerBowVisualModule)} cannot play release animation because AnimationPlayer is missing.");
                _warnedMissingAnimationPlayer = true;
            }

            return false;
        }

        if (_animationPlayer.HasAnimation(ReleaseAnimationName))
        {
            return true;
        }

        if (!_warnedMissingReleaseAnimation)
        {
            GD.PushWarning($"{nameof(PlayerBowVisualModule)} could not find release animation '{ReleaseAnimationName}'.");
            _warnedMissingReleaseAnimation = true;
        }

        return false;
    }

    private static T FindFirstDescendant<T>(Node root) where T : Node
    {
        if (root == null)
        {
            return null;
        }

        foreach (Node child in root.GetChildren())
        {
            if (child is T match)
            {
                return match;
            }

            T nestedMatch = FindFirstDescendant<T>(child);
            if (nestedMatch != null)
            {
                return nestedMatch;
            }
        }

        return null;
    }

    private static Node3D FindNode3DByName(Node root, string nodeName)
    {
        if (root == null)
        {
            return null;
        }

        foreach (Node child in root.GetChildren())
        {
            if (child is Node3D node3D && child.Name == nodeName)
            {
                return node3D;
            }

            Node3D nestedMatch = FindNode3DByName(child, nodeName);
            if (nestedMatch != null)
            {
                return nestedMatch;
            }
        }

        return null;
    }
}
