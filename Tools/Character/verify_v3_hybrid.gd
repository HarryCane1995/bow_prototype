extends SceneTree
const OUT = "res://.godot/hybrid-scenes"
var failures=[]
var samples=[]
var p
var w
var v
var cam
var gym
var monitor=false
var monitored_frames=0
func _initialize(): call_deferred("run")
func expect(ok,message):
    if not ok: failures.append(message); push_error(message)
func delay(t): await create_timer(t).timeout
func action(name,pressed):
    var e=InputEventAction.new();e.action=name;e.pressed=pressed
    Input.parse_input_event(e);Input.flush_buffered_events()
func key(code):
    for down in [true,false]:
        var e=InputEventKey.new();e.keycode=code;e.pressed=down
        Input.parse_input_event(e);Input.flush_buffered_events()
func mouse(button,pressed):
    var e=InputEventMouseButton.new();e.button_index=button;e.pressed=pressed
    Input.parse_input_event(e);Input.flush_buffered_events()
func look(yaw,pitch=0.0):
    var e=InputEventMouseMotion.new();e.relative=Vector2(deg_to_rad(yaw),deg_to_rad(pitch))/p.LookModule.MouseSensitivity
    Input.parse_input_event(e);Input.flush_buffered_events()
func box(pos,size):
    var body=StaticBody3D.new();var c=CollisionShape3D.new();var shape=BoxShape3D.new();shape.size=size;c.shape=shape
    body.add_child(c);gym.add_child(body);body.global_position=pos;return body
func check_masks():
    if not v.Active:return
    var visible=[]
    for name in ["HEAD","TORSO","ARMS","LEGS"]:
        var mesh=w.Skeleton.get_node(name)
        if mesh.visible and (mesh.layers & cam.cull_mask)!=0:visible.append(name)
    var wanted=["LEGS"] if p.CrouchSlideModule.IsSliding and not w.ExternalView else []
    expect(visible==wanted,"World parts leaked into gameplay camera: "+str(visible))
    for node in w.PresentationWeapon.find_children("*","VisualInstance3D",true,false):
        expect((node.layers & cam.cull_mask)==0,"World bow leaked into FP")
    expect(v.FpVisible==not w.ExternalView,"FP/external ownership")
    expect(v.FpSkeleton!=w.Skeleton,"Shared FP/world skeleton")
    expect(not w.Slide360Active,"V3 used V2 Slide 360")
func check_render_frame():
    if monitor:
        check_masks();monitored_frames+=1
func sample(name,shot=true):
    await process_frame;await RenderingServer.frame_post_draw
    check_masks()
    expect(v.FpBowAimErrorDegrees<0.05,"FP bow aim")
    samples.append({"case":name,"hybrid":v.Active,"fp":v.FpVisible,"legs":v.SlideLegsVisible,"slot":v.FpSlot,"clip":v.FpClip,"world_pose":w.PoseName,"fp_aim_error":v.FpBowAimErrorDegrees,"main_mask":cam.cull_mask})
    if shot:root.get_texture().get_image().save_png(OUT+"/"+name+".png")
func run():
    create_timer(35).timeout.connect(func():push_error("V3 smoke timeout");quit(1))
    Engine.max_fps=120;root.size=Vector2i(1280,720);root.title="BowPrototype V3 quick check"
    gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    gym.HumanRunLoggingEnabled=false;gym.HumanRunFullscreen=false
    root.add_child(gym);current_scene=gym
    await delay(0.4)
    p=gym.get_node("Player");w=p.get_node("MainCharacterV2");v=p.get_node("MainCharacterV3");cam=p.Camera
    Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
    expect(v.Active and v.FpVisible,"V3 default FP")
    var fp_parts=[]
    for mesh in v.FpSkeleton.find_children("*","MeshInstance3D",false,false):
        fp_parts.append(str(mesh.name))
        expect(mesh.mesh!=null and mesh.skin!=null,"FP region missing source data: "+str(mesh.name))
    fp_parts.sort()
    expect(fp_parts==["ARMS","TORSO"],"FP must contain only TORSO + ARMS: "+str(fp_parts))
    expect(v.get_node("FirstPerson").scene_file_path.ends_with("MainCharacter1POV.tscn"),"Missing separate 1POV scene")
    expect(w.scene_file_path.ends_with("MainCharacter3POV.tscn"),"Missing separate 3POV scene")
    monitor=true
    RenderingServer.frame_post_draw.connect(check_render_frame)
    await sample("01_idle")
    action("move_forward",true);await delay(0.25);await sample("02_run")
    action("crouch_slide",true);await delay(0.18);await sample("03_slide")
    expect(p.CrouchSlideModule.IsSliding and v.SlideLegsVisible,"Real slide entry")
    var locked=w.LockedSlideDirection
    var body_yaw=w.global_rotation.y
    var pelvis=w.Skeleton.get_bone_pose(w.Skeleton.find_bone("pelvis"))
    var spine=w.Skeleton.get_bone_pose(w.Skeleton.find_bone("spine_02"))
    key(KEY_F11);await delay(0.05)
    expect(w.Slide360Active and not v.FpVisible,"V2 Slide 360 fallback")
    key(KEY_F11);await delay(0.05)
    look(180);await delay(0.1);await sample("04_slide_back")
    expect(locked.is_equal_approx(w.LockedSlideDirection) and abs(angle_difference(body_yaw,w.global_rotation.y))<0.001,"Slide trajectory unlocked")
    expect(spine.is_equal_approx(w.Skeleton.get_bone_pose(w.Skeleton.find_bone("spine_02"))),"World slide torso turret")
    expect(pelvis.is_equal_approx(w.Skeleton.get_bone_pose(w.Skeleton.find_bone("pelvis"))),"World slide pelvis changed")
    look(-180,30);await delay(0.04);await sample("04b_slide_down")
    look(0,-30);action("crouch_slide",false);action("move_forward",false)
    p.CrouchSlideModule.CancelSlide();await delay(0.2);await sample("05_slide_exit")
    expect(not v.SlideLegsVisible,"Legs did not hide")
    key(KEY_F10);await delay(0.12);await sample("06_external")
    expect(w.ExternalView and not v.FpVisible,"F10 external")
    var external=w.get_node("ExternalCamera")
    for name in ["HEAD","TORSO","ARMS","LEGS"]:
        var mesh=w.Skeleton.get_node(name);expect(mesh.visible and (mesh.layers&external.cull_mask)!=0,"External missing "+name)
    key(KEY_F10);await delay(0.05)
    key(KEY_F11);await delay(0.15)
    expect(not v.Active and w.Enabled,"V2 comparison")
    root.get_texture().get_image().save_png(OUT+"/07_v2.png")
    key(KEY_F11);await delay(0.1);await sample("08_v3_return")
    # Independent FP key must not write the world skeleton or gameplay camera.
    var fp_anim=v.FpSkeleton.get_parent().get_node("AnimationPlayer")
    var world_anim=w.get_node("Body/AnimationPlayer")
    expect(fp_anim!=world_anim,"Shared animation player")
    expect(fp_anim.get_animation_library("")!=world_anim.get_animation_library(""),"Shared FP/world animation library")
    # One temporary FP-only key proves the future authoring slot and one-way
    # camera dependency. No production asset or world clip is edited.
    var fp_test=fp_anim.get_animation("BH01_IDLE").duplicate()
    fp_test.length=1.0
    var track=fp_test.find_track(NodePath("Skeleton3D:hand.R"),Animation.TYPE_POSITION_3D)
    if track<0:
        track=fp_test.add_track(Animation.TYPE_POSITION_3D)
        fp_test.track_set_path(track,NodePath("Skeleton3D:hand.R"))
    while fp_test.track_get_key_count(track)>0:fp_test.track_remove_key(track,0)
    var hand=v.FpSkeleton.find_bone("hand.R")
    var authored_hand=v.FpSkeleton.get_bone_pose_position(hand)
    fp_test.position_track_insert_key(track,0,authored_hand+Vector3(0.05,0,0))
    fp_test.position_track_insert_key(track,1,authored_hand+Vector3(0.05,0,0))
    var world_hand_before=w.Skeleton.get_bone_pose(w.Skeleton.find_bone("hand.R"))
    var proof=load("res://Tools/Character/V2AimProof.cs").new();root.add_child(proof);proof.Player=p;proof.V2=w
    fp_anim.get_animation_library("").add_animation("FP_IDLE",fp_test)
    await delay(0.13)
    expect(v.FpClip=="FP_IDLE" and not world_anim.has_animation("FP_IDLE"),"FP-only slot routing")
    expect(v.FpSkeleton.get_bone_pose_position(hand).distance_to(authored_hand)>0.04,"FP key not evaluated")
    await process_frame;await RenderingServer.frame_post_draw
    var calibration=JSON.parse_string(FileAccess.get_file_as_string(w.CameraCalibrationPath))
    var m=calibration.cameras.CAM_FP_WORLD.socket_offset_transform
    var expected_camera=proof.AuthoredWorld("FP_CAMERA_SOCKET").origin+w.Skeleton.global_basis*Vector3(m[0][3],m[1][3],m[2][3])
    expect(cam.global_position.distance_to(expected_camera)<0.0002,"FP animation fed back into gameplay camera")
    expect(world_hand_before.is_equal_approx(w.Skeleton.get_bone_pose(w.Skeleton.find_bone("hand.R"))),"FP key changed world hand")
    fp_anim.stop();fp_anim.play("BH01_IDLE",0);fp_anim.advance(0)
    fp_anim.get_animation_library("").remove_animation("FP_IDLE")
    # Real canonical walls in an isolated temporary fixture.
    box(Vector3(300,39.5,300),Vector3(200,1,200))
    for side in [-1,1]:
        var wall=box(Vector3(300+side*1.35,48,300),Vector3(1,16,100))
        p.global_position=Vector3(300,44,300);p.rotation=Vector3.ZERO;p.velocity=Vector3(0,1,-15);p.reset_physics_interpolation()
        action("move_forward",true);action("parkour_mode",true);await delay(0.2)
        expect(p.WallRunModule.IsWallRunning,"Canonical wall acquisition")
        await sample("09_wall_"+str(side))
        expect(v.FpSlot==("FP_WALLRUN_LEFT" if side<0 else "FP_WALLRUN_RIGHT"),"FP wall slot")
        action("parkour_mode",false);action("move_forward",false);await delay(0.05);wall.queue_free();await delay(0.05)
    p.global_position=Vector3(300,40.05,300);p.velocity=Vector3.ZERO;p.reset_physics_interpolation();await delay(0.3)
    var seq=p.BowVisualModule.ShotVisualSequence
    await process_frame;mouse(MOUSE_BUTTON_LEFT,true);await delay(0.4)
    expect(v.FpSlot==("FP_BOW_FULL_DRAW" if p.BowVisualModule.DrawAmount>=0.99 else "FP_BOW_DRAW_START"),"LMB draw slot: "+v.FpSlot+" draw="+str(p.BowVisualModule.DrawAmount))
    await process_frame;mouse(MOUSE_BUTTON_LEFT,false);await delay(0.05)
    expect(p.BowVisualModule.ShotVisualSequence==seq+1,"LMB single shot")
    await sample("10_lmb_release",false);await delay(0.35)
    mouse(MOUSE_BUTTON_RIGHT,true);await delay(0.07)
    expect(v.FpSlot=="FP_RMB_ANTICIPATION","RMB slot")
    mouse(MOUSE_BUTTON_RIGHT,false);await delay(0.08)
    expect(v.FpSlot=="FP_MELEE","Melee slot")
    await delay(0.5)
    # One real jump/fall/landing, then one manual grapple: presentation observers
    # must keep the upper-body layer and never reveal ordinary world geometry.
    await process_frame;action("jump",true);await delay(0.10);action("jump",false)
    expect(p.velocity.y>0 and not p.is_on_floor(),"Real jump entry")
    await sample("11_jump")
    var air_time=0.0
    while p.velocity.y>=0 and air_time<2:
        await delay(0.05);air_time+=0.05
    expect(p.velocity.y<0 and not p.is_on_floor(),"Fall state")
    await sample("12_fall",false)
    while not p.is_on_floor() and air_time<4:
        await delay(0.05);air_time+=0.05
    expect(p.is_on_floor(),"Landing")
    await sample("13_landing",false)
    var anchor=load("res://Scenes/GrappleAnchor.tscn").instantiate();gym.add_child(anchor)
    anchor.global_position=cam.global_position-cam.global_basis.z*8
    await physics_frame;await physics_frame
    await process_frame;action(p.SlingshotGrappleModule.GrappleAction,true);await delay(0.12);action(p.SlingshotGrappleModule.GrappleAction,false)
    expect(p.SlingshotGrappleModule.IsSlingshotActive,"Grapple acquired without Shift")
    await sample("14_grapple")
    var grapple_time=0.0
    while p.SlingshotGrappleModule.IsSlingshotActive and grapple_time<2:
        await delay(0.05);grapple_time+=0.05
    expect(not p.SlingshotGrappleModule.IsSlingshotActive,"Grapple completed")
    anchor.queue_free()
    key(KEY_F9);await delay(0.05);expect(not w.Enabled and not v.FpVisible,"F9 legacy fallback")
    key(KEY_F9);await delay(0.1);expect(w.Enabled and v.FpVisible,"F9 hybrid return")
    await sample("15_final",false)
    monitor=false
    FileAccess.open(OUT+"/smoke.json",FileAccess.WRITE).store_string(JSON.stringify({"failures":failures,"render_frames":monitored_frames,"samples":samples},"  "))
    print("V3_SMOKE_", "PASS" if failures.is_empty() else "FAIL", " frames=",monitored_frames," ",JSON.stringify(failures))
    quit(0 if failures.is_empty() else 1)
