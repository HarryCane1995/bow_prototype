extends "res://Tools/Blender/LevelBlockoutV02/verify_godot.gd"
## Reuse read-only collision comparison helpers. Only initial Player placement is synthetic.
var report: Dictionary
var sections: Array

func bl(v: Array) -> Vector3: return Vector3(v[0],v[2],-v[1])
func start_of(s: Dictionary) -> Vector3: return bl(s.entry)
func direction(s: Dictionary) -> Vector3:
    var d := bl(s.exit)-bl(s.entry)
    d.y=0
    return d.normalized()
func progress(s: Dictionary) -> float: return (player.position-start_of(s)).dot(direction(s))

func reset_at(s: Dictionary,along: float=1,lateral: float=0):
    for code in [KEY_W,KEY_S,KEY_A,KEY_D,KEY_CTRL,KEY_SHIFT,KEY_SPACE,KEY_E]:key(code,false)
    player.position=Vector3(0,.08,0)
    player.velocity=Vector3.ZERO
    await step(100)
    var d:=direction(s)
    player.position=start_of(s)+d*along+Vector3.UP.cross(d)*lateral+Vector3(0,.08,0)
    player.velocity=Vector3.ZERO
    player.rotation=Vector3(0,atan2(-d.x,-d.z),0)
    var motion:=InputEventMouseMotion.new()
    motion.relative=Vector2(0,player.CameraPivot.rotation.x/player.LookModule.MouseSensitivity)
    Input.parse_input_event(motion)
    Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
    player.reset_physics_interpolation()
    await step(12)

func run():
    OUT="res://Docs/Reviews/FlowCourseV03"
    create_timer(120).timeout.connect(func():push_error("V03 runtime QA timeout");quit(2))
    Engine.max_fps=60
    root.size=Vector2i(1280,720)
    report=JSON.parse_string(FileAccess.get_file_as_string(OUT+"/godot_export.json"))
    sections=report.sections
    level=load("res://Scenes/Levels/Level_Freestyle_GN_V03.tscn").instantiate()
    root.add_child(level);current_scene=level
    await step(45)
    player=level.get_node("Player")
    var imported:=level.get_node("ImportedLevel/SourceGeometry")
    var meshes:=imported.find_children("FLOW_*","MeshInstance3D",true,false)
    expect(meshes.size()==15,"15 separately selectable section meshes imported")
    expect(get_nodes_in_group("player").size()==1,"One canonical Player")
    expect(get_nodes_in_group("grapple_anchor").size()==1,"Canonical grapple anchor bound from exported marker")
    expect(player.is_on_floor() and player.position.length()<.15,"Spawn settles at origin on entry floor")
    var total:=0
    var box:=AABB()
    var first:=true
    var matches:=[]
    var ray_counts:={"floor":0,"wall":0,"slope":0}
    var ray_hits:={"floor":0,"wall":0,"slope":0}
    for mesh: MeshInstance3D in meshes:
        var shapes:=mesh.find_children("*","CollisionShape3D",true,false)
        expect(shapes.size()==1,"Section %s has one imported collision"%mesh.name)
        if shapes.is_empty():continue
        var collider: CollisionShape3D=shapes[0]
        expect(collider.shape is ConcavePolygonShape3D,"Section %s uses exact triangle collision"%mesh.name)
        var faces:=mesh.mesh.get_faces()
        total+=faces.size()/3
        var match_result:=triangle_match(faces,mesh.global_transform,collider.shape.get_faces(),collider.global_transform)
        matches.append({"section":mesh.name,"result":match_result})
        expect(match_result.unmatched_visual==0 and match_result.unmatched_collision==0,"Section %s collision equals visual mesh"%mesh.name)
        var b:=mesh.global_transform*mesh.get_aabb()
        box=b if first else box.merge(b);first=false
        for i in range(0,faces.size(),3):
            var a:=mesh.global_transform*faces[i]
            var b1:=mesh.global_transform*faces[i+1]
            var c:=mesh.global_transform*faces[i+2]
            var normal:=(c-a).cross(b1-a).normalized()
            if normal.y<-.001 or (b1-a).cross(c-a).length()<.5:continue
            var role:="floor" if normal.y>.999 else ("wall" if abs(normal.y)<.001 else "slope")
            var center:=(a+b1+c)/3
            ray_counts[role]+=1
            var hit:=cast(center+normal*.08,center-normal*.08)
            if not hit.is_empty() and center.distance_to(hit.position)<.015:ray_hits[role]+=1
    expect(total==int(report.triangles),"All exported triangles imported; preview guide excluded")
    var b: Array=report.bounds_blender
    expect(box.position.distance_to(Vector3(b[0][0],b[2][0],-b[1][1]))<.003 and box.end.distance_to(Vector3(b[0][1],b[2][1],-b[1][0]))<.003,"Metre scale and axes match Blender")
    for role in ray_counts:expect(ray_counts[role]>0 and ray_counts[role]==ray_hits[role],"Physics rays hit all sampled "+role+" surfaces")
    evidence["triangle_matches"]=matches;evidence["surface_rays"]={"counts":ray_counts,"hits":ray_hits}
    evidence["triangles"]=total
    for s: Dictionary in sections:
        for end_name in ["entry","exit"]:
            var point:=bl(s[end_name])+direction(s)*(.7 if end_name=="entry" else -.7)
            var hit:=cast(point+Vector3(0,.15,0),point-Vector3(0,.15,0))
            expect(not hit.is_empty(),"Section %02d %s has actual floor at declared height"%[s.id,end_name])
    expect(cast(Vector3(109,70,87),Vector3(109,-20,87)).is_empty(),"No invisible safety floor in open volume")
    await capture("godot_spawn")
    # Running jump across the actual generated gap.
    var gap: Dictionary=sections[1]
    await reset_at(gap)
    key(KEY_W,true)
    var takeoff: float=(float(gap.length)-float(gap.gap))*.5
    for i in 90:
        await step()
        if progress(gap)>takeoff-1.8:break
    key(KEY_SPACE,true);await step();key(KEY_SPACE,false)
    var airborne:=false
    var landed:=false
    for i in 100:
        await step();airborne=airborne or not player.is_on_floor()
        if airborne and player.is_on_floor():landed=progress(gap)>takeoff+float(gap.gap);break
    evidence["gap_jump"]={"gap_m":gap.gap,"landed":landed,"position":xyz(player.position),"progress_m":progress(gap)}
    expect(airborne and landed,"Physical W + Space crosses generated gap and lands")
    # Low passage uses the actual crouch/slide collider and current slide timer.
    var chute: Dictionary=sections[8]
    await reset_at(chute)
    key(KEY_W,true)
    var slide_seen:=false
    var passed:=false
    for i in 380:
        if progress(chute)>4:key(KEY_CTRL,true)
        await step();slide_seen=slide_seen or player.CrouchSlideModule.IsSliding
        if progress(chute)>float(chute.length)*.73:passed=player.is_on_floor();break
    evidence["low_slide"]={"slide_entered":slide_seen,"passed":passed,"position":xyz(player.position),"progress_m":progress(chute)}
    expect(slide_seen and passed,"Physical W + Ctrl traverses 1.25m low slide passage")
    # Grounded steep run enters and lands on its generated recovery.
    var descent: Dictionary=sections[7]
    await reset_at(descent)
    key(KEY_W,true)
    slide_seen=false;landed=false
    var peak_speed:=0.0
    for i in 220:
        if progress(descent)>3:key(KEY_CTRL,true)
        await step();slide_seen=slide_seen or player.CrouchSlideModule.IsSliding;peak_speed=maxf(peak_speed,player.velocity.length())
        if progress(descent)>7+absf(float(descent.height_change))+2 and player.is_on_floor():landed=true;break
    evidence["steep_descent"]={"slide_entered":slide_seen,"landed_on_recovery":landed,"peak_speed_mps":peak_speed,"position":xyz(player.position)}
    expect(slide_seen and landed,"Actual 45-degree descent reaches generated recovery under Player physics")
    # Grapple is a canonical anchor interaction, not a scripted launch velocity.
    var grapple: Dictionary=sections[6]
    await reset_at(grapple,3)
    var anchor: Node3D=get_nodes_in_group("grapple_anchor")[0]
    var aim: Vector3=(anchor.global_position-player.Camera.global_position).normalized()
    player.rotation.y=atan2(-aim.x,-aim.z)
    var motion:=InputEventMouseMotion.new();motion.relative=Vector2(0,(player.CameraPivot.rotation.x-asin(aim.y))/player.LookModule.MouseSensitivity)
    Input.parse_input_event(motion);Input.flush_buffered_events();await step(3)
    var los_query:=PhysicsRayQueryParameters3D.create(player.Camera.global_position,anchor.global_position,player.SlingshotGrappleModule.GrappleDetectionMask,[player.get_rid()])
    los_query.collide_with_areas=true
    var los:=level.get_world_3d().direct_space_state.intersect_ray(los_query)
    evidence["grapple_aim"]={"camera":xyz(player.Camera.global_position),"forward":xyz(-player.Camera.global_basis.z),"anchor":xyz(anchor.global_position),"aim_dot":(-player.Camera.global_basis.z).dot(aim),"mouse_mode":Input.mouse_mode,"ray_hit":str(los.get("collider","none")),"pitch":player.CameraPivot.rotation.x}
    await capture("godot_grapple_takeoff")
    key(KEY_E,true)
    var acquired:=false
    var launched:=false
    landed=false
    var last_state:=0
    for i in 280:
        await step()
        if i==0:key(KEY_E,false)
        var state: int=player.SlingshotGrappleModule.CurrentState
        acquired=acquired or state==1
        launched=launched or (last_state==2 and state==3);last_state=state
        if launched and player.is_on_floor():landed=progress(grapple)>float(grapple.length)*.48;break
    evidence["grapple_catch"]={"acquired":acquired,"launched":launched,"landed":landed,"progress_m":progress(grapple),"position":xyz(player.position)}
    expect(acquired and launched and landed,"Single physical E launches from actual anchor and lands beyond grapple break")
    await reset_at(sections[0],0)
    if DisplayServer.get_name()!="headless":
        var camera:=Camera3D.new();level.add_child(camera);camera.position=Vector3(155,155,205);camera.look_at(Vector3(0,7,0));camera.far=800;camera.fov=58;camera.make_current()
        level.get_node("CanvasLayer").visible=false
        for canvas in player.find_children("*","CanvasLayer",true,false):canvas.visible=false
        await step(8);await capture("godot_overview")
    finish()

func finish():
    evidence["checks"]=checks;evidence["passed"]=not failed;evidence["engine"]=Engine.get_version_info().string
    evidence["automated_not_human_playtest"]=true
    FileAccess.open(OUT+"/godot_qa.json",FileAccess.WRITE).store_string(JSON.stringify(evidence,"  "))
    print("V03_GODOT_QA ","PASS" if not failed else "FAIL"," checks=",checks.size())
    current_scene=null
    level.queue_free()
    player=null;level=null
    await step(8)
    quit(1 if failed else 0)
