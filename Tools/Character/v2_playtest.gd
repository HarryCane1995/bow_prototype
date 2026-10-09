extends SceneTree

# Bounded input-driven proof in the real Movement Gym. No replacement motor.
var player: Node3D
var v2: Node3D
var slide: Node
var evidence = []
const OUT = "res://.godot/humanoid-base/v2-playtest"

func _initialize():
    call_deferred("run")

func frames(count: int):
    for i in count:
        await physics_frame

func capture(label: String):
    await RenderingServer.frame_post_draw
    root.get_texture().get_image().save_png(OUT + "/" + label + ".png")
    var sk = v2.get("Skeleton") as Skeleton3D
    var state = {"view": label, "slide": slide.get("IsSliding"), "pose": v2.get("PoseName"),
        "position": str(player.global_position), "body_yaw": v2.global_rotation.y,
        "camera_yaw": player.global_rotation.y, "camera_pitch": player.get_node("CameraPivot").rotation.x,
        "body_skeleton_id": sk.get_instance_id(), "head_visible": sk.get_node("HEAD").visible}
    evidence.append(state)
    print("V2_PROOF ", JSON.stringify(state))

func look(x: float, y: float):
    var e = InputEventMouseMotion.new()
    e.relative = Vector2(x,y)
    Input.parse_input_event(e)

func reset_start():
    for a in ["move_forward", "move_back", "move_left", "move_right", "crouch_slide"]:
        Input.action_release(a)
    await frames(100)
    player = current_scene.get_node("Player")
    v2 = player.get_node("MainCharacterV2")
    slide = player.get_node("PlayerCrouchSlideModule")
    # Test-fixture reset only; production movement/collision parameters stay untouched.
    player.global_position = Vector3(0,0.1,5)
    player.velocity = Vector3.ZERO
    var pitch = player.get_node("CameraPivot").rotation.x
    look(player.rotation.y / 0.0017, pitch / 0.0017)
    player.rotation.y = 0
    v2.call("SetExternalView", false)
    await frames(25)

func run():
    DirAccess.make_dir_recursive_absolute(OUT)
    root.size = Vector2i(1280,720)
    root.mode = Window.MODE_WINDOWED
    Engine.max_fps = 60
    var gym = load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym)
    current_scene = gym
    player = gym.get_node("Player")
    v2 = player.get_node("MainCharacterV2")
    slide = player.get_node("PlayerCrouchSlideModule")
    await frames(60)
    await capture("01_idle_fp")
    v2.call("SetExternalView", true)
    await frames(3)
    await capture("02_idle_external")
    v2.call("SetExternalView", false)
    look(0,380)
    await frames(3)
    await capture("03_idle_look_down")
    look(0,-380)
    await reset_start()
    Input.action_press("move_forward")
    await frames(18)
    Input.action_press("crouch_slide")
    await frames(12)
    Input.action_release("move_forward")
    assert(slide.get("IsSliding"))
    assert(v2.get("PoseName") == "BH01_SLIDE")
    var locked_yaw = v2.global_rotation.y
    await capture("04_slide_fp")
    v2.call("SetExternalView", true)
    await frames(3)
    await capture("05_slide_external")
    look(340,190)
    await frames(3)
    assert(abs(angle_difference(locked_yaw, v2.global_rotation.y)) < 0.001)
    await capture("06_slide_external_yaw_pitch")
    v2.call("SetExternalView", false)
    await frames(3)
    await capture("07_slide_fp_yaw_pitch")
    Input.action_release("crouch_slide")
    await frames(75)
    assert(not slide.get("IsSliding"))
    assert(v2.get("PoseName") == "BH01_IDLE")
    await capture("08_slide_exit_idle")
    for direction in ["move_left", "move_right"]:
        await reset_start()
        player.global_position.x = 8 if direction == "move_left" else -8
        Input.action_press(direction)
        await frames(18)
        Input.action_press("crouch_slide")
        await frames(12)
        Input.action_release(direction)
        assert(slide.get("IsSliding"))
        v2.call("SetExternalView", true)
        await frames(2)
        await capture("09_slide_" + direction)
    await reset_start()
    v2.call("SetV2Enabled", false)
    await frames(4)
    assert(player.get_node("CanvasLayer_ViewModel").visible)
    assert(not v2.get_node("Body").visible)
    await capture("10_fallback")
    v2.call("SetV2Enabled", true)
    await frames(4)
    assert(not player.get_node("CanvasLayer_ViewModel").visible)
    await capture("11_v2_restored_fp")
    var file = FileAccess.open(OUT + "/results.json", FileAccess.WRITE)
    file.store_string(JSON.stringify({"status":"PASS", "evidence":evidence},"  "))
    print("V2_PLAYTEST_PASS")
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
