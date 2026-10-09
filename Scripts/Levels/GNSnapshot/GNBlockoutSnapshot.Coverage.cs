using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

public partial class GNBlockoutSnapshot
{
    private sealed class Target
    {
        public JsonObject Row;
        public string Id, Type;
        public Vector3 Position, Normal;
        public float Radius;
        public MeshInstance3D Marker;
        public Target(JsonObject row)
        {
            Row = row; Id = (string)row["id"]; Type = (string)row["type"];
            Position = Vec(row["position"]); Normal = row["normal"] == null ? Vector3.Up : Vec(row["normal"]);
            Radius = (float)row["radius"];
        }
    }
    private sealed class Session
    {
        public string Id = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff") + "Z";
        public string Snapshot;
        public DateTime StartedUtc = DateTime.UtcNow;
        public double Seconds;
        public bool Started;
        public int Resets, Falls;
        public Dictionary<string, (double Time, string Method)> Reached = new();
    }
    // Survives the existing F1 scene reload inside this process, never another launch.
    private static Session _session;
    private double _flush;
    private bool _ioFailed;
    private Session NewSession() => new() { Snapshot = (string)Manifest["glb_sha256"] };
    private void BeginOrResumeSession()
    {
        if (_session == null || _session.Snapshot != (string)Manifest["glb_sha256"] || _check) _session = NewSession();
        else _session.Resets++;
        SaveSession(false);
    }

    public override void _PhysicsProcess(double delta)
    {
        if (!ReadyForPlay || !IsInstanceValid(_player) || _reloadPending) return;
        if (_player.GlobalPosition.Y < _killY)
        {
            _reloadPending = true;
            CallDeferred(nameof(ReloadAfterFall));
            return;
        }
        if (_check) return;
        // Coverage starts with human traversal input, not while waiting at handoff.
        if (!_session.Started)
        {
            _session.Started = new[] { "move_forward", "move_back", "move_left", "move_right",
                _player.JumpModule.JumpAction, _player.SlingshotGrappleModule.GrappleAction }
                .Any(action => InputMap.HasAction(action) && Input.IsActionPressed(action));
            if (!_session.Started) return;
        }
        _session.Seconds += delta;
        foreach (Target t in _targets)
        {
            if (_session.Reached.ContainsKey(t.Id)) continue;
            string method = ReachedMethod(t);
            if (method == null) continue;
            _session.Reached[t.Id] = (_session.Seconds, method);
            t.Marker.Visible = false;
        }
        UpdateHud();
        _flush += delta;
        if (_flush >= 1) { _flush = 0; SaveSession(false); }
    }

    private string ReachedMethod(Target t)
    {
        if (t.Type == "GRAPPLE")
        {
            // This reads the actual point stored by successful canonical acquisition.
            // Looking at an available highlight or approaching the helper never counts.
            var grapple = _player.SlingshotGrappleModule;
            return grapple.IsSlingshotActive && grapple.CoverageActivePoint.DistanceTo(t.Position) < .02f
                ? "canonical_grapple_active_at_anchor" : null;
        }
        Vector3 foot = _player.GlobalPosition;
        if (t.Type == "LANDING")
        {
            if (!_player.IsOnFloor() || Mathf.Abs(foot.Y-t.Position.Y) > .35f) return null;
            var horizontal = new Vector2(foot.X-t.Position.X, foot.Z-t.Position.Z);
            return horizontal.Length() <= t.Radius && HasSurfaceContact(t, foot)
                ? "grounded_on_target_surface" : null;
        }
        if (t.Type == "WALLRUN")
        {
            Vector3 body = foot + Vector3.Up*.9f;
            return _player.WallRunModule.IsWallRunning && body.DistanceTo(t.Position) < t.Radius
                && Mathf.Abs(_player.WallRunModule.CoverageWallNormal.Dot(t.Normal)) > .9f
                ? "canonical_wallrun_near_matching_surface" : null;
        }
        return foot.DistanceTo(t.Position) <= t.Radius ? "physical_proximity" : null;
    }

    private bool HasSurfaceContact(Target t, Vector3 foot)
    {
        var query = PhysicsRayQueryParameters3D.Create(foot + Vector3.Up*.12f, foot-Vector3.Up*.4f, 1);
        query.Exclude = new Godot.Collections.Array<Rid> { _player.GetRid() };
        var hit = GetWorld3D().DirectSpaceState.IntersectRay(query);
        return hit.Count > 0 && hit["collider"].AsGodotObject() == GetNode<StaticBody3D>("Collision")
            && Mathf.Abs(hit["position"].AsVector3().Y-t.Position.Y) < .35f;
    }

    private void UpdateHud()
    {
        if (_hud == null) return;
        string Count(IEnumerable<Target> ts)
        {
            var a = ts.ToArray(); return $"{a.Count(t => _session.Reached.ContainsKey(t.Id))}/{a.Length}";
        }
        _hud.Text = $"TRAVERSAL COVERAGE  {_session.Reached.Count} / {_targets.Count}"
            + $"\nLANDING {Count(_targets.Where(t=>t.Type=="LANDING"))}   PASS {Count(_targets.Where(t=>t.Type=="PASS_THROUGH"))}"
            + $"\nGRAPPLE {Count(_targets.Where(t=>t.Type=="GRAPPLE"))}   WALLRUN {Count(_targets.Where(t=>t.Type=="WALLRUN"))}"
            + $"\nVERTICAL {Count(_targets.Where(t=>(bool?)t.Row["vertical"]==true))}   ARENA {Count(_targets.Where(t=>(bool?)t.Row["arena"]==true))}"
            + $"\nF3 markers {(_markersVisible?"ON":"OFF")} | Shift+F3 new coverage"
            + $"\nF1 reset player | {_session.Seconds:0}s | resets {_session.Resets}"
            + (!_session.Started ? "\nReady — move to start human coverage" : "")
            + (_ioFailed ? "\nLOG WRITE FAILED — see console" : "");
    }

    private void SaveSession(bool archive)
    {
        if (_check || _session == null) return;
        try
        {
            var records = new JsonArray();
            foreach (Target t in _targets)
            {
                JsonObject row = t.Row.DeepClone().AsObject();
                bool reached = _session.Reached.TryGetValue(t.Id, out var evidence);
                row["reached"] = reached;
                row["first_reached_seconds"] = reached ? JsonValue.Create(evidence.Time) : null;
                row["method"] = reached ? evidence.Method : null;
                row["anchor_used"] = t.Type == "GRAPPLE" && reached;
                records.Add(row);
            }
            var root = new JsonObject
            {
                ["session_id"] = _session.Id, ["snapshot_glb_sha256"] = _session.Snapshot,
                ["started_utc"] = _session.StartedUtc.ToString("O"), ["updated_utc"] = DateTime.UtcNow.ToString("O"),
                ["duration_seconds"] = _session.Seconds, ["human_input_started"] = _session.Started,
                ["resets"] = _session.Resets, ["falls"] = _session.Falls,
                ["reached"] = _session.Reached.Count, ["total"] = _targets.Count, ["targets"] = records,
                ["meaning"] = "Representative targets visited during this human session; not a reachability proof",
                ["archive_reason"] = archive ? "scene exit or explicit coverage reset; same session resumes across F1" : null
            };
            string dir = ProjectSettings.GlobalizePath("res://.godot/traversal-coverage");
            Directory.CreateDirectory(dir);
            string text = root.ToJsonString(new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(Path.Combine(dir,"latest.tmp"), text);
            File.Move(Path.Combine(dir,"latest.tmp"), Path.Combine(dir,"latest.json"), true);
            if (archive) File.WriteAllText(Path.Combine(dir,_session.Id+".json"), text);
        }
        catch (Exception error) { _ioFailed = true; GD.PushError("Coverage log: " + error.Message); }
    }

    public override void _ExitTree() => SaveSession(true);
    public override void _Notification(int what)
    {
        if (what == NotificationWMCloseRequest) SaveSession(true);
    }
}
