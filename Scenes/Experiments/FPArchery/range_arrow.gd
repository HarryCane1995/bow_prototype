extends Node3D

signal impact(collider: Node, point: Vector3)

var _velocity := Vector3.ZERO
var _gravity := 0.0
var _remaining := 3.0
var _stuck := false
var _excluded: Array[RID] = []
var _length: float


func _ready() -> void:
	var arrow := $Arrow as MeshInstance3D
	if not arrow:
		arrow = $Arrow.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	_length = arrow.mesh.get_aabb().size.z
	$Wake.position.z = _length + 0.145


func launch(arrow_frame: Transform3D, eye_position: Vector3, speed: float, gravity: float, shooter: RID) -> void:
	global_transform = arrow_frame
	var direction := -arrow_frame.basis.z
	_velocity = direction * speed
	_gravity = gravity
	_excluded = [shooter]
	# In a corner the FP viewport can still draw the bow past a wall. Trace
	# from the eye to the nock, then across the actual shaft on this same tick.
	global_position = eye_position
	_sweep_to(arrow_frame.origin)
	if not _stuck:
		_sweep_to(arrow_frame.origin + direction * _length)
	reset_physics_interpolation()


func _physics_process(delta: float) -> void:
	_remaining -= delta
	if _remaining <= 0.0:
		queue_free()
		return
	if _stuck:
		return
	var acceleration := Vector3.DOWN * _gravity
	var destination := global_position + _velocity * delta + acceleration * (0.5 * delta * delta)
	_velocity += acceleration * delta
	# Transport the fletching roll along the flight curve, including steep aim.
	var turn := Quaternion(-global_basis.z, _velocity.normalized())
	global_basis = (Basis(turn) * global_basis).orthonormalized()
	_sweep_to(destination)


func _sweep_to(destination: Vector3) -> void:
	var query := PhysicsRayQueryParameters3D.create(global_position, destination, 1, _excluded)
	query.collide_with_areas = true
	query.hit_from_inside = true
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		global_position = destination
		return
	global_position = hit.position
	_stuck = true
	_remaining = 4.5
	$Wake.visible = false
	impact.emit(hit.collider, global_position)
