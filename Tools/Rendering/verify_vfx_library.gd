extends SceneTree
## Isolated import/playback validation for the curated ten-effect art library.
## --capture writes ten 960x640 review frames; no gameplay scene is loaded.
var errors: Array[String] = []
var results: Array[Dictionary] = []
var output := "res://.godot/art-pass-vfx-review/"

func _init() -> void:
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	if not ok:
		errors.append(message)
		push_error("VFX_LIBRARY_FAIL: " + message)

func run() -> void:
	root.size = Vector2i(960, 640)
	DirAccess.make_dir_recursive_absolute(output)
	var index: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/ProceduralArt/VFX/library.json"))
	check(index.effects.size() == 10, "Ten curated archetypes")
	for entry in index.effects:
		var start_errors := errors.size()
		var packed := load(entry.review) as PackedScene
		check(packed != null, str(entry.effect) + " review scene imports")
		if packed == null:
			continue
		var scene: Node3D = packed.instantiate()
		root.add_child(scene)
		current_scene = scene
		await process_frame
		var effect: Node3D = scene.get_node("Explosion")
		effect.loop = false
		effect.restart()
		await create_timer(0.12).timeout
		check(effect.elapsed > 0.03, str(entry.effect) + " realtime playback advances")
		effect.paused = true
		var moment: float = effect.elapsed
		await create_timer(0.04).timeout
		check(is_equal_approx(moment, effect.elapsed), str(entry.effect) + " pause holds")
		effect.seek(float(entry.sample_time))
		var transforms: Array[Transform3D] = []
		var active := 0
		for component in effect.components:
			var node: MeshInstance3D = component.node
			check(node.mesh is ArrayMesh, str(entry.effect) + "/" + node.name + " mesh imports")
			check(node.material_override is ShaderMaterial, str(entry.effect) + "/" + node.name + " shader loads")
			transforms.append(node.global_transform)
			if node.visible:
				active += 1
				check(float(node.get_instance_shader_parameter("life_alpha")) > 0.0, str(entry.effect) + " active fade")
		check(active > 0, str(entry.effect) + " visible components at representative time")
		scene.set_view("TOP")
		await process_frame
		for i in effect.components.size():
			check(effect.components[i].node.global_transform.is_equal_approx(transforms[i]), str(entry.effect) + " camera-independent geometry")
		scene.yaw = 0.6
		scene.pitch = 0.28
		scene.distance = scene.review_distance
		scene.update_camera()
		var twin: Node3D = load(entry.scene).instantiate()
		scene.add_child(twin)
		twin.paused = true
		twin.seek(effect.duration * 0.75)
		check(not is_equal_approx(twin.elapsed, effect.elapsed), str(entry.effect) + " instance-independent time")
		twin.queue_free()
		await process_frame
		if "--capture" in OS.get_cmdline_user_args():
			await RenderingServer.frame_post_draw
			var image := root.get_texture().get_image()
			check(not image.is_empty(), str(entry.effect) + " GPU frame is present")
			image.save_png(output + str(entry.effect).to_lower() + ".png")
		effect.seek(effect.duration)
		for component in effect.components:
			check(not component.node.visible, str(entry.effect) + " all components hidden at end")
		var completion := [0]
		effect.finished.connect(func(): completion[0] += 1)
		effect.restart()
		effect._process(effect.duration + 0.01)
		effect._process(0.1)
		check(not effect.playing and completion[0] == 1, str(entry.effect) + " one-shot finishes exactly once")
		effect.loop = true
		effect.restart()
		effect._process(effect.duration + effect.loop_delay + 0.01)
		check(effect.playing and is_zero_approx(effect.elapsed), str(entry.effect) + " loop restarts")
		results.append({"effect": entry.effect, "result": "PASS" if start_errors == errors.size() else "FAIL", "components": effect.components.size(), "visible_at_sample": active})
		scene.queue_free()
		await process_frame
	var report := {"result": "PASS" if errors.is_empty() else "FAIL", "effects": results, "errors": errors, "captures": "--capture" in OS.get_cmdline_user_args()}
	var file := FileAccess.open(output + "runtime_report.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file.close()
	print("VFX_LIBRARY_QA=" + JSON.stringify(report))
	quit(0 if errors.is_empty() else 1)
