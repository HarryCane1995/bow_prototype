extends Node3D
## Isolated review only. R / Space or the on-screen buttons replay and pause.
@onready var explosion: Node3D = $Explosion
var pause_button: Button

func _ready() -> void:
	$Camera3D.look_at(Vector3(0, 1.15, 0))
	explosion.loop = true
	var ui := CanvasLayer.new()
	add_child(ui)
	var panel := VBoxContainer.new()
	panel.position = Vector2(24, 24)
	ui.add_child(panel)
	var title := Label.new()
	title.text = "PSX EXPLOSION / LOCAL VFX REVIEW\nBillboard quad • reference cube = 1 m\nR: restart     Space: pause / play"
	panel.add_child(title)
	var replay := Button.new()
	replay.text = "RESTART EXPLOSION"
	replay.pressed.connect(restart_effect)
	panel.add_child(replay)
	pause_button = Button.new()
	pause_button.text = "PAUSE"
	pause_button.pressed.connect(toggle_pause)
	panel.add_child(pause_button)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func restart_effect() -> void:
	explosion.restart()
	pause_button.text = "PAUSE"

func toggle_pause() -> void:
	explosion.paused = not explosion.paused
	pause_button.text = "PLAY" if explosion.paused else "PAUSE"

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_R:
			restart_effect()
		elif event.keycode == KEY_SPACE:
			toggle_pause()
