extends Node3D
@onready var effect: Node3D = $Explosion
@onready var camera: Camera3D = $Camera3D
var yaw := 0.6
var pitch := 0.28
var distance := 9.0
var dragging := false
var pause_button: Button

func _ready() -> void:
	effect.loop = true
	update_camera()
	var ui := CanvasLayer.new()
	add_child(ui)
	var panel := VBoxContainer.new()
	panel.position = Vector2(24, 24)
	ui.add_child(panel)
	var title := Label.new()
	title.text = "MESH EXPLOSION 3D / RUNTIME REVIEW\nSix independent mesh layers · cube = 1 m\nDrag: orbit · Wheel: zoom · R: restart · Space: pause"
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
	var target := Vector3(0, 0.9, 0)
	camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
	camera.look_at(target)

func set_view(view: String) -> void:
	if view == "TOP":
		pitch = 1.5
		distance = 9.0
	elif view == "SIDE":
		yaw = 1.57
		pitch = 0.04
		distance = 8.5
	else:
		yaw = 0.4
		pitch = 0.22
		distance = 13.0
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
