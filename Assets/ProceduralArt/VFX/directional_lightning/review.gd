extends Node3D
@onready var effect: Node3D = $Explosion
@onready var camera: Camera3D = $Camera3D
var yaw := 0.6
var pitch := 0.28
var distance := 9.0
var dragging := false
var pause_button: Button
var target := Vector3(0, 0.9, 0)
var review_distance := 9.0

func _ready() -> void:
	effect.loop = true
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(effect.manifest_path))
	var recipe: Dictionary = manifest.recipe
	var parameters: Dictionary = recipe.parameters
	if recipe.effect == "DIRECTIONAL_LIGHTNING":
		target.y = float(parameters.effect_length) * 0.45
	elif recipe.effect == "PROJECTILE_TRAIL":
		target.z = -float(parameters.effect_length) * 0.3
	if recipe.effect != "MESH_EXPLOSION_3D":
		review_distance = maxf(7.0, maxf(float(parameters.effect_radius), float(parameters.effect_length) * 0.65) * 2.5)
	var overall: float = parameters.overall_scale
	target *= overall
	review_distance *= overall
	distance = review_distance
	update_camera()
	var ui := CanvasLayer.new()
	add_child(ui)
	var panel := VBoxContainer.new()
	panel.position = Vector2(24, 24)
	ui.add_child(panel)
	var title := Label.new()
	title.text = str(recipe.effect).replace("_", " ") + " / RUNTIME REVIEW\nReal mesh layers · cube = 1 m\nDrag: orbit · Wheel: zoom · R: restart · Space: pause"
	panel.add_child(title)
	var restart := Button.new()
	restart.text = "RESTART"
	restart.pressed.connect(func(): effect.restart(); pause_button.text = "PAUSE")
	panel.add_child(restart)
	pause_button = Button.new()
	pause_button.text = "PAUSE"
	pause_button.pressed.connect(toggle_pause)
	panel.add_child(pause_button)
	for view in ["SIDE", "TOP", "GAMEPLAY"]:
		var button := Button.new()
		button.text = view
		button.pressed.connect(set_view.bind(view))
		panel.add_child(button)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func update_camera() -> void:
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func set_view(view: String) -> void:
	if view == "TOP":
		pitch = 1.5
		distance = review_distance
	elif view == "SIDE":
		yaw = 1.57
		pitch = 0.04
		distance = review_distance
	else:
		yaw = 0.4
		pitch = 0.22
		distance = review_distance * 1.45
	update_camera()

func toggle_pause() -> void:
	effect.paused = not effect.paused
	pause_button.text = "PLAY" if effect.paused else "PAUSE"

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			dragging = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(3.0, distance - 0.5)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(22.0, distance + 0.5)
		update_camera()
	elif event is InputEventMouseMotion and dragging:
		yaw -= event.relative.x * 0.006
		pitch = clampf(pitch + event.relative.y * 0.006, 0.02, 1.52)
		update_camera()
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_R:
			effect.restart()
		elif event.keycode == KEY_SPACE:
			toggle_pause()
