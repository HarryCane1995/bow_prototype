extends SceneTree

const EXPECTED_SHADER_PATH := "res://Assets/Materials/Simulation/sim_grid.gdshader"
const EXPECTED_VARIANTS := {
	"SimGrid_01": {"semantic": "SIM_GRID", "material": "res://Assets/Materials/Simulation/sim_grid.tres"},
	"SimGrid_02": {"semantic": "SIM_GRID_02", "material": "res://Assets/Materials/Simulation/sim_grid_02.tres"},
	"SimGrid_03": {"semantic": "SIM_GRID_03", "material": "res://Assets/Materials/Simulation/sim_grid_03.tres"},
	"SimGrid_04": {"semantic": "SIM_GRID_04", "material": "res://Assets/Materials/Simulation/sim_grid_04.tres"},
	"SimGrid_05": {"semantic": "SIM_GRID_05", "material": "res://Assets/Materials/Simulation/sim_grid_05.tres"},
}
const PARAMETER_NAMES := [
	"base_color",
	"grid_color",
	"cell_size",
	"line_width",
	"emission_strength",
	"scan_speed",
	"scan_strength",
	"noise_strength",
]


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty() or args.size() > 2:
		push_error("Usage: godot --path . --script res://Tools/SimulationMaterials/verify_sim_grid_pipeline.gd -- <palette .blend> [output.png]")
		quit(2)
		return

	var scene_path: String = args[0]
	var output_path := "res://.godot/sim-grid-palette-render.png"
	if args.size() == 2:
		output_path = args[1]

	var packed := load(scene_path) as PackedScene
	var expected_shader := load(EXPECTED_SHADER_PATH) as Shader
	if packed == null or expected_shader == null:
		push_error("Could not load the palette scene or shared SIM_GRID shader")
		quit(3)
		return

	var expected_materials: Dictionary = {}
	for node_name in EXPECTED_VARIANTS:
		var material_path: String = EXPECTED_VARIANTS[node_name]["material"]
		var material := load(material_path) as ShaderMaterial
		if material == null or material.shader != expected_shader:
			push_error("%s does not use the shared SIM_GRID shader" % material_path)
			quit(3)
			return
		expected_materials[node_name] = material

	var imported_root := packed.instantiate()
	var meshes: Array[MeshInstance3D] = []
	_collect_meshes(imported_root, meshes)
	meshes.sort_custom(func(a: MeshInstance3D, b: MeshInstance3D) -> bool: return String(a.name) < String(b.name))

	var errors: Array[String] = []
	var mesh_results: Array[Dictionary] = []
	var names: Array[String] = []
	for mesh_instance in meshes:
		var node_name := String(mesh_instance.name)
		names.append(node_name)
		if not EXPECTED_VARIANTS.has(node_name):
			errors.append("Unexpected palette mesh %s" % node_name)
			continue
		if mesh_instance.mesh == null:
			errors.append("%s has no mesh" % node_name)
			continue

		var surface_count := mesh_instance.mesh.get_surface_count()
		if surface_count != 1:
			errors.append("%s expected 1 surface, got %d" % [node_name, surface_count])

		var uv_entries := 0
		var runtime_surfaces := 0
		var expected_material: ShaderMaterial = expected_materials[node_name]
		for surface_index in surface_count:
			var material := mesh_instance.get_active_material(surface_index) as ShaderMaterial
			if material == null:
				errors.append("%s surface %d is not a ShaderMaterial" % [node_name, surface_index])
				continue
			if material != expected_material:
				errors.append("%s surface %d did not map to %s" % [node_name, surface_index, expected_material.resource_path])
			if material.resource_path != expected_material.resource_path:
				errors.append("%s surface %d material path is %s" % [node_name, surface_index, material.resource_path])
			if material.shader != expected_shader or material.shader.resource_path != EXPECTED_SHADER_PATH:
				errors.append("%s surface %d shader path mismatch" % [node_name, surface_index])
			runtime_surfaces += 1

			var arrays := mesh_instance.mesh.surface_get_arrays(surface_index)
			var uv_data: Variant = arrays[Mesh.ARRAY_TEX_UV]
			if uv_data != null and uv_data.size() > 0:
				uv_entries += uv_data.size()

		if uv_entries != 0:
			errors.append("%s unexpectedly contains %d UV entries" % [node_name, uv_entries])

		var parameters := {}
		for parameter_name in PARAMETER_NAMES:
			parameters[parameter_name] = expected_material.get_shader_parameter(parameter_name)
		mesh_results.append({
			"name": node_name,
			"semantic": EXPECTED_VARIANTS[node_name]["semantic"],
			"material": expected_material.resource_path,
			"surface_count": surface_count,
			"runtime_surfaces": runtime_surfaces,
			"uv_entries": uv_entries,
			"position": mesh_instance.position,
			"parameters": parameters,
		})

	var expected_names: Array[String] = []
	for expected_name in EXPECTED_VARIANTS:
		expected_names.append(expected_name)
	expected_names.sort()
	if names != expected_names:
		errors.append("Expected palette meshes %s, got %s" % [expected_names, names])

	if not errors.is_empty():
		for error in errors:
			push_error(error)
		imported_root.free()
		quit(4)
		return

	var viewport := SubViewport.new()
	viewport.name = "SimGridPaletteVerificationViewport"
	viewport.size = Vector2i(960, 540)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	get_root().add_child(viewport)

	var stage := Node3D.new()
	stage.name = "SimGridPaletteVerificationStage"
	viewport.add_child(stage)
	stage.add_child(imported_root)

	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.001, 0.002, 0.003, 1.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.08, 0.10, 0.13, 1.0)
	environment.ambient_light_energy = 0.35
	world_environment.environment = environment
	stage.add_child(world_environment)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 4.5, 20.0)
	camera.fov = 55.0
	camera.current = true
	stage.add_child(camera)
	camera.look_at(Vector3(0.0, 1.5, 0.0), Vector3.UP)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
	light.light_energy = 0.3
	stage.add_child(light)

	for _frame in 8:
		await process_frame

	var image := viewport.get_texture().get_image()
	if image == null or image.is_empty():
		push_error("Offscreen SIM_GRID palette render returned an empty image")
		viewport.queue_free()
		quit(5)
		return

	image.convert(Image.FORMAT_RGBA8)
	var absolute_output := ProjectSettings.globalize_path(output_path)
	var save_error := image.save_png(absolute_output)
	if save_error != OK:
		push_error("Could not save SIM_GRID palette render to %s" % absolute_output)
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
	if bright_samples < 50 or luminance_max < 0.25:
		push_error("SIM_GRID palette render lacks visible emissive detail")
		viewport.queue_free()
		quit(7)
		return

	var result := {
		"scene": scene_path,
		"shader": expected_shader.resource_path,
		"shader_count": 1,
		"variants": mesh_results,
		"render": {
			"path": output_path,
			"size": image.get_size(),
			"average_luminance": average_luminance,
			"maximum_luminance": luminance_max,
			"bright_samples": bright_samples,
			"sample_count": sample_count,
		},
	}
	print("SIM_GRID_PALETTE_VERIFY=" + JSON.stringify(result))
	viewport.queue_free()
	quit(0)


func _collect_meshes(node: Node, output: Array[MeshInstance3D]) -> void:
	var mesh_instance := node as MeshInstance3D
	if mesh_instance != null:
		output.append(mesh_instance)
	for child in node.get_children():
		_collect_meshes(child, output)
