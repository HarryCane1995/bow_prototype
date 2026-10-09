extends SceneTree

func _initialize():
	call_deferred("run")

func run():
	var packed = load("res://Samples.blend") as PackedScene
	if packed == null:
		push_error("Cannot load direct blend import")
		quit(1)
		return
	var scene = Node3D.new()
	root.add_child(scene)
	var sample = packed.instantiate()
	scene.add_child(sample)
	var meshes = sample.find_children("*", "MeshInstance3D", true, false)
	var textured = 0
	var uv_meshes = 0
	var normal_maps = 0
	var emission_maps = 0
	var triangles = 0
	var materials = {}
	for m in meshes:
		for s in range(m.mesh.get_surface_count()):
			var arrays = m.mesh.surface_get_arrays(s)
			if arrays[Mesh.ARRAY_TEX_UV] != null and arrays[Mesh.ARRAY_TEX_UV].size() > 0:
				uv_meshes += 1
			triangles += arrays[Mesh.ARRAY_INDEX].size() / 3 if arrays[Mesh.ARRAY_INDEX] != null else arrays[Mesh.ARRAY_VERTEX].size() / 3
			var mat = m.get_active_material(s)
			if mat is BaseMaterial3D:
				materials[mat.resource_name] = true
				if mat.albedo_texture != null and mat.albedo_texture.get_width() > 0:
					textured += 1
				if mat.normal_enabled and mat.normal_texture != null:
					normal_maps += 1
				if mat.emission_enabled and mat.emission_texture != null:
					emission_maps += 1
	var env = WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.16, 0.20, 0.25)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.65, 0.75, 0.88)
	env.environment.ambient_light_energy = 0.8
	scene.add_child(env)
	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-28, -30, 0)
	sun.light_energy = 2.0
	sun.light_color = Color(1, 0.87, 0.73)
	sun.shadow_enabled = true
	scene.add_child(sun)
	var camera = Camera3D.new()
	scene.add_child(camera)
	camera.position = Vector3(830, 470, 800)
	camera.look_at(Vector3(210, 180, -120))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 650
	camera.far = 5000
	camera.current = true
	var report = {"passed": meshes.size() > 20 and textured > 20 and normal_maps > 20, "direct_blend_import": true, "mesh_instances": meshes.size(), "uv_surfaces": uv_meshes, "textured_surfaces": textured, "normal_surfaces": normal_maps, "emission_surfaces": emission_maps, "triangles": triangles, "material_count": materials.size(), "engine": Engine.get_version_info().string}
	var file = FileAccess.open("res://runtime_validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	for frame in range(10):
		await process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://Godot_Six_Samples.png")
	print("HIGHRISE_GODOT_SANITY ", JSON.stringify(report))
	quit(0 if report.passed else 1)
