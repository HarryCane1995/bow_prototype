extends SceneTree

func _initialize():
	call_deferred("run")

func run():
	var args = OS.get_cmdline_user_args()
	var path = args[0] if args.size() > 0 else "res://Highrise100.gltf"
	var packed = load(path) as PackedScene
	assert(packed != null)
	var scene = packed.instantiate()
	root.add_child(scene)
	var report = {"root": scene.name, "children": [], "mesh_count": 0, "surfaces": 0, "uv": 0, "tangents": 0, "triangles": 0, "materials": {}, "flat_surfaces": [], "errors": []}
	for child in scene.get_children(): report.children.append(child.name)
	for o in scene.find_children("*", "MeshInstance3D", true, false):
		report.mesh_count += 1
		for s in o.mesh.get_surface_count():
			report.surfaces += 1
			var arrays = o.mesh.surface_get_arrays(s)
			if arrays[Mesh.ARRAY_TEX_UV] != null and arrays[Mesh.ARRAY_TEX_UV].size() > 0: report.uv += 1
			if arrays[Mesh.ARRAY_TANGENT] != null and arrays[Mesh.ARRAY_TANGENT].size() > 0: report.tangents += 1
			report.triangles += arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX] != null else arrays[Mesh.ARRAY_VERTEX].size()/3
			var m = o.get_active_material(s)
			if not m is BaseMaterial3D:
				report.errors.append(str(o.name)+": missing material")
				continue
			if m.albedo_texture == null:
				report.flat_surfaces.append({"mesh": o.name, "surface": s, "material": m.resource_name, "emission": m.emission, "emission_energy": m.emission_energy_multiplier})
			if report.materials.has(m.resource_name):
				if report.materials[m.resource_name].instance_id != m.get_instance_id(): report.errors.append(m.resource_name+": duplicate instance")
				continue
			var textures = {}
			for key in ["albedo_texture", "normal_texture", "emission_texture", "ao_texture", "roughness_texture", "metallic_texture", "orm_texture"]:
				var tex = m.get(key)
				if tex != null: textures[key] = {"path":tex.resource_path, "size":str(tex.get_size()), "rid":str(tex.get_rid())}
			var item = {"instance_id": m.get_instance_id(), "class": m.get_class(), "textures": textures, "normal_enabled":m.normal_enabled, "normal_scale":m.normal_scale, "ao_enabled":m.ao_enabled, "ao_channel":m.ao_texture_channel, "roughness_channel":m.get("roughness_texture_channel"), "metallic_channel":m.get("metallic_texture_channel"), "emission_enabled":m.emission_enabled, "emission_energy":m.emission_energy_multiplier, "repeat":m.texture_repeat, "filter":m.texture_filter}
			report.materials[m.resource_name]=item
			if m.albedo_texture != null:
				if not m.normal_enabled or m.normal_texture == null:report.errors.append(m.resource_name+": normal missing")
				if not m.ao_enabled or m.ao_texture == null or m.ao_texture_channel != BaseMaterial3D.TEXTURE_CHANNEL_RED:report.errors.append(m.resource_name+": AO R missing")
				if m.get("roughness_texture_channel") != BaseMaterial3D.TEXTURE_CHANNEL_GREEN or m.get("metallic_texture_channel") != BaseMaterial3D.TEXTURE_CHANNEL_BLUE:report.errors.append(m.resource_name+": ORM G/B mismatch")
	var methods=[]
	for info in ClassDB.class_get_method_list("RenderingServer"):
		if str(info.name).contains("material_get") or str(info.name).contains("shader_get"):methods.append(info.name)
	report.shader_inspection_methods=methods
	report.material_methods=[]
	for info in ClassDB.class_get_method_list("StandardMaterial3D"):
		if str(info.name).contains("shader"):report.material_methods.append(info.name)
	report.passed=report.errors.is_empty() and report.uv==report.surfaces and report.tangents==report.surfaces
	var out = args[1] if args.size()>1 else "res://material_inspection.json"
	FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("HIGHRISE_IMPORT_QA ",JSON.stringify({"root":report.root,"buildings":report.children.size(),"materials":report.materials.size(),"surfaces":report.surfaces,"triangles":report.triangles,"errors":report.errors,"shader_methods":methods,"material_methods":report.material_methods}))
	quit(0 if report.passed else 1)
