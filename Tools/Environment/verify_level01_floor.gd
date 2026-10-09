extends SceneTree
## Read-only runtime validation and optional capture of the actual Level_01 map.
const FLOOR_NAME := "L01_Arena01_TestFloor_01"
const MATERIAL_PATH := "res://Assets/Materials/Environment/FacadeFactory/Generated/tech_wall_627708735.tres"
const OUT := "res://.godot/level01-floor"

func _init() -> void:
	call_deferred("verify")

func verify() -> void:
	var packed := load("res://Level_01_Blockout.blend") as PackedScene
	assert(packed != null)
	var imported := packed.instantiate()
	var floor_node := imported.find_child(FLOOR_NAME, true, false) as MeshInstance3D
	assert(floor_node != null and floor_node.mesh != null, "Floor mesh missing")
	var material := floor_node.get_active_material(0) as ORMMaterial3D
	assert(material != null and material.resource_path == MATERIAL_PATH, "Exact exported ORMMaterial3D missing")
	assert(material.texture_repeat and material.uv1_scale == Vector3(1.5, 1.5, 1))
	assert(material.normal_enabled and is_equal_approx(material.normal_scale, .55))
	assert(not material.detail_enabled, "Separate micro detail must remain opt-in")
	var textures := {"albedo": material.albedo_texture, "normal": material.normal_texture,
		"orm": material.orm_texture, "emission": material.emission_texture}
	var maps := {}
	for channel in textures:
		var texture := textures[channel] as Texture2D
		assert(texture != null and texture.get_size() == Vector2(512, 512))
		assert(texture.resource_path.ends_with("tech_wall_627708735_" + channel + ".png"))
		maps[channel] = {"path": texture.resource_path, "size": [texture.get_width(), texture.get_height()]}
	var assigned_nodes := []
	for node in walk(imported):
		if node is MeshInstance3D:
			for surface in node.mesh.get_surface_count():
				var active: Material = node.get_active_material(surface)
				if active != null and active.resource_path == MATERIAL_PATH:
					assigned_nodes.append(str(node.name))
	assert(assigned_nodes == [FLOOR_NAME], "Material escaped the requested floor")
	var uv: PackedVector2Array = floor_node.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	var uv_min := Vector2(INF, INF)
	var uv_max := Vector2(-INF, -INF)
	for point in uv:
		uv_min = uv_min.min(point)
		uv_max = uv_max.max(point)
	var bounds := floor_node.transform * floor_node.mesh.get_aabb()
	var tile_meters := Vector2(bounds.size.x, bounds.size.z) / (uv_max - uv_min) / 1.5
	assert(tile_meters.is_equal_approx(Vector2(4, 4)), "Incorrect world-space texture density")
	imported.free()

	var level := load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate() as Node3D
	level.get_node("StartupWindowModeController").set("EnableStartupWindowMode", false)
	root.add_child(level)
	current_scene = level
	await create_timer(1.0).timeout
	await physics_frame
	var floor_rays := []
	for p in [Vector3(10, 10, 4), Vector3(50, 10, 4), Vector3(-60, 10, 30)]:
		var query := PhysicsRayQueryParameters3D.create(p, p - Vector3(0, 20, 0))
		var hit := root.world_3d.direct_space_state.intersect_ray(query)
		assert(not hit.is_empty())
		floor_rays.append({"body": str(hit.collider.name), "height": hit.position.y})
	var result := {"object": FLOOR_NAME, "material": MATERIAL_PATH, "maps": maps,
		"tile_meters": [tile_meters.x, tile_meters.y], "assigned_nodes": assigned_nodes,
		"separate_detail_enabled": material.detail_enabled, "floor_rays": floor_rays,
		"wrapper_loaded": true}
	var report := FileAccess.open(OUT + "/runtime_validation.json", FileAccess.WRITE)
	report.store_string(JSON.stringify(result, "\t"))
	report.close()
	print("LEVEL01_FLOOR_VERIFY=" + JSON.stringify(result))
	if "--capture" in OS.get_cmdline_user_args():
		level.process_mode = Node.PROCESS_MODE_DISABLED
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
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
			["floor_close", Vector3(14, 2.0, 5), Vector3(14, -.747, -1)],
			["floor_context", Vector3(-12, 8, 28), Vector3(6, -.747, -6)],
		]
		for view in views:
			camera.position = view[1]
			camera.look_at(view[2])
			await create_timer(.5).timeout
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(OUT + "/" + view[0] + ".png")
			print("LEVEL01_FLOOR_CAPTURE=" + OUT + "/" + view[0] + ".png")
	quit(0)

func walk(node: Node) -> Array[Node]:
	var result: Array[Node] = [node]
	for child in node.get_children():
		result.append_array(walk(child))
	return result
