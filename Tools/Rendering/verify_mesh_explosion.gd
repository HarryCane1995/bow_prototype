extends SceneTree
## Load, animate and render the exported mesh asset itself; no gameplay scene.
var errors: Array[String] = []
var output := "res://.godot/mesh-vfx-review/"

func _init() -> void:
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	if not ok:
		errors.append(message)
		push_error("MESH_VFX_QA_FAIL: " + message)

func run() -> void:
	var path := "res://Assets/VFX/Explosions/MeshExplosion3D/mesh_explosion_99/review.tscn"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("res://"):
			path = arg
	var packed := load(path) as PackedScene
	if packed == null:
		quit(1)
		return
	var scene := packed.instantiate()
	root.add_child(scene)
	current_scene = scene
	root.size = Vector2i(1200, 800)
	await process_frame
	var effect = scene.get_node("Explosion")
	check(effect.components.size() > 20, "Mesh components load")
	check(effect.get_node("Layers/petals/Petal_00").mesh is ArrayMesh, "OBJ imported as triangle mesh")
	check(effect.get_node("Layers/petals/Petal_00").material_override is ShaderMaterial, "Layer material loads")
	effect.loop = false
	effect.restart()
	await create_timer(.2).timeout
	check(effect.elapsed > .1, "Realtime player advances")
	effect.paused = true
	var moment: float = effect.elapsed
	await create_timer(.1).timeout
	check(is_equal_approx(effect.elapsed,moment), "Pause holds")
	effect.seek(.28)
	var petal: MeshInstance3D = effect.get_node("Layers/petals/Petal_00")
	var transform := petal.global_transform
	scene.set_view("TOP")
	await process_frame
	check(petal.global_transform.is_equal_approx(transform), "Orbit does not rotate effect meshes")
	check(petal.get_instance_shader_parameter("life_alpha") > 0, "Per-instance fade uniform is active")
	var twin = load(path.get_base_dir()+"/explosion.tscn").instantiate()
	scene.add_child(twin)
	twin.paused = true
	twin.seek(.7)
	check(not is_equal_approx(twin.elapsed,effect.elapsed), "Independent instances")
	twin.queue_free()
	if "--capture" in OS.get_cmdline_user_args():
		DirAccess.make_dir_recursive_absolute(output)
		for view in ["TOP","SIDE","GAMEPLAY"]:
			scene.set_view(view)
			effect.seek(.28)
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(output+view.to_lower()+".png")
		scene.set_view("GAMEPLAY")
		effect.seek(1.0)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output+"smoke.png")
	effect.seek(effect.duration)
	check(not petal.visible,"End of clip clears layer")
	effect.restart()
	effect.loop = false
	await create_timer(effect.duration+.15).timeout
	check(not effect.playing,"One-shot ends")
	print("MESH_VFX_QA="+JSON.stringify({"result":"PASS" if errors.is_empty() else "FAIL","errors":errors,"components":effect.components.size(),"billboards":0}))
	quit(0 if errors.is_empty() else 1)
