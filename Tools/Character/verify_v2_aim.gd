extends SceneTree
var fixture
var player
var v2
var camera
var failures=[]
var evidence=[]
const OUT="res://.godot/humanoid-base/v2-aim"
func _initialize():call_deferred("run")
func frames(n):
    for i in n:await RenderingServer.frame_post_draw
func expect(ok,message):
    if not ok:failures.append(message);push_error(message)
func look(yaw,pitch):
    var pivot=player.get_node("CameraPivot")
    var e=InputEventMouseMotion.new()
    e.relative=Vector2((player.rotation.y-deg_to_rad(yaw))/0.0017,(pivot.rotation.x-deg_to_rad(pitch))/0.0017)
    Input.parse_input_event(e)
func snapshot():
    var sk=v2.Skeleton
    var poses={}
    for i in sk.get_bone_count():poses[sk.get_bone_name(i)]=sk.get_bone_pose(i)
    return poses
func run():
    create_timer(25).timeout.connect(func():quit(1))
    DirAccess.make_dir_recursive_absolute(OUT)
    root.size=Vector2i(1280,720);Engine.max_fps=60
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    await frames(2)
    fixture=load("res://Tools/Character/V2AimProof.cs").new();root.add_child(fixture);fixture.Setup(gym)
    player=fixture.Player;v2=fixture.V2;camera=player.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    for side in ["Left","Right"]:
        fixture.Wall(side)
        for enabled in [false,true]:
            v2.SetV2Enabled(enabled)
            await frames(3)
            var sk=v2.Skeleton
            var socket=sk.global_transform*sk.get_bone_global_pose(sk.find_bone("FP_CAMERA_SOCKET")).origin
            print("ROLL_PROBE ",side," v2=",enabled," effects=",camera.get_parent().rotation_degrees," camera=",camera.global_rotation_degrees," local=",camera.rotation_degrees," pos=",camera.global_position," socket=",socket)
            root.get_texture().get_image().save_png(OUT+"/roll_"+side+"_"+str(enabled)+".png")
    fixture.Wall("None")
    for slide in [false,true]:
        look(0,0);fixture.Pose(slide)
        v2.UpperBodyAimWeight=0;v2.LeftArmIKWeight=0;v2.RightArmIKWeight=0
        await frames(12)
        var base=snapshot()
        v2.UpperBodyAimWeight=0.3;v2.LeftArmIKWeight=1;v2.RightArmIKWeight=1
        for angle in [Vector2(0,0),Vector2(45,0),Vector2(-45,0),Vector2(0,40),Vector2(0,-40),Vector2(40,35),Vector2(-40,-35),Vector2(110,75)]:
            look(angle.x,angle.y)
            await frames(3)
            var error=v2.BowAimErrorDegrees
            var current=snapshot()
            for bone in base:
                if bone=="root" or bone=="pelvis" or bone.begins_with("thigh") or bone.begins_with("calf") or bone.begins_with("foot") or bone.begins_with("toes"):
                    expect(base[bone].is_equal_approx(current[bone]),"Lower body changed: "+bone)
            expect(not slide or abs(v2.global_rotation.y)<0.0001,"Slide body followed look")
            if abs(angle.x)<=65 and abs(angle.y)<=55:expect(error<0.1,"Bow aim mismatch: "+str(error))
            var row={"slide":slide,"yaw":angle.x,"pitch":angle.y,"aim_error_deg":error,"left_reach_error_m":v2.LeftGripError,"right_reach_error_m":v2.RightGripError}
            evidence.append(row);print("AIM_PROBE ",JSON.stringify(row))
            root.get_texture().get_image().save_png(OUT+"/aim_"+str(slide)+"_"+str(angle.x)+"_"+str(angle.y)+".png")
            if angle==Vector2(40,35):
                v2.SetExternalView(true);await frames(2)
                root.get_texture().get_image().save_png(OUT+"/external_"+str(slide)+".png")
                v2.SetExternalView(false)
        v2.UpperBodyAimWeight=0;v2.LeftArmIKWeight=0;v2.RightArmIKWeight=0
        look(0,0);await frames(3)
        var restored=snapshot()
        for bone in base:expect(base[bone].is_equal_approx(restored[bone]),"Zero weights not authored: "+bone)
    var status="PASS" if failures.is_empty() else "FAIL"
    FileAccess.open(OUT+"/results.json",FileAccess.WRITE).store_string(JSON.stringify({"status":status,"evidence":evidence,"failures":failures},"  "))
    print("V2_AIM_",status)
    quit(0 if failures.is_empty() else 1)
