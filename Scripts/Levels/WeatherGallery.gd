extends Node3D

const ATMOSPHERE := preload("res://Assets/VFX/Workshop/Weather/Godot/WeatherAtmosphere.gd")
const TITLES := ["Дождь", "Ливень", "Брызги", "Низкий туман", "Банк тумана",
	"Снег", "Метель", "Град", "Пыльная буря", "Гроза"]
# Conservative peak native instances per single authored tile, including child spawners.
const COST := [150, 215, 122, 58, 48, 420, 295, 126, 205, 215]
@export_range(2400, 3800, 100) var instance_budget := 3200
const OFFSETS := [Vector3.ZERO, Vector3(1.8, 0, -1.4), Vector3(-2.1, 0, 1.65)]

@export var effects: Array[EffekseerEffect]
@export var walk_area := AABB(Vector3(-23, -3, -18), Vector3(59, 14, 57))
var active := false
var frozen := false
var strength := 1
var flags := PackedByteArray([1, 0, 0, 1, 0, 0, 0, 0, 0, 0])
var banks: Array[Array] = []
var toggles: Array[CheckBox] = []
var atmosphere := ATMOSPHERE.new()
var pause_button := Button.new()
var level_picker := OptionButton.new()

func _ready() -> void:
	add_child(atmosphere)
	for i in effects.size(): banks.append([])
	set_process(false)

func setup(controls: VBoxContainer, _cycle_button: CheckButton) -> void:
	var grid := GridContainer.new()
	grid.columns = 2
	controls.add_child(grid)
	for i in effects.size():
		var button := CheckBox.new()
		button.text = "%d  %s" % [i + 27, TITLES[i]]
		button.focus_mode = Control.FOCUS_NONE
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.set_pressed_no_signal(flags[i] == 1)
		button.toggled.connect(_switch.bind(i))
		grid.add_child(button)
		toggles.append(button)
	var row := HBoxContainer.new()
	controls.add_child(row)
	for label in ["Слабая", "Средняя", "Сильная"]: level_picker.add_item(label)
	level_picker.select(strength)
	level_picker.tooltip_text = "Интенсивность включённых эффектов"
	level_picker.focus_mode = Control.FOCUS_NONE
	level_picker.item_selected.connect(set_strength)
	row.add_child(level_picker)
	pause_button.toggle_mode = true
	pause_button.text = "Пауза"
	pause_button.focus_mode = Control.FOCUS_NONE
	pause_button.toggled.connect(_pause)
	row.add_child(pause_button)
	var restart := Button.new()
	restart.text = "T  Заново"
	restart.focus_mode = Control.FOCUS_NONE
	restart.pressed.connect(replay_shots)
	row.add_child(restart)

func set_active(on: bool) -> void:
	active = on
	set_process(on)
	if on:
		_track()
		atmosphere.attach(get_viewport().get_camera_3d())
		_refresh()
	else:
		for bank in banks: _trim(bank, 0)
		atmosphere.detach()
		_pause(false)
		pause_button.set_pressed_no_signal(false)

func _trim(bank: Array, size: int) -> void:
	while bank.size() > size:
		var e: EffekseerEmitter3D = bank.pop_back()
		e.stop()
		e.queue_free()

func _refresh() -> void:
	if not active: return
	var layers := PackedInt32Array()
	layers.resize(effects.size())
	var remaining := instance_budget
	# Give every selected system a first tile before distributing extra density.
	for copy_index in strength + 1:
		for i in effects.size():
			if not flags[i] or (copy_index == 2 and i in [3, 4]): continue
			if COST[i] <= remaining:
				layers[i] += 1
				remaining -= COST[i]
	for i in effects.size():
		var desired := layers[i]
		var bank := banks[i]
		_trim(bank, desired)
		while bank.size() < desired:
			var n := bank.size()
			var e := EffekseerEmitter3D.new()
			e.autoplay = false
			# Extra storm layers carry only rain. The bolt and lamp share one clock.
			e.effect = effects[1] if i == 9 and n > 0 else effects[i]
			e.position = OFFSETS[n]
			e.rotation.y = [0.0, 0.17, -0.11][n]
			atmosphere.add_child(e)
			bank.append(e)
			e.play()
			e.paused = frozen
	atmosphere.apply(flags, strength)

func _switch(on: bool, i: int) -> void:
	flags[i] = int(on)
	_refresh()

func set_strength(value: int) -> void:
	strength = clampi(value, 0, 2)
	level_picker.select(strength)
	_refresh()

func _pause(on: bool) -> void:
	frozen = on
	pause_button.text = "Продолжить" if on else "Пауза"
	for bank in banks:
		for e: EffekseerEmitter3D in bank: e.paused = on

func replay_shots() -> void:
	for bank in banks: _trim(bank, 0)
	atmosphere.reset_strike()
	pause_button.set_pressed_no_signal(false)
	_pause(false)
	_refresh()

func _track() -> void:
	var cam := get_viewport().get_camera_3d()
	if not cam: return
	var here := cam.global_position
	atmosphere.global_position = Vector3(here.x, global_position.y + 0.04, here.z)

func _process(delta: float) -> void:
	_track()
	var cam := get_viewport().get_camera_3d()
	if cam and cam != atmosphere.camera: atmosphere.attach(cam)
	if not frozen: atmosphere.advance(delta)
