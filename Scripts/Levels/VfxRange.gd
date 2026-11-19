extends Node3D

enum Mode { CHARGE, TRAIL, IMPACT, SEQUENCE, EXPLOSION, EXPLOSION_PS1, EXPLOSION_HYBRID }
const TITLES := ["Bow Charge", "Arrow Trail", "Arrow Impact", "Серия лука", "Explosion 01", "Explosion PS1", "Explosion Hybrid PS1"]

@export var charge_effect: EffekseerEffect
@export var trail_effect: EffekseerEffect
@export var impact_effect: EffekseerEffect
@export var explosion_effect: EffekseerEffect
@export var explosion_ps1_effect: EffekseerEffect
@export var explosion_hybrid_effect: EffekseerEffect
@export var bow_presentation: CanvasLayer
@export var demo_arrow_scene: PackedScene = preload("res://Scenes/ArrowProjectile.tscn")
@export_range(3, 40, 0.5, "suffix:m/s") var demo_speed := 12.0
@export_range(0.05, 1, 0.01) var charge_scale := 0.14
@export_range(0.1, 3, 0.05) var trail_scale := 0.85
@export_range(0.1, 2, 0.05) var impact_scale := 0.78
@export_range(0.25, 2, 0.05) var explosion_scale := 1.0
@export var bow_offset := Vector3(-0.055, -0.46, -0.60)
@export var zone := AABB(Vector3(-10, -2, -8), Vector3(21, 9, 18))

@onready var player: CharacterBody3D = get_tree().get_first_node_in_group("player")
@onready var shoot_point: Marker3D = player.get_node("CameraPivot/CameraEffectsPivot/Camera3D/ShootPoint")
@onready var panel: PanelContainer = $HUD/Panel
@onready var hint: Label = $HUD/Hint
@onready var status: Label = %Status
@onready var loop_button: CheckButton = %Loop
@onready var face: Area3D = $Target/FaceHitbox

@onready var gallery := $SmokeGallery
@onready var galleries := [$SmokeGallery, $ExplosionGallery, $FireGallery, $LightningGallery, $WeatherGallery]
@onready var gallery_controls := [%SmokeControls, %BlastControls, %FireControls, %LightningControls, %WeatherControls]
@onready var gallery_tabs := [%GallerySwitch, %BlastGallerySwitch, %FireGallerySwitch, %LightningGallerySwitch, %WeatherGallerySwitch]
const GALLERY_TITLES := ["Smoke Gallery", "Explosion Gallery", "Fire Gallery", "Lightning Gallery", "Weather & Atmosphere"]
const TAB_TITLES := ["7  Дым", "8  Взрывы", "9  Огонь", "0  Молнии", "P  Погода"]
var gallery_index := 0
var yard_pose: Transform3D

var selected := Mode.CHARGE
var in_range := false
var pending := false
var countdown := -1.0
var sequence_flight := false
var demo_arrow: Area3D
var trail: EffekseerEmitter3D
var charge: EffekseerEmitter3D
var contact := Vector3.ZERO
var normal := Vector3.UP
var return_pose: Transform3D
var can_return := false
var flash_fade: Tween

func _ready() -> void:
	%One.pressed.connect(select.bind(Mode.CHARGE))
	%Two.pressed.connect(select.bind(Mode.TRAIL))
	%Three.pressed.connect(select.bind(Mode.IMPACT))
	%Four.pressed.connect(select.bind(Mode.EXPLOSION))
	%Five.pressed.connect(select.bind(Mode.EXPLOSION_PS1))
	%Six.pressed.connect(select.bind(Mode.EXPLOSION_HYBRID))
	%Replay.pressed.connect(replay)
	%Series.pressed.connect(select.bind(Mode.SEQUENCE))
	loop_button.toggled.connect(_toggle_loop)
	for i in galleries.size():
		galleries[i].setup(gallery_controls[i], %CycleSmoke)
		gallery_tabs[i].pressed.connect(_toggle_gallery.bind(i))
	%ReplaySmoke.pressed.connect(func(): gallery.replay_shots())
	panel.hide()
	if OS.get_cmdline_user_args().has("--vfx-yard"):
		# Let the map finish placing the player so V can return to its normal start.
		get_tree().process_frame.connect(_enter_yard, CONNECT_ONE_SHOT | CONNECT_DEFERRED)

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.physical_keycode:
		KEY_V:
			if not in_range:
				_enter_yard()
			elif can_return:
				if gallery.active: _close_gallery(false)
				_move_player(return_pose)
				can_return = false
			else:
				return
		KEY_1 when in_range: select(Mode.CHARGE)
		KEY_2 when in_range: select(Mode.TRAIL)
		KEY_3 when in_range: select(Mode.IMPACT)
		KEY_4 when in_range: select(Mode.EXPLOSION)
		KEY_5 when in_range: select(Mode.EXPLOSION_PS1)
		KEY_6 when in_range: select(Mode.EXPLOSION_HYBRID)
		KEY_7 when in_range: _toggle_gallery(0)
		KEY_8 when in_range: _toggle_gallery(1)
		KEY_9 when in_range: _toggle_gallery(2)
		KEY_0 when in_range: _toggle_gallery(3)
		KEY_P when in_range: _toggle_gallery(4)
		KEY_T when gallery.active:
			if gallery_index != 2: gallery.replay_shots()
		KEY_L when gallery.active:
			if gallery_index in [0, 1, 3]: %CycleSmoke.button_pressed = not %CycleSmoke.button_pressed
		KEY_T when in_range: replay()
		KEY_L when in_range: loop_button.button_pressed = not loop_button.button_pressed
		KEY_G when in_range: select(Mode.SEQUENCE)
		_: return
	get_viewport().set_input_as_handled()

func _enter_yard() -> void:
	return_pose = player.global_transform
	can_return = true
	_move_player($ViewPoint.global_transform)

func _move_player(pose: Transform3D) -> void:
	player.global_transform = pose
	player.velocity = Vector3.ZERO
	player.reset_physics_interpolation()

func _physics_process(delta: float) -> void:
	if not is_instance_valid(player):
		return
	var local_player := to_local(player.global_position)
	var inside: bool = zone.has_point(local_player) or (gallery.active and gallery.walk_area.has_point(local_player))
	if inside != in_range:
		in_range = inside
		panel.visible = inside
		hint.visible = not inside
		if not inside:
			if gallery.active: _close_gallery(false)
			loop_button.button_pressed = false
			_cancel()
	if not in_range:
		return
	if pending:
		pending = false
		match selected:
			Mode.CHARGE, Mode.SEQUENCE:
				charge = _emit(charge_effect, _bow_pose(), charge_scale)
				sequence_flight = selected == Mode.SEQUENCE
				countdown = 1.0 if sequence_flight else 1.60
			Mode.TRAIL: _fire_demo(false)
			Mode.IMPACT:
				if _find_contact($Launch.global_position):
					_impact()
				countdown = 1.05
			Mode.EXPLOSION: _ground_explosion(explosion_effect)
			Mode.EXPLOSION_PS1: _ground_explosion(explosion_ps1_effect)
			Mode.EXPLOSION_HYBRID: _ground_explosion(explosion_hybrid_effect)
	elif countdown >= 0:
		countdown -= delta
		if countdown <= 0:
			countdown = -1
			if sequence_flight:
				sequence_flight = false
				_fire_demo(true)
			elif loop_button.button_pressed:
				pending = true

func _process(_delta: float) -> void:
	if is_instance_valid(charge):
		charge.global_transform = _bow_pose().scaled_local(Vector3.ONE * charge_scale)
	if is_instance_valid(demo_arrow) and is_instance_valid(trail):
		trail.global_position = demo_arrow.global_position

func _bow_pose() -> Transform3D:
	if bow_presentation and bow_presentation.visible:
		return bow_presentation.call(&"GetArrowFrame")
	return Transform3D(shoot_point.global_basis, shoot_point.to_global(bow_offset))

func _toggle_gallery(index: int) -> void:
	if gallery.active and gallery_index == index:
		_close_gallery(true)
		return
	if gallery.active:
		gallery.set_active(false)
	else:
		yard_pose = player.global_transform
		loop_button.button_pressed = false
		_cancel()
	_move_player(galleries[index].get_node("Overview").global_transform)
	gallery_index = index
	gallery = galleries[index]
	gallery.set_active(true)
	_show_gallery_controls(true)

func _close_gallery(restore_position: bool) -> void:
	gallery.set_active(false)
	if restore_position:
		_move_player(yard_pose)
	_show_gallery_controls(false)

func _show_gallery_controls(enabled: bool) -> void:
	var rows := $HUD/Panel/Rows
	for group in ["Pick", "Blasts", "Actions"]:
		rows.get_node(group).visible = not enabled
	for i in galleries.size():
		var current := enabled and gallery_index == i
		gallery_controls[i].visible = current
		gallery_tabs[i].text = "%s  Назад" % TAB_TITLES[i].left(1) if current else TAB_TITLES[i]
	rows.get_node("SmokeActions").visible = enabled and gallery_index in [0, 1, 3]
	status.text = GALLERY_TITLES[gallery_index] if enabled else TITLES[selected]

func select(mode: int) -> void:
	if gallery.active:
		_close_gallery(true)
	selected = mode
	replay()

func replay() -> void:
	if not in_range:
		return
	_cancel()
	status.text = TITLES[selected]
	pending = true

func _toggle_loop(enabled: bool) -> void:
	if enabled:
		replay()

func _cancel() -> void:
	if flash_fade:
		flash_fade.kill()
	$BlastFlash.light_energy = 0
	pending = false
	sequence_flight = false
	countdown = -1
	# Superseded arrows must never finish the next preview.
	var old_arrow := demo_arrow
	demo_arrow = null
	trail = null
	charge = null
	if is_instance_valid(old_arrow):
		old_arrow.queue_free()
	for emitter in $Effects.get_children():
		emitter.stop()
		emitter.queue_free()

func _find_contact(origin: Vector3) -> bool:
	var query := PhysicsRayQueryParameters3D.create(origin, face.global_position + face.global_basis.z * -0.22)
	query.collide_with_areas = true
	query.exclude = [player.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.get("collider") != face:
		status.text = "Линия до мишени перекрыта"
		return false
	contact = hit.position
	normal = hit.normal
	return true

func _fire_demo(with_impact: bool) -> void:
	var origin: Vector3 = _bow_pose().origin if with_impact else $Launch.global_position
	if not _find_contact(origin):
		countdown = 1.05
		return
	var direction := origin.direction_to(contact)
	var arrow: Area3D = demo_arrow_scene.instantiate()
	# The normal projectile performs its own physics sweep. Disable overlap
	# callbacks on this demonstration instance so its tip reaches the surface.
	arrow.monitoring = false
	arrow.monitorable = false
	arrow.set("FlightMode", 1) # ArrowFlightMode.Straight
	arrow.set("Speed", demo_speed)
	arrow.set("Lifetime", origin.distance_to(contact) / demo_speed + 0.4)
	arrow.transform = global_transform.affine_inverse() * Transform3D(Basis.looking_at(direction), origin)
	add_child(arrow)
	demo_arrow = arrow
	trail = _emit(trail_effect, _along_x(origin, direction), trail_scale)
	arrow.tree_exiting.connect(_arrow_finished.bind(arrow, with_impact), CONNECT_ONE_SHOT)

func _arrow_finished(arrow: Area3D, with_impact: bool) -> void:
	if arrow != demo_arrow or not arrow.is_queued_for_deletion() or not is_inside_tree() or is_queued_for_deletion():
		return
	demo_arrow = null
	if is_instance_valid(trail):
		trail.global_position = arrow.global_position
		trail.stop_root()
		trail = null
	if with_impact:
		if arrow.global_position.distance_to(contact) < 0.05:
			_impact()
		else:
			status.text = "Стрела не достигла мишени"
	countdown = 1.05 if with_impact else 0.60

func _impact() -> void:
	# +X is the incoming axis in the authored effect. The ejecta return along -X.
	var pose := _along_x(contact + normal * 0.025, -normal)
	# The source's ring is tilted 62 degrees. Align its plane with the face.
	_emit(impact_effect, pose.rotated_local(Vector3.UP, deg_to_rad(28)), impact_scale)

func _ground_explosion(effect: EffekseerEffect) -> void:
	countdown = 2.75
	var mark: Vector3 = $BlastOrigin.global_position
	var ray := PhysicsRayQueryParameters3D.create(mark + Vector3.UP * 1.5, mark + Vector3.DOWN * 2.0)
	ray.exclude = [player.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(ray)
	if hit.is_empty() or hit.normal.y < 0.7:
		status.text = "Под точкой взрыва нет пола"
		return
	var floor_point: Vector3 = hit.position + Vector3.UP * 0.025
	_emit(effect, Transform3D(Basis.IDENTITY, floor_point), explosion_scale)
	var flash: OmniLight3D = $BlastFlash
	flash.global_position = floor_point + Vector3.UP * 0.65 * explosion_scale
	flash.light_energy = 4.0
	flash_fade = create_tween()
	flash_fade.tween_property(flash, "light_energy", 0.0, 0.19).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)

func _along_x(origin: Vector3, axis: Vector3) -> Transform3D:
	var up := Vector3.UP if absf(axis.y) < 0.98 else Vector3.FORWARD
	var z := axis.cross(up).normalized()
	return Transform3D(Basis(axis, z.cross(axis), z), origin)

func _emit(resource: EffekseerEffect, pose: Transform3D, size_factor: float) -> EffekseerEmitter3D:
	var emitter := EffekseerEmitter3D.new()
	emitter.autoplay = false
	emitter.autofree = true
	emitter.effect = resource
	emitter.transform = $Effects.global_transform.affine_inverse() * pose.scaled_local(Vector3.ONE * size_factor)
	$Effects.add_child(emitter)
	emitter.play()
	return emitter
