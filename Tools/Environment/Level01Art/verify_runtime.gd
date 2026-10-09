extends SceneTree
## Loads the real wrapper, fingerprints imported collision and captures fixed views.
const OUT := "res://.godot/level01-art"

func _init() -> void:
	call_deferred("verify")

func walk(node: Node) -> Array[Node]:
	var result: Array[Node] = [node]
	for child in node.get_children():
		result.append_array(walk(child))
	return result

func verify() -> void:
	var before := "--before" in OS.get_cmdline_user_args()
	var phase := "before" if before else "after"
	if "--capture" in OS.get_cmdline_user_args():
		root.size = Vector2i(1440, 900)
	var level := load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate() as Node3D
	level.get_node("StartupWindowModeController").set("EnableStartupWindowMode", false)
	root.add_child(level)
	current_scene = level
	await process_frame
	await process_frame
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	await create_timer(.25).timeout
	await physics_frame
	if "--player" in OS.get_cmdline_user_args():
		await create_timer(.75).timeout
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT + "/" + phase + "_player.png")
	var imported := level.get_node("ImportedLevel")
	var collisions := {}
	var materials := {}
	var art_meshes := []
	var collision_nodes := {}
	for node in walk(imported):
		if node is CollisionShape3D:
			var shape: Shape3D = node.shape
			var data := str(shape.get("data")) if shape is ConcavePolygonShape3D else str(shape.get("size"))
			collisions[str(imported.get_path_to(node))] = [str(node.global_transform), data.sha256_text()]
			collision_nodes[str(imported.get_path_to(node))] = node
		if node is MeshInstance3D and node.mesh != null:
			if str(node.name).begins_with("L01_ART_"):
				art_meshes.append(str(node.name))
			for s in node.mesh.get_surface_count():
				var mat: Material = node.get_active_material(s)
				if mat != null and mat.resource_path.begins_with("res://Assets/Materials/Environment/Level01Art/"):
					assert(mat is ORMMaterial3D)
					assert(mat.albedo_texture != null and mat.orm_texture != null)
					materials[mat.resource_name] = mat.resource_path
	var rays := []
	var route_excludes: Array[RID] = []
	for body in walk(level):
		if body is CollisionObject3D and not imported.is_ancestor_of(body):
			route_excludes.append(body.get_rid())
	for point in [Vector3(96, 12, 49), Vector3(96, 12, 23), Vector3(108, 12, -10),
		Vector3(117, 12, -36), Vector3(96, 12, -71), Vector3(111, 12, -132), Vector3(10, 12, 4)]:
		point += level.get_node("ImportedLevel").position
		var query := PhysicsRayQueryParameters3D.create(point, point - Vector3(0, 30, 0))
		query.exclude = route_excludes
		var hit := root.world_3d.direct_space_state.intersect_ray(query)
		assert(not hit.is_empty(), "Missing route floor: " + str(point))
		assert(hit.collider is StaticBody3D and imported.is_ancestor_of(hit.collider))
		rays.append({"point": str(point), "body": str(hit.collider.name), "height": hit.position.y})
	level.process_mode = Node.PROCESS_MODE_DISABLED
	var ambient_effects := 0
	if not before:
		assert(level.has_node("ArtAtmosphere"), "Art atmosphere missing")
		for effect_name in ["ArrivalVent","NestVent","SwitchgearDischarge"]:
			var effect := level.get_node("ArtAtmosphere/" + effect_name)
			assert(effect.get("loop") and effect.get("components").size() > 0)
			effect.call("seek", .75 if effect_name != "SwitchgearDischarge" else .22)
			ambient_effects += 1
	var preserved := 0
	var reordered_boxes := 0
	if not before:
		var original: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OUT + "/runtime_before.json"))
		var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://Scenes/Levels/Level_01/combat_layout.json"))
		for key in original.collisions:
			assert(collisions.has(key), "Original collision missing: " + key)
			if collisions[key] != original.collisions[key]:
				# Material partitioning changes triangle order for Blender -col boxes.
				# Verify all six planes, outward winding and full face area instead.
				assert(str(key).begins_with("CB_"), "Original collision changed: " + key)
				var matched := false
				for item in layout.boxes:
					if str(key).get_slice("/", 0) == item.name:
						assert(verify_box(collision_nodes[key], item, imported.position), "Combat box changed: " + key)
						matched = true
				assert(matched, "Unknown changed collider: " + key)
				reordered_boxes += 1
			preserved += 1
		assert(materials.size() >= 12 and art_meshes.size() >= 20, "Art import missing")
		var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Materials/Environment/Level01Art/placement_manifest.json"))
		assert(materials.size() == manifest.materials.size(), "Some authored materials were lost on import")
		for key in manifest.materials:
			assert(materials.has("M_Level01_Art_" + key))
	var report := {"phase":phase, "collisions":collisions, "preserved_colliders":preserved,
		"materials":materials, "art_meshes":art_meshes, "route_rays":rays,"reordered_box_triangles":reordered_boxes,
		"wrapper_loaded":true, "ambient_effects":ambient_effects, "enemies":8,
		"player_position":str(level.get_node("Player").position)}
	var file := FileAccess.open(OUT + "/runtime_" + phase + ".json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("LEVEL01_ART_VERIFY ", phase, " colliders=", collisions.size(), " preserved=",preserved,
		" materials=",materials.size(), " art_meshes=", art_meshes.size())
	if "--capture" in OS.get_cmdline_user_args():
		root.size = Vector2i(1440, 900)
		for node in walk(level):
			if node is CanvasLayer:
				node.visible = false
		var camera := Camera3D.new()
		root.add_child(camera)
		camera.current = true
		camera.fov = 70
		camera.far = 2500
		var views := [
			["01_arrival", Vector3(101, 4, 55), Vector3(98, 2, 26)],
			["02_crossing", Vector3(111, 4, 9), Vector3(116, 2, -22)],
			["03_service", Vector3(118, 7, -31), Vector3(122, 3, -55)],
			["04_end", Vector3(115, 6, -97), Vector3(108, 2, -125)],
			["05_training", Vector3(32, 9, 27), Vector3(-4, 10, -20)],
			["06_overview", Vector3(188, 125, 109), Vector3(56, 0, -53)],
			["07_coolant", Vector3(162, 5, -52), Vector3(154, 4, -67)],
			["08_equipment", Vector3(86, 3, 44), Vector3(78, 2, 35)],
		]
		for view in views:
			camera.position = view[1]
			camera.look_at(view[2])
			await create_timer(.35).timeout
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(OUT + "/" + phase + "_" + view[0] + ".png")
			print("LEVEL01_ART_CAPTURE ",phase,"_",view[0])
	current_scene = null
	level.queue_free()
	await process_frame
	await process_frame
	quit(0)

func verify_box(node: CollisionShape3D, item: Dictionary, offset: Vector3) -> bool:
	var center := Vector3(item.position[0],item.position[1],item.position[2]) + offset
	var half := Vector3(item.size[0],item.size[1],item.size[2]) * .5
	var faces: PackedVector3Array = node.shape.get_faces()
	if faces.size() != 36:
		return false
	var areas := [0.0,0.0,0.0,0.0,0.0,0.0]
	for i in range(0,faces.size(),3):
		var a := node.global_transform * faces[i] - center
		var b := node.global_transform * faces[i+1] - center
		var c := node.global_transform * faces[i+2] - center
		for p in [a,b,c]:
			if not p.abs().is_equal_approx(half):
				# Imported transforms carry float rounding on the thin 7cm route pads.
				if (p.abs()-half).length() > .0001:
					return false
		var cross := (b-a).cross(c-a)
		var axis := cross.abs().max_axis_index()
		var centroid := (a+b+c)/3.0
		# Godot triangle fronts use clockwise winding.
		if cross[axis]*centroid[axis] >= 0:
			return false
		areas[axis*2+(1 if cross[axis]>0 else 0)] += cross.length()*.5
	for axis in 3:
		var area := 4.0 * half[(axis+1)%3] * half[(axis+2)%3]
		for side in 2:
			if absf(areas[axis*2+side]-area) > maxf(.001, area*.0001):
				return false
	return true
