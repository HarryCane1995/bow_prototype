extends SceneTree
const OUT="res://.godot/humanoid-base/v2-feedback"
var failures=[]
var rows=[]
class Probe extends Node:
    var fixture
    var camera
    var before_camera:Transform3D
    var before_socket:Transform3D
    var before_chest:Transform3D
    func _process(_dt):
        before_camera=camera.get_camera_transform()
        before_socket=fixture.AuthoredWorld("FP_CAMERA_SOCKET")
        before_chest=fixture.AuthoredWorld("chest")
func _initialize():call_deferred("run")
func vec(v):return [v.x,v.y,v.z]
func basis(b):return [vec(b.x),vec(b.y),vec(b.z)]
func transform(t):return {"origin":vec(t.origin),"basis":basis(t.basis)}
func input_delta(x,y):
    var e=InputEventMouseMotion.new();e.relative=Vector2(x,y)
    Input.parse_input_event(e);Input.flush_buffered_events()
func expect(ok,message):
    if not ok:failures.append(message)
func run():
    create_timer(45).timeout.connect(func():quit(1))
    DirAccess.make_dir_recursive_absolute(OUT)
    root.size=Vector2i(1280,720)
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    for i in 5:await process_frame
    var f=load("res://Tools/Character/V2AimProof.cs").new();root.add_child(f);f.Setup(gym)
    var p=f.Player;var v=f.V2;var sk=v.Skeleton
    var cam=p.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    var bow=v.find_child("Bow_Visual",true,false)
    var grip=sk.get_node("V2_LeftHandGrip")
    var probe=Probe.new();probe.fixture=f;probe.camera=cam;probe.process_priority=-9;root.add_child(probe)
    var calibration=JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.camera.json"))
    var m=calibration.cameras.CAM_FP_WORLD.socket_offset_transform
    var offset=Vector3(m[0][3],m[1][3],m[2][3])
    var sensitivity=p.LookModule.MouseSensitivity
    var baseline="--baseline" in OS.get_cmdline_user_args()
    for fps in [60,240]:
        Engine.max_fps=fps
        for slide in [false,true]:
            f.Pose(slide)
            for i in 35:await RenderingServer.frame_post_draw
            input_delta(p.rotation.y/sensitivity,p.get_node("CameraPivot").rotation.x/sensitivity)
            for pattern in ["yaw","pitch","circle","flick"]:
                var count=fps
                for i in count:
                    # Same angular path at each cap, including deliberately tiny input.
                    var t=float(i)/fps
                    var velocity=Vector2(2,0)
                    if pattern=="pitch":velocity=Vector2(0,2)
                    elif pattern=="circle":velocity=Vector2(cos(t*TAU),sin(t*TAU))*12
                    elif pattern=="flick":velocity=Vector2(600 if i==0 else (-600 if i==int(fps/2) else 0),0)*fps/60.0
                    input_delta(deg_to_rad(velocity.x)/sensitivity/fps,deg_to_rad(velocity.y)/sensitivity/fps)
                    var start=Time.get_ticks_usec()
                    await process_frame
                    await RenderingServer.frame_post_draw
                    var pre=probe.before_socket
                    var post=sk.global_transform*sk.get_bone_global_pose(sk.find_bone("FP_CAMERA_SOCKET"))
                    var chest=sk.global_transform*sk.get_bone_global_pose(sk.find_bone("chest"))
                    var camera=cam.get_camera_transform()
                    var camera_render=cam.get_global_transform_interpolated()
                    var expected_offset=offset
                    if slide:
                        var forward=v.global_basis.inverse()*-camera.basis.z
                        var y=atan2(-forward.x,-forward.z)
                        expected_offset=Basis((sk.global_basis.inverse()*Vector3.UP).normalized(),y)*offset
                    var expected=pre.origin+sk.global_basis*expected_offset
                    var hand=sk.global_transform*sk.get_bone_global_pose(sk.find_bone("hand.L"))
                    var bow_render=bow.get_global_transform_interpolated()
                    var body_forward=-v.global_basis.z;var look_forward=-camera.basis.z
                    body_forward.y=0;look_forward.y=0
                    var row={"frame":Engine.get_process_frames(),"physics":Engine.get_physics_frames(),"fps_cap":fps,"slide":slide,"pattern":pattern,
                        "dt":(Time.get_ticks_usec()-start)/1000000.0,"camera":transform(camera),"camera_before_late":transform(probe.before_camera),
                        "camera_render":transform(camera_render),"camera_render_yaw_error_deg":rad_to_deg((-camera_render.basis.z).angle_to(-camera.basis.z)),
                        "camera_render_position_error_m":camera_render.origin.distance_to(camera.origin),
                        "socket_pre":vec(pre.origin),"socket_post":vec(post.origin),"socket_delta_m":pre.origin.distance_to(post.origin),
                        "camera_preik_error_m":camera.origin.distance_to(expected),"camera_pass_delta_m":camera.origin.distance_to(probe.before_camera.origin),
                        "chest_delta_basis":basis(chest.basis*probe.before_chest.basis.inverse()),"hand":transform(hand),"bow":transform(bow_render),
                        "body_yaw_error_deg":rad_to_deg(body_forward.angle_to(look_forward)),
                        "bow_error_deg":rad_to_deg((-bow_render.basis.x).angle_to(-camera.basis.z)),
                        "grip_error_m":grip.global_position.distance_to(hand.origin),"reach_error_m":v.LeftGripError}
                    rows.append(row)
                    if not baseline:
                        expect(row.camera_render_yaw_error_deg<0.002 and row.camera_render_position_error_m<0.00001,"Camera ancestor interpolation phase lag")
                        expect(row.camera_preik_error_m<0.00001,"Camera used procedural socket")
                        expect(row.camera_pass_delta_m<0.00001,"Late competing camera writer")
                        expect(slide or row.body_yaw_error_deg<0.002,"Grounded yaw phase lead")
                        expect(row.bow_error_deg<0.002 and row.grip_error_m<0.00001,"Bow/hand phase lead")
                    if i==int(count/2):root.get_texture().get_image().save_png(OUT+"/"+("baseline" if baseline else "fixed")+"_"+str(fps)+"_"+("slide" if slide else "idle")+"_"+pattern+".png")
    var label="baseline" if baseline else "fixed"
    FileAccess.open(OUT+"/"+label+".json",FileAccess.WRITE).store_string(JSON.stringify({"failures":failures,"frames":rows},"  "))
    print("V2_FEEDBACK_",label," ","PASS" if failures.is_empty() else "FAIL"," samples=",rows.size()," failures=",failures.size())
    quit(0 if failures.is_empty() else 1)
