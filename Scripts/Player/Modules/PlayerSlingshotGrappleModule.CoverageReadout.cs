using Godot;

public partial class PlayerSlingshotGrappleModule
{
    // Passive snapshot telemetry; no state writes or alternate acquisition rules.
    public Vector3 CoverageActivePoint => _grapplePointPosition;
}
