extends SceneTree

const OUT = "res://.godot/humanoid-base/v2-camera"
var player: Node3D
var v2: Node3D
var camera: Camera3D
var source: Dictionary
var evidence = []
var failures = []
var socket_frames = []
var camera_offset: Vector3

func check_socket_frame():
    if not is_instance_valid(v2):
        push_error("Camera test player was replaced by Gym recovery")
        quit(1)
        return
    var sk = v2.get("Skeleton") as Skeleton3D
    var index = sk.find_bone("FP_CAMERA_SOCKET")
    var chain = []
    while index >= 0:
        chain.push_front(index)
        index=sk.get_bone_parent(index)
    # Independently accumulate current local bone poses, avoiding a cached global
    # socket transform. A camera reading last frame's pose will fail during blends.
    var actual_pose=Transform3D.IDENTITY
    for bone in chain:actual_pose *= sk.get_bone_pose(bone)
    var expected=sk.global_transform*(actual_pose.origin+camera_offset)
    var error=camera.global_position.distance_to(expected)
    expect(error<0.00001,"Socket/camera frame lag: " + str(error))
    socket_frames.append({"pose":v2.get("PoseName"),"camera_height":camera.global_position.y-v2.global_position.y,
        "position_error_m":error,"frame":Engine.get_process_frames()})

func sample_frames(count: int):
    for i in count:
        await RenderingServer.frame_post_draw
        check_socket_frame()

func toggle_external():
    var key=InputEventKey.new()
    key.keycode=KEY_F10;key.physical_keycode=KEY_F10;key.pressed=true
    Input.parse_input_event(key)
    key=InputEventKey.new();key.keycode=KEY_F10;key.physical_keycode=KEY_F10;key.pressed=false
    Input.parse_input_event(key)

func expect(condition: bool, message: String):
    if not condition:
        failures.append(message)
        push_error(message)

func _initialize():
    call_deferred("run")

func frames(count: int):
    for i in count:
        await physics_frame

func look(x: float, y: float):
    var e = InputEventMouseMotion.new()
    e.relative = Vector2(x,y)
    Input.parse_input_event(e)
    Input.flush_buffered_events()

func capture(pose: String):
    await RenderingServer.frame_post_draw
    expect(v2.get("PoseName") == pose,"Wrong pose: " + pose)
    var sk = v2.get("Skeleton") as Skeleton3D
    var worst = 0.0
    var checked = 0
    for bone in source.poses[pose].cameras.CAM_FP_WORLD.bone_uv:
        var uv = source.poses[pose].cameras.CAM_FP_WORLD.bone_uv[bone]
        if uv[2] <= camera.near:
            continue
        var actual = camera.unproject_position(sk.global_transform * sk.get_bone_global_pose(sk.find_bone(bone)).origin)
        var expected = Vector2(uv[0]*root.size.x,(1-uv[1])*root.size.y)
        worst = max(worst,actual.distance_to(expected))
        checked += 1
    expect(checked > 8,"Too few projected joints: " + str(checked))
    expect(worst < 0.1,"Camera projection differs from Blender: " + str(worst))
    var expected_fov=source.poses[pose].cameras.CAM_FP_WORLD.fov_y_degrees
    expect(abs(camera.fov-expected_fov)<0.001,"Source FOV mismatch")
    root.get_texture().get_image().save_png(OUT + "/godot_" + pose + "_CAM_FP_WORLD.png")
    var record = {"pose":pose,"max_bone_projection_error_px":worst,"joints_checked":checked,
        "fov":camera.fov,"camera_in_body":str(v2.global_transform.affine_inverse()*camera.global_transform),
        "camera_height":camera.global_position.y-v2.global_position.y,
        "actual_slide":player.get_node("PlayerCrouchSlideModule").get("IsSliding")}
    var bow=v2.find_child("Bow_Visual",true,false) as MeshInstance3D
    var bow_in_model=v2.get_node("Body").global_transform.affine_inverse()*bow.global_transform
    var m=source.poses[pose].bow_matrix
    var source_bow=Transform3D(Basis(Vector3(m[0][0],m[2][0],-m[1][0]),
        Vector3(m[0][2],m[2][2],-m[1][2]),-Vector3(m[0][1],m[2][1],-m[1][1])),
        Vector3(m[0][3],m[2][3],-m[1][3]))
    var bow_origin_error=bow_in_model.origin.distance_to(source_bow.origin)
    var bow_basis_error=max(bow_in_model.basis.x.distance_to(source_bow.basis.x),
        max(bow_in_model.basis.y.distance_to(source_bow.basis.y),bow_in_model.basis.z.distance_to(source_bow.basis.z)))
    expect(bow_origin_error<0.0001 and bow_basis_error<0.0001,"Bow source transform mismatch")
    record["bow_origin_error_m"]=bow_origin_error
    record["bow_basis_error"]=bow_basis_error
    evidence.append(record)
    print("V2_CAMERA_PROOF ",JSON.stringify(record))

func run():
    create_timer(20.0).timeout.connect(func():push_error("Camera test timed out");quit(1))
    DirAccess.make_dir_recursive_absolute(OUT)
    source = JSON.parse_string(FileAccess.get_file_as_string("res://.godot/humanoid-base/v2_source_capture.json"))
    var calibration=JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.camera.json"))
    expect(calibration.version==2 and not calibration.has("poses"),"Per-pose camera calibration is still present")
    var offset=calibration.cameras.CAM_FP_WORLD.socket_offset_transform
    camera_offset=Vector3(offset[0][3],offset[1][3],offset[2][3])
    root.size=Vector2i(1280,720)
    root.mode=Window.MODE_WINDOWED
    Engine.max_fps=60
    var gym=load("res://Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn").instantiate()
    root.add_child(gym);current_scene=gym
    player=gym.get_node("Player");v2=player.get_node("MainCharacterV2")
    camera=player.get_node("CameraPivot/CameraEffectsPivot/Camera3D")
    # Validate source calibration independently of the optional runtime aim layer.
    v2.set("UpperBodyAimWeight",0);v2.set("LeftArmIKWeight",0);v2.set("RightArmIKWeight",0)
    await frames(30)
    # Window creation/cursor capture can deliver an initial OS mouse delta.
    # Reset only this fixture's look to the calibrated neutral source frame.
    var sensitivity=player.get_node("PlayerLookModule").MouseSensitivity
    look(player.rotation.y/sensitivity,player.get_node("CameraPivot").rotation.x/sensitivity)
    await sample_frames(2)
    await capture("BH01_IDLE")
    Input.action_press("move_forward")
    await frames(18)
    Input.action_press("crouch_slide")
    await sample_frames(20)
    Input.action_release("move_forward")
    await capture("BH01_SLIDE")
    var sk_id=(v2.get("Skeleton") as Skeleton3D).get_instance_id()
    toggle_external()
    await frames(2)
    await RenderingServer.frame_post_draw
    expect(v2.get("ExternalView"),"F10 did not select external camera")
    expect((v2.get("Skeleton") as Skeleton3D).get_instance_id()==sk_id,"F10 changed skeleton instance")
    await RenderingServer.frame_post_draw
    root.get_texture().get_image().save_png(OUT+"/godot_BH01_SLIDE_external.png")
    toggle_external()
    await frames(2)
    expect(camera.current,"F10 did not restore gameplay camera")
    await RenderingServer.frame_post_draw
    var body_yaw=v2.global_rotation.y
    var eye_before=v2.global_transform.affine_inverse()*camera.global_position
    look(250,140)
    await frames(3)
    await RenderingServer.frame_post_draw
    expect(abs(angle_difference(body_yaw,v2.global_rotation.y))<0.001,"Slide yaw changed with mouse look")
    expect(eye_before.distance_to(v2.global_transform.affine_inverse()*camera.global_position)<0.001,"Eye origin drifted with mouse look")
    expect(abs(camera.global_rotation.y)>0.2 and abs(camera.global_rotation.x)>0.1,"Mouse look did not reach camera")
    expect(camera.project_ray_normal(Vector2(640,360)).distance_to(-camera.global_basis.z)<0.001,"Aim ray differs from camera forward")
    look(-250,-140)
    Input.action_release("crouch_slide")
    # Finish as soon as the real slide and its existing animation blend end;
    # a long fixed delay carries the player into the next Gym obstacle/recovery.
    for i in 60:
        await sample_frames(1)
        if not is_instance_valid(v2):return
        if v2.get("PoseName")=="BH01_IDLE":break
    await sample_frames(10)
    expect(v2.get("PoseName")=="BH01_IDLE","Slide exit did not return to Idle")
    expect(abs(camera.global_position.y-v2.global_position.y-evidence[0].camera_height)<0.0001,"Idle camera height did not return")
    var rise=evidence[0].camera_height-evidence[1].camera_height
    expect(rise>0.4 and rise<0.6,"Idle did not rise with chest")
    var transitional=socket_frames.filter(func(f):return f.camera_height>evidence[1].camera_height+0.01 and f.camera_height<evidence[0].camera_height-0.01)
    expect(transitional.size()>2,"Camera blend has no intermediate socket heights")
    v2.call("SetV2Enabled",false)
    await frames(2)
    expect(camera.transform.is_equal_approx(Transform3D.IDENTITY),"Fallback transform not restored")
    expect(player.get_node("PlayerCameraFovModule").process_mode != Node.PROCESS_MODE_DISABLED,"Fallback FOV owner not restored")
    v2.call("SetV2Enabled",true)
    await frames(2)
    expect(abs(camera.fov-source.poses.BH01_SLIDE.cameras.CAM_FP_WORLD.fov_y_degrees)<0.001,"V2 FOV not restored")
    var status="PASS" if failures.is_empty() else "FAIL"
    FileAccess.open(OUT+"/results.json",FileAccess.WRITE).store_string(JSON.stringify({"status":status,"evidence":evidence,"failures":failures,
        "socket_frames":socket_frames,"idle_camera_rise_m":rise,"blend_intermediate_frames":transitional.size()},"  "))
    print("V2_CAMERA_SOCKET_",status," rise_m=",rise," samples=",socket_frames.size()," blend_frames=",transitional.size())
    # Let the renderer detach the moved weapon before tearing down the viewport.
    current_scene.queue_free()
    await frames(3)
    quit(0 if failures.is_empty() else 1)
