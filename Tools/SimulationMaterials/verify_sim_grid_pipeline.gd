extends SceneTree

const EXPECTED_MATERIAL_PATH := "res://Assets/Materials/Simulation/sim_grid.tres"
const EXPECTED_SHADER_PATH := "res://Assets/Materials/Simulation/sim_grid.gdshader"
const EXPECTED_NODES := ["SimGrid_Floor", "SimGrid_Scaled", "SimGrid_Wall"]


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty() or args.size() > 2:
		push_error("Usage: godot --headless --path . --script res://Tools/SimulationMaterials/verify_sim_grid_pipeline.gd -- <imported .blend> [output.png]")
		quit(2)
		return

	var scene_path: String = args[0]
	var output_path := "res://.godot/sim-grid-render.png"
	if args.size() == 2:
		output_path = args[1]

	var packed := load(scene_path) as PackedScene
	var expected_material := load(EXPECTED_MATERIAL_PATH) as ShaderMaterial
	if packed == null or expected_material == null or expected_material.shader == null:
		push_error("Could not load probe scene or SIM_GRID runtime material")
		quit(3)
		return

	var imported_root := packed.instantiate()
	var meshes: Array[MeshInstance3D] = []
	_collect_meshes(imported_root, meshes)
	meshes.sort_custom(func(a: MeshInstance3D, b: MeshInstance3D) -> bool: return String(a.name) < String(b.name))

	var errors: Array[String] = []
	var mesh_results: Array[Dictionary] = []
	var names: Array[String] = []
	for mesh_instance in meshes:
		names.append(mesh_instance.name)
		if mesh_instance.mesh == null:
			errors.append("%s has no mesh" % mesh_instance.name)
			continue

		var surface_count := mesh_instance.mesh.get_surface_count()
		if surface_count != 1:
			errors.append("%s expected 1 surface, got %d" % [mesh_instance.name, surface_count])

		var uv_entries := 0
		var runtime_surfaces := 0
		for surface_index in surface_count:
			var material := mesh_instance.get_active_material(surface_index) as ShaderMaterial
			if material == null:
				errors.append("%s surface %d is not a ShaderMaterial" % [mesh_instance.name, surface_index])
				continue
			if material != expected_material:
				errors.append("%s surface %d does not use the shared SIM_GRID material" % [mesh_instance.name, surface_index])
			if material.resource_path != EXPECTED_MATERIAL_PATH:
				errors.append("%s surface %d material path is %s" % [mesh_instance.name, surface_index, material.resource_path])
			if material.shader == null or material.shader.resource_path != EXPECTED_SHADER_PATH:
				errors.append("%s surface %d shader path mismatch" % [mesh_instance.name, surface_index])
			runtime_surfaces += 1

			var arrays := mesh_instance.mesh.surface_get_arrays(surface_index)
			var uv_data: Variant = arrays[Mesh.ARRAY_TEX_UV]
			if uv_data != null and uv_data.size() > 0:
				uv_entries += uv_data.size()

		if uv_entries != 0:
			errors.append("%s unexpectedly contains %d UV entries" % [mesh_instance.name, uv_entries])

		mesh_results.append({
			"name": mesh_instance.name,
			"surface_count": surface_count,
			"runtime_surfaces": runtime_surfaces,
			"uv_entries": uv_entries,
			"position": mesh_instance.position,
			"rotation": mesh_instance.rotation,
			"scale": mesh_instance.scale,
		})

	if names != EXPECTED_NODES:
		errors.append("Expected mesh nodes %s, got %s" % [EXPECTED_NODES, names])

	if not errors.is_empty():
		for error in errors:
			push_error(error)
		imported_root.free()
		quit(4)
		return

	var viewport := SubViewport.new()
	viewport.name = "SimGridVerificationViewport"
	viewport.size = Vector2i(640, 480)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	get_root().add_child(viewport)

	var stage := Node3D.new()
	stage.name = "SimGridVerificationStage"
	viewport.add_child(stage)
	stage.add_child(imported_root)

	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.001, 0.002, 0.003, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.08, 0.12, 0.14, 1.0)
	environment.ambient_light_energy = 0.4
	world_environment.environment = environment
	stage.add_child(world_environment)

	var camera := Camera3D.new()
	camera.position = Vector3(10.0, 7.0, 10.0)
	camera.fov = 55.0
	camera.current = true
	stage.add_child(camera)
	camera.look_at(Vector3(1.5, 1.0, -1.4), Vector3.UP)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
	light.light_energy = 0.35
	stage.add_child(light)

	for _frame in 8:
		await process_frame

	var image := viewport.get_texture().get_image()
	if image == null or image.is_empty():
		push_error("Offscreen SIM_GRID render returned an empty image")
		viewport.queue_free()
		quit(5)
		return

	image.convert(Image.FORMAT_RGBA8)
	var absolute_output := ProjectSettings.globalize_path(output_path)
	var save_error := image.save_png(absolute_output)
	if save_error != OK:
		push_error("Could not save SIM_GRID render to %s" % absolute_output)
		viewport.queue_free()
		quit(6)
		return

	var luminance_sum := 0.0
	var luminance_max := 0.0
	var bright_samples := 0
	var sample_count := 0
	for y in range(0, image.get_height(), 4):
		for x in range(0, image.get_width(), 4):
			var color := image.get_pixel(x, y)
			var luminance := Vector3(color.r, color.g, color.b).dot(Vector3(0.2126, 0.7152, 0.0722))
			luminance_sum += luminance
			luminance_max = max(luminance_max, luminance)
			if luminance > 0.18:
				bright_samples += 1
			sample_count += 1

	var average_luminance: float = luminance_sum / float(max(sample_count, 1))
	if bright_samples < 20 or luminance_max < 0.25:
		push_error("SIM_GRID render lacks visible emissive grid detail")
		viewport.queue_free()
		quit(7)
		return

	var result := {
		"scene": scene_path,
		"material": expected_material.resource_path,
		"shader": expected_material.shader.resource_path,
		"parameters": {
			"base_color": expected_material.get_shader_parameter("base_color"),
			"grid_color": expected_material.get_shader_parameter("grid_color"),
			"cell_size": expected_material.get_shader_parameter("cell_size"),
			"line_width": expected_material.get_shader_parameter("line_width"),
			"emission_strength": expected_material.get_shader_parameter("emission_strength"),
			"scan_speed": expected_material.get_shader_parameter("scan_speed"),
			"scan_strength": expected_material.get_shader_parameter("scan_strength"),
			"noise_strength": expected_material.get_shader_parameter("noise_strength"),
		},
		"meshes": mesh_results,
		"render": {
			"path": output_path,
			"size": image.get_size(),
			"average_luminance": average_luminance,
			"maximum_luminance": luminance_max,
			"bright_samples": bright_samples,
			"sample_count": sample_count,
		},
	}
	print("SIM_GRID_PIPELINE_VERIFY=" + JSON.stringify(result))
	viewport.queue_free()
	quit(0)


func _collect_meshes(node: Node, output: Array[MeshInstance3D]) -> void:
	var mesh_instance := node as MeshInstance3D
	if mesh_instance != null:
		output.append(mesh_instance)
	for child in node.get_children():
		_collect_meshes(child, output)
