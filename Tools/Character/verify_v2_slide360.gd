extends SceneTree
const OUT="res://.godot/humanoid-base/v2-feedback"
var failures=[]
var rows=[]
func _initialize():call_deferred("run")
func expect(ok,message):
    if not ok:failures.append(message);push_error(message)
func input_delta(dx,dy=0.0):
    var e=InputEventMouseMotion.new();e.relative=Vector2(dx,dy);Input.parse_input_event(e)
    Input.flush_buffered_events()
func capture_pose(sk):
    var pose={}
    for b in sk.get_bone_count():pose[sk.get_bone_name(b)]=sk.get_bone_pose(b)
    return pose
func run():
    create_timer(30).timeout.connect(func():quit(1))
    root.size=Vector2i(1280,720);Engine.max_fps=60 if "--60" in OS.get_cmdline_user_args() else 240
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    for i in 5:await process_frame
    var f=load("res://Tools/Character/V2AimProof.cs").new();root.add_child(f);f.Setup(gym)
    var p=f.Player;var v=f.V2;var sk=v.Skeleton
    var sensitivity=p.get_node("PlayerLookModule").MouseSensitivity
    f.Pose(true)
    for i in 40:await RenderingServer.frame_post_draw
    var base=capture_pose(sk)
    var spine=sk.find_bone("spine_02")
    var initial=sk.get_bone_global_pose(spine)
    var previous=initial
    var camera=p.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    var bow=v.find_child("Bow_Visual",true,false)
    for degree in range(0,721):
        if degree>0:input_delta(-deg_to_rad(1)/sensitivity)
        await process_frame
        await RenderingServer.frame_post_draw
        var pose=capture_pose(sk)
        var current=sk.get_bone_global_pose(spine)
        var jump=rad_to_deg(previous.basis.get_rotation_quaternion().angle_to(current.basis.get_rotation_quaternion()))
        expect(jump<1.1,"Spine snap at "+str(degree)+": "+str(jump))
        var sk_axis=sk.global_basis.inverse()*Vector3.UP
        var expected=Basis(sk_axis,deg_to_rad(degree))*initial.basis
        expect(rad_to_deg(expected.get_rotation_quaternion().angle_to(current.basis.get_rotation_quaternion()))<0.08,"Turret yaw is not on spine at "+str(degree))
        for bone in base:
            if bone=="root" or bone=="pelvis" or bone.begins_with("thigh") or bone.begins_with("calf") or bone.begins_with("foot") or bone.begins_with("toes"):
                expect(base[bone].is_equal_approx(pose[bone]),"Lower body drift "+bone)
        expect(abs(v.global_rotation.y)<0.00001,"Body root yaw unlocked")
        expect(v.BowAimErrorDegrees<0.05,"Bow lost 360 aim")
        var rendered=rad_to_deg((-bow.get_global_transform_interpolated().basis.x).angle_to(-camera.get_global_transform_interpolated().basis.z))
        expect(rendered<0.05,"Interpolated bow lag")
        rows.append({"frame":Engine.get_process_frames(),"degree":degree,"relative_yaw":v.ClampedAimDegrees.x,"spine_step_deg":jump,
            "aim_error_deg":v.BowAimErrorDegrees,"rendered_error_deg":rendered,"left_reach_error_m":v.LeftGripError})
        if degree%90==0 and degree<=360:
            root.get_texture().get_image().save_png(OUT+"/slide360_fp_"+str(degree)+".png")
            v.SetExternalView(true);await RenderingServer.frame_post_draw
            root.get_texture().get_image().save_png(OUT+"/slide360_external_"+str(degree)+".png")
            v.SetExternalView(false)
        if degree==360 or degree==720:
            var max_position=0.0;var max_angle=0.0
            for bone in base:
                var pos=base[bone].origin.distance_to(pose[bone].origin)
                var angle=rad_to_deg(base[bone].basis.get_rotation_quaternion().angle_to(pose[bone].basis.get_rotation_quaternion()))
                max_position=max(max_position,pos);max_angle=max(max_angle,angle)
                expect(pos<0.0001 and angle<0.08,"Revolution drift "+bone)
            print("REVOLUTION_DRIFT degree=",degree," position_m=",max_position," angle_deg=",max_angle)
        previous=current
    f.Pose(false)
    for i in 35:await RenderingServer.frame_post_draw
    expect(not v.Slide360Active,"Slide flag persisted")
    # A grounded body normally follows player yaw. Freeze only this fixture's
    # body transform to prove the existing limit still applies off-slide.
    v.set_process(false)
    input_delta(-deg_to_rad(100)/sensitivity)
    f.SolveFrozenBody()
    expect(abs(v.ClampedAimDegrees.x-65)<0.02,"Grounded yaw limit changed")
    FileAccess.open(OUT+"/slide360_"+str(Engine.max_fps)+".json",FileAccess.WRITE).store_string(JSON.stringify({"status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"frames":rows},"  "))
    print("SLIDE360_", "PASS" if failures.is_empty() else "FAIL", " samples=",rows.size())
    quit(0 if failures.is_empty() else 1)
