extends SceneTree
## Read-only materials and imported scene QA. Only its own JSON evidence is written.
const MAT := "res://Assets/Materials/Environment/FacadeFactory/"
const SCENE := "res://Scenes/Debug/Level_Facade_Review.tscn"
var failures: Array[String] = []

func _init() -> void:
	call_deferred("run")

func check(value: bool, message: String) -> void:
	if not value:
		failures.append(message)
		push_error(message)

func material_files(path: String) -> Array[String]:
	var result: Array[String] = []
	for file in DirAccess.get_files_at(path):
		if file.ends_with(".tres") and file != "review_settings.tres":
			result.append(path + file)
	for sub in DirAccess.get_directories_at(path):
		result.append_array(material_files(path + sub + "/"))
	return result

func run() -> void:
	var records: Array[Dictionary] = []
	for path in material_files(MAT):
		var mat := load(path) as ORMMaterial3D
		check(mat != null, "Expected ORM material: " + path)
		if mat == null:
			continue
		var textures := [mat.albedo_texture, mat.emission_texture, mat.normal_texture, mat.orm_texture]
		var sizes: Array[Vector2i] = []
		for tex in textures:
			check(tex != null, "Missing texture: " + path)
			if tex == null:
				continue
			check(tex.get_width() > 0 and tex.get_height() > 0, "Empty texture: " + path)
			sizes.append(Vector2i(tex.get_width(), tex.get_height()))
		for size in sizes:
			check(size == sizes[0], "Channel resolution mismatch: " + path)
		check(mat.normal_enabled and mat.normal_scale <= 0.6, "Normal setup: " + path)
		check(mat.ao_enabled and not mat.texture_repeat, "AO / unique sheet setup: " + path)
		check(mat.emission_enabled and mat.emission_energy_multiplier > 0.0, "Emission setup: " + path)
		check(mat.emission_operator == BaseMaterial3D.EMISSION_OP_MULTIPLY, "Emission should multiply white with texture")
		records.append({"material": path, "resolution": str(sizes[0]), "channels_loaded": sizes.size()})
	check(records.size() == 36, "Expected 24 main + 12 resolution samples")
	var scene = load(SCENE).instantiate()
	root.add_child(scene)
	await process_frame
	check(scene.towers.size() == 8, "Expected 8 existing tower copies")
	check(scene.surface_count == 21, "Expected 21 textured surfaces")
	var textured_surfaces := 0
	for tower in scene.towers:
		for node in tower.find_children("*", "MeshInstance3D", true, false):
			for surface in node.mesh.get_surface_count():
				if node.get_surface_override_material(surface) is ORMMaterial3D:
					var arrays: Array = node.mesh.surface_get_arrays(surface)
					check(arrays[Mesh.ARRAY_TEX_UV] != null and arrays[Mesh.ARRAY_TEX_UV].size() > 0, "UV missing: " + str(node.name))
					check(arrays[Mesh.ARRAY_TANGENT] != null and arrays[Mesh.ARRAY_TANGENT].size() > 0, "Tangents missing: " + str(node.name))
					textured_surfaces += 1
	var settings: Resource = scene.material_settings.duplicate()
	var original := load(MAT + "corporate_monolith_s42_512x1024.tres") as ORMMaterial3D
	settings.emission_strength = 0.5
	settings.uv_scale = Vector2(0.75, 0.5)
	settings.macro_tint = Color(0.8, 0.9, 1.0)
	var altered: ORMMaterial3D = settings.make_material(original)
	check(is_equal_approx(altered.emission_energy_multiplier, original.emission_energy_multiplier * 0.5), "EmissionStrength control")
	check(altered.uv1_scale == Vector3(0.75, 0.5, 1), "UVScale control")
	check(altered.albedo_color == Color(0.8, 0.9, 1), "MacroTint control")
	check(original.uv1_scale == Vector3.ONE and original.albedo_color == Color.WHITE, "Resource mutated")
	scene._toggle_emission()
	for mat in scene.materials:
		check(is_zero_approx(mat.emission_energy_multiplier), "Emission toggle")
	scene._toggle_emission()
	for i in scene.materials.size():
		check(is_equal_approx(scene.materials[i].emission_energy_multiplier, scene.originals[i]), "Emission restore")
	var report := {"passed": failures.is_empty(), "materials": records, "towers": scene.towers.size(),
		"textured_surfaces": textured_surfaces, "settings_controls": true, "failures": failures}
	var file := FileAccess.open("res://Tools/Art/FacadeFactory/review/godot_validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  ") + "\n")
	print("FACADE_GODOT_QA ", JSON.stringify({"passed": failures.is_empty(), "materials": records.size(), "surfaces": textured_surfaces}))
	quit(0 if failures.is_empty() else 1)
