using Godot;

// Slide-only presentation, beside SwayRoot in the existing viewmodel viewport.
// Reads ability state and body yaw; never writes Player, camera, velocity or collision.
public partial class FirstPersonSlideLegs : Node3D
{
    [ExportGroup("Slide Legs Composition")]
    [Export] public bool Enabled { get; set; } = true;
    [Export] public Vector3 SlidePosition { get; set; } = new(0, -0.90f, -2.0f);
    [Export(PropertyHint.Range, "0.5,1.5,0.05")] public float VisualScale { get; set; } = 1;
    [Export(PropertyHint.Range, "0,0.3,0.01,suffix:m")] public float EntryDrop { get; set; } = 0.15f;
    [Export(PropertyHint.Range, "0.02,0.2,0.01,suffix:s")] public float EntrySeconds { get; set; } = 0.07f;

    // Retained for serialized Inspector compatibility with the earlier input-driven pass.
    [ExportGroup("Legacy Input Yaw (unused)")]
    [Export(PropertyHint.Range, "5,40,1,suffix:/s")] public float TurnResponse { get; set; } = 18;
    [Export(PropertyHint.Range, "0.01,0.5,0.01")] public float InputDeadzone { get; set; } = 0.12f;

    public float TargetYawDegrees => Mathf.RadToDeg(_targetYaw);
    public float VisualYawDegrees => Mathf.RadToDeg(_yaw);
    public Vector3 LockedWorldDirection { get; private set; }
    public Vector2 CameraLocalDirection { get; private set; }
    // Older external audit drivers read this name. It is now local heading, not input.
    public Vector2 LastIntent => CameraLocalDirection;

    private PlayerController _player;
    private float _targetYaw, _yaw, _entry;
    private bool _wasSliding;

    public override void _Ready()
    {
        ProcessPriority = 25;
        // Observe every successful physics transition, after PlayerController updates.
        ProcessPhysicsPriority = 25;
        Visible = false;
        // Resolve our own player through ancestry, including the SubViewport.
        for (Node node = GetParent(); node != null; node = node.GetParent())
            if (node is PlayerController player) { _player = player; break; }
        // This SubViewport's camera is fixed at its origin. Keep the slide body
        // in that visual space, independent of any ancestor pitch/pose offsets.
        TopLevel = true;
    }

    public override void _PhysicsProcess(double delta)
    {
        var slide = _player?.CrouchSlideModule;
        bool sliding = slide?.IsSliding == true;
        if (sliding && !_wasSliding)
        {
            Vector3 direction = slide.SlideDirection;
            direction.Y = 0;
            if (direction.IsZeroApprox())
                direction = new Vector3(_player.Velocity.X, 0, _player.Velocity.Z);
            LockedWorldDirection = direction.Normalized();
            _entry = 0;
        }
        else if (!sliding)
        {
            LockedWorldDirection = Vector3.Zero;
            CameraLocalDirection = Vector2.Zero;
            _targetYaw = _yaw = _entry = 0;
            Visible = false;
        }
        // Track ability lifetime, not visibility: losing floor contact must not recapture.
        _wasSliding = sliding;
    }

    public override void _Process(double delta)
    {
        var grapple = _player?.SlingshotGrappleModule;
        bool sliding = Enabled && _wasSliding && !LockedWorldDirection.IsZeroApprox()
            // Airborne slide entry exists; this layer needs actual floor contact.
            && _player.IsOnFloor()
            && _player.WallRunModule?.IsWallRunning != true
            && grapple?.IsSlingshotActive != true && grapple?.IsNormalMovementBlocked != true;
        Visible = sliding;
        if (!sliding) { _entry = 0; return; }

        // MouseLook's yaw carrier is Player; camera pitch/roll are child pivots.
        // Build a horizontal frame from its right axis rather than camera forward,
        // which collapses at vertical pitch. Never project through a full 3D basis.
        Vector3 right = _player.GlobalBasis.X;
        right.Y = 0;
        right = right.Normalized();
        Vector3 forward = Vector3.Up.Cross(right);
        CameraLocalDirection = new Vector2(LockedWorldDirection.Dot(right),
            -LockedWorldDirection.Dot(forward)).Normalized();
        _targetYaw = Mathf.Atan2(-CameraLocalDirection.X, -CameraLocalDirection.Y);
        // Camera counter-rotation must be exact: smoothing here would rotate the
        // apparent world heading whenever the player turns their head.
        _yaw = _targetYaw;
        float dt = (float)delta;
        _entry = Mathf.MoveToward(_entry, 1, dt / Mathf.Max(EntrySeconds, 0.001f));
        float entry = _entry * _entry * (3 - 2 * _entry);
        Transform = new Transform3D(new Basis(Vector3.Up, _yaw).Scaled(Vector3.One * VisualScale),
            SlidePosition + Vector3.Down * (EntryDrop * (1 - entry)));
    }
}
