extends Node3D
## Viewer-only camera. No Player dependency and no project InputMap mutations.
@export_range(1.0,500.0,1.0) var move_speed_mps: float = 85.0
@export_range(1.0,10.0,0.1) var fast_multiplier: float = 5.0
@export_range(0.01,0.5,0.01) var mouse_sensitivity_degrees: float = 0.10
@export var capture_on_start: bool = true
@onready var camera: Camera3D = $Camera3D
var controls_enabled := true

func _ready() -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	if capture_on_start and DisplayServer.get_name() != "headless" and not "--showcase-qa" in OS.get_cmdline_user_args():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
	if not controls_enabled:return
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_RIGHT:Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:move_speed_mps = minf(move_speed_mps*1.25,500.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:move_speed_mps = maxf(move_speed_mps/1.25,2.0)
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotation.y -= deg_to_rad(event.relative.x*mouse_sensitivity_degrees)
		rotation.x = clampf(rotation.x-deg_to_rad(event.relative.y*mouse_sensitivity_degrees),deg_to_rad(-88.0),deg_to_rad(88.0))

func _process(delta: float) -> void:
	if not controls_enabled or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:return
	var direction := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):direction -= global_basis.z
	if Input.is_physical_key_pressed(KEY_S):direction += global_basis.z
	if Input.is_physical_key_pressed(KEY_A):direction -= global_basis.x
	if Input.is_physical_key_pressed(KEY_D):direction += global_basis.x
	if Input.is_physical_key_pressed(KEY_E) or Input.is_physical_key_pressed(KEY_SPACE):direction += Vector3.UP
	if Input.is_physical_key_pressed(KEY_Q):direction -= Vector3.UP
	var speed := move_speed_mps
	if Input.is_physical_key_pressed(KEY_SHIFT):speed *= fast_multiplier
	if Input.is_physical_key_pressed(KEY_CTRL):speed *= 0.2
	if direction.length_squared()>0:global_position += direction.normalized()*speed*delta

func aim_from(position_world: Vector3,target_world: Vector3) -> void:
	global_position = position_world
	look_at(target_world,Vector3.UP)
