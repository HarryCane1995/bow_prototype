extends SceneTree
## Runtime integration check using Level_01 and the production arrow collision path.
const LEVEL = "res://Scenes/Levels/Level_01/Level_01.tscn"
const EFFECT = "res://Assets/VFX/Explosions/MeshExplosion3D/mesh_explosion_99_r02/explosion.tscn"
const OUT = "res://.godot/cyborg-death-vfx/"
var errors: Array[String] = []
var level: Node3D

func _init() -> void:
	call_deferred("run")

func check(ok: bool, message: String) -> void:
	if not ok:
		errors.append(message)
		push_error("CYBORG_VFX_QA: " + message)

func effects() -> Array:
	return level.get_children().filter(func(n): return n.scene_file_path == EFFECT)

func open_level() -> void:
	level = load(LEVEL).instantiate()
	# Test-only isolation: never change serialized player, enemy or window settings.
	level.get_node("StartupWindowModeController").EnableStartupWindowMode = false
	for child in level.get_node("CombatDraft").get_children():
		if child.is_in_group("enemy"):
			child.CanShoot = false
	root.add_child(level)
	current_scene = level
	await process_frame
	await process_frame

func run() -> void:
	create_timer(45).timeout.connect(func(): push_error("Cyborg VFX QA timeout"); quit(1))
	Engine.max_fps = 120
	root.size = Vector2i(1200, 800)
	DirAccess.make_dir_recursive_absolute(OUT)
	await open_level()
	var enemies = get_nodes_in_group("enemy")
	check(enemies.size() == 8, "Level_01 has eight cyborgs")
	for enemy in enemies:
		check(enemy.DeathEffectScene.resource_path == EFFECT, "Exact r02 export assigned")
		check(enemy.CurrentHealth == 8, "Default health matches ordinary arrow damage")
	var victim = level.get_node("CombatDraft/Cyborg_01_Read")
	var origin: Vector3 = victim.global_position
	var shot = load("res://Scenes/ArrowProjectile.tscn").instantiate()
	shot.FlightMode = 1
	level.add_child(shot)
	shot.global_position = origin + Vector3(0, 1.45, 4)
	shot.Initialize(Vector3.FORWARD, 40.0, 8.0, 2.0)
	for frame in 90:
		await process_frame
		if not is_instance_valid(victim):
			break
	check(not is_instance_valid(victim), "Real arrow collision destroys cyborg")
	check(effects().size() == 1, "One arrow spawns exactly one effect")
	if effects().is_empty():
		quit(1)
		return
	var first = effects()[0]
	check(first.get_parent() == level, "Effect survives outside enemy subtree")
	check(first.global_position.is_equal_approx(origin), "Ground ring uses enemy world origin")
	check(first.global_basis.is_equal_approx(Basis.IDENTITY), "Enemy facing does not tilt or scale effect")
	check(not first.loop and first.playing, "Death effect is playing once")
	check(first.components.size() == 42, "All exported mesh components loaded")
	first.paused = true
	first.seek(0.28)
	if "--capture" in OS.get_cmdline_user_args():
		# The presentation module reselects its gameplay camera every frame.
		# Freeze only this test instance before taking the detached review view.
		var player = level.get_node("Player")
		player.process_mode = Node.PROCESS_MODE_DISABLED
		player.hide()
		for canvas in player.find_children("*", "CanvasLayer", true, false):
			canvas.hide()
		var camera := Camera3D.new()
		level.add_child(camera)
		camera.global_position = origin + Vector3(6, 3.5, 7)
		camera.look_at(origin + Vector3(0, 1, 0))
		camera.current = true
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT + "level01-death.png")
	first.paused = false

	var second = level.get_node("CombatDraft/Cyborg_02_LeftAngle")
	second.ApplyDamage(0)
	second.ApplyDamage(-10)
	check(second.CurrentHealth == 8 and not second.IsDead, "Non-positive damage ignored")
	second.ApplyDamage(3)
	check(second.CurrentHealth == 5 and not second.IsDead and effects().size() == 1, "Nonlethal hit does not explode")
	second.ApplyDamage(5)
	second.ApplyDamage(8)
	check(second.IsDead and not second.CanShoot and not second.visible, "Death disables enemy immediately")
	var elevated = level.get_node("CombatDraft/Cyborg_04_HighNest")
	var elevated_origin: Vector3 = elevated.global_position
	elevated.ApplyDamage(8)
	await process_frame
	await process_frame
	check(effects().size() == 3, "Repeated hit gives one effect; simultaneous death is independent")
	check(effects().any(func(n): return n.global_position.is_equal_approx(elevated_origin)), "Elevated cyborg effect stays at its world height")
	check(not is_instance_valid(second) and not is_instance_valid(elevated), "Dead bodies leave scene")
	await create_timer(float(first.duration) + 0.3).timeout
	check(effects().is_empty() and not is_instance_valid(first), "Finished effects free themselves")
	check(get_nodes_in_group("enemy").size() == 5, "Only hit enemies were removed")

	var no_effect = load("res://Scenes/Enemies/CyborgPressureEnemy.tscn").instantiate()
	no_effect.DeathEffectScene = null
	no_effect.CanShoot = false
	level.add_child(no_effect)
	no_effect.ApplyDamage(8)
	await process_frame
	await process_frame
	check(not is_instance_valid(no_effect) and effects().is_empty(), "Empty VFX field still allows clean death")
	var last = level.get_node("CombatDraft/Cyborg_03_Window")
	last.ApplyDamage(8)
	await process_frame
	await process_frame
	var pending = effects()[0]
	level.queue_free()
	await process_frame
	await process_frame
	check(not is_instance_valid(pending), "Level unload also frees active VFX")
	await open_level()
	check(get_nodes_in_group("enemy").size() == 8 and effects().is_empty(), "Reload restores enemies without stale effects")
	level.queue_free()
	await process_frame
	await process_frame
	var report = {"result": "PASS" if errors.is_empty() else "FAIL", "errors": errors, "effect": EFFECT,
		"level_cyborgs": 8, "real_arrow_collision": true, "duplicate_and_concurrent_deaths": true,
		"automatic_cleanup": true, "level_reload": true}
	FileAccess.open(OUT + "qa.json", FileAccess.WRITE).store_string(JSON.stringify(report, "  "))
	print("CYBORG_VFX_QA=" + JSON.stringify(report))
	quit(0 if errors.is_empty() else 1)
