extends SceneTree
## Short real-input smoke check; fixture changes and clip injection stay in memory.
const OUT = "res://.godot/rmb-foundation"
var failures = []
var trace = []
var commits = 0
var releases = 0
var parries = 0
var hits = 0
var worst_aim = 0.0
var combat
var player
var v2
var camera
var gym

func _initialize(): call_deferred("run")
func expect(ok, message):
	if not ok:
		failures.append(message)
		push_error(message)
func frames(n):
	for i in n: await process_frame
func delay(seconds): await create_timer(seconds).timeout
func rmb(pressed):
	var e = InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_RIGHT
	e.pressed = pressed
	Input.parse_input_event(e)
	Input.flush_buffered_events()
func action(name, pressed):
	var e = InputEventAction.new()
	e.action = name
	e.pressed = pressed
	Input.parse_input_event(e)
func key(code):
	var e = InputEventKey.new()
	e.keycode = code
	e.pressed = true
	Input.parse_input_event(e)
	e = InputEventKey.new()
	e.keycode = code
	e.pressed = false
	Input.parse_input_event(e)
func idle():
	await delay(0.58)
	expect(combat.StateName == "Idle", "Recovery did not return to Idle")
func aim_sample():
	worst_aim = max(worst_aim, v2.BowAimErrorDegrees)
	expect(v2.BowAimErrorDegrees < 0.15, "V2 aim IK changed")
func on_release(origin, direction, charge, ready):
	releases += 1
	expect(origin.is_equal_approx(camera.global_position), "Power aim origin differs from gameplay camera")
	expect(direction.angle_to(-camera.global_basis.z.normalized()) < 0.0001, "Power aim differs from current gameplay camera")
	trace.append({"release_charge":charge,"ready":ready,"aim_direction":str(direction)})
func arrows():
	return gym.get_children().filter(func(n): return n.get_script() != null and str(n.get_script().resource_path).ends_with("/ArrowProjectile.cs")).size()

func run():
	create_timer(35).timeout.connect(func(): push_error("RMB smoke timeout"); quit(1))
	Engine.max_fps = 120
	root.size = Vector2i(1280,720)
	root.title = "BowPrototype RMB quick check"
	gym = load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
	gym.HumanRunLoggingEnabled = false
	gym.HumanRunFullscreen = false
	root.add_child(gym)
	current_scene = gym
	await frames(25)
	player = gym.get_node("Player")
	v2 = player.get_node("MainCharacterV2")
	combat = player.get_node("PlayerRmbCombat")
	camera = player.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	combat.MeleeCommitted.connect(func(): commits += 1)
	combat.ParrySucceeded.connect(func(_p): parries += 1)
	combat.MeleeHitReported.connect(func(_t,_p): hits += 1)
	combat.PowerShotReleased.connect(on_release)
	combat.StateChanged.connect(func(previous,current): trace.append({"from":previous,"to":current,"held":combat.HeldTime}))
	expect(v2.Enabled and not v2.ExternalView, "Initial V2/1POV configuration changed")

	# Immediate DOWN and short release; hit callback only inside active window.
	rmb(true)
	expect(combat.StateName == "RmbAnticipation" and combat.IsParryWindowOpen, "DOWN did not immediately open parry")
	expect(commits == 0, "Melee fired on DOWN")
	await delay(0.045)
	rmb(false)
	expect(combat.StateName == "Melee" and commits == 1 and releases == 0, "Tap did not commit only melee")
	expect(not combat.TryParryProjectile(gym,true), "Parry accepted after melee commit")
	expect(not combat.TryReportMeleeHit(gym,Vector3.ZERO), "Melee hit before active window")
	await delay(0.11)
	expect(combat.IsMeleeActive and combat.TryReportMeleeHit(gym,Vector3.ZERO), "Melee active hook failed")
	expect(not combat.TryReportMeleeHit(gym,Vector3.ZERO) and hits == 1, "Duplicate melee target accepted")
	aim_sample()
	await idle()

	# Both events in one frame must remain a tap, not disappear in polling.
	rmb(true); rmb(false)
	expect(commits == 2 and combat.StateName == "Melee", "Very short tap lost")
	for i in 8: rmb(true); rmb(false)
	expect(commits == 2, "Busy spam queued extra melee")
	await idle()
	rmb(true); await delay(0.035); rmb(false)
	expect(commits == 3, "Fresh repeated tap did not work after recovery")
	await idle()

	# Hold and release before full charge, with mouse look in the release frame.
	rmb(true); await delay(0.23)
	expect(combat.StateName == "PowerShotPrep" and commits == 3 and not combat.IsParryWindowOpen, "Hold did not select only power prep")
	var motion = InputEventMouseMotion.new()
	motion.relative = Vector2(70,-30)
	Input.parse_input_event(motion)
	rmb(false); await frames(3)
	expect(releases == 1 and commits == 3, "Hold release also emitted melee or duplicate release")
	rmb(false); await frames(2)
	expect(releases == 1, "Duplicate UP emitted another power release")
	aim_sample()
	await idle()

	rmb(true); await delay(1.0)
	expect(combat.PowerReady and combat.ChargeAmount == 1, "Long hold did not reach PowerShotReady")
	rmb(false); await frames(3)
	expect(releases == 2 and commits == 3, "Ready release counts invalid")
	await idle()

	# Reactive parry consumes the entire gesture, including continuing hold.
	rmb(true)
	expect(not combat.TryParryProjectile(gym,false), "Ineligible projectile was parried")
	expect(combat.DebugTryParry(), "Immediate debug parry failed")
	expect(combat.StateName == "ParrySuccess" and not combat.IsParryWindowOpen, "Parry did not consume its window")
	expect(not combat.DebugTryParry(), "Parry succeeded twice")
	await delay(0.5)
	rmb(false); await frames(3)
	expect(parries == 1 and commits == 3 and releases == 2, "Parry continued into melee or hold")
	await idle()
	rmb(true); await delay(0.155)
	expect(not combat.DebugTryParry(), "Expired parry window accepted a hit")
	rmb(false); await idle()

	# A supplied animation resolves via the resource; no production export needed.
	var anim = v2.get_node("Body/AnimationPlayer")
	var library = anim.get_animation_library("")
	library.add_animation("BH01_RMB_ANTICIPATION", anim.get_animation("BH01_IDLE").duplicate())
	rmb(true); await frames(3)
	expect(v2.PoseName == "BH01_RMB_ANTICIPATION", "Animation slot was not consumed")
	rmb(false); await idle()
	library.remove_animation("BH01_RMB_ANTICIPATION")

	# Real movement and slide + free yaw; state logic never acquires the motor.
	var floor = StaticBody3D.new()
	var collision = CollisionShape3D.new()
	var shape = BoxShape3D.new()
	shape.size = Vector3(250,1,250)
	collision.shape = shape
	floor.add_child(collision); gym.add_child(floor)
	floor.global_position = player.global_position + Vector3(0,-0.6,0)
	action("move_forward",true); await delay(0.18)
	rmb(true); await delay(0.035); rmb(false)
	expect(combat.StateName == "Melee" and player.velocity.length() > 1, "Tap while moving failed")
	await idle()
	action("crouch_slide",true); await delay(0.06)
	expect(player.get_node("PlayerCrouchSlideModule").IsSliding, "No real slide in fixture")
	var locked = v2.LockedSlideDirection
	var yaw = v2.global_rotation.y
	rmb(true); await delay(0.23)
	expect(combat.StateName == "PowerShotPrep" and v2.PoseName == "BH01_SLIDE", "RMB displaced slide pose")
	motion = InputEventMouseMotion.new()
	motion.relative = Vector2(-TAU / player.get_node("PlayerLookModule").MouseSensitivity, -80)
	Input.parse_input_event(motion)
	await frames(3)
	expect(locked.is_equal_approx(v2.LockedSlideDirection) and abs(angle_difference(yaw,v2.global_rotation.y)) < 0.001, "RMB broke slide direction lock")
	aim_sample()
	rmb(false); await frames(3)
	action("move_forward",false); action("crouch_slide",false)
	await idle()

	key(KEY_F10); await frames(3)
	expect(v2.ExternalView, "F10 external view failed")
	key(KEY_F10); await frames(3)
	expect(not v2.ExternalView and camera.current, "F10 FP return failed")
	key(KEY_F9); await frames(3)
	expect(not v2.Enabled, "F9 fallback failed")
	key(KEY_F9); await frames(3)
	expect(v2.Enabled and not v2.ExternalView, "F9 V2 return failed")
	aim_sample()

	var before_arrows = arrows()
	action("fire",true); await delay(0.05); action("fire",false); await frames(3)
	expect(arrows() > before_arrows, "Ordinary LMB shot stopped spawning arrows")
	rmb(true); await delay(0.04)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	await frames(3)
	expect(combat.StateName == "Idle" and not combat.IsParryWindowOpen, "Cursor release left a stuck gesture")
	rmb(false)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(OUT+"/runtime.png")
	var result = {"status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"melee_commits":commits,"power_releases":releases,"parries":parries,"melee_hits":hits,"worst_bow_aim_degrees":worst_aim,"trace":trace}
	FileAccess.open(OUT+"/runtime_validation.json",FileAccess.WRITE).store_string(JSON.stringify(result,"  "))
	print("RMB_SMOKE_",result.status," melee=",commits," power=",releases," parry=",parries," aim_error=",worst_aim)
	quit(0 if failures.is_empty() else 1)
