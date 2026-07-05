using Godot;
using System;
using System.Collections.Generic;

public partial class ImportedLevelMarkerBinder : Node
{
    private static readonly string[] SupportedMarkerNames =
    {
        "PlayerSpawn",
        "PlayerStart",
        "EnemySpawn",
        "GrappleAnchor",
        "KillPlane",
        "FinishTrigger"
    };

    [ExportGroup("Scene Links")]
    [Export] public NodePath ImportedLevelPath { get; set; } = new("../ImportedLevel");
    [Export] public NodePath PlayerPath { get; set; } = new("../Player");
    [Export] public NodePath WrapperSpawnPath { get; set; } = new("../PlayerSpawn");
    [Export] public NodePath GrappleAnchorsPath { get; set; } = new("GrappleAnchors");
    [Export] public NodePath FallbackCollisionShapePath { get; set; } = new("../Debug/TemporarySafetyFloor/CollisionShape3D");

    [ExportGroup("Gameplay Scenes")]
    [Export] public PackedScene GrappleAnchorScene { get; set; }

    [ExportGroup("Import Handling")]
    [Export] public bool DisableImportedLights { get; set; } = true;
    [Export] public bool EnableFallbackCollisionWhenImportHasNone { get; set; } = true;

    public override void _Ready()
    {
        CallDeferred(nameof(BindImportedMarkers));
    }

    private void BindImportedMarkers()
    {
        var importedLevel = GetNodeOrNull<Node>(ImportedLevelPath);
        if (importedLevel == null)
        {
            GD.PushWarning($"ImportedLevelMarkerBinder: imported level was not found at {ImportedLevelPath}.");
            return;
        }

        var markers = CollectMarkers(importedLevel);
        LogMarkers(markers);
        LogImportedMeshCount(importedLevel);
        DisableLightsIfRequested(importedLevel);
        EnsureCollisionFallback(importedLevel);
        PlacePlayer(markers);
        CreateGrappleAnchors(markers);
    }

    private static Dictionary<string, List<Node3D>> CollectMarkers(Node root)
    {
        var markers = new Dictionary<string, List<Node3D>>();
        foreach (string markerName in SupportedMarkerNames)
        {
            markers[markerName] = new List<Node3D>();
        }

        CollectMarkersRecursive(root, markers);
        return markers;
    }

    private static void CollectMarkersRecursive(Node node, Dictionary<string, List<Node3D>> markers)
    {
        if (node is Node3D node3D)
        {
            foreach (string markerName in SupportedMarkerNames)
            {
                if (IsMarkerName(node.Name, markerName))
                {
                    markers[markerName].Add(node3D);
                    break;
                }
            }
        }

        foreach (Node child in node.GetChildren())
        {
            CollectMarkersRecursive(child, markers);
        }
    }

    private static bool IsMarkerName(StringName nodeName, string markerName)
    {
        string name = nodeName.ToString();
        return string.Equals(name, markerName, StringComparison.OrdinalIgnoreCase)
            || name.StartsWith(markerName + "_", StringComparison.OrdinalIgnoreCase)
            || name.StartsWith(markerName + ".", StringComparison.OrdinalIgnoreCase);
    }

    private void LogMarkers(Dictionary<string, List<Node3D>> markers)
    {
        foreach ((string markerName, List<Node3D> nodes) in markers)
        {
            if (nodes.Count == 0)
            {
                GD.Print($"ImportedLevelMarkerBinder: marker {markerName} not found.");
                continue;
            }

            foreach (Node3D marker in nodes)
            {
                GD.Print($"ImportedLevelMarkerBinder: found {markerName} at {marker.GetPath()} -> {marker.GlobalPosition}.");
            }
        }
    }

    private void DisableLightsIfRequested(Node importedLevel)
    {
        var lights = new List<Light3D>();
        CollectNodesOfType(importedLevel, lights);

        if (lights.Count == 0)
        {
            GD.Print("ImportedLevelMarkerBinder: imported level contains no Light3D nodes.");
            return;
        }

        if (!DisableImportedLights)
        {
            GD.Print($"ImportedLevelMarkerBinder: preserved {lights.Count} imported Light3D node(s) because DisableImportedLights is false.");
            return;
        }

        foreach (Light3D light in lights)
        {
            light.Visible = false;
        }

        GD.Print($"ImportedLevelMarkerBinder: disabled {lights.Count} imported Light3D node(s) because DisableImportedLights is true.");
    }

    private static void LogImportedMeshCount(Node importedLevel)
    {
        var meshes = new List<MeshInstance3D>();
        CollectNodesOfType(importedLevel, meshes);

        if (meshes.Count == 0)
        {
            GD.PushWarning("ImportedLevelMarkerBinder: imported level contains no MeshInstance3D nodes. Check that the Blender/GLB source exports visible geometry.");
            return;
        }

        GD.Print($"ImportedLevelMarkerBinder: imported level contains {meshes.Count} MeshInstance3D node(s).");
    }

    private void EnsureCollisionFallback(Node importedLevel)
    {
        bool hasCollision = HasImportedCollision(importedLevel);
        var fallbackCollisionShape = GetNodeOrNull<CollisionShape3D>(FallbackCollisionShapePath);

        if (fallbackCollisionShape != null)
        {
            fallbackCollisionShape.Disabled = hasCollision || !EnableFallbackCollisionWhenImportHasNone;
        }

        if (hasCollision)
        {
            GD.Print("ImportedLevelMarkerBinder: imported level collision found.");
            return;
        }

        GD.PushWarning("ImportedLevelMarkerBinder: imported level has no CollisionObject3D/CollisionShape3D nodes. Add Godot collision suffixes in Blender for real level collision.");

        if (fallbackCollisionShape != null && EnableFallbackCollisionWhenImportHasNone)
        {
            GD.PushWarning("ImportedLevelMarkerBinder: temporary safety floor collision was enabled so the level can be test-run.");
        }
    }

    private static bool HasImportedCollision(Node node)
    {
        if (node is CollisionObject3D or CollisionShape3D)
        {
            return true;
        }

        foreach (Node child in node.GetChildren())
        {
            if (HasImportedCollision(child))
            {
                return true;
            }
        }

        return false;
    }

    private void PlacePlayer(Dictionary<string, List<Node3D>> markers)
    {
        var player = GetNodeOrNull<Node3D>(PlayerPath);
        if (player == null)
        {
            GD.PushWarning($"ImportedLevelMarkerBinder: player was not found at {PlayerPath}.");
            return;
        }

        Node3D spawn = FirstMarker(markers, "PlayerSpawn")
            ?? FirstMarker(markers, "PlayerStart")
            ?? GetNodeOrNull<Node3D>(WrapperSpawnPath);

        if (spawn == null)
        {
            GD.PushWarning("ImportedLevelMarkerBinder: no PlayerSpawn/PlayerStart marker or wrapper fallback spawn was found.");
            return;
        }

        player.GlobalTransform = spawn.GlobalTransform;

        if (player is CharacterBody3D characterBody)
        {
            characterBody.Velocity = Vector3.Zero;
        }

        GD.Print($"ImportedLevelMarkerBinder: player placed at {spawn.GetPath()} -> {spawn.GlobalPosition}.");
    }

    private void CreateGrappleAnchors(Dictionary<string, List<Node3D>> markers)
    {
        if (GrappleAnchorScene == null)
        {
            GD.PushWarning("ImportedLevelMarkerBinder: GrappleAnchor markers found, but no GrappleAnchorScene is assigned.");
            return;
        }

        var grappleAnchorMarkers = markers["GrappleAnchor"];
        if (grappleAnchorMarkers.Count == 0)
        {
            return;
        }

        var grappleAnchorsRoot = GetNodeOrNull<Node>(GrappleAnchorsPath);
        if (grappleAnchorsRoot == null)
        {
            GD.PushWarning($"ImportedLevelMarkerBinder: GrappleAnchors container was not found at {GrappleAnchorsPath}.");
            return;
        }

        foreach (Node3D marker in grappleAnchorMarkers)
        {
            if (GrappleAnchorScene.Instantiate() is not Node3D grappleAnchor)
            {
                GD.PushWarning("ImportedLevelMarkerBinder: GrappleAnchorScene did not instantiate as Node3D.");
                return;
            }

            grappleAnchor.Name = $"Runtime_{marker.Name}";
            grappleAnchorsRoot.AddChild(grappleAnchor);
            grappleAnchor.GlobalTransform = marker.GlobalTransform;
        }

        GD.Print($"ImportedLevelMarkerBinder: created {grappleAnchorMarkers.Count} runtime grapple anchor(s).");
    }

    private static Node3D FirstMarker(Dictionary<string, List<Node3D>> markers, string markerName)
    {
        return markers.TryGetValue(markerName, out List<Node3D> nodes) && nodes.Count > 0 ? nodes[0] : null;
    }

    private static void CollectNodesOfType<T>(Node node, List<T> nodes) where T : Node
    {
        if (node is T typedNode)
        {
            nodes.Add(typedNode);
        }

        foreach (Node child in node.GetChildren())
        {
            CollectNodesOfType(child, nodes);
        }
    }
}
