extends SceneTree
## Disposable rendering/check runner. Not attached to the saved test scene.
func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	var packed := load("res://Assets/Characters/BaseHumanoid/Humanoid_Base_Test.tscn") as PackedScene
	var scene := packed.instantiate()
	root.add_child(scene)
	root.size = Vector2i(1400, 1000)
	var probe := OS.get_cmdline_user_args().has("--skin-probe")
	if probe:
		for kind in ["Male", "Female"]:
			var model := scene.get_node(kind)
			var sk := model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
			for entry in [["forearm.L", -90.0], ["calf.R", 115.0]]:
				var index := sk.find_bone(entry[0])
				var axis := sk.get_bone_global_rest(index).basis.inverse() * Vector3.RIGHT
				sk.set_bone_pose_rotation(index, sk.get_bone_pose_rotation(index) * Quaternion(axis.normalized(), deg_to_rad(entry[1])))
			print("HUMANOID_SKIN_PROBE ", kind, " elbow=-90 knee=115; temporary only")
		var camera := scene.get_node("ReviewCamera") as Camera3D
		camera.position = Vector3(2.8, 1.6, 5.0)
		camera.look_at(Vector3(0, 0.95, 0))
		camera.size = 2.5
	for i in 12: await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var output := "res://Assets/Characters/BaseHumanoid/Review/Godot_skin_probe.png" if probe else "res://Assets/Characters/BaseHumanoid/Review/Godot_pair.png"
	var result := image.save_png(output)
	print("HUMANOID_GODOT_CAPTURE ", result, " ", image.get_size())
	quit(result)
