extends SceneTree
## Pixel regression on the actual gameplay camera, including its screen-reading pass.
const OUT = "res://.godot/cyborg-vfx-visibility/"
const EFFECT = "res://Assets/VFX/Explosions/MeshExplosion3D/mesh_explosion_99_r02/explosion.tscn"
var level: Node3D
var errors: Array[String] = []

func _init() -> void:
	call_deferred("run")

func capture(name: String) -> Image:
	await process_frame
	await RenderingServer.frame_post_draw
	await process_frame
	await RenderingServer.frame_post_draw
	var result := root.get_texture().get_image()
	result.save_png(OUT + name + ".png")
	return result

func difference(a: Image, b: Image, center: Vector2) -> int:
	var count := 0
	# Keep the measurement around the victim, away from HUD/first-person arms.
	for y in range(maxi(0, int(center.y) - 100), mini(a.get_height(), int(center.y) + 100)):
		for x in range(maxi(0, int(center.x) - 150), mini(a.get_width(), int(center.x) + 150)):
			var ca := a.get_pixel(x, y)
			var cb := b.get_pixel(x, y)
			if maxf(absf(ca.r-cb.r), maxf(absf(ca.g-cb.g),absf(ca.b-cb.b))) > 0.06:
				count += 1
	return count

func run() -> void:
	Engine.max_fps = 120
	root.size = Vector2i(1200,800)
	DirAccess.make_dir_recursive_absolute(OUT)
	level = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
	level.get_node("StartupWindowModeController").EnableStartupWindowMode = false
	for n in level.get_node("CombatDraft").get_children():
		if n.is_in_group("enemy"):
			n.CanShoot = false
	root.add_child(level)
	current_scene = level
	await create_timer(0.5).timeout
	var player = level.get_node("Player")
	var victim = level.get_node("CombatDraft/Cyborg_01_Read")
	# The combat start is behind cover. Use an unobstructed nearby firing position.
	player.global_position = victim.global_position + Vector3(6, 0, 7)
	player.reset_physics_interpolation()
	await create_timer(0.12).timeout
	# Keep the player's real camera, cull mask and attached post-processing intact.
	player.process_mode = Node.PROCESS_MODE_DISABLED
	var camera = root.get_camera_3d()
	camera.look_at(victim.global_position + Vector3.UP)
	camera.reset_physics_interpolation()
	var center: Vector2 = camera.unproject_position(victim.global_position + Vector3.UP)
	var post = level.get_node("StylizedContactDarkening")
	victim.ApplyDamage(8)
	await process_frame
	await process_frame
	var effect = level.get_children().filter(func(n): return n.scene_file_path == EFFECT)[0]
	effect.paused = true
	effect.seek(0.28)
	effect.hide()
	var background = await capture("background")
	effect.show()
	var composite = await capture("with-post")
	post.Enabled = false
	effect.hide()
	var plain_background = await capture("background-no-post")
	effect.show()
	var plain = await capture("without-post")
	var composite_pixels := difference(background, composite, center)
	var plain_pixels := difference(plain_background, plain, center)
	if plain_pixels < 80:
		errors.append("Test firing position does not expose enough of the explosion")
	if composite_pixels < 80 or composite_pixels < plain_pixels * 0.5:
		errors.append("Gameplay post-processing hides the mesh explosion")
	post.Enabled = true
	# Realtime replay with no seek/freeze: prove more than a forced snapshot.
	effect.restart()
	var live_frames := 0
	var peak_pixels := 0
	var live_trace: Array = []
	for i in 8:
		if not is_instance_valid(effect):
			break
		var frame = await capture("live_%02d" % i)
		var pixels := difference(background, frame, center)
		live_frames += int(pixels >= 80)
		if pixels > peak_pixels:
			peak_pixels = pixels
			frame.save_png(OUT + "live-peak.png")
		live_trace.append({"seconds": effect.elapsed if is_instance_valid(effect) else -1, "visible_pixels": pixels})
	if live_frames < 2:
		errors.append("Explosion does not remain visible during normal playback")
	var report = {"result": "PASS" if errors.is_empty() else "FAIL", "errors": errors,
		"camera": str(camera.get_path()), "screen_center": str(center), "with_post_pixels": composite_pixels,
		"without_post_pixels": plain_pixels, "live_visible_frames": live_frames, "live_trace": live_trace}
	FileAccess.open(OUT + "qa.json", FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("CYBORG_VISIBILITY_QA=" + JSON.stringify(report))
	level.queue_free()
	await process_frame
	await process_frame
	quit(0 if errors.is_empty() else 1)
