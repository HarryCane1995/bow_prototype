extends Node3D

enum Phase { REST, DRAW, RELEASE, CANCEL, EQUIP, UNEQUIP, LOWERED }

const IDLE := &"FPV_IDLE"
const READY := &"FPV_READY"
const EQUIP := &"FPV_EQUIP"
const UNEQUIP := &"FPV_UNEQUIP"
const DRAW_START := &"FPV_DRAW_START"
const DRAW_CHARGE := &"FPV_DRAW_CHARGE"
const HOLD := &"FPV_FULL_DRAW_HOLD"
const RELEASE := &"FPV_RELEASE"
const CANCEL := &"FPV_CANCEL_DRAW"
const RUN := &"FPV_RUN_SWAY"
const JUMP := &"FPV_JUMP"
const LAND := &"FPV_LAND"
const PRECISION_HOLD := &"FPV_PRECISION_FULL_DRAW_HOLD"
const PRECISION_CLIPS := {
	DRAW_START: &"FPV_PRECISION_DRAW_START", DRAW_CHARGE: &"FPV_PRECISION_DRAW_CHARGE",
	HOLD: PRECISION_HOLD, RELEASE: &"FPV_PRECISION_RELEASE", CANCEL: &"FPV_PRECISION_CANCEL_DRAW",
}
const START_FRACTION := 0.18
const RELEASE_SNAP_SECONDS := 0.08
const REDRAW_SNAP_SECONDS := 2.0 / 60.0
const RENOCK_FRACTION := 20.0 / 27.0 # Blender release is frames 1–28; the arrow returns on 21.

@export_group("Playback")
@export_range(0.15, 2.5, 0.05) var playback_speed := 1.0
## Duration of the return after the initial string snap, at normal playback speed.
@export_range(0.14, 0.8, 0.01, "suffix:s") var release_recovery_seconds := 0.37
@export_group("Movement feedback")
## Amount of authored running motion, additional stride under draw, and look inertia.
@export_range(0.0, 1.0, 0.05) var movement_sway_gain := 1.0
## Additional recoil and landing response of the whole first-person rig.
@export_range(0.0, 2.0, 0.05) var secondary_motion_gain := 1.0

var active_clip: StringName
var skeleton: Skeleton3D
var animation_player: AnimationPlayer
var arrow_mesh: MeshInstance3D

var _phase := Phase.REST
var _clock := 0.0
var _hold_clock := 0.0
var _rest_clock := 0.0
var _ready_time := 0.9
var _airborne := false
var _landing_time := 0.0
var _last_rest_clip: StringName
var _precision_pose := false
var _release_strength := 1.0
var _release_starts := {}
var _release_offsets: Array[Transform3D] = []
var _relaxed_nock: Vector3
var _draw_travel: Vector3
var _draw_orientations := {}
var _draw_carry := 0.0
var _draw_after_snap := false
var _recoil := 0.0
var _recoil_speed := 0.0
var _arrow_bone := -1
var _tip_bone := -1
var _bow_grip := -1
var _arrow_rest := -1
var _support_hand := -1
var _support_clavicle := -1
var _hook_finger := -1
var _draw_clavicle := -1
var _nock_in_finger := Vector3.ZERO
var _grip_in_palm := Vector3.ZERO
var _string_bones := PackedInt32Array()
var _string_lengths := PackedFloat32Array()
var _sight_rotation := Quaternion.IDENTITY
@onready var _rig: Node3D = $Rig
@onready var _authored_root: Transform3D = _rig.transform
var _turn := Vector2.ZERO
var _stride := 0.0
var _stride_weight := 0.0
var _neutral: Array[Transform3D] = []
var _from_pose: Array[Transform3D] = []
var _fade_time := 0.0
var _fade_duration := 0.0
var _regrip_from_axis := Vector3.ZERO
var _phase_positions: Dictionary[StringName, PackedVector3Array] = {}


func _ready() -> void:
	animation_player = _rig.find_children("*", "AnimationPlayer", true, false)[0]
	skeleton = _rig.find_children("*", "Skeleton3D", true, false)[0]
	arrow_mesh = _rig.find_child("NockedArrow*", true, false) as MeshInstance3D
	assert(arrow_mesh != null, "Expected separate NockedArrow mesh")
	_arrow_bone = skeleton.find_bone("ArrowSocket")
	_tip_bone = skeleton.find_bone("ArrowTip")
	assert(_arrow_bone >= 0 and _tip_bone >= 0, "Missing arrow endpoints")
	_bow_grip = skeleton.find_bone("BowGrip")
	_arrow_rest = skeleton.find_bone("ArrowRest")
	assert(_arrow_rest >= 0, "Missing left index contact on FPArchery")
	_support_hand = skeleton.find_bone("Hand.L")
	_support_clavicle = skeleton.find_bone("Clavicle.L")
	_hook_finger = skeleton.find_bone("Middle3.R")
	_draw_clavicle = skeleton.find_bone("Clavicle.R")
	var rest_palm := skeleton.get_bone_global_rest(_support_hand)
	_grip_in_palm = rest_palm.affine_inverse() * skeleton.get_bone_global_rest(_bow_grip).origin
	var rest_nock := skeleton.get_bone_global_rest(_arrow_bone).origin
	for name_: StringName in [&"StringUpper", &"StringLower"]:
		var index := skeleton.find_bone(name_)
		_string_bones.append(index)
		_string_lengths.append(skeleton.get_bone_global_rest(index).origin.distance_to(rest_nock))
	for mesh in _rig.find_children("*", "MeshInstance3D", true, false):
		mesh.layers = 1 << 18
	animation_player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	for clip: StringName in [IDLE, READY, EQUIP, UNEQUIP, DRAW_START, DRAW_CHARGE,
			HOLD, RELEASE, CANCEL, RUN, JUMP, LAND]:
		assert(animation_player.has_animation(clip), "Missing animation " + clip)
	for clip: StringName in PRECISION_CLIPS.values():
		assert(animation_player.has_animation(clip), "Missing animation " + clip)
	# A reversed equip/unequip keeps its current height; a cancelled draw
	# starts from its current string extension even if the carry pose is moving.
	for clip: StringName in [CANCEL, EQUIP, UNEQUIP]:
		var points := PackedVector3Array()
		for i in 33:
			_sample(clip, _length(clip) * i / 32.0)
			points.append(_phase_point(clip))
		_phase_positions[clip] = points
	for sniper: bool in [false, true]:
		_precision_pose = sniper
		var orientations: Array[Quaternion] = []
		for i in 33:
			_sample_draw(i / 32.0)
			orientations.append(skeleton.get_bone_global_pose(_bow_grip).basis.get_rotation_quaternion())
		_draw_orientations[sniper] = orientations
		_sample(RELEASE, 0.0)
		_release_starts[sniper] = _capture_pose()
	_precision_pose = false
	_sample(DRAW_START, 0.0)
	_neutral = _capture_pose()
	_relaxed_nock = _nock_in_grip()
	_sample(RELEASE, 0.0)
	_draw_travel = _nock_in_grip() - _relaxed_nock
	_nock_in_finger = skeleton.get_bone_global_pose(_hook_finger).affine_inverse() * skeleton.get_bone_global_pose(_arrow_bone).origin
	_sample(READY, 0.0)
	_seat_nocking_hand()
	_last_rest_clip = READY


func begin_draw() -> void:
	if _phase == Phase.RELEASE and _clock < REDRAW_SNAP_SECONDS:
		# Both input edges can arrive before the next render. Let the old
		# string leave the fingers while gameplay is already charging again.
		_draw_after_snap = true
		return
	_draw_carry = 0.0
	if _phase == Phase.RELEASE or _phase == Phase.CANCEL or (_phase == Phase.REST and _last_rest_clip == PRECISION_HOLD):
		# A second press can catch the bow while the shoulder is still braced.
		# Match that carry angle instead of lowering to ready and lifting twice.
		var grip_rotation := skeleton.get_bone_global_pose(_bow_grip).basis.get_rotation_quaternion()
		var orientations: Array[Quaternion] = _draw_orientations[_precision_pose]
		var nearest := 0
		for i in range(1, orientations.size()):
			if absf(grip_rotation.dot(orientations[i])) > absf(grip_rotation.dot(orientations[nearest])):
				nearest = i
		_draw_carry = nearest / (orientations.size() - 1.0)
		if _phase == Phase.RELEASE:
			# A braced shoulder can stay high while a loose string is reloaded.
			_draw_carry = minf(_draw_carry, lerpf(0.72, 1.0, _visible_extension()))
	_transition(Phase.DRAW, 0.035 if _phase == Phase.REST and _last_rest_clip != PRECISION_HOLD else 0.10)
	_hold_clock = 0.0
	visible = true
	arrow_mesh.visible = true
	_seat_nocking_hand()


func release_draw(amount: float) -> void:
	# Draw, Alt and repeated presses can coincide between two displayed poses.
	# The string unloads only the extension that the player actually saw.
	_draw_after_snap = false
	_release_strength = _visible_extension()
	_release_offsets.resize(_neutral.size())
	var release_start: Array[Transform3D] = _release_starts[_precision_pose]
	for i in _neutral.size():
		var start := _neutral[i].interpolate_with(release_start[i], _release_strength)
		var shown := skeleton.get_bone_pose(i)
		_release_offsets[i] = Transform3D(shown.basis * start.basis.inverse(), shown.origin - start.origin)
	_from_pose.clear()
	_phase = Phase.RELEASE
	_clock = 0.0
	_recoil_speed = minf(72.0, _recoil_speed + lerpf(17.0, 66.0, clampf(amount, 0.0, 1.0)))
	arrow_mesh.visible = false


func cancel_draw() -> void:
	if _draw_after_snap:
		_draw_after_snap = false
		return
	_transition(Phase.CANCEL, 0.045)
	_clock = _nearest_phase_time(CANCEL)
	arrow_mesh.visible = true


func set_equipped(value: bool) -> void:
	_draw_after_snap = false
	visible = true
	var reversing := _phase == Phase.EQUIP or _phase == Phase.UNEQUIP
	var start := _nearest_phase_time(EQUIP if value else UNEQUIP) if reversing else 0.0
	_transition(Phase.EQUIP if value else Phase.UNEQUIP, 0.045 if reversing or _phase == Phase.LOWERED else 0.09)
	_clock = start
	if value:
		arrow_mesh.visible = true


func _nock_in_grip() -> Vector3:
	var grip := skeleton.get_bone_global_pose(_bow_grip)
	return grip.affine_inverse() * skeleton.get_bone_global_pose(_arrow_bone).origin


func _visible_extension() -> float:
	var displacement := (_nock_in_grip() - _relaxed_nock).dot(_draw_travel)
	return clampf(displacement / _draw_travel.length_squared(), 0.0, 1.0)


func _phase_point(clip: StringName) -> Vector3:
	if clip == CANCEL:
		return _nock_in_grip()
	return skeleton.get_bone_global_pose(_arrow_bone).origin


func _nearest_phase_time(clip: StringName) -> float:
	var point := _phase_point(clip)
	var points := _phase_positions[clip]
	var nearest := 0
	for i in range(1, points.size()):
		if points[i].distance_squared_to(point) < points[nearest].distance_squared_to(point):
			nearest = i
	return _length(clip) * nearest / (points.size() - 1.0)


func on_jump() -> void:
	_airborne = true
	_landing_time = 0.0
	if _last_rest_clip == JUMP:
		_last_rest_clip = &"" # A second accepted jump replays the takeoff beat.


func on_land() -> void:
	_airborne = false
	_landing_time = _length(LAND)


func turn_sway(pixels: Vector2) -> void:
	_turn = (_turn + pixels * 0.00048).clamp(Vector2(-0.035, -0.027), Vector2(0.035, 0.027))


func nock_in_camera(view_camera: Camera3D) -> Vector3:
	var socket := skeleton.get_bone_global_pose(_arrow_bone).origin
	return view_camera.to_local(skeleton.to_global(socket))


func _projection_scale(view_camera: Camera3D, world_camera: Camera3D) -> Vector3:
	var fp := view_camera.get_camera_projection()
	var world := world_camera.get_camera_projection()
	return Vector3(fp.x.x / world.x.x, fp.y.y / world.y.y, 1.0)


func align_arrow(view_camera: Camera3D, world_camera: Camera3D, sight_depth: float, delta: float) -> void:
	_rig.transform = _authored_root
	if not visible:
		_sight_rotation = Quaternion.IDENTITY
		return
	var eye := view_camera.get_camera_transform()
	var in_view := eye.affine_inverse() * skeleton.global_transform
	var nock := in_view * skeleton.get_bone_global_pose(_arrow_bone).origin
	var tip := in_view * skeleton.get_bone_global_pose(_tip_bone).origin
	# During sniper recovery the string is already loose. Re-aiming its hidden
	# arrow would pull the supporting wrist back in a single displayed frame.
	if (_phase == Phase.REST and arrow_mesh.visible) or _phase == Phase.DRAW or _phase == Phase.CANCEL:
		var projection := _projection_scale(view_camera, world_camera)
		# Both viewports show the same sight at the centre. A common depth
		# factor preserves the physical shaft length when switching FOVs.
		# Refine this direction for near targets where parallax is visible.
		var aim := Vector3.FORWARD * maxf(sight_depth, -nock.z + tip.distance_to(nock) + world_camera.near)
		var desired := nock.direction_to(aim)
		for i in 3:
			desired = nock.direction_to(aim * (desired * projection).length())
		_sight_rotation = Quaternion(nock.direction_to(tip), desired).normalized()
	elif _phase != Phase.RELEASE or _clock > RELEASE_SNAP_SECONDS:
		_sight_rotation = _sight_rotation.slerp(Quaternion.IDENTITY, 1.0 - exp(-delta * 14.0))
	# Turn the whole assembly about the string contact. Both grips, the shaft,
	# fletching and the two limbs keep their authored relationship.
	var turn := eye.basis * Basis(_sight_rotation) * eye.basis.inverse()
	var pivot := eye * nock
	var model := _rig.global_transform
	_rig.global_transform = Transform3D(turn * model.basis, pivot + turn * (model.origin - pivot))


func arrow_in_world(view_camera: Camera3D, world_camera: Camera3D) -> Transform3D:
	var in_view := view_camera.get_camera_transform().affine_inverse() * skeleton.global_transform
	var nock := in_view * skeleton.get_bone_global_pose(_arrow_bone)
	var tip := in_view * skeleton.get_bone_global_pose(_tip_bone).origin
	var shaft := tip - nock.origin
	var projection := _projection_scale(view_camera, world_camera)
	var world_shaft := shaft * projection
	# Scaling both endpoints about the eye keeps their screen positions while
	# matching the length of the free-flight mesh. Its tip points along -Z.
	var depth_scale := shaft.length() / world_shaft.length()
	# The imported Blender bone keeps +Y along its length and +Z across the
	# fletching. The free mesh uses Godot's -Z forward and +Y up.
	var up := (nock.basis.z * projection).normalized()
	var frame := Transform3D(Basis.looking_at(world_shaft.normalized(), up), nock.origin * projection * depth_scale)
	return world_camera.get_camera_transform() * frame


func present(delta: float, amount: float, speed: float, precision := false, wall_stride := false) -> void:
	if _draw_after_snap and _clock >= REDRAW_SNAP_SECONDS:
		_draw_after_snap = false
		begin_draw()
	# A release or cancel starts in the pose that was visible on the input
	# edge. Alt can be switched freely while drawing without restarting charge.
	if _precision_pose != precision and (_phase == Phase.REST or _phase == Phase.DRAW):
		if _phase == Phase.DRAW:
			_start_fade(0.20, true)
		_precision_pose = precision
	var step := delta * playback_speed
	if _phase == Phase.RELEASE:
		var snap_step := clampf(RELEASE_SNAP_SECONDS - _clock, 0.0, delta)
		var recovery_rate := (_length(RELEASE) - RELEASE_SNAP_SECONDS) / release_recovery_seconds
		_clock += snap_step + (delta - snap_step) * playback_speed * recovery_rate
	else:
		_clock += step
	_landing_time = maxf(0.0, _landing_time - step)
	_turn *= exp(-delta * 13.0)
	# Model-space turn inertia leaves both cameras and the aiming ray fixed.
	var aim := 1.0 if precision else amount
	if _phase == Phase.RELEASE:
		aim = maxf(aim, _release_strength * (1.0 - smoothstep(RELEASE_SNAP_SECONDS, _length(RELEASE), _clock)))
	var damping := lerpf(1.0, 0.18, aim)
	rotation = Vector3(_turn.y * 0.50, _turn.x * 0.72, -_turn.x * 0.44) * damping * movement_sway_gain
	# The authored run occupies the whole rig. Retain a much smaller stride
	# under the draw pose, including during an uninterrupted moving hold.
	_stride = fmod(_stride + delta * speed * 2.3, TAU)
	var stride_target := clampf(speed / 4.2, 0.0, 1.0) if _phase == Phase.DRAW and not _airborne else 0.0
	_stride_weight = lerpf(_stride_weight, stride_target, 1.0 - exp(-delta * 12.0))
	position = Vector3(sin(_stride), cos(_stride * 2.0) * 0.55, 0.0) * (0.003 * _stride_weight * damping * movement_sway_gain)
	_apply_recoil(delta)
	match _phase:
		Phase.DRAW:
			var carried := amount
			if _draw_carry > 0.0:
				carried += _draw_carry * pow(1.0 - amount, 1.0 / _draw_carry)
			_sample_draw(carried)
			if amount >= 1.0:
				_hold_clock += step
		Phase.RELEASE:
			_present_release()
			if _clock >= _length(RELEASE) * RENOCK_FRACTION:
				arrow_mesh.visible = true
			if precision and _clock >= RELEASE_SNAP_SECONDS:
				_resume_ready(false)
			elif _clock >= _length(RELEASE):
				_resume_ready()
		Phase.CANCEL:
			_sample(CANCEL, _clock)
			if _clock >= _length(CANCEL):
				_resume_ready()
		Phase.EQUIP:
			_sample(EQUIP, _clock)
			if _clock >= _length(EQUIP):
				_resume_ready()
		Phase.UNEQUIP:
			_sample(UNEQUIP, _clock)
			if _clock >= _length(UNEQUIP):
				_phase = Phase.LOWERED
				visible = false
		Phase.REST:
			_present_locomotion(step, speed, precision, wall_stride)
		Phase.LOWERED:
			return
	if not _from_pose.is_empty():
		_fade_time += delta
		var weight := smoothstep(0.0, _fade_duration, _fade_time)
		var target_axis := skeleton.get_bone_global_pose(_bow_grip).basis.y.normalized()
		_mix_pose(_from_pose, weight)
		if not _regrip_from_axis.is_zero_approx():
			_lower_elbow_during_regrip(weight, target_axis)
		if _fade_time >= _fade_duration:
			_from_pose.clear()
			_regrip_from_axis = Vector3.ZERO
	if _phase == Phase.REST and not arrow_mesh.visible:
		var finger := skeleton.get_bone_global_pose(_hook_finger).origin
		var nock := skeleton.get_bone_global_pose(_arrow_bone).origin
		arrow_mesh.visible = finger.distance_to(nock) <= 0.04 or (not precision and _from_pose.is_empty())
	if arrow_mesh.visible:
		_align_arrow_on_index()
		_seat_nocking_hand()


func _align_arrow_on_index() -> void:
	var arrow := skeleton.get_bone_global_pose(_arrow_bone)
	var contact := skeleton.get_bone_global_pose(_arrow_rest).origin
	var turn := Quaternion(arrow.basis.y.normalized(), arrow.origin.direction_to(contact))
	arrow.basis = Basis(turn) * arrow.basis
	skeleton.set_bone_global_pose(_arrow_bone, arrow)


func _seat_nocking_hand() -> void:
	# Use the contact inside the curled fingers, not the finger joint origin.
	# Carry, movement and interrupted blends all share this loaded grip.
	var pinch := skeleton.get_bone_global_pose(_hook_finger) * _nock_in_finger
	var shoulder := skeleton.get_bone_global_pose(_draw_clavicle)
	shoulder.origin += skeleton.get_bone_global_pose(_arrow_bone).origin - pinch
	skeleton.set_bone_global_pose(_draw_clavicle, shoulder)


func _sample_draw(amount: float) -> void:
	if amount < START_FRACTION:
		_sample(DRAW_START, _length(DRAW_START) * amount / START_FRACTION)
	elif amount < 1.0:
		_sample(DRAW_CHARGE, _length(DRAW_CHARGE) * (amount - START_FRACTION) / (1.0 - START_FRACTION))
	else:
		_sample_loop(HOLD, _hold_clock)


func _present_release() -> void:
	_sample(RELEASE, _clock)
	# The difference from the full-strength clip's first pose persists through
	# the snap. The wrist and the bow therefore recoil from the displayed
	# partial pose, while the authored string can already move on frame one.
	var remaining := 1.0 - smoothstep(RELEASE_SNAP_SECONDS, _length(RELEASE), _clock)
	for i in _release_offsets.size():
		var pose := _neutral[i].interpolate_with(skeleton.get_bone_pose(i), _release_strength)
		var offset := Transform3D.IDENTITY.interpolate_with(_release_offsets[i], remaining)
		skeleton.set_bone_pose(i, Transform3D(offset.basis * pose.basis, pose.origin + offset.origin))
	_restore_contacts()


func _apply_recoil(delta: float) -> void:
	# Exact damped oscillation. A rapid second shot adds an impulse at the
	# existing position; neither render rate nor shot count shifts the base.
	var decay := exp(-24.0 * delta)
	var phase := 48.0 * delta
	var c := cos(phase)
	var s := sin(phase)
	var amplitude := (_recoil_speed + 24.0 * _recoil) / 48.0
	var next := decay * (_recoil * c + amplitude * s)
	_recoil_speed = decay * 48.0 * (amplitude * c - _recoil * s) - 24.0 * next
	_recoil = next
	position.y += 0.002 * _recoil * secondary_motion_gain
	rotation.x += 0.008 * _recoil * secondary_motion_gain


func _present_locomotion(step: float, speed: float, precision: bool, wall_stride: bool) -> void:
	_ready_time = maxf(0.0, _ready_time - step)
	var clip := IDLE
	if precision:
		clip = PRECISION_HOLD
	elif _airborne and not wall_stride:
		clip = JUMP
	elif _landing_time > 0.0:
		clip = LAND
	elif speed > 0.45:
		clip = RUN
	elif _ready_time > 0.0:
		clip = READY
	if _last_rest_clip != clip:
		var aiming := clip == PRECISION_HOLD or _last_rest_clip == PRECISION_HOLD
		# READY can become IDLE while the elbow is still passing under the limb.
		if aiming or _from_pose.is_empty() or _regrip_from_axis.is_zero_approx():
			var regrip: bool = aiming and arrow_mesh.visible
			_start_fade(0.19 if regrip else 0.085, regrip)
		_rest_clock = 0.0
		_last_rest_clip = clip
	if clip == JUMP or clip == LAND:
		_sample(clip, _rest_clock)
	else:
		_sample_loop(clip, _rest_clock)
	if clip == RUN and movement_sway_gain < 1.0:
		_mix_pose(_neutral, movement_sway_gain)
	var cadence := clampf(speed / 4.2, 0.65, 1.45) if clip == RUN else 1.0
	_rest_clock += step * cadence


func _resume_ready(show_arrow := true) -> void:
	_phase = Phase.REST
	_last_rest_clip = &""
	_ready_time = 0.86
	arrow_mesh.visible = show_arrow


func _transition(next: Phase, fade: float) -> void:
	_start_fade(fade)
	_phase = next
	_clock = 0.0


func _start_fade(duration: float, regrip := false) -> void:
	_from_pose = _capture_pose()
	_regrip_from_axis = skeleton.get_bone_global_pose(_bow_grip).basis.y.normalized() if regrip else Vector3.ZERO
	_fade_time = 0.0
	_fade_duration = duration


func _capture_pose() -> Array[Transform3D]:
	var poses: Array[Transform3D] = []
	poses.resize(skeleton.get_bone_count())
	for i in poses.size():
		poses[i] = skeleton.get_bone_pose(i)
	return poses


func _mix_pose(source: Array[Transform3D], weight: float) -> void:
	for i in source.size():
		skeleton.set_bone_pose(i, source[i].interpolate_with(skeleton.get_bone_pose(i), weight))
	_restore_contacts()


func _lower_elbow_during_regrip(weight: float, target_axis: Vector3) -> void:
	# Let the elbow lead below the sweeping lower limb while the palm turns
	# about its grip. A rigid motion keeps the wrist straight and the grasp centred.
	var amount := clampf(_regrip_from_axis.angle_to(target_axis) / deg_to_rad(70.0), 0.0, 1.0)
	var arc := pow(4.0 * weight * (1.0 - weight), 0.6)
	var turn := Basis(Vector3(1.0, -0.5, 0.6).normalized(), deg_to_rad(62.0) * amount * arc)
	var pivot := skeleton.get_bone_global_pose(_bow_grip).origin
	var shoulder := skeleton.get_bone_global_pose(_support_clavicle)
	shoulder = Transform3D(turn * shoulder.basis, pivot + turn * (shoulder.origin - pivot))
	skeleton.set_bone_global_pose(_support_clavicle, shoulder)


func _restore_contacts() -> void:
	# A local-pose blend does not preserve contacts across independent bone
	# chains. Move the rigid bow to the actual palm without stretching the arm.
	var grip := skeleton.get_bone_global_pose(_bow_grip)
	grip.origin = skeleton.get_bone_global_pose(_support_hand) * _grip_in_palm
	skeleton.set_bone_global_pose(_bow_grip, grip)
	var nock := skeleton.get_bone_global_pose(_arrow_bone).origin
	for i in _string_bones.size():
		var string := skeleton.get_bone_global_pose(_string_bones[i])
		var span := nock - string.origin
		var turn := Quaternion(string.basis.y.normalized(), span.normalized())
		string.basis = Basis(turn) * string.basis
		string.basis.y = span / _string_lengths[i]
		skeleton.set_bone_global_pose(_string_bones[i], string)


func _length(clip: StringName) -> float:
	return animation_player.get_animation(clip).length


func _sample_loop(clip: StringName, clock: float) -> void:
	_sample(clip, fmod(clock, _length(clip)))


func _sample(clip: StringName, time: float) -> void:
	if _precision_pose:
		clip = PRECISION_CLIPS.get(clip, clip)
	if active_clip != clip:
		animation_player.play(clip, 0.0)
		active_clip = clip
	animation_player.seek(clampf(time, 0.0, _length(clip)), true, true)
