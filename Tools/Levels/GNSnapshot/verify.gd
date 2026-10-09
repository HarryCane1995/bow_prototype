extends SceneTree
## Structural/physics import checks only. Never drives traversal or writes a human session.
var failures: Array[String] = []
func check(ok: bool, label: String) -> void:
    if not ok: failures.append(label)

func _initialize():
    call_deferred("run")

func run():
    var level = load("res://Scenes/Levels/Level_Freestyle_01.tscn").instantiate()
    root.add_child(level)
    current_scene = level
    for i in range(45): await physics_frame
    var branch = level.get_node("GN_Blockout_Current")
    var player = level.get_node("Player")
    var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Levels/Level_Freestyle_01/Generated/GN_Blockout_Current.json"))
    check(branch.ReadyForPlay, "canonical player and snapshot ready")
    check(player.scene_file_path == "res://Scenes/Player.tscn", "canonical Player scene")
    check(player.is_on_floor(), "spawn settles on generated floor")
    check(branch.TargetCount > 0 and branch.TargetCount == manifest.targets.size(), "manifest targets loaded")
    check(branch.AnchorCount == manifest.anchors.size(), "canonical anchors instantiated")
    check(branch.CollisionTriangles == int(manifest.triangles), "triangle count matches Blender")
    check(level.find_children("*", "CharacterBody3D", true, false).size() == 1, "one player only")
    var collision = branch.get_node("Collision")
    var all_faces: Array[Vector3] = []
    for child in collision.get_children():
        check(child.shape is ConcavePolygonShape3D, "static concave collision")
        for p in child.shape.get_faces(): all_faces.append(child.global_transform*p)
    var lo = Vector3(INF,INF,INF)
    var hi = -lo
    for p in all_faces:
        lo = lo.min(p); hi = hi.max(p)
    var bounds = manifest.bounds
    check(lo.distance_to(Vector3(bounds[0][0],bounds[1][0],bounds[2][0])) < .001, "world min bounds / axes / scale")
    check(hi.distance_to(Vector3(bounds[0][1],bounds[1][1],bounds[2][1])) < .001, "world max bounds / axes / scale")
    var probes := 0
    var missed: Array[String] = []
    for t in manifest.targets:
        if t.type == "GRAPPLE": continue
        var p = Vector3(t.position[0],t.position[1],t.position[2])
        var n = Vector3(t.normal[0],t.normal[1],t.normal[2])
        var query = PhysicsRayQueryParameters3D.create(p+n*.12,p-n*.12,1)
        query.exclude = [player.get_rid()]
        var hit = level.get_world_3d().direct_space_state.intersect_ray(query)
        probes += 1
        if hit.is_empty() or hit.collider != collision: missed.append(t.id)
    check(missed.is_empty(), "every non-grapple target lies on actual imported collision")
    for i in range(manifest.anchors.size()):
        var a = branch.get_node("GrappleAnchors").get_child(i)
        var row = manifest.anchors[i]
        check(a.scene_file_path == "res://Scenes/GrappleAnchor.tscn" and a.is_in_group("grapple_anchor"), "canonical grapple type")
        check(a.global_position.distance_to(Vector3(row.position[0],row.position[1],row.position[2])) < .001, "anchor world transform")
    var result = {"pass":failures.is_empty(),"failures":failures,"collision_triangles":branch.CollisionTriangles,
        "target_count":branch.TargetCount,"anchors":branch.AnchorCount,"target_collision_probes":probes,
        "missed_target_ids":missed,"world_min":[lo.x,lo.y,lo.z],"world_max":[hi.x,hi.y,hi.z],
        "spawn_grounded":player.is_on_floor(),"player_position":[player.position.x,player.position.y,player.position.z],
        "human_playtest_performed":false}
    DirAccess.make_dir_recursive_absolute("res://Docs/Reviews/GNSnapshot")
    var file = FileAccess.open("res://Docs/Reviews/GNSnapshot/verification.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(result,"  "));file.close()
    print("GN_SNAPSHOT_VERIFICATION ", JSON.stringify(result))
    quit(0 if failures.is_empty() else 1)
