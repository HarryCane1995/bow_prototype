extends Node3D
## Isolated art viewer: no Player, map wrapper, input-map writes or gameplay nodes.

@export var material_settings: Resource
const OUT := "res://Tools/Art/FacadeFactory/review/"
const MAT_DIR := "res://Assets/Materials/Environment/FacadeFactory/"
var camera: Camera3D
var towers: Array[Node3D] = []
var bounds: Array[AABB] = []
var materials: Array[ORMMaterial3D] = []
var originals: Array[float] = []
var info: Label
var selected := -1
var target := Vector3(0, 18, 20)
var yaw := 0.25
var pitch := 0.17
var distance := 175.0
var emission_on := true
var normal_on := true
var surface_count := 0

func _ready() -> void:
	DisplayServer.window_set_title("BOWPROTOTYPE / FACADE FACTORY 0.1")
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	get_window().size = Vector2i(1440, 900)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_build_stage()
	for child in $ReviewBuildings.get_children():
		if child is Node3D and str(child.name).begins_with("L01_Skyline_"):
			towers.append(child)
	towers.sort_custom(func(a: Node3D, b: Node3D) -> bool: return str(a.name) < str(b.name))
	for tower in towers:
		_apply(tower)
		bounds.append(_bounds(tower))
	_build_ui()
	select(-1)
	print("FACADE_REVIEW_READY towers=%d surfaces=%d materials=%d" % [towers.size(), surface_count, materials.size()])
	var args := OS.get_cmdline_user_args()
	if "--capture" in args or "--capture-and-exit" in args:
		call_deferred("_capture", "--capture-and-exit" in args)

func _build_stage() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.027, 0.042, 0.055)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.60, 0.72, 0.77)
	env.ambient_light_energy = 0.65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_intensity = 0.45
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-32, -28, 0)
	sun.light_color = Color(0.82, 0.92, 1.0)
	sun.light_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 220.0
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-18, 155, 0)
	fill.light_color = Color(0.41, 0.73, 0.67)
	fill.light_energy = 0.25
	add_child(fill)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(210, 135)
	floor_mesh.mesh = plane
	floor_mesh.position = Vector3(0, -0.25, 20)
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color(0.055, 0.075, 0.085)
	floor_mat.roughness = 1.0
	floor_mesh.material_override = floor_mat
	add_child(floor_mesh)
	camera = Camera3D.new()
	camera.fov = 48
	camera.far = 600
	add_child(camera)
	camera.current = true

func _apply(node: Node) -> void:
	if node is MeshInstance3D:
		for i in node.mesh.get_surface_count():
			var old: Material = node.mesh.surface_get_material(i)
			if old != null and old.resource_name.begins_with("M_Level01_Facade_"):
				var stem: String = old.resource_name.trim_prefix("M_Level01_Facade_")
				var source := load(MAT_DIR + stem + ".tres") as ORMMaterial3D
				assert(source != null, stem)
				var mat: ORMMaterial3D = material_settings.make_material(source)
				node.set_surface_override_material(i, mat)
				materials.append(mat)
				originals.append(mat.emission_energy_multiplier)
				surface_count += 1
	for child in node.get_children():
		_apply(child)

func _bounds(node: Node3D) -> AABB:
	var result := AABB()
	var first := true
	for mesh in node.find_children("*", "MeshInstance3D", true, false):
		var box: AABB = mesh.global_transform * mesh.get_aabb()
		result = box if first else result.merge(box)
		first = false
	return result

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := ColorRect.new()
	panel.color = Color(0.025, 0.039, 0.05, 0.94)
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	panel.offset_bottom = 107
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(panel)
	info = Label.new()
	info.position = Vector2(25, 16)
	info.add_theme_font_size_override("font_size", 20)
	info.add_theme_color_override("font_color", Color(0.77, 0.88, 0.84))
	layer.add_child(info)
	var controls := HBoxContainer.new()
	controls.position = Vector2(25, 115)
	layer.add_child(controls)
	for i in range(-1, 8):
		var button := Button.new()
		button.text = "ALL" if i < 0 else "%02d" % (i + 1)
		button.custom_minimum_size = Vector2(46, 32)
		button.pressed.connect(select.bind(i))
		controls.add_child(button)
	for item in [["EMISSION", _toggle_emission], ["NORMAL", _toggle_normal]]:
		var button := Button.new()
		button.text = item[0]
		button.pressed.connect(item[1])
		controls.add_child(button)

func select(index: int) -> void:
	selected = index
	for i in towers.size():
		towers[i].visible = index < 0 or i == index
	if index < 0:
		camera.projection = Camera3D.PROJECTION_ORTHOGONAL
		camera.size = 102
		target = Vector3(0, 22, 21)
		distance = 178
		yaw = 0.60
		pitch = 0.45
	else:
		camera.projection = Camera3D.PROJECTION_PERSPECTIVE
		var box := bounds[index]
		target = box.get_center()
		distance = max(box.size.y, box.size.x * 1.5) * 1.70
		yaw = 0.36
		pitch = 0.06
	_update_camera()
	_update_label()

func _update_camera() -> void:
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func _update_label() -> void:
	var description := "8 EXISTING SKYSCRAPERS / 6 FACADE GRAMMARS"
	if selected >= 0:
		var tower := towers[selected]
		description = "%02d  %s" % [selected + 1, str(tower.name).trim_prefix("L01_Skyline_")]
		for mesh in tower.find_children("*", "MeshInstance3D", true, false):
			for i in mesh.mesh.get_surface_count():
				var mat: Material = mesh.get_surface_override_material(i)
				if mat != null:
					description += "   /   " + mat.resource_name
					break
			if description.contains(" / "):
				break
	info.text = "FACADE FACTORY / 0.1    " + description + "\n0: all   1-8 / arrows: building   drag RMB: orbit   wheel: zoom   E: emission   N: normal\nEMISSION %s  /  NORMAL %s" % ["ON" if emission_on else "OFF", "ON" if normal_on else "OFF"]

func _toggle_emission() -> void:
	emission_on = not emission_on
	for i in materials.size():
		materials[i].emission_energy_multiplier = originals[i] if emission_on else 0.0
	_update_label()

func _toggle_normal() -> void:
	normal_on = not normal_on
	for mat in materials:
		mat.normal_enabled = normal_on
	_update_label()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		yaw -= event.relative.x * 0.007
		pitch = clampf(pitch + event.relative.y * 0.005, -0.35, 1.0)
		_update_camera()
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(5.0, distance * 0.88)
			camera.size = maxf(15.0, camera.size * 0.88)
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(320, distance / 0.88)
			camera.size = minf(220.0, camera.size / 0.88)
		_update_camera()
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode >= KEY_0 and event.keycode <= KEY_8:
			select(event.keycode - KEY_1)
		elif event.keycode == KEY_RIGHT:
			select(posmod(selected + 1, towers.size()))
		elif event.keycode == KEY_LEFT:
			select(posmod(selected - 1, towers.size()))
		elif event.keycode == KEY_E:
			_toggle_emission()
		elif event.keycode == KEY_N:
			_toggle_normal()

func _save_frame(filename: String) -> void:
	await get_tree().create_timer(0.6).timeout
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	assert(image.save_png(OUT + filename) == OK)
	print("FACADE_CAPTURE ", filename)

func _capture(exit_after: bool) -> void:
	await get_tree().create_timer(1.0).timeout
	await _save_frame("GODOT_FACADE_OVERVIEW.png")
	for index in [0, 1, 3, 4, 7]:
		select(index)
		await _save_frame("GODOT_FACADE_%02d.png" % (index + 1))
	select(7)
	_toggle_emission()
	await _save_frame("GODOT_EMISSION_OFF.png")
	_toggle_emission()
	await _save_frame("GODOT_EMISSION_ON.png")
	select(-1)
	if exit_after:
		get_tree().quit()
