extends SceneTree
## Technical verifier and test-scene builder. No Player integration or gameplay.
const BASE := "res://Assets/Characters/BaseHumanoid/"
var failures: Array[String] = []
var report: Dictionary = {"bodies": {}}

func _initialize() -> void:
	call_deferred("run")

func expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
		push_error(message)

func owned(node: Node, parent: Node, scene: Node) -> Node:
	parent.add_child(node)
	node.owner = scene
	return node

func material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.85
	return mat

func box(node_name: String, size: Vector3, position: Vector3, mat: Material, scene: Node3D) -> void:
	var mesh := MeshInstance3D.new()
	mesh.name = node_name
	var shape := BoxMesh.new()
	shape.size = size
	mesh.mesh = shape
	mesh.material_override = mat
	mesh.position = position
	owned(mesh, scene, scene)

func label3d(text: String, position: Vector3, scene: Node3D, font_size: int = 38) -> void:
	var label := Label3D.new()
	label.name = "Label_" + str(scene.get_child_count())
	label.text = text
	label.font_size = font_size
	label.pixel_size = 0.002
	label.position = position
	label.modulate = Color(0.83, 0.86, 0.90)
	label.outline_size = 0
	owned(label, scene, scene)

func run() -> void:
	var scene := Node3D.new()
	scene.name = "Humanoid_Base_Test"
	root.add_child(scene)
	var hierarchy: Array = []
	for kind in ["Male", "Female"]:
		var path: String = BASE + "Exports/Humanoid_" + kind + ".glb"
		var packed := load(path) as PackedScene
		expect(packed != null, "Missing PackedScene " + path)
		if packed == null: continue
		var model := packed.instantiate() as Node3D
		model.name = kind
		model.position.x = -0.70 if kind == "Male" else 0.65
		owned(model, scene, scene)
		var skeletons := model.find_children("*", "Skeleton3D", true, false)
		var meshes := model.find_children("*", "MeshInstance3D", true, false)
		expect(skeletons.size() == 1, kind + " skeleton count")
		expect(meshes.size() == 1, kind + " body mesh count")
		expect(model.find_children("*", "AnimationPlayer", true, false).is_empty(), kind + " unexpected animation player")
		if skeletons.size() != 1 or meshes.size() != 1: continue
		var sk := skeletons[0] as Skeleton3D
		var mesh := meshes[0] as MeshInstance3D
		expect(sk.get_bone_count() == 53, kind + " bone count")
		expect(sk.find_bone("root") >= 0 and sk.get_bone_parent(sk.find_bone("root")) == -1, kind + " root bone")
		var current_hierarchy: Array = []
		for i in sk.get_bone_count():
			current_hierarchy.append([sk.get_bone_name(i), sk.get_bone_parent(i)])
			expect(sk.get_bone_rest(i).is_finite(), kind + " invalid bone rest")
			expect(sk.get_bone_rest(i).basis.get_scale().is_equal_approx(Vector3.ONE), kind + " nonunit bone scale " + sk.get_bone_name(i))
		if hierarchy.is_empty(): hierarchy = current_hierarchy
		else: expect(current_hierarchy == hierarchy, "Male/female hierarchy mismatch")
		expect(mesh.skin != null, kind + " missing skin")
		expect(mesh.skin.get_bind_count() == 53, kind + " bind count")
		expect(mesh.get_node(mesh.skeleton) == sk, kind + " wrong skin skeleton binding")
		expect(mesh.scale.is_equal_approx(Vector3.ONE), kind + " mesh scale")
		expect(sk.scale.is_equal_approx(Vector3.ONE), kind + " skeleton scale")
		var aabb := mesh.get_aabb()
		var expected_height := 1.8 if kind == "Male" else 1.7
		expect(absf(aabb.size.y - expected_height) < 0.007, kind + " wrong height")
		expect(absf(aabb.position.y) < 0.002, kind + " not on floor")
		var foot := sk.get_bone_global_rest(sk.find_bone("foot.L")).origin
		var toes := sk.get_bone_global_rest(sk.find_bone("toes.L")).origin
		expect(toes.z > foot.z + 0.1, kind + " model front is not +Z")
		var triangles := 0
		var vertices := 0
		var weighted_vertices := 0
		var max_weight_error := 0.0
		for s in mesh.mesh.get_surface_count():
			var arrays := mesh.mesh.surface_get_arrays(s)
			var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var ix: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
			vertices += v.size()
			triangles += ix.size() / 3
			expect(weights.size() == v.size() * 4, kind + " missing skin weights")
			for i in v.size():
				var total := 0.0
				for k in 4:
					total += weights[i * 4 + k]
					if weights[i * 4 + k] > 0:
						expect(indices[i * 4 + k] >= 0 and indices[i * 4 + k] < 53, kind + " invalid bone index")
				if total > 0: weighted_vertices += 1
				max_weight_error = maxf(max_weight_error, absf(total - 1.0))
			expect(mesh.mesh.surface_get_material(s) is StandardMaterial3D, kind + " missing debug material")
		expect(max_weight_error < 0.0002, kind + " weights are not normalized")
		report.bodies[kind] = {"skeleton_bones": sk.get_bone_count(), "skin_binds": mesh.skin.get_bind_count(),
			"vertices": vertices, "triangles": triangles, "height_m": aabb.size.y, "ground_y": aabb.position.y,
			"weighted_vertices": weighted_vertices, "max_weight_error": max_weight_error,
			"model_front": "+Z", "hierarchy": current_hierarchy}
	var floor_mat := material(Color(0.085, 0.098, 0.12))
	box("Floor", Vector3(8, 0.06, 8), Vector3(0, -0.03, 0), floor_mat, scene)
	var ruler_mat := material(Color(0.60, 0.68, 0.75))
	box("Scale_1_8m", Vector3(0.008, 1.8, 0.008), Vector3(1.52, 0.9, 0), ruler_mat, scene)
	for i in 19:
		box("Scale_Tick_%02d" % i, Vector3(0.065 if i % 5 == 0 or i == 18 else 0.035, 0.003, 0.006), Vector3(1.55, float(i) / 10.0, 0), ruler_mat, scene)
	label3d("1.8 m", Vector3(1.54, 1.88, 0), scene, 28)
	label3d("MALE / 1.80 m", Vector3(-0.7, 0.10, 0.40), scene, 28)
	label3d("FEMALE / 1.70 m", Vector3(0.65, 0.10, 0.40), scene, 28)
	var camera := Camera3D.new()
	camera.name = "ReviewCamera"
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.25
	camera.position = Vector3(0.07, 1.16, 5.0)
	camera.rotation_degrees.x = -2.5
	camera.current = true
	owned(camera, scene, scene)
	var key := DirectionalLight3D.new()
	key.name = "KeyLight"
	key.rotation_degrees = Vector3(-35, -35, 0)
	key.light_energy = 1.2
	key.shadow_enabled = true
	owned(key, scene, scene)
	var fill := DirectionalLight3D.new()
	fill.name = "FillLight"
	fill.rotation_degrees = Vector3(-15, 145, 0)
	fill.light_energy = 0.45
	owned(fill, scene, scene)
	var env := WorldEnvironment.new()
	env.name = "NeutralEnvironment"
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.055, 0.067, 0.085)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.74, 0.8, 0.9)
	env.environment.ambient_light_energy = 0.5
	owned(env, scene, scene)
	var ui := CanvasLayer.new()
	ui.name = "ReviewTitle"
	owned(ui, scene, scene)
	var title := Label.new()
	title.name = "Title"
	title.text = "HUMANOID BASE / BH_01\n53 BONES  |  NEUTRAL A-POSE  |  METERS"
	title.position = Vector2(30, 22)
	title.add_theme_font_size_override("font_size", 20)
	title.modulate = Color(0.8, 0.85, 0.92)
	owned(title, ui, scene)
	var result := PackedScene.new()
	expect(result.pack(scene) == OK, "Pack test scene failed")
	expect(ResourceSaver.save(result, BASE + "Humanoid_Base_Test.tscn") == OK, "Save test scene failed")
	report["failures"] = failures
	report["result"] = "PASS" if failures.is_empty() else "FAIL"
	var file := FileAccess.open(BASE + "Review/godot_import_qa.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	print("HUMANOID_IMPORT_", report.result, " ", JSON.stringify(report.bodies))
	quit(0 if failures.is_empty() else 1)
