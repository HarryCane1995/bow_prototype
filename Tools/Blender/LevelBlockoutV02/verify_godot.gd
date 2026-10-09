extends SceneTree
## Runtime import/collision checks; does not alter the playable scene or Player.
const SCENE = "res://Scenes/Levels/Level_Freestyle_GN_V02.tscn"
var OUT = "res://Docs/Reviews/GNLevelBlockoutV02"
var level: Node3D
var player: CharacterBody3D
var checks: Array = []
var evidence: Dictionary = {}
var failed := false

func _initialize():
    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--review-dir="): OUT = argument.trim_prefix("--review-dir=")
    call_deferred("run")
func expect(ok: bool, label: String):
    checks.append({"check": label, "passed": ok})
    if not ok:
        failed = true
        push_error(label)

func step(count: int = 1):
    for i in count:
        await physics_frame
        await process_frame

func key(code: Key, down: bool):
    var event := InputEventKey.new()
    event.physical_keycode = code
    event.keycode = code
    event.pressed = down
    Input.parse_input_event(event)
    Input.flush_buffered_events()

func xyz(v: Vector3) -> Array: return [v.x, v.y, v.z]
func cast(a: Vector3, b: Vector3) -> Dictionary:
    var query := PhysicsRayQueryParameters3D.create(a, b, 1, [player.get_rid()])
    query.hit_back_faces = false
    return level.get_world_3d().direct_space_state.intersect_ray(query)

func triangle_match(visual: PackedVector3Array, visual_transform: Transform3D,
        collision: PackedVector3Array, collision_transform: Transform3D) -> Dictionary:
    # Quantized dictionary equality can reject points straddling a rounding boundary.
    # Search neighbouring centroid buckets, then compare actual vertex distances.
    var buckets := {}
    var consumed := {}
    var unmatched := 0
    var max_error := 0.0
    for i in range(0, collision.size(), 3):
        var tri := [collision_transform*collision[i], collision_transform*collision[i+1], collision_transform*collision[i+2]]
        var cell := Vector3i(((tri[0]+tri[1]+tri[2])/3.0/.1).floor())
        if not buckets.has(cell): buckets[cell] = []
        buckets[cell].append([i, tri])
    for i in range(0, visual.size(), 3):
        var tri := [visual_transform*visual[i], visual_transform*visual[i+1], visual_transform*visual[i+2]]
        var cell := Vector3i(((tri[0]+tri[1]+tri[2])/3.0/.1).floor())
        var best := INF
        var best_id := -1
        for x in range(-1,2):
            for y in range(-1,2):
                for z in range(-1,2):
                    for candidate in buckets.get(cell+Vector3i(x,y,z), []):
                        if consumed.has(candidate[0]): continue
                        var error := 0.0
                        for vertex: Vector3 in tri:
                            var nearest := INF
                            for other: Vector3 in candidate[1]: nearest = minf(nearest, vertex.distance_to(other))
                            error = maxf(error, nearest)
                        if error < best:
                            best = error
                            best_id = candidate[0]
        if best <= .001:
            consumed[best_id] = true
            max_error = maxf(max_error, best)
        else:
            unmatched += 1
    return {"unmatched_visual": unmatched, "unmatched_collision": collision.size()/3-consumed.size(), "max_vertex_error_m": max_error}

func clear_capsule_at(feet: Vector3) -> bool:
    var query := PhysicsShapeQueryParameters3D.new()
    query.shape = player.get_node("CollisionShape3D").shape
    query.transform = Transform3D(Basis.IDENTITY, feet + Vector3(0, .92, 0))
    query.collision_mask = 1
    query.exclude = [player.get_rid()]
    return level.get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty()

func capture(name: String):
    if DisplayServer.get_name() != "headless":
        await RenderingServer.frame_post_draw
        root.get_texture().get_image().save_png(OUT + "/" + name + ".png")

func run():
    create_timer(100).timeout.connect(func(): push_error("V02 runtime QA timeout"); quit(2))
    Engine.max_fps = 60
    root.size = Vector2i(1280, 720)
    level = load(SCENE).instantiate()
    root.add_child(level)
    current_scene = level
    await step(60)
    player = level.get_node("Player")
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    var imported := level.get_node("ImportedLevel")
    var meshes := imported.find_children("*", "MeshInstance3D", true, false)
    var bodies := imported.find_children("*", "StaticBody3D", true, false)
    var shapes := imported.find_children("*", "CollisionShape3D", true, false)
    expect(meshes.size() == 1, "Only one generated visual mesh imported")
    expect(bodies.size() == 1 and shapes.size() == 1, "One imported static body and collision shape")
    expect(imported.find_children("*CUTTER*", "", true, false).is_empty(), "No Cutter or authoring helper imported")
    expect(get_nodes_in_group("player").size() == 1, "One canonical Player")
    expect(player.is_on_floor() and abs(player.position.y) < .08, "Player settles on protected origin floor")
    expect(player.position.length() < .15, "Imported spawn remains at origin")
    if meshes.size() != 1 or shapes.size() != 1:
        finish()
        return
    var mesh: MeshInstance3D = meshes[0]
    var collider: CollisionShape3D = shapes[0]
    expect(collider.shape is ConcavePolygonShape3D, "Static concave triangle collision, no convex hull filling gaps")
    expect(not collider.disabled and bodies[0].collision_layer == 1, "Collision active on world layer 1")
    var visual_faces := mesh.mesh.get_faces()
    var collision_faces: PackedVector3Array = collider.shape.get_faces()
    var match_result := triangle_match(visual_faces, mesh.global_transform, collision_faces, collider.global_transform)
    evidence["triangle_match"] = match_result
    evidence["imported_metadata"] = {}
    for meta in mesh.get_meta_list(): evidence["imported_metadata"][meta] = mesh.get_meta(meta)
    expect(match_result.unmatched_visual == 0 and match_result.unmatched_collision == 0,
        "Every collision triangle matches the rendered mesh within 1 mm, including cuts and openings")
    var box := mesh.global_transform * mesh.get_aabb()
    var expected = JSON.parse_string(FileAccess.get_file_as_string(OUT + "/godot_export.json"))
    var bounds: Array = expected.bounds_blender
    expect(mesh.get_meta("extras", {}).get("source_geometry_sha256", "") == expected.geometry_sha256,
        "Imported snapshot matches the recorded Blender evaluated geometry hash")
    var expected_min := Vector3(bounds[0][0], bounds[2][0], -bounds[1][1])
    var expected_max := Vector3(bounds[0][1], bounds[2][1], -bounds[1][0])
    expect(box.position.distance_to(expected_min) < .003 and box.end.distance_to(expected_max) < .003,
        "Godot bounds match Blender evaluated bounds with correct axes and metre scale")
    expect(visual_faces.size()/3 == int(expected.triangles), "All evaluated source triangles survived import")
    expect(mesh.mesh.surface_get_material(0) != null, "Graybox material imported")
    var spawn_hit := cast(Vector3(0, 80, 0), Vector3(0, -20, 0))
    expect(not spawn_hit.is_empty() and abs(spawn_hit.position.y) < .01, "Spawn has clear sky and actual collidable floor at Y=0")
    expect(cast(Vector3(109, 60, 87), Vector3(109, -20, 87)).is_empty(), "Empty domain margin has no invisible safety floor")
    evidence["mesh"] = {"triangles": visual_faces.size()/3, "collision_triangles": collision_faces.size()/3,
        "aabb_min": xyz(box.position), "aabb_max": xyz(box.end), "seed": mesh.get_meta("extras", {}).get("seed", -1)}
    var samples := {"floor": 0, "wall": 0, "ramp": 0}
    var hits := {"floor": 0, "wall": 0, "ramp": 0}
    var elevated_points: Array[Vector3] = []
    var ramp_points: Array[Vector3] = []
    var wall_probes: Array = []
    for i in range(0, visual_faces.size(), 3):
        var a := mesh.global_transform * visual_faces[i]
        var b := mesh.global_transform * visual_faces[i+1]
        var c := mesh.global_transform * visual_faces[i+2]
        # Godot's imported render triangles use clockwise front faces.
        var normal := (c-a).cross(b-a).normalized()
        var center := (a+b+c)/3
        var role := "floor" if normal.y > .999 else ("wall" if abs(normal.y) < .001 else "ramp")
        if normal.y < -.001 or (b-a).cross(c-a).length() < .5:
            continue
        if samples[role] < 40:
            samples[role] += 1
            var hit := cast(center+normal*.15, center-normal*.15)
            if not hit.is_empty() and hit.position.distance_to(center) < .025:
                hits[role] += 1
        if normal.y > .999 and center.y > 3 and elevated_points.size() < 80 and clear_capsule_at(center):
            elevated_points.append(center)
        if normal.y > .8 and normal.y < .99 and ramp_points.size() < 60 and clear_capsule_at(center+Vector3(0,.3,0)):
            ramp_points.append(center)
        if role == "wall" and wall_probes.size() < 30 and center.y > 2:
            var feet := center+normal*1.0-Vector3(0,.9,0)
            if clear_capsule_at(feet): wall_probes.append([feet, normal])
    for role in samples:
        if role == "ramp" and samples[role] == 0:
            evidence["optional_ramp_rays"] = "No ramp surfaces in this seed; not required by the floating-space grammar."
            continue
        expect(samples[role] >= (2 if role == "ramp" else 10) and samples[role] == hits[role], "Physics rays hit actual " + role + " surfaces")
    evidence["surface_rays"] = {"samples": samples, "hits": hits}
    expect(not elevated_points.is_empty(), "Upper landing with full standing capsule clearance exists")
    evidence["ramp_standing_case"] = "available" if not ramp_points.is_empty() else "skipped: no suitable optional ramp landing in this seed"
    expect(not wall_probes.is_empty(), "Accessible wall collision test point exists")
    if not wall_probes.is_empty():
        var probe: Array = wall_probes[0]
        expect(player.test_move(Transform3D(Basis.IDENTITY, probe[0]), -probe[1]*2), "Actual Player capsule cannot pass through a structural wall")
    # A real input jump on the spawn pad must return to its imported collision.
    key(KEY_SPACE, true)
    await step()
    key(KEY_SPACE, false)
    var peak := player.position.y
    var airborne := false
    for i in 70:
        await step()
        peak = maxf(peak, player.position.y)
        airborne = airborne or not player.is_on_floor()
    expect(airborne and peak > 1.5 and player.is_on_floor() and abs(player.position.y) < .08,
        "Canonical Player jumps and physically lands on spawn collision")
    evidence["spawn_jump_peak_m"] = peak
    # Initial placement only; gravity and landing use unchanged canonical Player physics.
    var landings: Array = []
    var tested_heights: Array[int] = []
    for p in elevated_points:
        var band := roundi(p.y)
        if tested_heights.has(band): continue
        tested_heights.append(band)
        player.global_position = p+Vector3(0,.7,0)
        player.velocity = Vector3.ZERO
        player.reset_physics_interpolation()
        await step(35)
        var good: bool = player.is_on_floor() and abs(player.position.y-p.y) < .08
        landings.append({"target": xyz(p), "actual": xyz(player.position), "passed": good})
        expect(good, "Player physically lands on upper level Y=%.2f" % p.y)
        if landings.size() == 3: break
    if not ramp_points.is_empty():
        var p: Vector3 = ramp_points[0]
        player.global_position = p+Vector3(0,.7,0)
        player.velocity = Vector3.ZERO
        player.reset_physics_interpolation()
        await step(35)
        expect(player.is_on_floor() and abs(player.position.y-p.y) < .3, "Player stands on a generated ramp")
        evidence["ramp_landing"] = {"target": xyz(p), "actual": xyz(player.position)}
    evidence["upper_landings"] = landings
    player.global_position = Vector3(0,.05,0)
    player.rotation = Vector3.ZERO
    player.velocity = Vector3.ZERO
    player.reset_physics_interpolation()
    await step(30)
    await capture("godot_spawn")
    if DisplayServer.get_name() != "headless":
        var review_camera := Camera3D.new()
        level.add_child(review_camera)
        review_camera.position = Vector3(160,105,185)
        review_camera.look_at(Vector3(0,10,0))
        review_camera.far = 700
        review_camera.fov = 62
        review_camera.make_current()
        level.get_node("CanvasLayer").visible = false
        for canvas in player.find_children("*", "CanvasLayer", true, false): canvas.visible = false
        await step(5)
        await capture("godot_overview")
    await step(20)
    finish()

func finish():
    evidence["checks"] = checks
    evidence["passed"] = not failed
    evidence["engine"] = Engine.get_version_info().string
    evidence["automated_not_human_playtest"] = true
    FileAccess.open(OUT + "/godot_qa.json", FileAccess.WRITE).store_string(JSON.stringify(evidence, "  "))
    print("V02_GODOT_QA ", "PASS" if not failed else "FAIL", " checks=", checks.size())
    quit(1 if failed else 0)
