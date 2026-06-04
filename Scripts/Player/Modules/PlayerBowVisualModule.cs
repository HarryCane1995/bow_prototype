using Godot;

public partial class PlayerBowVisualModule : Node
{
    [Export] public NodePath AnimationPlayerPath { get; set; } = new("../CameraPivot/Camera3D/BowViewModelHolder/Bow_ViewModel/AnimationPlayer");
    [Export] public string DrawAnimationName { get; set; } = "Draw";
    [Export] public string ReleaseAnimationName { get; set; } = "Release";
    [Export] public bool UseReleaseAnimation { get; set; } = false;
    [Export] public NodePath ArrowVisualPath { get; set; } = new("../CameraPivot/Camera3D/BowViewModelHolder/Bow_ViewModel/BowRig/NockPoint_Bone/Arrow_Bone/Arrow_Visual");
    [Export] public bool HideArrowOnShot { get; set; } = true;
    [Export] public float ArrowShowDelay { get; set; } = 0.15f;
    [Export] public float DrawResetSpeed { get; set; } = 12.0f;

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
