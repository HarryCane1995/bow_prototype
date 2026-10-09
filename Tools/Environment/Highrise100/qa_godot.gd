extends SceneTree

func _initialize():
	call_deferred("run")

func run():
	var packed = load("res://Samples.blend") as PackedScene
	if packed == null:
		quit(1)
		return
	var scene = Node3D.new()
	root.add_child(scene)
	var sample = packed.instantiate()
	scene.add_child(sample)
	var selected = JSON.parse_string(FileAccess.get_file_as_string("res://selected.json"))
	var report = {"assets": selected.size(), "mesh_instances": 0, "surfaces": 0, "uv_surfaces": 0, "normal_surfaces": 0, "tangent_surfaces": 0, "textured_surfaces": 0, "orm_surfaces": 0, "emission_surfaces": 0, "missing_materials": 0, "missing_textures": 0, "triangles": 0, "engine": Engine.get_version_info().string, "direct_blend_import": true, "production_integration": false}
	var per_asset = {}
	var mats = {}
	for o in sample.find_children("*", "MeshInstance3D", true, false):
		report.mesh_instances += 1
		var id = o.name.substr(0, 5)
		if not per_asset.has(id): per_asset[id] = {"triangles": 0, "surfaces": 0}
		for s in range(o.mesh.get_surface_count()):
			report.surfaces += 1
			per_asset[id].surfaces += 1
			var arrays = o.mesh.surface_get_arrays(s)
			if arrays[Mesh.ARRAY_TEX_UV] != null and arrays[Mesh.ARRAY_TEX_UV].size() > 0: report.uv_surfaces += 1
			if arrays[Mesh.ARRAY_TANGENT] != null and arrays[Mesh.ARRAY_TANGENT].size() > 0: report.tangent_surfaces += 1
			var tris = arrays[Mesh.ARRAY_INDEX].size() / 3 if arrays[Mesh.ARRAY_INDEX] != null else arrays[Mesh.ARRAY_VERTEX].size() / 3
			report.triangles += tris
			per_asset[id].triangles += tris
			var mat = o.get_active_material(s)
			if not mat is BaseMaterial3D:
				report.missing_materials += 1
				continue
			mats[mat.resource_name] = true
			if mat.albedo_texture != null:
				report.textured_surfaces += 1
				if mat.albedo_texture.get_width() <= 0: report.missing_textures += 1
				if mat.normal_enabled and mat.normal_texture != null: report.normal_surfaces += 1
				if mat.emission_enabled and mat.emission_texture != null: report.emission_surfaces += 1
				if mat is StandardMaterial3D and mat.roughness_texture != null and mat.metallic_texture != null and mat.roughness_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_GREEN and mat.metallic_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_BLUE: report.orm_surfaces += 1
	var expected_triangles = 0
	for r in selected: expected_triangles += r.triangles
	report.per_asset = per_asset
	report.expected_triangles = expected_triangles
	report.materials = mats.keys()
	report.passed = per_asset.size() == 12 and report.triangles == expected_triangles and report.missing_materials == 0 and report.missing_textures == 0 and report.uv_surfaces == report.surfaces and report.normal_surfaces == report.textured_surfaces and report.orm_surfaces == report.textured_surfaces and report.emission_surfaces == report.textured_surfaces
	var env = WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.16, 0.20, 0.25)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.65, 0.75, 0.88)
	env.environment.ambient_light_energy = 0.85
	scene.add_child(env)
	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-28,-30,0)
	sun.light_energy = 2.0
	scene.add_child(sun)
	var camera = Camera3D.new()
	scene.add_child(camera)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.far = 5000
	camera.current = true
	var visual = DisplayServer.get_name() != "headless"
	if visual:
		DirAccess.make_dir_recursive_absolute("res://Views")
		for r in selected:
			for o in sample.find_children("*", "MeshInstance3D", true, false): o.visible = o.name.begins_with(r.id)
			var p = Vector3(r.position[0], r.height * 0.47, -r.position[1])
			camera.position = p + Vector3(230, 110, 330)
			camera.look_at(p)
			camera.size = max(r.height*1.16, 140)
			for frame in range(3): await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("res://Views/" + r.id + ".png")
		for o in sample.find_children("*", "MeshInstance3D", true, false): o.visible = true
		camera.position = Vector3(1200,680,900)
		camera.look_at(Vector3(360,160,-240))
		camera.size = 1050
		for frame in range(3): await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://Godot_12_Samples.png")
	report.visual_rendered = visual
	var file = FileAccess.open("res://runtime_validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"))
	print("UV_MATERIAL_GODOT_SANITY ", JSON.stringify(report))
	quit(0 if report.passed else 1)
