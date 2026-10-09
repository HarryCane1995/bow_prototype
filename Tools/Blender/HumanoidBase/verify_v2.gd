extends SceneTree

func _initialize():
    call_deferred("check")

func argument(name, fallback):
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with(name + "="): return arg.substr(name.length()+1)
    return fallback

func check():
    create_timer(20).timeout.connect(func():quit(1))
    var model_path = argument("--model", "res://Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.glb")
    var model
    if str(model_path).begins_with("res://.godot/"):
        var document = GLTFDocument.new()
        var state = GLTFState.new()
        assert(document.append_from_file(model_path,state) == OK)
        model = document.generate_scene(state,60,false,false)
        load("res://Scripts/Editor/Import/V2AnimationPostImport.gd").apply_metadata(model,str(model_path).get_basename()+".animations.json")
    else:
        var packed = load(model_path) as PackedScene
        assert(packed != null)
        model = packed.instantiate()
    root.add_child(model)
    var sk = model.find_child("Skeleton3D", true, false) as Skeleton3D
    var anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
    assert(sk != null and sk.get_bone_count() == 54)
    var socket = sk.find_bone("FP_CAMERA_SOCKET")
    assert(socket >= 0 and sk.get_bone_name(sk.get_bone_parent(socket)) == "chest")
    print("V2_CLIPS ", anim.get_animation_list())
    anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
    var capture = JSON.parse_string(FileAccess.get_file_as_string(argument("--capture", "res://.godot/humanoid-base/v2_source_capture.json")))
    var errors = {}
    for clip in capture.actions:
        assert(anim.has_animation(clip))
        var animation = anim.get_animation(clip)
        var loop_mode = animation.loop_mode
        var samples = [capture.poses[clip]]
        if capture.has("clips"):
            var metadata = capture.clips[clip]
            assert(abs(animation.length-metadata.duration_seconds)<0.001, "Clip timing changed: " + clip)
            assert((loop_mode == Animation.LOOP_LINEAR) == metadata.loop, "Loop metadata lost: " + clip)
            var full = metadata.samples
            samples = [full[0],full[full.size()/2],full[-1]]
        animation.loop_mode = Animation.LOOP_NONE # Allow checking the exact endpoint.
        var worst = 0.0
        for sample in samples:
            anim.play(clip,0)
            anim.seek(sample.get("time",0.5),true)
            var sample_worst = 0.0
            var detail = {}
            for i in sk.get_bone_count():
                var bone = sk.get_bone_name(i)
                var src = sample.bones[bone]
                var expected = Vector3(src[0][3], src[2][3], -src[1][3])
                var actual = sk.global_transform * sk.get_bone_global_pose(i).origin
                worst = max(worst, actual.distance_to(expected))
                if actual.distance_to(expected) > sample_worst:
                    sample_worst = actual.distance_to(expected)
                    detail = {"bone":bone,"actual":actual,"expected":expected}
            if sample_worst >= 0.0001: print("V2_SAMPLE_MISMATCH ",clip," t=",sample.get("time",0.5)," ",detail)
        animation.loop_mode = loop_mode
        errors[clip] = worst
        assert(worst < 0.0001, str(errors))
    var bow = load("res://Assets/Models/Bow/cyber_bow_preview.glb").instantiate()
    root.add_child(bow)
    anim.play("BH01_IDLE")
    anim.seek(0.5, true)
    var m = capture.poses.BH01_IDLE.bow_matrix
    var x = Vector3(m[0][0], m[2][0], -m[1][0])
    var y = Vector3(m[0][2], m[2][2], -m[1][2])
    var z = -Vector3(m[0][1], m[2][1], -m[1][1])
    var origin = Vector3(m[0][3],m[2][3],-m[1][3])
    var desired_mesh = Transform3D(Basis(x,y,z),origin)
    var attachment = sk.get_bone_global_pose(sk.find_bone("hand.L")).affine_inverse() * desired_mesh
    print("VERIFIED_GRIP_OFFSET ", attachment)
    var target_path = "res://Scenes/Characters/MainCharacterV2.tscn"
    var text = FileAccess.get_file_as_string(target_path)
    var values = []
    # .tscn Transform3D stores basis rows; Basis.x/y/z expose columns.
    var rows = attachment.basis.transposed()
    for v in [rows.x,rows.y,rows.z,attachment.origin]:
        for f in [v.x,v.y,v.z]: values.append(str(f))
    var rx = RegEx.new()
    rx.compile("BowMeshInHand = Transform3D\\([^\\n]+\\)")
    text = rx.sub(text,"BowMeshInHand = Transform3D(" + ", ".join(values) + ")")
    if "--write-grip-offset" in OS.get_cmdline_user_args():
        FileAccess.open(target_path,FileAccess.WRITE).store_string(text)
    print("V2_IMPORT_PASS ", JSON.stringify(errors))
    quit()
