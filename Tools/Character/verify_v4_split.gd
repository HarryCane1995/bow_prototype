extends SceneTree
const OUT="res://.godot/split-presentation"
var failures=[]
var p
var v
var gym
var seen={}
func _initialize():call_deferred("run")
func expect(ok,message):
    if not ok:failures.append(message);push_error(message)
func delay(t):await create_timer(t).timeout
func action(name,down):
    var e=InputEventAction.new();e.action=name;e.pressed=down;Input.parse_input_event(e);Input.flush_buffered_events()
func key(code):
    for down in [true,false]:
        var e=InputEventKey.new();e.keycode=code;e.pressed=down;Input.parse_input_event(e);Input.flush_buffered_events()
func mouse(button,down):
    var e=InputEventMouseButton.new();e.button_index=button;e.pressed=down;Input.parse_input_event(e);Input.flush_buffered_events()
func box(pos,size):
    var b=StaticBody3D.new();var c=CollisionShape3D.new();var s=BoxShape3D.new();s.size=size;c.shape=s;b.add_child(c);gym.add_child(b);b.global_position=pos;return b
func monitor():
    if not v or not v.Active:return
    seen[v.StateName]=true
    expect(v.FirstPerson.Clip.begins_with("BH01_1POV_"),"FP indexed routing")
    expect(v.ThirdPerson.Clip.begins_with("BH01_3POV_"),"World indexed routing")
    for part in ["HEAD","TORSO","ARMS","LEGS"]:
        expect((v.ThirdPerson.Skeleton.get_node(part).layers&p.Camera.cull_mask)==0,"World geometry leaked "+part)
func shot(name):
    await RenderingServer.frame_post_draw
    root.get_texture().get_image().save_png(OUT+"/"+name+".png")
func run():
    DirAccess.make_dir_recursive_absolute(OUT)
    create_timer(35).timeout.connect(func():push_error("TIMEOUT");quit(1))
    Engine.max_fps=120;root.size=Vector2i(1280,720)
    gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    gym.HumanRunLoggingEnabled=false;gym.HumanRunFullscreen=false;root.add_child(gym);current_scene=gym
    await delay(.5);p=gym.get_node("Player");v=p.get_node("MainCharacterV4");Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
    expect(v.Active and v.FpVisible,"Default split ON")
    expect(not p.BowVisualModule.ArrowPresentationOwnedByHands,"Arrow visual owner remains gameplay bow module")
    expect(v.FirstPerson.Skeleton!=v.ThirdPerson.Skeleton,"Skeleton isolation")
    expect(v.FirstPerson.Animations.get_animation_library("")!=v.ThirdPerson.Animations.get_animation_library(""),"Library isolation")
    var names=[]
    for mesh in v.FirstPerson.Skeleton.find_children("*","MeshInstance3D",false,false):names.append(str(mesh.name))
    expect(names==["ARMS"],"Only arms geometry: "+str(names))
    RenderingServer.frame_post_draw.connect(monitor)
    await shot("01_idle")
    action("move_forward",true);await delay(.3);await shot("02_run")
    action("crouch_slide",true);await delay(.2)
    expect(p.CrouchSlideModule.IsSliding,"Real slide");await shot("03_slide")
    action("crouch_slide",false);action("move_forward",false);p.CrouchSlideModule.CancelSlide()
    key(KEY_F10);await delay(.2);expect(v.ExternalView and not v.FpVisible,"External only world");await shot("04_external")
    for part in ["HEAD","TORSO","ARMS","LEGS"]:expect(v.ThirdPerson.Skeleton.get_node(part).visible,"External part "+part)
    key(KEY_F10);await delay(.1)
    var before=v.ThirdPerson.AdvanceCount;await delay(.1);expect(v.ThirdPerson.AdvanceCount>before,"World continues hidden")
    box(Vector3(300,39.5,300),Vector3(200,1,200))
    for side in [-1,1]:
        var wall=box(Vector3(300+side*1.35,48,300),Vector3(1,16,100))
        p.global_position=Vector3(300,44,300);p.rotation=Vector3.ZERO;p.velocity=Vector3(0,1,-15);p.reset_physics_interpolation()
        action("move_forward",true);action("parkour_mode",true);await delay(.2)
        expect(p.WallRunModule.IsWallRunning,"Wall acquisition "+str(side));await shot("05_wall_"+str(side))
        action("parkour_mode",false);action("move_forward",false);await delay(.05);wall.queue_free();await delay(.05)
    p.global_position=Vector3(300,40.05,300);p.velocity=Vector3.ZERO;p.rotation=Vector3.ZERO;p.reset_physics_interpolation();await delay(.4)
    action("jump",true);await delay(.1);action("jump",false);await shot("06_jump")
    await delay(1.5)
    p.global_position=Vector3(300,40.05,300);p.velocity=Vector3.ZERO;p.reset_physics_interpolation();await delay(.4)
    mouse(MOUSE_BUTTON_RIGHT,true);await delay(.05);expect(v.StateName=="RmbAnticipation","RMB anticipation")
    await delay(.17);await shot("07_ready");await delay(.85);expect(v.StateName=="BowFullDraw","Bow full draw")
    mouse(MOUSE_BUTTON_RIGHT,false);await delay(.5)
    var seq=p.BowVisualModule.ShotVisualSequence
    await process_frame;mouse(MOUSE_BUTTON_LEFT,true);await delay(.4);await shot("08_draw")
    expect(p.BowVisualModule.IsDrawing,"Real LMB drawing")
    await process_frame;mouse(MOUSE_BUTTON_LEFT,false);await delay(.05)
    expect(p.BowVisualModule.ShotVisualSequence==seq+1,"Single gameplay shot before="+str(seq)+" after="+str(p.BowVisualModule.ShotVisualSequence));await delay(.4)
    var fp_arrow=v.FirstPerson.Bow.find_child("Arrow_Visual",true,false)
    var world_arrow=v.ThirdPerson.Bow.find_child("Arrow_Visual",true,false)
    expect(fp_arrow.visible==world_arrow.visible,"Both bow representations mirror arrow visibility")
    var anchor=load("res://Scenes/GrappleAnchor.tscn").instantiate();gym.add_child(anchor)
    anchor.global_position=p.Camera.global_position-p.Camera.global_basis.z*8;await physics_frame;await physics_frame
    action(p.SlingshotGrappleModule.GrappleAction,true);await delay(.12);action(p.SlingshotGrappleModule.GrappleAction,false)
    expect(p.SlingshotGrappleModule.IsSlingshotActive,"Real grapple");await shot("09_grapple");await delay(1)
    key(KEY_F12);await delay(.2);expect(not v.Active and p.get_node("MainCharacterV3").Active,"V3 fallback")
    key(KEY_F11);await delay(.1);expect(not p.get_node("MainCharacterV3").Active and p.get_node("MainCharacterV2").Enabled,"V2 fallback")
    key(KEY_F12);await delay(.2);expect(v.Active and v.FpVisible,"Return split")
    p.global_position=Vector3(300,40.05,300);p.velocity=Vector3.ZERO;p.rotation=Vector3.ZERO;p.reset_physics_interpolation();await delay(.5)
    # Mutating either private runtime library cannot move gameplay camera or the
    # other rig. All mutations exist only in this disposable driver process.
    var cam_before=p.Camera.global_transform
    var fp_before=v.FirstPerson.Skeleton.get_bone_pose(v.FirstPerson.Skeleton.find_bone("hand.R"))
    var wa=v.ThirdPerson.Animations;var wl=wa.get_animation_library("")
    var world_original=wl.get_animation("BH01_3POV_IDLE")
    var changed=world_original.duplicate()
    var bone=v.ThirdPerson.Skeleton.find_bone("chest")
    var track=changed.find_track(NodePath("Skeleton3D:chest"),Animation.TYPE_POSITION_3D)
    expect(track>=0,"World chest animation track")
    if track>=0:
        while changed.track_get_key_count(track)>0:changed.track_remove_key(track,0)
        var pos=v.ThirdPerson.Skeleton.get_bone_pose_position(bone)+Vector3(0,1,0)
        changed.position_track_insert_key(track,0,pos);changed.position_track_insert_key(track,1,pos)
        wl.remove_animation("BH01_3POV_IDLE");wl.add_animation("BH01_3POV_IDLE",changed);wa.play("BH01_3POV_IDLE",0)
        await delay(.1)
        expect(p.Camera.global_transform.is_equal_approx(cam_before),"World animation moved camera")
        expect(fp_before.is_equal_approx(v.FirstPerson.Skeleton.get_bone_pose(v.FirstPerson.Skeleton.find_bone("hand.R"))),"World animation moved FP")
        wl.remove_animation("BH01_3POV_IDLE");wl.add_animation("BH01_3POV_IDLE",world_original);wa.play("BH01_3POV_IDLE",0)
    var fa=v.FirstPerson.Animations;var fl=fa.get_animation_library("")
    var fp_original=fl.get_animation("BH01_1POV_IDLE")
    var fchanged=fp_original.duplicate()
    var fh=v.FirstPerson.Skeleton.find_bone("hand.R")
    var ft=fchanged.find_track(NodePath("Skeleton3D:hand.R"),Animation.TYPE_POSITION_3D)
    expect(ft>=0,"FP hand animation track")
    if ft>=0:
        while fchanged.track_get_key_count(ft)>0:fchanged.track_remove_key(ft,0)
        var fpos=v.FirstPerson.Skeleton.get_bone_pose_position(fh)+Vector3(.05,0,0)
        fchanged.position_track_insert_key(ft,0,fpos);fchanged.position_track_insert_key(ft,1,fpos)
        fl.remove_animation("BH01_1POV_IDLE");fl.add_animation("BH01_1POV_IDLE",fchanged);fa.play("BH01_1POV_IDLE",0)
        await delay(.1)
        expect(p.Camera.global_transform.is_equal_approx(cam_before),"FP animation moved camera")
        expect(not wa.has_animation("BH01_1POV_IDLE"),"FP clip leaked into world library")
        fl.remove_animation("BH01_1POV_IDLE");fl.add_animation("BH01_1POV_IDLE",fp_original);fa.play("BH01_1POV_IDLE",0)
    var fp_run=v.FirstPerson.Slots.Clips[1];v.FirstPerson.Slots.Clips[1]=&"MISSING_FP_TEST"
    action("move_forward",true);await delay(.25)
    expect(v.FirstPerson.Clip=="BH01_1POV_IDLE" and v.ThirdPerson.Clip=="BH01_3POV_RUN","Branch-specific missing FP fallback")
    v.FirstPerson.Slots.Clips[1]=fp_run
    var world_run=v.ThirdPerson.Slots.Clips[1];v.ThirdPerson.Slots.Clips[1]=&"MISSING_WORLD_TEST"
    await delay(.1)
    expect(v.FirstPerson.Clip=="BH01_1POV_RUN" and v.ThirdPerson.Clip=="BH01_3POV_IDLE","Branch-specific missing world fallback")
    v.ThirdPerson.Slots.Clips[1]=world_run;action("move_forward",false)
    for state in ["Idle","Run","Slide","JumpTakeoff","JumpAir","Fall","Landing","WallrunLeft","WallrunRight","GrapplePull","GrappleLaunch","GrappleFlight","BowReady","RmbAnticipation"]:
        expect(seen.has(state),"Unseen state "+state)
    FileAccess.open(OUT+"/smoke.json",FileAccess.WRITE).store_string(JSON.stringify({"failures":failures,"seen":seen.keys(),"fp_clips":v.FirstPerson.Animations.get_animation_list(),"world_clips":v.ThirdPerson.Animations.get_animation_list()},"  "))
    gym.queue_free();await process_frame;await process_frame;quit(0 if failures.is_empty() else 1)
