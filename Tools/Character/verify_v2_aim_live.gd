extends SceneTree
var player
var v2
var camera
var failures=[]
var worst=0.0
func _initialize():call_deferred("run")
func frames(n):
    for i in n:await physics_frame
func expect(ok,message):
    if not ok:failures.append(message);push_error(message)
func look(x,y):
    var e=InputEventMouseMotion.new();e.relative=Vector2(x,y);Input.parse_input_event(e)
func sample(n):
    for i in n:
        await RenderingServer.frame_post_draw
        worst=max(worst,v2.BowAimErrorDegrees)
        expect(v2.BowAimErrorDegrees<0.1,"Current-frame aim lag")
        var sk=v2.Skeleton
        var hand=sk.global_transform*sk.get_bone_global_pose(sk.find_bone("hand.L"))
        var grip=sk.get_node("V2_LeftHandGrip")
        expect(grip.global_transform.is_equal_approx(hand),"Attachment lag")
func run():
    create_timer(15).timeout.connect(func():quit(1))
    var full_circle="--slide360" in OS.get_cmdline_user_args()
    root.size=Vector2i(1280,720);Engine.max_fps=240 if full_circle else 60
    if full_circle:DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    player=gym.get_node("Player");v2=player.get_node("MainCharacterV2")
    camera=player.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    await frames(20)
    Input.action_press("move_forward");await frames(18)
    Input.action_press("crouch_slide");await sample(12)
    Input.action_release("move_forward")
    expect(v2.PoseName=="BH01_SLIDE","Not a real slide")
    var body_yaw=v2.global_rotation.y
    if full_circle:
        var sensitivity=player.get_node("PlayerLookModule").MouseSensitivity
        for i in 80:
            look(-deg_to_rad(9)/sensitivity,0)
            Input.flush_buffered_events()
            await sample(1)
            expect(player.get_node("PlayerCrouchSlideModule").IsSliding,"360 sweep left the real Slide")
            expect(abs(angle_difference(body_yaw,v2.global_rotation.y))<0.001,"Slide yaw changed")
        print("LIVE_SLIDE360 two_turns=720 root_yaw=",v2.global_rotation.y)
    else:
        for i in 5:
            look(70,-30);await sample(1)
            expect(abs(angle_difference(body_yaw,v2.global_rotation.y))<0.001,"Slide yaw changed")
        look(-350,150)
    Input.action_release("crouch_slide")
    while v2.PoseName=="BH01_SLIDE":await sample(1)
    await sample(10)
    print("V2_AIM_LIVE_", "PASS" if failures.is_empty() else "FAIL", " max_error_deg=",worst)
    quit(0 if failures.is_empty() else 1)
