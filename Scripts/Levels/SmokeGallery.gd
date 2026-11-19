extends Node3D

@export_range(1, 99) var first_number := 7
@export var walk_area := AABB(Vector3(-7, -2, 1), Vector3(34, 9, 26))
@onready var fixtures: Node3D = get_node_or_null("Fixtures")
var active := false
var toggles: Array[CheckButton] = []
var replays: Array[Button] = []
var emitters: Array[EffekseerEmitter3D] = []
var cycle: CheckButton

func _ready() -> void:
	visible = false
	set_process(false)

func setup(controls: VBoxContainer, cycle_button: CheckButton) -> void:
	cycle = cycle_button
	for emitter: EffekseerEmitter3D in $Stations.get_children():
		var i := emitters.size()
		emitters.append(emitter)
		var marker := Label3D.new()
		marker.text = "%02d" % (first_number + i)
		marker.position = Vector3(0, 0.25 - (emitter.position.y - 0.025) / emitter.scale.y, 2.65)
		marker.pixel_size = 0.008
		marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		emitter.add_child(marker)
		var row := HBoxContainer.new()
		controls.add_child(row)
		var toggle := CheckButton.new()
		toggle.text = "%02d  %s" % [first_number + i, emitter.name]
		toggle.focus_mode = Control.FOCUS_NONE
		toggle.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		toggle.toggled.connect(_toggle.bind(i))
		row.add_child(toggle)
		toggles.append(toggle)
		if emitter.get_meta("continuous", false):
			replays.append(null)
		else:
			var button := Button.new()
			button.text = "Повтор"
			button.focus_mode = Control.FOCUS_NONE
			button.pressed.connect(restart.bind(i))
			row.add_child(button)
			replays.append(button)
	visible = false
	set_process(false)

func set_active(enabled: bool) -> void:
	active = enabled
	visible = enabled
	if fixtures:
		fixtures.process_mode = Node.PROCESS_MODE_INHERIT if enabled else Node.PROCESS_MODE_DISABLED
	set_process(enabled and replays.any(func(button): return button != null))
	for i in emitters.size():
		toggles[i].set_pressed_no_signal(enabled)
		_toggle(enabled, i)

func _toggle(enabled: bool, i: int) -> void:
	if replays[i]:
		replays[i].disabled = not enabled
	if active and enabled:
		restart(i)
	else:
		emitters[i].stop()

func restart(i: int) -> void:
	if active and toggles[i].button_pressed:
		emitters[i].stop()
		emitters[i].play()

func replay_shots() -> void:
	for i in emitters.size():
		if replays[i]:
			restart(i)

func _process(_delta: float) -> void:
	if cycle.button_pressed:
		for i in emitters.size():
			if replays[i] and toggles[i].button_pressed and not emitters[i].is_playing():
				emitters[i].play()
