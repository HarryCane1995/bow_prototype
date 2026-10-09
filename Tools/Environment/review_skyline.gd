extends SceneTree
## External review only: never saves or mutates production resources.
var level: Node3D
var camera: Camera3D
var out := "res://Art/Environment/Skyscrapers/Review"

func _init() -> void:
	call_deferred("review")

func review() -> void:
	var args := OS.get_cmdline_user_args()
	var prefix := "before" if "--before" in args else "after"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	level = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
	level.get_node("StartupWindowModeController").set("EnableStartupWindowMode", false)
	root.add_child(level)
	current_scene = level
	await create_timer(1.0).timeout
	level.process_mode = Node.PROCESS_MODE_DISABLED
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	root.size = Vector2i(1440, 900)
	camera = Camera3D.new()
	root.add_child(camera)
	camera.current = true
	camera.fov = 78
	camera.far = 2200
	var views := [
		["route_spawn", Vector3(-26.2, 29.8, -127.2), Vector3(20, 80, 20)],
		["overview", Vector3(465, 340, 510), Vector3(-12, 83, -20)],
		["route_ground", Vector3(112, 2.2, 34), Vector3(278, 98, -80)],
		["skyline_east", Vector3(100, 70, -120), Vector3(320, 116, -40)],
		["skyline_west", Vector3(-56, 73, -117), Vector3(-280, 155, -140)],
	]
	if "--close" in args:
		views = [
			["exoskeleton", Vector3(-95, 132, 37), Vector3(-242, 90, -105)],
			["suspended", Vector3(125, 86, 123), Vector3(243, 51, -12)],
			["landmark", Vector3(-200, 151, 178), Vector3(-80, 133, 326)],
		]
	for view in views:
		camera.fov = 55 if view[0] == "overview" else 78
		level.get_node("Player/CanvasLayer_ViewModel").visible = str(view[0]).begins_with("route")
		level.get_node("CanvasLayer").visible = str(view[0]).begins_with("route")
		camera.position = view[1]
		camera.look_at(view[2])
		await create_timer(0.45).timeout
		await RenderingServer.frame_post_draw
		var path := "%s/%s_%s.png" % [out, prefix, view[0]]
		root.get_texture().get_image().save_png(path)
		print("SKYLINE_CAPTURE ", path)
	quit()
