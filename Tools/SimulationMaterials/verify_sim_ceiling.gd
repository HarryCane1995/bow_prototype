extends SceneTree

const CEILING_NODE := "ENV_SimCeiling_GN"
const MATERIAL_PATH := "res://Assets/Materials/Simulation/sim_grid_ceiling.tres"
const SHADER_PATH := "res://Assets/Materials/Simulation/sim_grid.gdshader"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty() or args.size() > 2:
		push_error("Usage: godot --path . --script res://Tools/SimulationMaterials/verify_sim_ceiling.gd -- <Level_01 .blend> [output.png]")
		quit(2)
		return

	var scene_path: String = args[0]
	var output_path := "res://.godot/sim-ceiling-runtime.png"
	if args.size() == 2:
		output_path = args[1]

	var packed := load(scene_path) as PackedScene
	var expected_material := load(MATERIAL_PATH) as ShaderMaterial
	if packed == null or expected_material == null or expected_material.shader == null:
		push_error("Could not load Level_01 or SIM_GRID_CEILING runtime material")
		quit(3)
		return

	var imported_root := packed.instantiate()
	var ceiling_nodes: Array[MeshInstance3D] = []
	var all_meshes: Array[MeshInstance3D] = []
	_collect_meshes(imported_root, all_meshes, ceiling_nodes)
	if ceiling_nodes.size() != 1:
		push_error("Expected one %s MeshInstance3D, got %d" % [CEILING_NODE, ceiling_nodes.size()])
		imported_root.free()
		quit(4)
		return
	if all_meshes.size() > 30:
		push_error("Imported mesh-node count exploded to %d" % all_meshes.size())
		imported_root.free()
		quit(5)
		return

	var ceiling := ceiling_nodes[0]
	var vertex_count := 0
	var mapped_surfaces := 0
	var surface_paths: Array[String] = []
	for surface_index in ceiling.mesh.get_surface_count():
		var arrays := ceiling.mesh.surface_get_arrays(surface_index)
		var vertices: Variant = arrays[Mesh.ARRAY_VERTEX]
		if vertices != null:
			vertex_count += vertices.size()
		var material := ceiling.get_active_material(surface_index) as ShaderMaterial
		if material != null:
			surface_paths.append(material.resource_path)
			if material == expected_material and material.shader.resource_path == SHADER_PATH:
				mapped_surfaces += 1

	if vertex_count < 1000:
		push_error("Ceiling geometry is unexpectedly small: %d vertices" % vertex_count)
		imported_root.free()
		quit(6)
		return
	if mapped_surfaces != 1:
		push_error("SIM_GRID_CEILING mapping mismatch: %s" % surface_paths)
		imported_root.free()
		quit(7)
		return

	var collision_nodes := _count_collision_nodes(ceiling)
	if collision_nodes != 0:
		push_error("Decorative ceiling unexpectedly contains %d collision node(s)" % collision_nodes)
		imported_root.free()
		quit(8)
		return

	var viewport := SubViewport.new()
	viewport.name = "SimCeilingVerificationViewport"
	viewport.size = Vector2i(1280, 720)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	get_root().add_child(viewport)

	var stage := Node3D.new()
	viewport.add_child(stage)
	stage.add_child(imported_root)

	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.001, 0.002, 0.005, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.04, 0.06, 0.09, 1.0)
	environment.ambient_light_energy = 0.22
	world_environment.environment = environment
	stage.add_child(world_environment)

	var center := ceiling.to_global(ceiling.mesh.get_aabb().get_center())
	var camera := Camera3D.new()
	camera.position = center + Vector3(0.0, -48.0, 145.0)
	camera.fov = 62.0
	camera.current = true
	stage.add_child(camera)
	camera.look_at(center + Vector3(0.0, -2.0, 0.0), Vector3.UP)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55.0, -25.0, 0.0)
	light.light_energy = 0.22
	stage.add_child(light)

	for _frame in 10:
		await process_frame

	var image := viewport.get_texture().get_image()
	if image == null or image.is_empty():
		push_error("Runtime ceiling render returned an empty image")
		viewport.queue_free()
		quit(9)
		return
	image.convert(Image.FORMAT_RGBA8)
	var save_error := image.save_png(ProjectSettings.globalize_path(output_path))
	if save_error != OK:
		push_error("Could not save ceiling screenshot to %s" % output_path)
		viewport.queue_free()
		quit(10)
		return

	var bright_samples := 0
	var maximum_luminance := 0.0
	var sample_count := 0
	for y in range(0, image.get_height(), 5):
		for x in range(0, image.get_width(), 5):
			var color := image.get_pixel(x, y)
			var luminance := Vector3(color.r, color.g, color.b).dot(Vector3(0.2126, 0.7152, 0.0722))
			maximum_luminance = max(maximum_luminance, luminance)
			if luminance > 0.12:
				bright_samples += 1
			sample_count += 1
	if bright_samples < 60 or maximum_luminance < 0.2:
		push_error("Runtime ceiling render lacks visible grid detail")
		viewport.queue_free()
		quit(11)
		return

	var result := {
		"scene": scene_path,
		"ceiling_node": ceiling.name,
		"mesh_nodes": all_meshes.size(),
		"total_nodes": _count_nodes(imported_root),
		"surface_count": ceiling.mesh.get_surface_count(),
		"mapped_surfaces": mapped_surfaces,
		"material": expected_material.resource_path,
		"shader": expected_material.shader.resource_path,
		"vertex_count": vertex_count,
		"aabb_size": ceiling.mesh.get_aabb().size,
		"global_position": ceiling.global_position,
		"collision_nodes": collision_nodes,
		"render": {
			"path": output_path,
			"size": image.get_size(),
			"bright_samples": bright_samples,
			"sample_count": sample_count,
			"maximum_luminance": maximum_luminance,
		},
	}
	print("SIM_CEILING_VERIFY=" + JSON.stringify(result))
	viewport.queue_free()
	quit(0)


func _collect_meshes(node: Node, all_meshes: Array[MeshInstance3D], ceiling_nodes: Array[MeshInstance3D]) -> void:
	var mesh_instance := node as MeshInstance3D
	if mesh_instance != null:
		all_meshes.append(mesh_instance)
		if mesh_instance.name == CEILING_NODE:
			ceiling_nodes.append(mesh_instance)
	for child in node.get_children():
		_collect_meshes(child, all_meshes, ceiling_nodes)


func _count_nodes(node: Node) -> int:
	var count := 1
	for child in node.get_children():
		count += _count_nodes(child)
	return count


func _count_collision_nodes(node: Node) -> int:
	var count := 0
	if node is CollisionObject3D or node is CollisionShape3D or node is CollisionPolygon3D:
		count += 1
	for child in node.get_children():
		count += _count_collision_nodes(child)
	return count
