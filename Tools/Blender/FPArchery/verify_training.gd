extends SceneTree
## Run with Godot .NET, --fixed-fps 60 and a rendering driver. Add -- --frames for PNGs.
## All controls below use Godot input events. The grapple case can start on a sampled
## floor point of the actual level when the player cannot see an existing anchor.

const LEVEL := "res://Scenes/Levels/Level_01/Level_01.tscn"
const OUT := "res://.godot/fp-archery-qa/training"
const ARROW_SCRIPT := "res://Scripts/Combat/ArrowProjectile.cs"
const STUDIO := "ViewContainer/ViewViewport/Studio/"

var level: Node3D
var player
var display
var visual
var split
var yard
var world_camera: Camera3D
var view_camera: Camera3D
var save_frames := false
var checks := {}
var measurements := {}
var images: Array[String] = []
var effects: Array[String] = []
var player_arrows := 0
var last_arrow: Area3D
var shaft_at_fire := Transform3D.IDENTITY
var nock_pixel := Vector2.ZERO
var tip_pixel := Vector2.ZERO
var shaft_length := 0.0


func _initialize() -> void:
	call_deferred("run")


func check(name_: String, passed: bool) -> void:
	checks[name_] = passed
	if not passed:
		push_error(name_)


func ticks(count: int = 1) -> void:
	for i in count:
		await physics_frame
		await process_frame


func send_event(event: InputEvent) -> void:
	Input.parse_input_event(event)
	Input.flush_buffered_events()


func key(code: Key, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.keycode = code
	event.pressed = pressed
	send_event(event)


func tap(code: Key) -> void:
	key(code, true)
	await ticks(2)
	key(code, false)
	await ticks(2)


func mouse(button: MouseButton, pressed: bool) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = button
	event.pressed = pressed
	event.position = root.get_visible_rect().size * 0.5
	event.global_position = event.position
	send_event(event)


func aim_at(point: Vector3) -> void:
	for i in 5:
		var wanted := world_camera.global_position.direction_to(point)
		var actual := -world_camera.global_basis.z.normalized()
		var yaw := wrapf(atan2(-wanted.x, -wanted.z) - atan2(-actual.x, -actual.z), -PI, PI)
		var pitch := asin(wanted.y) - asin(actual.y)
		if absf(yaw) + absf(pitch) < 0.0003:
			return
		var motion := InputEventMouseMotion.new()
		motion.relative = Vector2(-yaw, -pitch) / float(player.LookModule.MouseSensitivity)
		motion.screen_relative = motion.relative
		send_event(motion)
		await ticks(2)


func photograph(filename: String) -> void:
	if save_frames:
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		var err := image.save_png(OUT + "/" + filename + ".png")
		check("Кадр " + filename, err == OK and not image.is_empty())
		images.append(filename + ".png")
	var frames: Dictionary = measurements.get_or_add("hand_projections", {})
	var pose := {"clip": str(visual.active_clip)}
	var screen := view_camera.get_viewport().get_visible_rect().size
	var skeleton: Skeleton3D = visual.skeleton
	# All samples are in the rendered FP view; (0,0) is the upper-left corner.
	for joint: String in ["Hand.L", "Index1.L", "Middle3.L", "Hand.R", "Index1.R", "Middle3.R"]:
		var point := skeleton.to_global(skeleton.get_bone_global_pose(skeleton.find_bone(joint)).origin)
		var uv := view_camera.unproject_position(point) / screen
		pose[joint] = {"uv": [snappedf(uv.x, 0.001), snappedf(uv.y, 0.001)], "in_frame": view_camera.is_position_in_frustum(point)}
	frames[filename] = pose


func horizontal_speed() -> float:
	return Vector2(player.velocity.x, player.velocity.z).length()


func eye_height() -> float:
	return world_camera.global_position.y - player.global_position.y


func fp_visible() -> bool:
	return (display.visible and visual.is_visible_in_tree() and view_camera.current
		and view_camera.get_viewport().render_target_update_mode != SubViewport.UPDATE_DISABLED
		and not player.get_node("CanvasLayer_ViewModel").visible and not split.get_node("FirstPerson").visible
		and root.get_camera_3d() == world_camera)


func open_lane() -> Vector3:
	var start: Vector3 = player.global_position
	var front := -world_camera.global_basis.z.slide(Vector3.UP).normalized()
	var chosen := front
	var longest := -1.0
	for index in 16:
		var direction := front.rotated(Vector3.UP, index * TAU / 16.0)
		var length := 17.0
		for height: float in [0.43, 1.38]:
			var eye := start + Vector3.UP * height
			var barrier := physics_ray(eye, eye + direction * length, false)
			if not barrier.is_empty():
				length = minf(length, eye.distance_to(barrier.position))
		for metres: float in [3.0, 8.0, 13.0]:
			var sample := start + direction * metres
			var surface := physics_ray(sample + Vector3.UP * 0.8, sample + Vector3.DOWN * 1.4, false)
			if surface.is_empty() or surface.normal.y < 0.78:
				length = minf(length, metres - 1.0)
				break
		if length > longest:
			longest = length
			chosen = direction
	measurements["lane_clearance_m"] = longest
	return chosen


func locomotion() -> void:
	# CombatSpawn has a wall in its authored forward direction. Turn using mouse look.
	await aim_at(world_camera.global_position + open_lane() * 50.0)
	var standing := eye_height()
	var base_fov := world_camera.fov
	var start: Vector3 = player.global_position
	key(KEY_W, true)
	await ticks(18)
	var cruise := horizontal_speed()
	key(KEY_SHIFT, true)
	await ticks(9)
	var parkour := horizontal_speed()
	var moving_fov := world_camera.fov
	var profile = player.ActiveTuningProfile
	var move_speed: float = profile.MoveSpeed
	check("W и Shift ведут штатный мотор по уровню", player.global_position.distance_to(start) > 2.0 and absf(cruise - move_speed) < 0.7 and absf(parkour - move_speed) < 0.7 and player.ParkourIntentModule.IsActive)
	check("Анимация движения нового лука", visual.active_clip == &"FPV_RUN_SWAY" and fp_visible())
	check("Мировой FOV отвечает на скорость", absf(base_fov - profile.PlayerFov) < 1.0 and moving_fov > base_fov + 1.0)
	key(KEY_SHIFT, false)
	key(KEY_CTRL, true)
	var slide_speed := 0.0
	var low := standing
	var sliding := false
	for i in 13:
		await ticks()
		if player.CrouchSlideModule.IsSliding:
			sliding = true
			slide_speed = maxf(slide_speed, horizontal_speed())
			low = minf(low, eye_height())
	check("Подкат по Ctrl с опусканием камеры и сохранением FP", sliding and slide_speed > cruise + 2.0 and low < standing - 0.13 and fp_visible())
	await photograph("01-slide")
	key(KEY_W, false)
	key(KEY_SPACE, true)
	await ticks(2)
	var first_impulse: float = player.velocity.y
	key(KEY_CTRL, false)
	key(KEY_SPACE, false)
	await ticks(7)
	var before_second: float = player.velocity.y
	key(KEY_SPACE, true)
	await ticks(2)
	var second_impulse: float = player.velocity.y
	key(KEY_SPACE, false)
	check("Прыжок выводит из подката", not player.CrouchSlideModule.IsSliding and first_impulse > 0 and not player.is_on_floor() and fp_visible())
	check("Второе нажатие Space даёт воздушный прыжок", second_impulse > before_second + 0.5 and second_impulse > 0)
	measurements.merge({"walk_mps": cruise, "shift_mps": parkour, "slide_mps": slide_speed, "standing_eye_m": standing,
		"sliding_eye_m": low, "base_fov_deg": base_fov, "moving_fov_deg": moving_fov,
		"jump_vertical_mps": first_impulse, "air_jump_vertical_mps": second_impulse})
	for i in 170:
		await ticks()
		if player.is_on_floor():
			break
	await ticks(15)
	check("Приземление и восстановление камеры", player.is_on_floor() and eye_height() > low + 0.13 and fp_visible())


func on_level_child(node: Node) -> void:
	if not node is Area3D or node.get_script() == null or node.get_script().resource_path != ARROW_SCRIPT:
		return
	player_arrows += 1
	last_arrow = node as Area3D
	shaft_at_fire = display.GetArrowFrame()
	var skeleton: Skeleton3D = visual.skeleton
	var nock := skeleton.to_global(skeleton.get_bone_global_pose(skeleton.find_bone("ArrowSocket")).origin)
	var tip := skeleton.to_global(skeleton.get_bone_global_pose(skeleton.find_bone("ArrowTip")).origin)
	shaft_length = nock.distance_to(tip)
	var pixels := world_camera.get_viewport().get_visible_rect().size / view_camera.get_viewport().get_visible_rect().size
	nock_pixel = view_camera.unproject_position(nock) * pixels
	tip_pixel = view_camera.unproject_position(tip) * pixels


func projected_bow_angle() -> float:
	var rig: Skeleton3D = visual.skeleton
	var top := view_camera.unproject_position(rig.to_global(rig.get_bone_global_pose(rig.find_bone("BowCamUpper")).origin))
	var bottom := view_camera.unproject_position(rig.to_global(rig.get_bone_global_pose(rig.find_bone("BowCamLower")).origin))
	var span := top - bottom
	return rad_to_deg(atan2(absf(span.y), absf(span.x)))


func bow_on_range() -> void:
	var target: Area3D = yard.get_node("Target/FaceHitbox")
	var face_material: StandardMaterial3D = yard.get_node("Target/Face").get_active_material(0)
	await aim_at(target.global_position)
	var aim := world_camera.global_position.direction_to(target.global_position)
	check("Мышь навела штатную игровую камеру на мишень", aim.dot(-world_camera.global_basis.z) > 0.998)
	var sequence: int = player.BowVisualModule.ShotVisualSequence
	mouse(MOUSE_BUTTON_LEFT, true)
	await ticks(16)
	var intermediate: float = player.BowVisualModule.DrawAmount
	check("Непрерывное натяжение от штатной ЛКМ", intermediate > 0.0 and intermediate < 1.0 and visual.active_clip in [&"FPV_DRAW_CHARGE", &"FPV_DRAW_START"])
	await ticks(65)
	check("Устойчивое полное натяжение на тренировочной камере", player.BowVisualModule.DrawAmount > 0.99 and visual.active_clip == &"FPV_FULL_DRAW_HOLD" and fp_visible())
	var normal_tilt := projected_bow_angle()
	measurements["normal_tilt_deg"] = normal_tilt
	check("Полный обычный заряд сохраняет пологий наклон", normal_tilt > 10.0 and normal_tilt < 23.0)
	await photograph("02-full-draw")
	await process_frame
	mouse(MOUSE_BUTTON_LEFT, false)
	await RenderingServer.frame_post_draw
	var sampled := is_instance_valid(last_arrow)
	check("ЛКМ создаёт один штатный снаряд в Level_01", sampled and last_arrow.scene_file_path == player.BowShootModule.PresentedArrowScene.resource_path and player_arrows == 1 and player.BowVisualModule.ShotVisualSequence == sequence + 1)
	if sampled:
		var projectile_frame := last_arrow.global_transform
		var launch_angle := rad_to_deg((-projectile_frame.basis.z).angle_to(-shaft_at_fire.basis.z))
		var start_px := world_camera.unproject_position(shaft_at_fire.origin)
		var end_px := world_camera.unproject_position(shaft_at_fire.origin - shaft_at_fire.basis.z * shaft_length)
		var alignment_px := maxf(start_px.distance_to(nock_pixel), end_px.distance_to(tip_pixel))
		var at_tip := projectile_frame.origin.distance_to(shaft_at_fire.origin - shaft_at_fire.basis.z * shaft_length)
		measurements.merge({"launch_angle_deg": launch_angle, "shaft_projection_error_px": alignment_px, "spawn_tip_error_m": at_tip})
		check("Направление и начало полёта совпадают с видимой стрелой", launch_angle < 1.0 and alignment_px < 1.8 and at_tip < 0.025)
	var target_flashed := false
	var released := false
	for i in 32:
		await ticks()
		target_flashed = target_flashed or face_material.albedo_color.is_equal_approx(target.HitColor)
		released = released or (visual.active_clip == &"FPV_RELEASE" and not visual.arrow_mesh.visible)
	check("Выпуск, скрытие стрелы и реальное попадание в TargetHitbox", target_flashed and released and player_arrows == 1)
	measurements["partial_draw"] = intermediate


func controls() -> void:
	var initial_count := player_arrows
	var base_fov := world_camera.fov
	key(KEY_ALT, true)
	await ticks(32)
	var precision_fov := world_camera.fov
	check("Alt меняет FOV точного прицеливания", precision_fov < base_fov - 10.0)
	var sniper_tilt := projected_bow_angle()
	measurements["precision_tilt_deg"] = sniper_tilt
	check("С Alt лук встаёт вертикально", sniper_tilt > 82.0 and visual.active_clip == &"FPV_PRECISION_FULL_DRAW_HOLD")
	await photograph("02b-sniper")
	await process_frame
	mouse(MOUSE_BUTTON_LEFT, true)
	await ticks(3)
	measurements["precision_at_release"] = {"start_count": initial_count, "shots": player_arrows,
		"clip": str(visual.active_clip), "angle_deg": projected_bow_angle()}
	check("Alt и ЛКМ выпускают снайперскую стрелу из вертикальной стойки",
			player_arrows == initial_count + 1 and visual.active_clip == &"FPV_PRECISION_RELEASE" and projected_bow_angle() > 72.0)
	mouse(MOUSE_BUTTON_LEFT, false)
	await ticks(26)
	check("Лук вернулся в снайперскую стойку, повторного выстрела нет", player_arrows == initial_count + 1 and projected_bow_angle() > 82.0)
	initial_count = player_arrows
	key(KEY_ALT, false)
	await ticks(30)
	check("Отпускание Alt возвращает горизонтальную стойку", projected_bow_angle() < 6.0)
	measurements["precision_fov_deg"] = precision_fov
	mouse(MOUSE_BUTTON_LEFT, true)
	await ticks(12)
	await tap(KEY_Q)
	mouse(MOUSE_BUTTON_LEFT, false)
	await ticks(2)
	var cancelled: bool = visual.active_clip == &"FPV_CANCEL_DRAW"
	await ticks(35)
	check("Q отменяет натяжение без выстрела", cancelled and player_arrows == initial_count and player.BowVisualModule.DrawAmount < 0.02)
	await tap(KEY_Q)
	await ticks(40)
	var lowered: bool = not visual.visible
	await tap(KEY_Q)
	await ticks(42)
	check("Q убирает и поднимает лук в покое", lowered and fp_visible())
	mouse(MOUSE_BUTTON_RIGHT, true)
	await ticks(2)
	var state: String = player.get_node("PlayerRmbCombat").StateName
	mouse(MOUSE_BUTTON_RIGHT, false)
	await ticks(30)
	check("ПКМ сохраняет штатный боевой жест без лишней стрелы", state != "Idle" and player_arrows == initial_count)
	await tap(KEY_F10)
	var external_camera: Camera3D = split.get_node("ExternalCamera")
	var external_ok: bool = split.ExternalView and root.get_camera_3d() == external_camera and not display.visible and split.get_node("ThirdPerson").visible
	await tap(KEY_F10)
	check("F10 переключает на 3POV и обратно", external_ok and fp_visible())


func record_effect(node: Node) -> void:
	if node is EffekseerEmitter3D and node.effect:
		effects.append(node.effect.resource_path)


func vfx_controls() -> void:
	var count := player_arrows
	var charge: String = yard.charge_effect.resource_path
	var trail: String = yard.trail_effect.resource_path
	var impact: String = yard.impact_effect.resource_path
	yard.get_node("Effects").child_entered_tree.connect(record_effect)
	await tap(KEY_G)
	var charge_playing: bool = is_instance_valid(yard.charge) and yard.charge.is_playing()
	var demo_seen := false
	for i in 145:
		await ticks()
		demo_seen = demo_seen or is_instance_valid(yard.demo_arrow)
		if impact in effects:
			break
	check("G демонстрирует заряд, полёт и попадание", charge_playing and demo_seen and charge in effects and trail in effects and impact in effects and player_arrows == count)
	await tap(KEY_T)
	check("T повторяет выбранный эффект", effects.count(charge) == 2 and is_instance_valid(yard.charge))
	var tabs: Array[Key] = [KEY_7, KEY_8, KEY_9, KEY_0, KEY_P]
	var opened: Array[String] = []
	var live_effects := false
	for i in tabs.size():
		await tap(tabs[i])
		var gallery = yard.galleries[i]
		if gallery.active and yard.gallery_index == i and yard.gallery_controls[i].is_visible_in_tree():
			opened.append(gallery.name)
		if i == 0 and gallery.active:
			await tap(KEY_T)
			for emitter in gallery.emitters:
				live_effects = live_effects or emitter.is_playing()
	await tap(KEY_P)
	check("Пять вкладок VFX, работающий эффект и возврат во двор", opened.size() == tabs.size() and live_effects and not yard.gallery.active and yard.panel.visible)
	measurements["vfx_tabs"] = opened
	measurements["vfx_effects"] = effects


func physics_ray(from: Vector3, to: Vector3, areas := true) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(from, to)
	query.exclude = [player.get_rid()]
	query.collide_with_areas = areas
	return level.get_world_3d().direct_space_state.intersect_ray(query)


func grapple_setup() -> Dictionary:
	var anchors := get_nodes_in_group("grapple_anchor")
	anchors.sort_custom(func(a, b): return player.global_position.distance_squared_to(a.global_position) < player.global_position.distance_squared_to(b.global_position))
	for target: Node3D in anchors:
		var center := target.global_position
		if world_camera.global_position.distance_to(center) < player.ActiveTuningProfile.MaxGrappleDistance and physics_ray(world_camera.global_position, center).get("collider") == target:
			return {"target": target}
	for target: Node3D in anchors:
		for radius: float in [9.0, 13.0, 6.0]:
			for index in 8:
				var offset := Vector3(cos(index * PI / 4.0), 0, sin(index * PI / 4.0)) * radius
				var start := target.global_position + offset
				var floor_hit := physics_ray(start, start + Vector3.DOWN * 28.0, false)
				if floor_hit.is_empty() or floor_hit.normal.y < 0.8:
					continue
				var feet: Vector3 = floor_hit.position + Vector3.UP * 0.08
				if physics_ray(feet + Vector3.UP * 1.3, target.global_position).get("collider") == target:
					return {"target": target, "feet": feet}
	return {}


func grappling() -> void:
	var setup := grapple_setup()
	check("На реальном уровне есть достижимый GrappleAnchor", not setup.is_empty())
	if setup.is_empty():
		return
	if setup.has("feet"):
		player.global_position = setup.feet
		player.velocity = Vector3.ZERO
		player.reset_physics_interpolation()
		await ticks(8)
	var anchor: Node3D = setup.target
	await aim_at(anchor.global_position)
	var grapple = player.SlingshotGrappleModule
	key(KEY_E, true)
	var pulling := false
	var launching := false
	var fp_throughout := true
	var launch_speed := 0.0
	for i in 140:
		await ticks()
		if i == 2:
			key(KEY_E, false)
		if grapple.CurrentState == 1:
			pulling = true
			fp_throughout = fp_throughout and fp_visible()
		if grapple.CurrentState == 2:
			launching = true
		if grapple.CurrentState == 3 and launching:
			launch_speed = player.velocity.length()
			break
	key(KEY_E, false)
	var correct: bool = grapple.CoverageActivePoint.distance_to(anchor.global_position) < 0.1
	check("E захватывает реальный якорь, проходит Pulling и Launching с сохранением лука", correct and pulling and launching and launch_speed > 1 and fp_throughout and fp_visible())
	measurements.merge({"grapple_anchor": str(anchor.get_path()), "grapple_floor_setup": setup.has("feet"), "launch_mps": launch_speed})
	if launching:
		await photograph("03-grapple")


func finish() -> void:
	var ok := not checks.values().has(false)
	var report := {"passed": ok, "scene": LEVEL, "checks": checks, "measurements": measurements, "screenshots": images, "player_projectiles": player_arrows}
	var output := FileAccess.open(OUT + "/report.json", FileAccess.WRITE)
	if output:
		output.store_string(JSON.stringify(report, "  "))
	print("TRAINING_ARCHERY_QA ", JSON.stringify(report))
	quit(0 if ok else 1)


func run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	save_frames = "--frames" in OS.get_cmdline_user_args()
	var packed := load(LEVEL) as PackedScene
	level = packed.instantiate()
	# Keep captures at the requested size on the isolated render desktop.
	level.get_node("StartupWindowModeController").EnableStartupWindowMode = false
	root.add_child(level)
	current_scene = level
	await ticks(32)
	player = level.get_node("Player")
	display = player.get_node_or_null("TrainingArcheryPresentation")
	check("У Level_01 тренировочный игрок", display != null)
	if display == null:
		finish()
		return
	split = player.get_node("MainCharacterV4")
	visual = display.get_node(STUDIO + "ViewModel")
	view_camera = display.get_node(STUDIO + "ViewCamera")
	world_camera = player.Camera
	yard = level.get_node("VfxRange")
	level.child_entered_tree.connect(on_level_child)
	check("Стартовый захват и единственное FP-представление", Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and fp_visible() and visual.skeleton != null)
	await locomotion()
	var return_to: Vector3 = player.global_position
	await tap(KEY_V)
	await ticks(18)
	check("V переносит во двор и открывает его панель", yard.in_range and yard.panel.visible and fp_visible())
	await photograph("00-yard-ready")
	await bow_on_range()
	await controls()
	await vfx_controls()
	await tap(KEY_V)
	check("V возвращает на уровень", not yard.in_range and player.global_position.distance_to(return_to) < 0.75)
	await grappling()
	finish()
