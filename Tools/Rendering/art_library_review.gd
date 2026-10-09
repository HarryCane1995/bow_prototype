extends Node3D
## Isolated procedural-art inspection. It never loads gameplay or level geometry.
var camera: Camera3D
var stage: Node3D
var pick: OptionButton
var category: OptionButton
var shape_pick: OptionButton
var caption: Label
var entries: Array = []
var current_effect: Node3D
var yaw := 0.18
var pitch := 0.10
var distance := 6.5
var dragging := false
var kind := "Materials"

func _ready() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("101a21")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("c0d0d2")
	env.ambient_light_energy = 0.65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.environment = env
	add_child(world)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-32,-32,0)
	light.light_energy = 1.8
	add_child(light)
	var rim := DirectionalLight3D.new()
	rim.rotation_degrees = Vector3(-15,145,0)
	rim.light_color = Color("91b5c6")
	rim.light_energy = 0.7
	add_child(rim)
	camera = Camera3D.new()
	camera.fov = 43
	add_child(camera)
	camera.current = true
	stage = Node3D.new()
	add_child(stage)
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	canvas.add_child(panel)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation",12)
	panel.add_child(row)
	var title := Label.new()
	title.text = "  BOW / ART LIBRARY  "
	row.add_child(title)
	category = OptionButton.new()
	for label in ["Materials","VFX","Billboards"]: category.add_item(label)
	row.add_child(category)
	category.item_selected.connect(func(i): select_category(category.get_item_text(i)))
	pick = OptionButton.new()
	pick.custom_minimum_size.x = 280
	row.add_child(pick)
	pick.item_selected.connect(show_entry)
	shape_pick = OptionButton.new()
	for label in ["BOX","PLANE 3x3","WALL CORNER","CYLINDER","COLUMN CLUSTER"]:shape_pick.add_item(label)
	row.add_child(shape_pick)
	shape_pick.item_selected.connect(func(_i): show_entry(pick.selected))
	for label in ["PREV","NEXT","FRAME","RESTART"]:
		var button := Button.new()
		button.text = label
		row.add_child(button)
		button.pressed.connect(func(): action(label))
	caption = Label.new()
	caption.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	caption.position = Vector2(24,-74)
	caption.add_theme_font_size_override("font_size",17)
	canvas.add_child(caption)
	select_category("Materials")

func action(label: String) -> void:
	if label in ["PREV","NEXT"]:
		var i := posmod(pick.selected + (1 if label == "NEXT" else -1),entries.size())
		pick.select(i)
		show_entry(i)
	elif label == "FRAME":
		yaw = 0.18
		pitch = 0.10
		update_camera()
	elif current_effect != null:
		current_effect.restart()

func read_json(path: String) -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string(path))

func select_category(value: String) -> void:
	kind = value
	category.select(["Materials","VFX","Billboards"].find(value))
	pick.clear()
	match value:
		"Materials": entries = read_json("res://Assets/ProceduralArt/Materials/manifest.json").materials
		"VFX": entries = read_json("res://Assets/ProceduralArt/VFX/library.json").effects
		"Billboards": entries = read_json("res://Assets/ProceduralArt/Billboards/manifest.json").items
	for entry in entries:pick.add_item(str(entry.get("id",entry.get("effect","Asset"))).replace("_"," "))
	shape_pick.visible = value == "Materials"
	pick.select(0)
	show_entry(0)

func add_mesh(mesh: Mesh, material: Material, position_at: Vector3, rotation_at := Vector3.ZERO) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.material_override = material
	node.position = position_at
	node.rotation_degrees = rotation_at
	stage.add_child(node)
	return node

func show_entry(index: int) -> void:
	for child in stage.get_children():
		stage.remove_child(child)
		child.queue_free()
	current_effect = null
	var entry: Dictionary = entries[index]
	var label := str(entry.get("id",entry.get("effect","")))
	distance = 6.5
	if kind == "Materials":
		var mat: ORMMaterial3D = load(entry.material).duplicate()
		var shape := shape_pick.selected
		if shape == 0:
			var box := BoxMesh.new()
			box.size = Vector3(2.8,2.8,2.8)
			add_mesh(box,mat,Vector3.ZERO,Vector3(0,-18,0))
		elif shape in [1,2]:
			var quad := QuadMesh.new()
			quad.size = Vector2(3.1,3.1)
			if shape == 1:
				mat.uv1_scale = Vector3(3,3,1)
				add_mesh(quad,mat,Vector3.ZERO)
			else:
				add_mesh(quad,mat,Vector3(-1.1,0,0),Vector3(0,28,0))
				add_mesh(quad,mat,Vector3(1.1,0,0),Vector3(0,-28,0))
		else:
			var cyl := CylinderMesh.new()
			cyl.top_radius = 0.75
			cyl.bottom_radius = 0.75
			cyl.height = 3.1
			cyl.radial_segments = 32
			cyl.cap_top = false
			cyl.cap_bottom = false
			if shape == 3:add_mesh(cyl,mat,Vector3.ZERO)
			else:
				for x in [-1.6,0,1.6]:add_mesh(cyl,mat,Vector3(x,0,abs(x)*-0.4))
				distance = 8.3
		caption.text = "%02d / 50   %s\n%s  |  Drag orbit · Wheel zoom" % [index+1,label,entry.description]
	elif kind == "Billboards":
		var sign: Node3D = load(entry.scene).instantiate()
		stage.add_child(sign)
		var wall := BoxMesh.new()
		wall.size = Vector3(6,4,.12)
		var wall_mat := StandardMaterial3D.new()
		wall_mat.albedo_color = Color("26343b")
		wall_mat.roughness = 0.85
		add_mesh(wall,wall_mat,Vector3(0,0,-.19))
		caption.text = "%02d / 12   %s\nDrag orbit · Wheel zoom" % [index+1,label]
	else:
		current_effect = load(entry.scene).instantiate()
		stage.add_child(current_effect)
		current_effect.loop = true
		distance = 11.5
		caption.text = "%02d / 10   %s\n3D mesh assembly · RESTART replays · Drag orbit · Wheel zoom" % [index+1,label]
	update_camera()

func update_camera() -> void:
	var target := Vector3(0,0.7,0) if kind == "VFX" else Vector3.ZERO
	camera.position = target + Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
	camera.look_at(target)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:dragging = event.pressed
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			distance = clampf(distance*(0.90 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.10),2,35)
			update_camera()
	elif event is InputEventMouseMotion and dragging:
		yaw -= event.relative.x*.008
		pitch = clampf(pitch+event.relative.y*.006,-1.4,1.4)
		update_camera()
	elif event is InputEventKey and event.pressed:
		if event.keycode == KEY_RIGHT:action("NEXT")
		if event.keycode == KEY_LEFT:action("PREV")
		if event.keycode == KEY_R:action("RESTART")
