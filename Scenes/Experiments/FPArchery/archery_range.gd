extends Node3D

const BowPresentation = preload("res://Scenes/Experiments/FPArchery/viewmodel.gd")
const BowAudio = preload("res://Scenes/Experiments/FPArchery/bow_audio.gd")
const RangeArrow = preload("res://Scenes/Experiments/FPArchery/range_arrow.gd")
const ARROW_SCENE := preload("res://Scenes/Experiments/FPArchery/RangeArrow.tscn")
const EYE_HEIGHT := 1.65
const SIGHT_RANGE := 160.0

@export_group("Draw")
@export_range(0.1, 2.5, 0.01, "suffix:s") var charge_time := 0.72
@export_range(8.0, 100.0, 1.0, "suffix:m/s") var tap_speed := 35.0
@export_range(8.0, 150.0, 1.0, "suffix:m/s") var full_speed := 74.0
@export_range(0.0, 25.0, 0.1, "suffix:m/s²") var arrow_gravity := 4.0
@export_group("Movement")
@export_range(1.0, 9.0, 0.1, "suffix:m/s") var walk_speed := 3.8
@export_range(1.0, 12.0, 0.1, "suffix:m/s") var sprint_speed := 6.2
@export_range(2.0, 10.0, 0.1, "suffix:m/s") var jump_speed := 5.2
@export_range(0.02, 0.5, 0.005, "suffix:deg/px") var look_sensitivity := 0.105

var draw_amount := 0.0
var is_drawing := false
var equipped := true
var shots := 0
var hits := 0
var captured := true

@onready var player: CharacterBody3D = %Player
@onready var world_camera: Camera3D = %WorldCamera
@onready var view_camera: Camera3D = $Presentation/ViewContainer/ViewViewport/Studio/ViewCamera
@onready var viewmodel: BowPresentation = $Presentation/ViewContainer/ViewViewport/Studio/ViewModel
@onready var _audio: BowAudio = $BowAudio
@onready var _hud := $RangeHUD

var _yaw := 0.0
var _pitch := 0.0
var _sprint := false
var _precision_held := false
var _no_system_capture := false
var _pending_shots: Array[Dictionary] = []
var _sight_depth := SIGHT_RANGE


func _ready() -> void:
	_no_system_capture = DisplayServer.get_name() == "headless" or OS.get_cmdline_user_args().has("--no-capture")
	get_window().focus_exited.connect(_focus_lost)
	_set_captured(true)
	_update_camera()
	viewmodel.align_arrow(view_camera, world_camera, _sight_depth, 0.0)
	_update_hud()


func _exit_tree() -> void:
	if not _no_system_capture and captured and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _input(event: InputEvent) -> void:
	if handle_control_event(event):
		get_viewport().set_input_as_handled()


func handle_control_event(event: InputEvent) -> bool:
	if not is_node_ready():
		return false
	if event is InputEventMouseMotion:
		if not captured:
			return false
		var motion := event as InputEventMouseMotion
		_yaw -= deg_to_rad(motion.screen_relative.x * look_sensitivity)
		_pitch = clampf(_pitch - deg_to_rad(motion.screen_relative.y * look_sensitivity), -1.47, 1.47)
		viewmodel.turn_sway(motion.screen_relative)
		_update_camera()
		return true
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if not captured:
			if button.button_index == MOUSE_BUTTON_LEFT and button.pressed:
				_set_captured(true)
				return true
			return false
		match button.button_index:
			MOUSE_BUTTON_LEFT:
				if button.pressed:
					begin_draw()
				else:
					release_draw()
				return true
			MOUSE_BUTTON_RIGHT:
				if button.pressed:
					cancel_draw()
				return true
	if event is InputEventKey:
		var key := event as InputEventKey
		var code := key.physical_keycode if key.physical_keycode != KEY_NONE else key.keycode
		if code == KEY_ESCAPE and key.pressed and not key.echo:
			_set_captured(false)
			return true
		if not captured or key.echo:
			return false
		if code == KEY_SHIFT:
			_sprint = key.pressed
			return true
		if code == KEY_ALT:
			_precision_held = key.pressed
			_update_hud()
			return true
		if key.pressed:
			match code:
				KEY_CTRL:
					cancel_draw()
					return true
				KEY_E:
					toggle_equipped()
					return true
				KEY_SPACE:
					jump()
					return true
	return false


func begin_draw() -> void:
	if not equipped or is_drawing:
		return
	if _precision_held:
		_fire(1.0, true)
		return
	is_drawing = true
	draw_amount = 0.0
	viewmodel.begin_draw()
	_audio.nock()


func release_draw() -> void:
	if not is_drawing:
		return
	_fire(draw_amount, false)


func _fire(amount: float, precision: bool) -> void:
	# Freeze the visible ends and roll at the input edge. A later camera turn
	# cannot redirect a shot queued for the next physics tick.
	_pending_shots.append({
		"frame": viewmodel.arrow_in_world(view_camera, world_camera),
		"eye": world_camera.get_camera_transform().origin,
		"amount": amount,
		"precision": precision
	})
	shots += 1
	is_drawing = false
	viewmodel.release_draw(amount)
	_audio.fire(amount)
	draw_amount = 0.0
	_update_hud()


func cancel_draw() -> void:
	if not is_drawing:
		return
	is_drawing = false
	draw_amount = 0.0
	viewmodel.cancel_draw()
	_audio.settle()
	_update_hud()


func toggle_equipped() -> void:
	equipped = not equipped
	is_drawing = false
	draw_amount = 0.0
	viewmodel.set_equipped(equipped)
	_audio.settle()
	_update_hud()


func jump() -> void:
	if player.is_on_floor() and player.velocity.y <= 0.1:
		player.velocity.y = jump_speed
		viewmodel.on_jump()


func _process(delta: float) -> void:
	if is_drawing and draw_amount < 1.0:
		draw_amount = minf(1.0, draw_amount + delta / charge_time)
		if draw_amount == 1.0:
			_audio.full_draw()
	var speed := Vector2(player.velocity.x, player.velocity.z).length()
	viewmodel.present(delta, draw_amount, speed, equipped and _precision_held)
	_update_camera()
	viewmodel.align_arrow(view_camera, world_camera, _sight_depth, delta)
	_update_hud()


func _physics_process(delta: float) -> void:
	var input_dir := Vector2.ZERO
	if captured:
		input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var speed := sprint_speed if _sprint else walk_speed
	var wanted := Basis(Vector3.UP, _yaw) * Vector3(input_dir.x, 0.0, input_dir.y) * speed
	var grounded := player.is_on_floor()
	var acceleration := 26.0 if grounded else 11.0
	var horizontal := Vector2(player.velocity.x, player.velocity.z)
	horizontal = horizontal.move_toward(Vector2(wanted.x, wanted.z), acceleration * delta)
	player.velocity.x = horizontal.x
	player.velocity.z = horizontal.y
	if not grounded:
		player.velocity.y -= 15.5 * delta
	var falling_speed := player.velocity.y
	player.move_and_slide()
	if not grounded and player.is_on_floor() and falling_speed < -0.9:
		viewmodel.on_land()
	if player.global_position.y < -6.0:
		player.global_position = Vector3(0.0, 0.015, 0.0)
		player.velocity = Vector3.ZERO
		player.reset_physics_interpolation()
	_update_sight_depth()
	for pending in _pending_shots:
		_launch(pending.frame, pending.eye, pending.amount, pending.precision)
	_pending_shots.clear()


func _update_sight_depth() -> void:
	var camera := world_camera.get_camera_transform()
	var aim := camera.origin - camera.basis.z * SIGHT_RANGE
	var query := PhysicsRayQueryParameters3D.create(camera.origin, aim, 1, [player.get_rid()])
	query.collide_with_areas = true
	var collision := get_world_3d().direct_space_state.intersect_ray(query)
	_sight_depth = camera.origin.distance_to(collision.position) if not collision.is_empty() else SIGHT_RANGE


func _launch(arrow_frame: Transform3D, eye: Vector3, amount: float, precision: bool) -> void:
	var projectile: RangeArrow = ARROW_SCENE.instantiate()
	$Arrows.add_child(projectile)
	projectile.impact.connect(_on_impact)
	projectile.launch(arrow_frame, eye, lerpf(tap_speed, full_speed, amount),
			0.0 if precision else arrow_gravity, player.get_rid())


func _on_impact(collider: Node, point: Vector3) -> void:
	var target := collider
	while target and not target.is_in_group(&"fp_archery_target"):
		target = target.get_parent()
	if target == null or not target.has_method(&"register_hit"):
		return
	target.call(&"register_hit", point)
	hits += 1
	if _hud.has_method(&"flash_hit"):
		_hud.call(&"flash_hit")
	_audio.hit()
	_update_hud()


func _set_captured(value: bool) -> void:
	captured = value
	if not _no_system_capture:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if value else Input.MOUSE_MODE_VISIBLE
	if not value:
		_sprint = false
		_precision_held = false
		cancel_draw()
	_update_hud()


func _focus_lost() -> void:
	if not _no_system_capture:
		_set_captured(false)


func _update_camera() -> void:
	world_camera.global_position = player.get_global_transform_interpolated().origin + Vector3.UP * EYE_HEIGHT
	world_camera.rotation = Vector3(_pitch, _yaw, 0.0)


func _update_hud() -> void:
	_hud.call(&"update_status", equipped, draw_amount, shots, hits, captured, _precision_held and not is_drawing)
