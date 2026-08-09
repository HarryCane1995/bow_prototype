extends Node3D

const OUTPUT_DIRECTORY := "res://.godot/cybercity_concrete_tower_preview"

@onready var _level: Node3D = $Level_CyberCity
@onready var _camera: Camera3D = $PreviewCamera


func _ready() -> void:
	_hide_canvas_layers(_level)
	_disable_other_cameras(_level)
	_camera.make_current()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

	for _frame in 8:
		await get_tree().physics_frame

	var tower := _level.get_node_or_null("ManualConcreteParkourTower") as Node3D
	var player := _level.get_node_or_null("Player") as CharacterBody3D
	if tower == null or player == null:
		push_error("CyberCityConcreteTowerCapture: tower or player was not found.")
		get_tree().quit(2)
		return

	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIRECTORY))
	_verify_route_surfaces(player)
	await _capture_overview()
	await _capture_concrete_closeup()
	await _run_player_route(player)
	await _capture_player_accessible_point(player)
	get_tree().quit(0)


func _hide_canvas_layers(node: Node) -> void:
	if node is CanvasLayer:
		(node as CanvasLayer).visible = false
	for child in node.get_children():
		_hide_canvas_layers(child)


func _disable_other_cameras(node: Node) -> void:
	if node is Camera3D:
		(node as Camera3D).current = false
	for child in node.get_children():
		_disable_other_cameras(child)


func _verify_route_surfaces(player: CharacterBody3D) -> void:
	var checkpoints := {
		"entry_bridge": Vector3(716.5, 150, 138),
		"lower_terrace": Vector3(729, 150, 138),
		"mid_terrace": Vector3(760, 220, 113),
		"upper_terrace": Vector3(736, 275, 138),
		"crown_terrace": Vector3(736, 340, 138),
		"roof_cap": Vector3(761, 375, 138),
	}
	var space_state := get_world_3d().direct_space_state
	for checkpoint_name in checkpoints:
		var from: Vector3 = checkpoints[checkpoint_name]
		var query := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 600.0)
		query.exclude = [player.get_rid()]
		var hit := space_state.intersect_ray(query)
		if hit.is_empty():
			push_error("CYBERCITY_TOWER_SURFACE_MISSING checkpoint=%s" % checkpoint_name)
			continue
		print(
			"CYBERCITY_TOWER_SURFACE checkpoint=%s collider=%s y=%.3f"
			% [checkpoint_name, hit.collider.name, (hit.position as Vector3).y]
		)


func _run_player_route(player: CharacterBody3D) -> void:
	var start := player.global_position
	player.rotation.y = -PI / 2.0
	Input.action_press("move_forward")
	var elapsed := 0.0
	while elapsed < 8.0 and player.global_position.x < 729.0:
		await get_tree().physics_frame
		elapsed += get_physics_process_delta_time()
	Input.action_release("move_forward")
	for _frame in 12:
		await get_tree().physics_frame
	var end := player.global_position
	var success := end.x >= 725.0 and end.y > 124.0 and player.is_on_floor()
	print(
		"CYBERCITY_TOWER_PLAYER_ROUTE success=%s start=%s end=%s on_floor=%s elapsed=%.2f"
		% [success, start, end, player.is_on_floor(), elapsed]
	)
	if not success:
		push_error("Player did not reach and remain on the lower access terrace.")


func _capture_overview() -> void:
	_camera.fov = 48.0
	_camera.global_transform = Transform3D(Basis.IDENTITY, Vector3(620, 230, 350)).looking_at(
		Vector3(760, 160, 138), Vector3.UP
	)
	await _save_frame("cybercity_concrete_tower_overview.png")


func _capture_concrete_closeup() -> void:
	_camera.fov = 52.0
	_camera.global_transform = Transform3D(Basis.IDENTITY, Vector3(711.5, 152, 149)).looking_at(
		Vector3(730, 154, 149), Vector3.UP
	)
	await _save_frame("cybercity_concrete_tower_close.png")


func _capture_player_accessible_point(player: CharacterBody3D) -> void:
	_camera.fov = 70.0
	var eye_position := player.global_position + Vector3.UP * 1.55
	_camera.global_transform = Transform3D(Basis.IDENTITY, eye_position).looking_at(
		Vector3(704, 124.8, 138), Vector3.UP
	)
	await _save_frame("cybercity_concrete_tower_player_point.png")


func _save_frame(file_name: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var output_path := OUTPUT_DIRECTORY.path_join(file_name)
	var error := image.save_png(ProjectSettings.globalize_path(output_path))
	if error != OK:
		push_error("Could not save screenshot %s: %s" % [output_path, error])
	else:
		print("CYBERCITY_TOWER_SCREENSHOT=" + output_path)
