extends SceneTree
## Real Level_01 input-driven rendering review. No gameplay/resource edits.
## Inputs pass through Input.parse_input_event and the existing Player modules.
const OUT := "res://.godot/level01-shadows/"
var level: Node3D
var player: CharacterBody3D
var sun: DirectionalLight3D
var samples: Array = []
var perf: Array = []
var frame_index := 0
var recording := false
var recording_tick := 0
var seen_slide := false
var seen_wallrun := false
var max_speed := 0.0
var label := ""

func _init() -> void:
	call_deferred("run")

func key(code: Key, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.physical_keycode = code
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func look(yaw: float, pitch: float = 0.0) -> void:
	var motion := InputEventMouseMotion.new()
	motion.relative = Vector2(deg_to_rad(yaw), deg_to_rad(pitch)) / player.get("LookModule").MouseSensitivity
	Input.parse_input_event(motion)
	Input.flush_buffered_events()

func frames(count: int) -> void:
	for i in count:
		await physics_frame

func place(position: Vector3, yaw: float = 0.0, pitch: float = -12.0) -> void:
	for code in [KEY_W, KEY_A, KEY_S, KEY_D, KEY_CTRL, KEY_C, KEY_SHIFT, KEY_SPACE]:
		key(code, false)
	await frames(80)
	player.global_position = position
	player.velocity = Vector3.ZERO
	player.reset_physics_interpolation()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	look(rad_to_deg(player.rotation.y) - yaw, rad_to_deg(player.get_node("CameraPivot").rotation.x) - pitch)
	await frames(20)

func capture(name: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(OUT + name + ".png")
	var item := {"name": name, "position": str(player.global_position), "velocity": str(player.velocity),
		"slide": player.get("CrouchSlideModule").IsSliding, "wallrun": player.get("WallRunModule").IsWallRunning,
		"wall_debug": player.get("WallRunModule").GetDebugText(), "camera": str(player.get("Camera").global_transform)}
	samples.append(item)
	print("SHADOW_MOVEMENT=" + JSON.stringify(item))

func record_frame() -> void:
	if not recording:
		return
	seen_slide = seen_slide or player.get("CrouchSlideModule").IsSliding
	seen_wallrun = seen_wallrun or player.get("WallRunModule").IsWallRunning
	max_speed = maxf(max_speed, Vector2(player.velocity.x, player.velocity.z).length())
	recording_tick += 1
	if recording_tick % 2 != 0:
		return
	root.get_texture().get_image().save_jpg(OUT + "motion/frame_%04d.jpg" % frame_index, .9)
	frame_index += 1

func benchmark(name: String) -> void:
	await create_timer(1.0).timeout
	var times: Array[float] = []
	var gpu: Array[float] = []
	var previous := Time.get_ticks_usec()
	for i in 240:
		await process_frame
		var now := Time.get_ticks_usec()
		times.append((now - previous) / 1000.0)
		gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()))
		previous = now
	times.sort()
	gpu.sort()
	perf.append({"name": name, "median_ms": times[120], "p95_ms": times[228], "fps": 1000.0 / times[120], "gpu_ms": gpu[120]})
	print("SHADOW_GAMEPLAY_PERF=" + JSON.stringify(perf[-1]))

func run() -> void:
	DirAccess.make_dir_recursive_absolute(OUT + "motion")
	root.title = "Level_01 - Shadow quality review"
	root.size = Vector2i(1440, 900)
	level = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
	level.get_node("StartupWindowModeController").set("EnableStartupWindowMode", false)
	root.add_child(level)
	current_scene = level
	await create_timer(2.0).timeout
	player = level.get_node("Player")
	sun = level.get_node("World/DirectionalLight3D")
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	await place(Vector3(14, -.7, 12))
	if "--review-only" in OS.get_cmdline_user_args():
		await capture("REVIEW_LEFT_RUNNING")
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		print("SHADOW_REVIEW_READY: production settings, playable floor viewpoint")
		return
	# Same playable scene/camera, including the character, FP viewport and all effects.
	sun.light_angular_distance = 8
	sun.directional_shadow_max_distance = 100
	sun.directional_shadow_split_2 = .2
	sun.directional_shadow_blend_splits = false
	RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW)
	await benchmark("before")
	await capture("GAMEPLAY_BEFORE")
	sun.light_angular_distance = 0
	sun.directional_shadow_max_distance = 80
	sun.directional_shadow_split_2 = .25
	sun.directional_shadow_blend_splits = true
	RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_MEDIUM)
	await benchmark("after")
	await capture("GAMEPLAY_AFTER")
	Engine.max_fps = 60
	RenderingServer.frame_post_draw.connect(record_frame)
	recording = true
	label = "slow_pan"
	for i in 90:
		look(.25)
		await frames(1)
	await capture("MOVE_01_PAN")
	recording = false
	await place(Vector3(20, -.7, 28))
	recording = true
	label = "run"
	key(KEY_W, true)
	await frames(75)
	await capture("MOVE_02_RUN")
	key(KEY_CTRL, true)
	await frames(14)
	await capture("MOVE_03_SLIDE")
	look(120, 12)
	await frames(10)
	await capture("MOVE_04_FAST_LOOK")
	look(-120, -12)
	await frames(15)
	key(KEY_CTRL, false)
	key(KEY_W, false)
	recording = false
	# Existing imported long wall. Entry uses a run, jump and parkour input.
	await place(Vector3(-35.55, -.7, -4), 0, -8)
	recording = true
	label = "wallrun"
	key(KEY_W, true)
	await frames(25)
	key(KEY_SHIFT, true)
	key(KEY_SPACE, true)
	await frames(12)
	key(KEY_SPACE, false)
	await capture("MOVE_05_WALLRUN")
	await frames(40)
	await capture("MOVE_06_WALLRUN_EXIT")
	key(KEY_SHIFT, false)
	key(KEY_W, false)
	recording = false
	await place(Vector3(14, -.7, 12))
	await capture("REVIEW_LEFT_RUNNING")
	var report := {"input": "InputEventKey + InputEventMouseMotion through existing Player input pipeline", "samples": samples,
		"performance": perf, "seen_slide": seen_slide, "seen_wallrun": seen_wallrun, "max_horizontal_speed": max_speed, "motion_frames": frame_index,
		"taa": root.use_taa, "main_scene": level.scene_file_path, "left_running": true}
	FileAccess.open(OUT + "movement.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	print("SHADOW_REVIEW_READY=" + JSON.stringify(report))
	# Return normal project synchronization; the game remains fully playable.
	Engine.max_fps = 0
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
