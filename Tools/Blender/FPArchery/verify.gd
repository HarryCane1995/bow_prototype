extends SceneTree
## godot --path . --fixed-fps 60 --script Tools/Blender/FPArchery/verify.gd -- --no-capture
## Add --frames after -- to save gameplay screenshots (requires a rendering driver).
## Godot's --write-movie records this entire sequence as one gameplay clip.

const SCENE := preload("res://Scenes/Experiments/FPArchery/ArcheryRange.tscn")
const OUT := "res://.godot/fp-archery-qa"
const HORIZONTAL_LIMIT := 23.0
const VERTICAL_LIMIT := 82.0
const MAX_PROJECTION_ERROR := 1.25 # Pixels in the world viewport.
const STRING_BONES: Array[StringName] = [&"StringUpper", &"StringLower"]

class Shot:
	var label: String
	var nock: Vector3
	var tip: Vector3
	var nock_pixel: Vector2
	var tip_pixel: Vector2
	var aim: Vector3
	var fin: Vector3
	var release_camera: Transform3D
	var handoff: Transform3D
	var speed: float
	var projectile: Node3D
	var velocity: Vector3
	var spawn_tip: Vector3
	var target: Node
	var sampled := false
	var compare_center_ray := false

var scene
var visual
var skeleton: Skeleton3D
var view_camera: Camera3D
var world_camera: Camera3D
var fin_in_socket: Vector3
var grip_in_hand: Vector3
var string_end_in_bone: Array[Vector3] = []
var worst_string_gap := 0.0
var worst_grip_gap := 0.0
var worst_left_wrist_bend := 0.0
var worst_index_contact_gap := 0.0
var worst_loaded_finger_gap := 0.0
var pending_shot: Shot
var failures: Array[String] = []
var save_frames: bool


func _initialize() -> void:
	call_deferred("run")


func check(value: bool, message: String) -> void:
	if not value:
		failures.append(message)
		push_error(message)


func frames(count: int) -> void:
	for i in count:
		await process_frame


func snap(label: String) -> void:
	if save_frames:
		await RenderingServer.frame_post_draw
		var result := root.get_texture().get_image().save_png(OUT + "/" + label + ".png")
		check(result == OK, "Сохранение кадра " + label)


func button(code: MouseButton, down: bool) -> void:
	var input := InputEventMouseButton.new()
	input.button_index = code
	input.pressed = down
	root.push_input(input, true)


func key(code: Key, down: bool) -> void:
	var input := InputEventKey.new()
	input.physical_keycode = code
	input.keycode = code
	input.pressed = down
	root.push_input(input, true)


func bone(name_: StringName) -> Transform3D:
	return skeleton.get_bone_global_pose(skeleton.find_bone(name_))


func rest(name_: StringName) -> Transform3D:
	return skeleton.get_bone_global_rest(skeleton.find_bone(name_))


func joint_pixel(name_: StringName) -> Vector2:
	return view_camera.unproject_position(skeleton.to_global(bone(name_).origin))


func bow_tilt() -> float:
	var span := joint_pixel(&"BowCamUpper") - joint_pixel(&"BowCamLower")
	return rad_to_deg(atan2(absf(span.y), absf(span.x)))


func tip_above_index() -> bool:
	return joint_pixel(&"ArrowTip").y < joint_pixel(&"Index1.L").y


func wrist_depth(hand: StringName) -> float:
	return -view_camera.to_local(skeleton.to_global(bone(hand).origin)).z


func grip_gap() -> float:
	return (bone(&"Hand.L") * grip_in_hand).distance_to(bone(&"BowGrip").origin)


func string_gap() -> float:
	var nock := bone(&"ArrowSocket").origin
	var gap := 0.0
	for i in STRING_BONES.size():
		var end := bone(STRING_BONES[i]) * string_end_in_bone[i]
		gap = maxf(gap, end.distance_to(nock))
	return gap


func observe_contacts() -> void:
	if is_instance_valid(skeleton) and visual.visible:
		worst_grip_gap = maxf(worst_grip_gap, grip_gap())
		worst_string_gap = maxf(worst_string_gap, string_gap())
		if visual.arrow_mesh.visible:
			worst_loaded_finger_gap = maxf(worst_loaded_finger_gap, fingertip_gap())
			var index_contact := bone(&"ArrowRest").origin
			var on_shaft := Geometry3D.get_closest_point_to_segment(index_contact, bone(&"ArrowSocket").origin, bone(&"ArrowTip").origin)
			worst_index_contact_gap = maxf(worst_index_contact_gap, index_contact.distance_to(on_shaft))
		var wrist := bone(&"Hand.L").origin
		var knuckles := (bone(&"Index1.L").origin + bone(&"Pinky1.L").origin) * 0.5
		var forearm := wrist - bone(&"Forearm.L").origin
		worst_left_wrist_bend = maxf(worst_left_wrist_bend, rad_to_deg(forearm.angle_to(knuckles - wrist)))


func fingertip_gap() -> float:
	var nock := bone(&"ArrowSocket").origin
	return minf(nock.distance_to(bone(&"Index3.R").origin), nock.distance_to(bone(&"Middle3.R").origin))


# Both assets have a single amber vane. We use its radial direction to
# observe roll independently of either skeleton's axis naming convention.
func amber_vane(mesh: Mesh, nock: Vector3, shaft: Vector3) -> Vector3:
	var radial_sum := Vector3.ZERO
	for surface in mesh.get_surface_count():
		var material := mesh.surface_get_material(surface)
		if not material or not material.resource_name.ends_with("Amber"):
			continue
		var vertices: PackedVector3Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex in vertices:
			var offset := vertex - nock
			var along := offset.dot(shaft)
			var radial := offset - shaft * along
			if along > 0.01 and along < 0.1 and radial.length() > 0.008:
				radial_sum += radial
	check(not radial_sum.is_zero_approx(), "Геометрия янтарного пера доступна")
	return radial_sum.normalized()


func measure_held_mesh() -> void:
	var held: MeshInstance3D = visual.arrow_mesh
	var mesh_to_rig := skeleton.global_transform.affine_inverse() * held.global_transform
	var mesh_nock := mesh_to_rig.affine_inverse() * rest(&"ArrowSocket").origin
	var mesh_tip := mesh_to_rig.affine_inverse() * rest(&"ArrowTip").origin
	var shaft := mesh_nock.direction_to(mesh_tip)
	var first := INF
	var last := -INF
	for surface in held.mesh.get_surface_count():
		var vertices: PackedVector3Array = held.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex in vertices:
			var distance := (vertex - mesh_nock).dot(shaft)
			first = minf(first, distance)
			last = maxf(last, distance)
	check(absf(first) < 0.001 and absf(last - mesh_nock.distance_to(mesh_tip)) < 0.001,
			"ArrowSocket и ArrowTip совпадают с концами видимой геометрии")
	var rest_fin := mesh_to_rig.basis * amber_vane(held.mesh, mesh_nock, shaft)
	fin_in_socket = rest(&"ArrowSocket").basis.inverse() * rest_fin
	grip_in_hand = rest(&"Hand.L").affine_inverse() * rest(&"BowGrip").origin
	for string_bone in STRING_BONES:
		string_end_in_bone.append(rest(string_bone).affine_inverse() * rest(&"ArrowSocket").origin)


func world_pixel(fp_point: Vector3) -> Vector2:
	var uv := view_camera.unproject_position(fp_point) / view_camera.get_viewport().get_visible_rect().size
	return uv * world_camera.get_viewport().get_visible_rect().size


func unproject_to_world(fp_point: Vector3) -> Vector3:
	return world_camera.project_position(world_pixel(fp_point), -view_camera.to_local(fp_point).z)


func reference_shot() -> Shot:
	var shot := Shot.new()
	var socket := skeleton.global_transform * bone(&"ArrowSocket")
	var fp_nock := socket.origin
	var fp_tip := skeleton.to_global(bone(&"ArrowTip").origin)
	shot.nock_pixel = world_pixel(fp_nock)
	shot.tip_pixel = world_pixel(fp_tip)
	# Intersect both sightlines with their separate optical-depth planes.
	# A common depth scale conserves shaft length without moving either pixel.
	var projected_nock := unproject_to_world(fp_nock)
	var projected_tip := unproject_to_world(fp_tip)
	var scale_factor := fp_nock.distance_to(fp_tip) / projected_nock.distance_to(projected_tip)
	var eye := world_camera.global_position
	shot.nock = eye + (projected_nock - eye) * scale_factor
	shot.tip = eye + (projected_tip - eye) * scale_factor
	shot.aim = shot.nock.direction_to(shot.tip)
	var projected_fin := unproject_to_world(socket * (fin_in_socket * 0.03))
	shot.fin = (projected_fin - projected_nock).slide(shot.aim).normalized()
	shot.release_camera = world_camera.global_transform
	return shot


func pixel_at_release(point: Vector3, shot: Shot) -> Vector2:
	# The player can turn again before physics consumes the shot. Keep the
	# original camera frame for the projection comparison.
	var local_point := shot.release_camera.affine_inverse() * point
	return world_camera.unproject_position(world_camera.to_global(local_point))


func release_sample(label: String) -> Shot:
	var shot := reference_shot()
	shot.label = label
	shot.handoff = visual.arrow_in_world(view_camera, world_camera)
	shot.speed = lerpf(scene.tap_speed, scene.full_speed, scene.draw_amount)
	var declared_tip := shot.handoff.origin - shot.handoff.basis.z * shot.nock.distance_to(shot.tip)
	check(pixel_at_release(shot.handoff.origin, shot).distance_to(shot.nock_pixel) < MAX_PROJECTION_ERROR
			and pixel_at_release(declared_tip, shot).distance_to(shot.tip_pixel) < MAX_PROJECTION_ERROR,
			label + " — совмещение обеих экранных точек при смене камер")
	pending_shot = shot
	button(MOUSE_BUTTON_LEFT, false)
	return shot


func arrow_spawned(arrow: Node) -> void:
	if pending_shot == null:
		return
	var shot := pending_shot
	pending_shot = null
	shot.projectile = arrow as Node3D
	arrow.connect(&"impact", func(collider: Node, _point: Vector3) -> void: shot.target = collider)
	# child_entered_tree fires immediately before launch() in the physics
	# callback. The deferred read sees the result of that very callback.
	observe_launch.call_deferred(shot)


func observe_launch(shot: Shot) -> void:
	var arrow := shot.projectile
	var art := arrow.get_node("Arrow") as MeshInstance3D
	if not art:
		art = arrow.get_node("Arrow").find_children("*", "MeshInstance3D", true, false)[0]
	var bounds := art.mesh.get_aabb()
	var local_nock := Vector3(0, 0, bounds.end.z)
	var local_tip := Vector3(0, 0, bounds.position.z)
	var nock := art.to_global(local_nock)
	var tip := art.to_global(local_tip)
	var pixel_error := maxf(pixel_at_release(nock, shot).distance_to(shot.nock_pixel),
			pixel_at_release(tip, shot).distance_to(shot.tip_pixel))
	check(pixel_error < MAX_PROJECTION_ERROR and nock.distance_to(shot.nock) < 0.002
			and tip.distance_to(shot.tip) < 0.002, shot.label + " — геометрия снаряда в кадре отделения")
	shot.velocity = arrow.get("_velocity")
	var axis_error := rad_to_deg(shot.velocity.angle_to(shot.aim))
	check(axis_error < 0.15 and absf(shot.velocity.length() - shot.speed) < 0.1,
			shot.label + " — начальная скорость вдоль видимого древка")
	var actual_fin := art.global_basis * amber_vane(art.mesh, local_nock, Vector3.FORWARD)
	var roll_error := rad_to_deg(actual_fin.slide(shot.aim).angle_to(shot.fin))
	check(roll_error < 4.0 and arrow.global_basis.y.angle_to(shot.handoff.basis.y) < deg_to_rad(0.3),
			shot.label + " — сохранение ориентации оперения")
	if shot.compare_center_ray:
		check_center_ray_would_miss_axis(shot)
	shot.spawn_tip = tip
	shot.sampled = true
	print("FP_LAUNCH ", shot.label, " pixel_error=", snappedf(pixel_error, 0.001),
			" axis_deg=", snappedf(axis_error, 0.001), " fin_deg=", snappedf(roll_error, 0.001))


func check_center_ray_would_miss_axis(shot: Shot) -> void:
	var eye := shot.release_camera.origin
	var central_end := eye - shot.release_camera.basis.z * 160.0
	var query := PhysicsRayQueryParameters3D.create(eye, central_end, 1)
	query.collide_with_areas = true
	var hit := world_camera.get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		central_end = hit.position
	var recast_axis := shot.nock.direction_to(central_end)
	var separation := rad_to_deg(shot.aim.angle_to(recast_axis))
	check(separation > 0.25, "Резкий перевод действительно отделяет видимую ось от повторного луча в центр")
	print("FP_CONTROL повторный_луч_в_центр_отклонился_бы_на_градусы=", snappedf(separation, 0.001))


func check_travel(shot: Shot) -> void:
	check(shot.sampled, shot.label + " — физический снаряд появился на ближайшем шаге")
	if not shot.sampled:
		return
	var displacement := shot.projectile.global_position - shot.spawn_tip
	var flat_speed := Vector2(shot.velocity.x, shot.velocity.z)
	var elapsed := Vector2(displacement.x, displacement.z).dot(flat_speed) / flat_speed.length_squared()
	var predicted: Vector3 = shot.velocity * elapsed + Vector3.DOWN * (0.5 * scene.arrow_gravity * elapsed * elapsed)
	check(elapsed > 0.008 and displacement.distance_to(predicted) < 0.008,
			shot.label + " — наблюдаемый полёт следует начальному импульсу и гравитации")


func mouse_turn(yaw: float, pitch: float) -> void:
	var motion := InputEventMouseMotion.new()
	motion.relative = -Vector2(rad_to_deg(yaw), rad_to_deg(pitch)) / float(scene.look_sensitivity)
	motion.screen_relative = motion.relative
	root.push_input(motion, true)


func steer(direction: Vector3, target_direction: Vector3, weight: float) -> void:
	var from_yaw := atan2(-direction.x, -direction.z)
	var to_yaw := atan2(-target_direction.x, -target_direction.z)
	var yaw := wrapf(to_yaw - from_yaw, -PI, PI)
	var pitch := asin(target_direction.y) - asin(direction.y)
	mouse_turn(yaw * weight, pitch * weight)


func run() -> void:
	if DisplayServer.get_name() != "headless" and not OS.get_cmdline_user_args().has("--no-capture"):
		push_error("Для автоматического прогона с рендером добавьте -- --no-capture.")
		quit(2)
		return
	save_frames = OS.get_cmdline_user_args().has("--frames") and DisplayServer.get_name() != "headless"
	DirAccess.make_dir_recursive_absolute(OUT)
	root.size = Vector2i(1280, 720)
	scene = SCENE.instantiate()
	root.add_child(scene)
	current_scene = scene
	visual = scene.viewmodel
	skeleton = visual.skeleton
	view_camera = scene.view_camera
	world_camera = scene.world_camera
	scene.get_node("Arrows").child_entered_tree.connect(arrow_spawned)
	if skeleton.find_bone(&"ArrowTip") < 0 or skeleton.find_bone(&"ArrowRest") < 0 or not visual.has_method(&"arrow_in_world"):
		push_error("Проверка требует FPArchery.glb с ArrowTip и ArrowRest и viewmodel.arrow_in_world().")
		quit(2)
		return
	measure_held_mesh()
	process_frame.connect(observe_contacts)
	await frames(27)
	check(visual.active_clip == &"FPV_READY", "Стартовая поза")
	check(is_equal_approx(view_camera.fov, 65.0) and is_equal_approx(world_camera.fov, 98.0)
			and view_camera.get_world_3d() != world_camera.get_world_3d(), "Независимые камеры рук и мира")
	check(visual.find_children("*", "MeshInstance3D", true, false).size() == 4, "Две руки, лук и отдельная стрела")
	check(visual.animation_player.get_animation_list().size() >= 12, "Импорт двенадцати клипов")
	var ready_tilt := bow_tilt()
	check(ready_tilt < HORIZONTAL_LIMIT, "Горизонтальное ношение в READY")
	check(tip_above_index(), "В покое наконечник виден над левой кистью")
	var contact_parent := skeleton.get_bone_parent(skeleton.find_bone(&"ArrowRest"))
	check(skeleton.get_bone_name(contact_parent) == &"Index1.L", "Древко опирается непосредственно на левый указательный палец")
	var finger_contact := rest(&"ArrowRest").origin
	var finger_axis := Geometry3D.get_closest_point_to_segment(finger_contact, rest(&"Index1.L").origin, rest(&"Index2.L").origin)
	check(finger_contact.distance_to(finger_axis) < 0.017, "Направляющая древка расположена у поверхности перчатки")
	await snap("01-ready")
	var base_nock := bone(&"ArrowSocket").origin
	var resting_line := Geometry3D.get_closest_point_to_segment(base_nock, bone(&"StringUpper").origin, bone(&"StringLower").origin)
	check(resting_line.distance_to(base_nock) < 0.002, "В покое хвостовик уже на свободной прямой тетиве")
	var base_limb := bone(&"BowGrip").basis.inverse() * bone(&"BowUpper").basis
	check(fingertip_gap() < 0.022, "Правая рука держит хвостовик до нажатия ЛКМ")
	var last := base_nock
	var max_step := 0.0
	var max_gap := 0.0
	var max_grip := grip_gap()
	var max_hook := 0.0
	button(MOUSE_BUTTON_LEFT, true)
	check(scene.is_drawing, "Реакция на ЛКМ")
	# A screenshot resumes after rendering, while process_frame fires before
	# nodes process. Cross a full presentation tick before reading the clip.
	await frames(2)
	check(visual.active_clip == &"FPV_DRAW_START", "Начало анимации натяжения")
	for i in 53:
		await process_frame
		var nock := bone(&"ArrowSocket").origin
		max_step = maxf(max_step, last.distance_to(nock))
		max_grip = maxf(max_grip, grip_gap())
		if scene.draw_amount >= 0.3:
			max_hook = maxf(max_hook, fingertip_gap())
		last = nock
		max_gap = maxf(max_gap, string_gap())
		if i == 20:
			check(visual.active_clip == &"FPV_DRAW_CHARGE", "Промежуточное натяжение")
			await snap("02-draw")
	var hold_nock := bone(&"ArrowSocket").origin
	var bent := bone(&"BowGrip").basis.inverse() * bone(&"BowUpper").basis
	var bend_degrees := rad_to_deg(base_limb.get_rotation_quaternion().angle_to(bent.get_rotation_quaternion()))
	check(base_nock.distance_to(hold_nock) > 0.25 and max_step < 0.037, "Непрерывный ход тетивы")
	check(bend_degrees > 8.0, "Поворот плеча лука при натяжении")
	check(max_gap < 0.003, "Оба конца тетивы сходятся у хвостовика")
	check(max_grip < 0.012, "Левая кисть сохраняет контакт с рукоятью во время поворота")
	check(max_hook < 0.022, "Правая кисть тянет стрелу из исходного хвата")
	check(scene.draw_amount == 1.0 and visual.active_clip == &"FPV_FULL_DRAW_HOLD", "Полное удержание")
	var hold_tilt := bow_tilt()
	check(hold_tilt > 10.0 and hold_tilt < 23.0, "У обычного полного натяжения небольшой наклон")
	check(tip_above_index(), "При обычном полном натяжении наконечник виден над указательным пальцем")
	var viewport_size := view_camera.get_viewport().get_visible_rect().size
	var elbow_in_frame := joint_pixel(&"Forearm.L") / viewport_size
	check(elbow_in_frame.x < 0.36 and elbow_in_frame.y > 0.90 and joint_pixel(&"Hand.L").y > viewport_size.y * 0.60,
			"При полном натяжении левое предплечье входит снизу слева")
	await snap("03-hold")
	var wander := 0.0
	for i in 102:
		await process_frame
		wander = maxf(wander, hold_nock.distance_to(bone(&"ArrowSocket").origin))
	check(wander > 0.00005 and wander < 0.003, "Микродвижение удержания за границей цикла")
	var hold_wrist_y := view_camera.unproject_position(skeleton.to_global(bone(&"Hand.R").origin)).y
	var support_depth := wrist_depth(&"Hand.L")
	var draw_hand_depth := wrist_depth(&"Hand.R")
	var full_shot := release_sample("Полный выстрел")
	check(scene.shots == 1 and not visual.arrow_mesh.visible, "Стрела отделяется на отпускании")
	var lowest_wrist_y := hold_wrist_y
	var support_push := 0.0
	for i in 6:
		await process_frame
		support_push = maxf(support_push, wrist_depth(&"Hand.L") - support_depth)
		var wrist := view_camera.unproject_position(skeleton.to_global(bone(&"Hand.R").origin))
		lowest_wrist_y = maxf(lowest_wrist_y, wrist.y)
	check(lowest_wrist_y - hold_wrist_y < 0.08 * view_camera.get_viewport().get_visible_rect().size.y,
			"В первые 100 мс выпуска запястье сохраняет высоту у лица")
	check(visual.active_clip == &"FPV_RELEASE", "Анимация выпуска")
	check(support_push > 0.022 and support_push < 0.070 and wrist_depth(&"Hand.R") - draw_hand_depth < 0.012,
			"Лук с левой рукой уходит вперёд, правая кисть остаётся у лица")
	check_travel(full_shot)
	await snap("04-release")
	await frames(5)
	check(wrist_depth(&"Hand.L") - support_depth < 0.55 * support_push, "Левая рука возвращается после импульса")
	check(scene.hits == 1 and full_shot.target == scene.get_node("Environment/CenterTarget"),
			"Попадание в центральную мишень")
	await snap("05-hit")
	await frames(37)
	check(visual.arrow_mesh.visible and bow_tilt() < HORIZONTAL_LIMIT,
			"После полного выпуска новая стрела и лук в горизонтальной стойке")
	button(MOUSE_BUTTON_LEFT, true)
	await frames(18)
	var partial: float = scene.draw_amount
	button(MOUSE_BUTTON_RIGHT, true)
	button(MOUSE_BUTTON_RIGHT, false)
	button(MOUSE_BUTTON_LEFT, false)
	await frames(2)
	check(partial > 0.2 and partial < 0.7 and visual.active_clip == &"FPV_CANCEL_DRAW", "Отмена частичного натяжения")
	await frames(38)
	check(scene.shots == 1 and visual.arrow_mesh.visible and bow_tilt() < HORIZONTAL_LIMIT,
			"Отмена вернула горизонтальную стойку без лишнего выстрела")

	# Turn with game input before aiming the partial draw at the other lane.
	var near_target: Node3D = scene.get_node("Environment/NearTarget")
	for i in 22:
		var toward := world_camera.global_position.direction_to(near_target.global_position)
		steer(-world_camera.global_basis.z, toward, 0.14)
		await process_frame
	button(MOUSE_BUTTON_LEFT, true)
	await frames(21)
	check(scene.draw_amount > 0.32 and scene.draw_amount < 0.66, "Неполный заряд второго выстрела")
	# Sight along the actual shaft in the pose reached at this input instant.
	# No test code writes the camera transform, an arrow, or a target.
	for i in 3:
		var sight := reference_shot()
		steer(sight.aim, sight.nock.direction_to(near_target.global_position), 1.0)
	await snap("06-partial-aim")
	var partial_shot := release_sample("Частичный выстрел после поворота")
	check(scene.shots == 2 and not visual.arrow_mesh.visible, "Мгновенный выпуск частичного заряда")
	# A subsequent look event in the same frame must not steer an arrow
	# whose release was already registered.
	mouse_turn(deg_to_rad(2.7), deg_to_rad(-1.4))
	await frames(3)
	check_travel(partial_shot)
	await frames(16)
	check(scene.hits == 2 and partial_shot.target == near_target, "Частичная стрела попала в соседнюю мишень")
	await snap("07-side-hit")
	await frames(25)
	check(visual.arrow_mesh.visible and bow_tilt() < HORIZONTAL_LIMIT,
			"После частичного выпуска обе руки вернулись в горизонтальную стойку")

	button(MOUSE_BUTTON_LEFT, true)
	await frames(5)
	# Shift from a near plate to the back wall and release before the next
	# presentation tick. Recasting the reticle would change the launch axis.
	mouse_turn(deg_to_rad(-16.0), deg_to_rad(2.0))
	var quick_shot := release_sample("Быстрый перевод на дальнюю стену")
	quick_shot.compare_center_ray = true
	await frames(3)
	check_travel(quick_shot)
	button(MOUSE_BUTTON_LEFT, true)
	await frames(4)
	check(scene.is_drawing and visual.active_clip == &"FPV_DRAW_START" and visual.arrow_mesh.visible,
			"Быстрый повторный ввод прерывает отдачу")
	button(MOUSE_BUTTON_RIGHT, true)
	button(MOUSE_BUTTON_RIGHT, false)
	button(MOUSE_BUTTON_LEFT, false)
	await frames(34)
	check(scene.shots == 3 and bow_tilt() < HORIZONTAL_LIMIT, "Быстрая отмена повторного натяжения")
	key(KEY_E, true)
	key(KEY_E, false)
	await frames(5)
	check(visual.active_clip == &"FPV_UNEQUIP", "Опускание лука")
	await frames(42)
	check(not scene.equipped and not visual.visible, "Лук убран")
	key(KEY_E, true)
	key(KEY_E, false)
	await frames(5)
	check(visual.active_clip == &"FPV_EQUIP", "Подъём лука")
	await frames(38)
	Input.action_press(&"move_right")
	key(KEY_SHIFT, true)
	await frames(15)
	check(visual.active_clip == &"FPV_RUN_SWAY" and scene.player.position.x > 0.1, "Бег со смещением рук")
	var run_tilt := bow_tilt()
	check(run_tilt < HORIZONTAL_LIMIT, "Горизонтальный лук во время бега")
	await snap("08-run")
	Input.action_release(&"move_right")
	key(KEY_SHIFT, false)
	key(KEY_SPACE, true)
	key(KEY_SPACE, false)
	await frames(7)
	check(visual.active_clip == &"FPV_JUMP" and scene.player.position.y > 0.2, "Прыжок")
	var landed := false
	for i in 100:
		await process_frame
		landed = landed or visual.active_clip == &"FPV_LAND"
	check(landed, "Реакция на приземление")
	check(visual.active_clip == &"FPV_IDLE", "Спокойная стойка")
	var idle_tilt := bow_tilt()
	check(idle_tilt < HORIZONTAL_LIMIT and grip_gap() < 0.012, "Горизонтальная стойка IDLE с опорой на левую кисть")
	button(MOUSE_BUTTON_LEFT, true)
	await frames(50)
	key(KEY_ALT, true)
	var switch_hook_gap := 0.0
	var last_tilt := bow_tilt()
	var largest_tilt_step := 0.0
	for i in 18:
		await process_frame
		switch_hook_gap = maxf(switch_hook_gap, fingertip_gap())
		var tilt := bow_tilt()
		largest_tilt_step = maxf(largest_tilt_step, absf(tilt - last_tilt))
		last_tilt = tilt
	var sniper_tilt := bow_tilt()
	check(scene.draw_amount == 1.0 and sniper_tilt > VERTICAL_LIMIT, "Alt переводит натянутый лук в вертикаль")
	check(switch_hook_gap < 0.035 and largest_tilt_step < 20.0, "Смена хвата по Alt плавная, пальцы сохраняют контакт")
	await snap("09-precision")
	key(KEY_ALT, false)
	await frames(18)
	check(absf(bow_tilt() - hold_tilt) < 2.0 and scene.draw_amount == 1.0, "Отпускание Alt возвращает обычный угол с тем же натяжением")
	button(MOUSE_BUTTON_RIGHT, true)
	button(MOUSE_BUTTON_RIGHT, false)
	button(MOUSE_BUTTON_LEFT, false)
	await frames(36)
	key(KEY_ALT, true)
	await frames(18)
	var sniper_depth := wrist_depth(&"Hand.L")
	var shots_before: int = scene.shots
	button(MOUSE_BUTTON_LEFT, true)
	var peak_depth := sniper_depth
	var last_depth := sniper_depth
	var largest_return_step := 0.0
	var saw_sniper_release := false
	for i in 13:
		await process_frame
		var depth := wrist_depth(&"Hand.L")
		peak_depth = maxf(peak_depth, depth)
		largest_return_step = maxf(largest_return_step, last_depth - depth)
		last_depth = depth
		saw_sniper_release = saw_sniper_release or visual.active_clip == &"FPV_PRECISION_RELEASE"
		if i == 4:
			button(MOUSE_BUTTON_LEFT, false)
	check(scene.shots == shots_before + 1 and saw_sniper_release and peak_depth > sniper_depth + 0.022,
			"Alt и ЛКМ дают один мгновенный выпуск с импульсом левой руки")
	check(largest_return_step < 0.020, "Левая рука плавно гасит импульс снайперского выстрела")
	await frames(22)
	check(scene.shots == shots_before + 1 and bow_tilt() > VERTICAL_LIMIT and absf(wrist_depth(&"Hand.L") - sniper_depth) < 0.007,
			"С удержанным Alt левая кисть возвращается к исходной снайперской стойке")
	key(KEY_ALT, false)
	await frames(20)
	check(worst_grip_gap < 0.005, "Кисть остаётся на рукояти и при частичной отдаче, отмене и быстром повторе")
	check(worst_left_wrist_bend < 2.0, "Левая ладонь продолжает линию предплечья при хвате и на переходах")
	check(worst_string_gap < 0.0025, "Обе ветви тетивы сходятся на всех переходах, включая частичный выстрел")
	check(worst_index_contact_gap < 0.0025, "Древко остаётся у указательного пальца при движении, натяжении и смене стоек")
	check(worst_loaded_finger_gap < 0.022, "Пальцы правой руки держат каждую видимую стрелу в покое, в движении и на переходах")
	print("FP_BOW_TILT ready=", snappedf(ready_tilt, 0.01), " hold=", snappedf(hold_tilt, 0.01),
			" precision=", snappedf(sniper_tilt, 0.01), " support_push_m=", snappedf(support_push, 0.0001),
			" switch_hook_m=", snappedf(switch_hook_gap, 0.0001),
			" run=", snappedf(run_tilt, 0.01), " idle=", snappedf(idle_tilt, 0.01))
	print("FP_ARCHERY_QA shots=", scene.shots, " hits=", scene.hits, " max_draw_step=", max_step,
			" hold_drift=", wander, " draw_string_gap=", max_gap, " draw_grip_gap=", max_grip,
			" cycle_string_gap=", worst_string_gap, " cycle_grip_gap=", worst_grip_gap,
			" left_wrist_degrees=", worst_left_wrist_bend, " index_contact_gap=", worst_index_contact_gap, " loaded_finger_gap=", worst_loaded_finger_gap,
			" limb_degrees=", bend_degrees, " failures=", failures)
	for voice in scene.find_children("*", "AudioStreamPlayer", true, false):
		voice.stop()
	scene.queue_free()
	if DisplayServer.get_name() == "headless":
		# The dummy mixer runs on wall time, and releases finished voices on
		# subsequent main-loop updates, even during accelerated simulation.
		for i in 16:
			OS.delay_msec(12)
			await process_frame
	await frames(3)
	quit(0 if failures.is_empty() else 1)
