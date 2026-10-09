using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;

// The scene owns only the generated asset bridge and passive coverage tooling.
// All movement, input acquisition and presentation remain in Scenes/Player.tscn.
public partial class GNBlockoutSnapshot : Node3D
{
    public const string ManifestPath = "res://Assets/Levels/Level_Freestyle_01/Generated/GN_Blockout_Current.json";
    public JsonObject Manifest { get; private set; }
    public int CollisionTriangles { get; private set; }
    public int AnchorCount { get; private set; }
    public int TargetCount => _targets.Count;
    public bool ReadyForPlay { get; private set; }
    private PlayerController _player;
    private readonly List<Target> _targets = new();
    private Label _hud;
    private Node3D _markers;
    private bool _check, _reloadPending, _markersVisible = true;
    private float _killY;

    public static Vector3 Vec(JsonNode n) => new((float)n[0], (float)n[1], (float)n[2]);
    public static float[] Array(Vector3 p) => new[] { p.X, p.Y, p.Z };

    public override void _Ready()
    {
        ProcessPhysicsPriority = 100; // Observe canonical Player after MoveAndSlide.
        _check = OS.GetCmdlineUserArgs().Contains("--coverage-check") || DisplayServer.GetName() == "headless";
        try
        {
            Manifest = JsonNode.Parse(File.ReadAllText(ProjectSettings.GlobalizePath(ManifestPath))).AsObject();
            string glb = ProjectSettings.GlobalizePath("res://Assets/Levels/Level_Freestyle_01/Generated/GN_Blockout_Current.glb");
            string hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(glb))).ToLowerInvariant();
            if (hash != (string)Manifest["glb_sha256"]) throw new InvalidDataException("GLB and manifest do not match. Re-export Current.");
            BuildCollision(GetNode<Node3D>("Visual"));
            BuildAnchors();
            _markers = GetNode<Node3D>("CoverageDebug");
            foreach (JsonObject row in Manifest["targets"].AsArray()) _targets.Add(new Target(row));
            if (_targets.Count == 0 || CollisionTriangles == 0) throw new InvalidDataException("Snapshot is empty.");
            _killY = (float)Manifest["bounds"][1][0] - 35;
            BuildHud();
            BeginOrResumeSession();
            foreach (Target target in _targets) BuildMarker(target);
            // The sibling Player has completed its normal _Ready by the deferred bind.
            CallDeferred(nameof(BindPlayer));
        }
        catch (Exception error)
        {
            GD.PushError("GN snapshot could not load: " + error);
            SetPhysicsProcess(false);
        }
    }

    private void BuildCollision(Node node)
    {
        if (node is MeshInstance3D visual && visual.Mesh != null)
        {
            var shape = visual.Mesh.CreateTrimeshShape();
            if (shape == null) throw new InvalidDataException("Cannot create exact static collision.");
            CollisionTriangles += shape.GetFaces().Length / 3;
            GetNode<StaticBody3D>("Collision").AddChild(new CollisionShape3D
            {
                Name = "Surface" + CollisionTriangles, Shape = shape,
                Transform = GlobalTransform.AffineInverse() * visual.GlobalTransform
            });
        }
        foreach (Node child in node.GetChildren()) BuildCollision(child);
    }

    private void BuildAnchors()
    {
        PackedScene packed = GD.Load<PackedScene>("res://Scenes/GrappleAnchor.tscn");
        foreach (JsonObject row in Manifest["anchors"].AsArray())
        {
            var anchor = packed.Instantiate<GrappleAnchor>();
            anchor.Name = "GrappleAnchor_" + (string)row["id"];
            anchor.Position = Vec(row["position"]);
            anchor.SetMeta("coverage_id", (string)row["id"]);
            anchor.SetMeta("section_id", (int)row["section_id"]);
            anchor.SetMeta("grapple_required", (bool?)row["grapple_required"] ?? false);
            anchor.SetMeta("snapshot_metadata", row.ToJsonString());
            GetNode<Node3D>("GrappleAnchors").AddChild(anchor);
            AnchorCount++;
        }
    }

    private void BindPlayer()
    {
        _player = GetParent().GetNode<PlayerController>("Player");
        ReadyForPlay = _player.Camera != null && _player.MovementModule != null && _player.WallRunModule != null
            && _player.SlingshotGrappleModule != null && _player.CrouchSlideModule != null;
        GetWindow().Title = "BowPrototype | V06 human traversal coverage | Seed " + Manifest["controls"]["Seed"];
        UpdateHud();
        GD.Print($"GN_SNAPSHOT_READY ready={ReadyForPlay} triangles={CollisionTriangles} anchors={AnchorCount} targets={TargetCount} spawn={_player.GlobalPosition} check={_check}");
    }

    private void BuildHud()
    {
        var canvas = new CanvasLayer { Name = "CoverageHUD", Layer = 3 };
        AddChild(canvas);
        _hud = new Label { Position = new Vector2(18, 82), MouseFilter = Control.MouseFilterEnum.Ignore };
        _hud.AddThemeFontSizeOverride("font_size", 17);
        _hud.AddThemeConstantOverride("outline_size", 5);
        _hud.AddThemeColorOverride("font_outline_color", Colors.Black);
        canvas.AddChild(_hud);
    }

    private void BuildMarker(Target t)
    {
        var material = new StandardMaterial3D
        {
            AlbedoColor = t.Type == "GRAPPLE" ? new Color(1,.3f,.9f) : new Color(1,.7f,.05f),
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded
        };
        t.Marker = new MeshInstance3D
        {
            Name = t.Id, Position = t.Position + (t.Type == "GRAPPLE" ? Vector3.Up*.8f : t.Normal*.5f),
            Mesh = new SphereMesh { Radius = .28f, Height = .56f, RadialSegments = 8, Rings = 4 },
            MaterialOverride = material, CastShadow = GeometryInstance3D.ShadowCastingSetting.Off
        };
        _markers.AddChild(t.Marker);
        var label = new Label3D { Text = t.Type, FontSize = 26, PixelSize = .008f,
            Position = Vector3.Up*.65f, Billboard = BaseMaterial3D.BillboardModeEnum.Enabled,
            Modulate = new Color(1,.85f,.3f), NoDepthTest = false };
        t.Marker.AddChild(label);
        t.Marker.Visible = !_session.Reached.ContainsKey(t.Id);
    }

    public override void _UnhandledKeyInput(InputEvent input)
    {
        if (input is not InputEventKey { Pressed: true, Echo: false } key || key.Keycode != Key.F3) return;
        if (key.ShiftPressed)
        {
            SaveSession(true);
            _session = NewSession();
            foreach (Target t in _targets) t.Marker.Visible = true;
            SaveSession(false);
        }
        else
        {
            _markersVisible = !_markersVisible;
            _markers.Visible = _markersVisible;
        }
        UpdateHud();
        GetViewport().SetInputAsHandled();
    }

    private void ReloadAfterFall()
    {
        _session.Falls++;
        GetTree().ReloadCurrentScene(); // Same canonical reset as the existing F1.
    }
}
