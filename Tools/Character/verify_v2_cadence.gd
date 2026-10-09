extends SceneTree
const OUT="res://.godot/humanoid-base/v2-cadence"
var rows=[]
func _initialize():call_deferred("run")
func basis_rows(b):return [str(b.x),str(b.y),str(b.z)]
func yaw(b):return rad_to_deg(atan2(b.z.x,b.z.z))
func run():
    create_timer(30).timeout.connect(func():quit(1))
    DirAccess.make_dir_recursive_absolute(OUT)
    root.size=Vector2i(1280,720)
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    for i in 5:await process_frame
    var fixture=load("res://Tools/Character/V2AimProof.cs").new();root.add_child(fixture);fixture.Setup(gym)
    var p=fixture.Player;var v=fixture.V2;var sk=v.Skeleton
    var cam=p.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    var bow=v.find_child("Bow_Visual",true,false)
    var grip=sk.get_node("V2_LeftHandGrip")
    var target=v.get_node("V2_BowAimTarget")
    var modes={}
    for n in [p,v,sk,cam,grip,bow]:modes[str(n.get_path())]={"mode":n.physics_interpolation_mode,"effective":n.is_physics_interpolated_and_enabled()}
    print("CADENCE_MODES ",JSON.stringify(modes))
    for fps in [60,240]:
        Engine.max_fps=fps
        var start=Time.get_ticks_usec();var last=start
        for i in (120 if fps==60 else 480):
            await process_frame
            var now=Time.get_ticks_usec();var dt=(now-last)/1000000.0;last=now
            var t=(now-start)/1000000.0
            var e=InputEventMouseMotion.new()
            var pattern="yaw"
            if t<0.5:e.relative=Vector2(28*dt,0)
            elif t<1.0:pattern="pitch";e.relative=Vector2(0,14*dt)
            elif t<1.7:pattern="circle";e.relative=Vector2(cos(t*14),sin(t*14))*32*dt
            else:pattern="flick";e.relative=Vector2(75 if i%20==0 else 0,0)
            Input.parse_input_event(e)
            await RenderingServer.frame_post_draw
            var interpolated=bow.get_global_transform_interpolated()
            var bone=sk.get_bone_global_pose(sk.find_bone("hand.L"))
            var rendered_forward=-interpolated.basis.x.normalized()
            var error=rad_to_deg(rendered_forward.angle_to(-cam.global_basis.z))
            rows.append({"frame":Engine.get_process_frames(),"physics":Engine.get_physics_frames(),"fps_cap":fps,"dt":dt,"pattern":pattern,
                "camera_yaw":yaw(cam.global_basis),"bow_solved_yaw":rad_to_deg(atan2(-(-bow.global_basis.x).x,-(-bow.global_basis.x).z)),
                "solved_error_deg":v.BowAimErrorDegrees,"interpolated_error_deg":error,
                "camera_basis":basis_rows(cam.global_basis),"target_basis":basis_rows(target.global_basis),
                "torso":str(sk.get_bone_global_pose(sk.find_bone("chest"))),"hand":str(bone),"bow":str(bow.global_transform),
                "attachment_error_m":grip.global_position.distance_to((sk.global_transform*bone).origin)})
        print("CADENCE_FPS ",fps," actual=",(120 if fps==60 else 480)/((Time.get_ticks_usec()-start)/1000000.0))
    var label="baseline" if "--baseline" in OS.get_cmdline_user_args() else "fixed"
    FileAccess.open(OUT+"/"+label+".json",FileAccess.WRITE).store_string(JSON.stringify({"modes":modes,"frames":rows},"  "))
    for fps in [60,240]:
        var mx=0.0;var solved=0.0
        for r in rows:
            if r.fps_cap==fps:mx=max(mx,r.interpolated_error_deg);solved=max(solved,r.solved_error_deg)
        print("CADENCE_RESULT ",label," cap=",fps," interpolated_error_deg=",mx," solved_error_deg=",solved)
    quit()
