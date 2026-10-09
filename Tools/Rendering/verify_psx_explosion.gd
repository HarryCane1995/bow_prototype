extends SceneTree
## Isolated runtime/resource QA, with optional real-GPU screenshot capture.
var output := "res://.godot/vfx-review/"

func _init() -> void:
	call_deferred("run")

func check(value: bool, description: String) -> void:
	if not value:
		push_error("VFX_QA_FAIL: " + description)
		quit(1)
		assert(value, description)

func run() -> void:
	var args := OS.get_cmdline_user_args()
	var path := "res://Assets/VFX/Explosions/PSXExplosion/psx_explosion_99/review.tscn"
	for arg in args:
		if arg.begins_with("res://"):
			path = arg
	var packed := load(path) as PackedScene
	check(packed != null, "Review scene loads")
	var scene := packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	root.size = Vector2i(1100, 760)
	await process_frame
	var effect = scene.get_node("Explosion")
	check(effect.instance_material is ShaderMaterial, "Material loads")
	check(effect.instance_material.get_shader_parameter("color_sheet") is Texture2D, "Color atlas imported")
	check(effect.instance_material.get_shader_parameter("emission_sheet") is Texture2D, "Emission atlas imported")
	effect.loop = false
	effect.restart()
	await create_timer(.35).timeout
	check(effect.current_frame > 0, "Playback advances")
	effect.paused = true
	var paused_frame: int = effect.current_frame
	await create_timer(.15).timeout
	check(effect.current_frame == paused_frame, "Pause holds")
	var twin = load(path.get_base_dir() + "/explosion.tscn").instantiate()
	scene.add_child(twin)
	check(twin.instance_material != effect.instance_material, "Instances own animation state")
	twin.queue_free()
	if "--capture" in args:
		DirAccess.make_dir_recursive_absolute(output)
		for index in [0, 4, 9, 18, effect.frame_count - 1]:
			effect.set_frame(index)
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(output + "frame_%02d.png" % index)
	effect.paused = false
	await create_timer(effect.frame_count / effect.fps + .1).timeout
	check(effect.current_frame == effect.frame_count - 1 and not effect.playing, "One-shot ends on clear frame")
	effect.restart()
	check(effect.current_frame == 0 and effect.playing, "Restart resets")
	print("VFX_QA_PASS: resources, frame advance, pause, instance isolation, one-shot, restart")
	quit(0)
