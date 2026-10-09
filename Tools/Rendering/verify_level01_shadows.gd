extends SceneTree
## Isolated Level_01 shadow audit. Overrides affect this process only; no resources are saved.
const OUT := "res://.godot/level01-shadows/"
var level: Node3D
var sun: DirectionalLight3D
var environment: Environment
var floor_mesh: MeshInstance3D
var floor_material: Material
var contact: Node
var quad: MeshInstance3D
var camera: Camera3D
var results: Array = []

func _init() -> void:
	call_deferred("run")

func props(object: Object, keywords: Array) -> Dictionary:
	var output := {}
	for property in object.get_property_list():
		var key := str(property.name)
		for word in keywords:
			if word in key:
				var value = object.get(key)
				output[key] = str(value) if value is Object or value is Vector3 or value is Color else value
				break
	return output

func write_json(path: String, value: Variant) -> void:
	var file := FileAccess.open(OUT + path, FileAccess.WRITE)
	file.store_string(JSON.stringify(value, "\t"))
	file.close()

func walk(node: Node) -> Array[Node]:
	var nodes: Array[Node] = [node]
	for child in node.get_children():
		nodes.append_array(walk(child))
	return nodes

func run() -> void:
	DirAccess.make_dir_recursive_absolute(OUT)
	var config_path := "res://Tools/Rendering/level01_shadow_cases.json"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--config="):
			config_path = arg.trim_prefix("--config=")
	var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(config_path))
	assert(config.has("cases"), "Shadow review requires a cases array")
	level = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
	level.get_node("StartupWindowModeController").set("EnableStartupWindowMode", false)
	root.add_child(level)
	current_scene = level
	root.size = Vector2i(1440, 900)
	await create_timer(1.5).timeout
	sun = level.get_node("World/DirectionalLight3D")
	environment = level.get_node("World/WorldEnvironment").environment
	floor_mesh = level.find_child("L01_Arena01_TestFloor_01", true, false)
	floor_material = floor_mesh.get_active_material(0)
	contact = level.get_node("StylizedContactDarkening")
	quad = level.find_child("FullscreenQuad", true, false)
	var audit := {"engine": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method(),
		"driver": RenderingServer.get_current_rendering_driver_name(), "adapter": RenderingServer.get_video_adapter_name(),
		"lights": [], "environment": props(environment, ["ssao", "ssil", "sdfgi", "ssr", "glow", "fog", "tonemap", "adjustment", "ambient", "reflected"]),
		"viewport": props(root, ["msaa", "taa", "screen_space_aa", "scaling_3d", "use_debanding"]),
		"camera": props(root.get_camera_3d(), ["near", "far", "fov"]),
		"floor_material": props(floor_material, ["normal", "detail", "emission", "albedo", "orm", "ao_", "texture_filter"]),
		"contact_darkening": props(contact, ["Enabled", "Mode", "Strength", "Radius", "Bias", "Fade"]), "project": {}, "geometry": []}
	for node in walk(level):
		if node is Light3D:
			audit.lights.append({"path": str(node.get_path()), "class": node.get_class(), "visible": node.is_visible_in_tree(), "properties": props(node, ["shadow", "light_"])})
		if node is MeshInstance3D and node.mesh != null and "L01_" in str(node.name):
			audit.geometry.append({"name": str(node.name), "bounds": str(node.global_transform * node.get_aabb())})
	for property in ProjectSettings.get_property_list():
		var key := str(property.name)
		if key.begins_with("rendering/") and ("shadow" in key or "ssao" in key or "ssil" in key or "anti_aliasing" in key or "sdfgi" in key or "rendering_method" in key):
			audit.project[key] = {"value": ProjectSettings.get_setting_with_override(key), "hint": property.hint_string}
	var enums := {}
	for key in ClassDB.class_get_integer_constant_list("RenderingServer"):
		if "SHADOW_QUALITY" in key:
			enums[key] = ClassDB.class_get_integer_constant("RenderingServer", key)
	audit["shadow_filter_enums"] = enums
	write_json(str(config.get("audit_name", "audit_before")) + ".json", audit)
	print("SHADOW_AUDIT=" + OUT + str(config.get("audit_name", "audit_before")) + ".json")
	level.process_mode = Node.PROCESS_MODE_DISABLED
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	for node in walk(level):
		if node is CanvasLayer:
			node.visible = false
	camera = Camera3D.new()
	root.add_child(camera)
	camera.current = true
	camera.fov = 70
	camera.far = 2500
	quad.reparent(camera, false)
	quad.transform = Transform3D.IDENTITY
	level.get_node("Player").visible = false
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var base_sun := props(sun, ["shadow", "light_angular_distance"])
	var base_env := props(environment, ["ssao_enabled", "ssil_enabled"])
	var base_taa := root.use_taa
	var base_filter: int = ProjectSettings.get_setting_with_override("rendering/lights_and_shadows/directional_shadow/soft_shadow_filter_quality")
	var base_size: int = ProjectSettings.get_setting_with_override("rendering/lights_and_shadows/directional_shadow/size")
	for settings in config.get("cases", []):
		for key in base_sun:
			sun.set(key, base_sun[key])
		for key in base_env:
			environment.set(key, base_env[key])
		root.use_taa = base_taa
		quad.visible = true
		floor_mesh.material_override = null
		RenderingServer.directional_shadow_atlas_set_size(base_size, true)
		RenderingServer.directional_soft_shadow_filter_set_quality(base_filter)
		for key in settings.get("sun", {}):
			sun.set(key, settings.sun[key])
		for key in settings.get("environment", {}):
			environment.set(key, settings.environment[key])
		root.use_taa = settings.get("taa", base_taa)
		quad.visible = settings.get("contact", true)
		if settings.get("neutral", false):
			var gray := StandardMaterial3D.new()
			gray.albedo_color = Color(.45, .45, .45)
			gray.roughness = .85
			floor_mesh.material_override = gray
		elif settings.get("no_normal", false):
			var clean := floor_material.duplicate() as BaseMaterial3D
			clean.normal_enabled = false
			clean.detail_enabled = false
			floor_mesh.material_override = clean
		if settings.has("atlas") or settings.has("atlas_16_bits"):
			RenderingServer.directional_shadow_atlas_set_size(int(settings.get("atlas", base_size)), settings.get("atlas_16_bits", true))
		if settings.has("filter"):
			RenderingServer.directional_soft_shadow_filter_set_quality(int(settings.filter))
		var eye: Array = settings.get("eye", [-12, 8, 28])
		var aim: Array = settings.get("aim", [6, -.747, -6])
		camera.position = Vector3(eye[0], eye[1], eye[2])
		camera.look_at(Vector3(aim[0], aim[1], aim[2]))
		await create_timer(1.0).timeout
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT + settings.name + ".png")
		var timings: Array[float] = []
		var gpu: Array[float] = []
		var previous := Time.get_ticks_usec()
		for i in 90:
			await process_frame
			var now := Time.get_ticks_usec()
			timings.append((now - previous) / 1000.0)
			previous = now
			gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()))
		timings.sort()
		gpu.sort()
		var result := {"case": settings, "frame_ms_median": timings[45], "frame_ms_p95": timings[85], "fps_median": 1000 / timings[45], "gpu_ms_median": gpu[45]}
		results.append(result)
		write_json(str(config.get("report_name", "diagnostics")) + ".json", results)
		print("SHADOW_CASE=" + JSON.stringify(result))
	quit(0)
