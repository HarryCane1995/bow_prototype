extends SceneTree
## One short real-input routing pass. The fixture and animated proof clip are temporary.
const OUT = "res://.godot/locomotion-authoring"
var failures = []
var rows = []
var player
var v2
var camera
var proof
var offset: Vector3
var gym

func _initialize(): call_deferred("run")
func expect(ok, message):
    if not ok: failures.append(message); push_error(message)
func delay(t): await create_timer(t).timeout
func action(name, pressed):
    var e = InputEventAction.new(); e.action = name; e.pressed = pressed
    Input.parse_input_event(e); Input.flush_buffered_events()
func key(code):
    for down in [true,false]:
        var e = InputEventKey.new(); e.keycode = code; e.pressed = down
        Input.parse_input_event(e); Input.flush_buffered_events()
func box(position, size):
    var body = StaticBody3D.new(); var collision = CollisionShape3D.new()
    var shape = BoxShape3D.new(); shape.size = size; collision.shape = shape
    body.add_child(collision); gym.add_child(body); body.global_position = position
    return body
func sample(label, pose):
    await process_frame
    await RenderingServer.frame_post_draw
    var expected_offset = offset
    if v2.PoseName == "BH01_SLIDE":
        var forward = v2.global_basis.inverse() * -camera.global_basis.z
        expected_offset = Basis((v2.Skeleton.global_basis.inverse()*Vector3.UP).normalized(),atan2(-forward.x,-forward.z)) * offset
    var expected = proof.AuthoredWorld("FP_CAMERA_SOCKET").origin + v2.Skeleton.global_basis*expected_offset
    var error = camera.global_position.distance_to(expected)
    expect(v2.PoseName == pose, label + ": wrong pose " + v2.PoseName)
    expect(v2.BowAimErrorDegrees < 0.15, label + ": aim layer")
    expect(error < 0.0002, label + ": camera differs from pre-IK socket")
    rows.append({"case":label,"pose":v2.PoseName,"state":v2.LocomotionState,"wall_side":player.WallRunModule.ActiveWallSide,"speed":v2.HorizontalSpeed,"aim_error_degrees":v2.BowAimErrorDegrees,"camera_preik_error_m":error})

func run():
    create_timer(25).timeout.connect(func():push_error("V2 locomotion timeout");quit(1))
    Engine.max_fps = 120
    root.size = Vector2i(1280,720)
    root.title = "BowPrototype V2 locomotion quick check"
    gym = load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    gym.HumanRunLoggingEnabled = false; gym.HumanRunFullscreen = false
    root.add_child(gym); current_scene = gym
    await delay(0.3)
    player = gym.get_node("Player"); v2 = player.get_node("MainCharacterV2")
    camera = player.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    proof = load("res://Tools/Character/V2AimProof.cs").new(); root.add_child(proof)
    proof.Player = player; proof.V2 = v2 # Read-only authored-chain helper; do not freeze the motor.
    var calibration = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.camera.json"))
    var m = calibration.cameras.CAM_FP_WORLD.socket_offset_transform
    offset = Vector3(m[0][3],m[1][3],m[2][3])
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    box(Vector3(300,39.5,300),Vector3(200,1,200))
    player.global_position = Vector3(300,40.05,300); player.rotation = Vector3.ZERO; player.velocity = Vector3.ZERO
    player.reset_physics_interpolation()
    await delay(0.35)
    expect(v2.Enabled and not v2.ExternalView,"Initial V2/FP")
    await sample("idle","BH01_IDLE")
    action("move_forward",true); await delay(0.25)
    await sample("grounded run","BH01_RUN")
    var anim = v2.get_node("Body/AnimationPlayer")
    expect(anim.get_animation("BH01_RUN").loop_mode == Animation.LOOP_LINEAR,"Run loop metadata")
    v2.RunPlaybackSpeedScale = 1.25; await delay(0.05)
    expect(abs(anim.speed_scale-1.25)<0.001,"Run playback multiplier")

    # Exercise the unchanged camera/IK cadence on a genuinely moving base clip.
    var document = GLTFDocument.new(); var state = GLTFState.new()
    expect(document.append_from_file(OUT+"/multiframe/MultiFrameTest.glb",state)==OK,"Load temporary clip")
    var model = document.generate_scene(state,60,false,false)
    var test = model.find_child("AnimationPlayer",true,false).get_animation("BH01_TEST_MULTIFRAME").duplicate()
    test.loop_mode = Animation.LOOP_LINEAR
    var library = anim.get_animation_library(""); var original_run = library.get_animation("BH01_RUN")
    library.remove_animation("BH01_RUN"); library.add_animation("BH01_RUN",test); anim.play("BH01_RUN",0)
    for i in 3:
        await delay(0.2)
        await sample("animated run " + str(i),"BH01_RUN")
    library.remove_animation("BH01_RUN"); library.add_animation("BH01_RUN",original_run)
    anim.play("BH01_RUN",0); v2.RunPlaybackSpeedScale = 1.0; model.free()
    action("move_forward",false); await delay(0.45)
    await sample("run to idle","BH01_IDLE")

    action("move_forward",true); await delay(0.25)
    action("crouch_slide",true); await delay(0.12)
    expect(player.CrouchSlideModule.IsSliding,"Real slide entry")
    await sample("slide","BH01_SLIDE")
    action("crouch_slide",false); action("move_forward",false)
    player.CrouchSlideModule.CancelSlide(); await delay(0.2)

    for side in [-1,1]:
        var wall = box(Vector3(300+side*1.35,48,300),Vector3(1,16,100))
        player.global_position = Vector3(300,44,300); player.rotation = Vector3.ZERO
        player.velocity = Vector3(0,1,-15); player.reset_physics_interpolation()
        action("move_forward",true); action("parkour_mode",true)
        await delay(0.2)
        var label = "left" if side<0 else "right"
        expect(player.WallRunModule.IsWallRunning,"Real " + label + " wall acquisition")
        expect(player.WallRunModule.ActiveWallSide == (1 if side<0 else 2),"Authoritative wall side")
        await sample(label + " wallrun","BH01_WALLRUN_LEFT" if side<0 else "BH01_WALLRUN_RIGHT")
        action("parkour_mode",false); action("move_forward",false)
        await delay(0.06); wall.queue_free(); await delay(0.06)
        await sample(label + " wall exit","BH01_IDLE")

    key(KEY_F10); await delay(0.04); expect(v2.ExternalView,"F10 external")
    key(KEY_F10); await delay(0.04); expect(not v2.ExternalView and camera.current,"F10 FP")
    key(KEY_F9); await delay(0.04); expect(not v2.Enabled,"F9 fallback")
    key(KEY_F9); await delay(0.04); expect(v2.Enabled and not v2.ExternalView,"F9 V2 return")
    FileAccess.open(OUT+"/runtime.json",FileAccess.WRITE).store_string(JSON.stringify({"failures":failures,"samples":rows},"  "))
    print("V2_LOCOMOTION_", "PASS" if failures.is_empty() else "FAIL", " ",JSON.stringify(rows))
    quit(0 if failures.is_empty() else 1)
