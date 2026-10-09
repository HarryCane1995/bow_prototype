extends SceneTree
## Disposable slope fixture using the unchanged canonical Player and physical inputs.
var world: Node3D
var player: CharacterBody3D
var fixture: Node3D
var results: Array = []
func _initialize(): call_deferred("run")
func step(n=1):
    for i in n:
        await physics_frame
        await process_frame
func key(k,down):
    var e=InputEventKey.new();e.keycode=k;e.physical_keycode=k;e.pressed=down
    Input.parse_input_event(e);Input.flush_buffered_events()
func box(size: Vector3,pos: Vector3):
    var body=StaticBody3D.new();var shape=CollisionShape3D.new();var b=BoxShape3D.new()
    b.size=size;shape.shape=b;body.add_child(shape);fixture.add_child(body);body.position=pos
func ramp(angle: float):
    var run=18.0/tan(deg_to_rad(angle))
    fixture=Node3D.new();world.add_child(fixture)
    box(Vector3(18,1,35),Vector3(0,17.5,17.5))
    box(Vector3(24,1,100),Vector3(0,-.5,-run-50))
    var a=Vector3(-9,18,0);var b=Vector3(-9,0,-run);var c=Vector3(9,0,-run);var d=Vector3(9,18,0)
    var st=SurfaceTool.new();st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for v in [a,b,c,a,c,d]:st.add_vertex(v)
    st.generate_normals();var mesh=st.commit()
    var body=StaticBody3D.new();var shape=CollisionShape3D.new();shape.shape=mesh.create_trimesh_shape()
    body.add_child(shape);fixture.add_child(body)
    return run
func run():
    Engine.max_fps=240
    world=Node3D.new();root.add_child(world);current_scene=world
    player=load("res://Scenes/Player.tscn").instantiate();world.add_child(player)
    var holding=StaticBody3D.new();var collider=CollisionShape3D.new();var b=BoxShape3D.new();b.size=Vector3(20,1,20)
    collider.shape=b;holding.add_child(collider);world.add_child(holding);holding.position=Vector3(0,-.5,180)
    for angle in [35.0,45.0,55.0,70.0]:
        key(KEY_W,false);key(KEY_CTRL,false)
        player.position=Vector3(0,.05,180);player.velocity=Vector3.ZERO
        await step(80)
        if is_instance_valid(fixture):fixture.queue_free();await step(2)
        var run_length=ramp(angle)
        player.position=Vector3(0,18.05,20);player.rotation=Vector3.ZERO;player.velocity=Vector3.ZERO;player.reset_physics_interpolation()
        await step(20)
        key(KEY_W,true);await step(30);key(KEY_CTRL,true)
        var airborne_ticks=0;var floor_ticks=0;var slide_ticks=0;var peak_speed=0.0;var landed=false;var samples=[]
        for tick in 180:
            await step()
            peak_speed=max(peak_speed,player.velocity.length())
            if player.position.z<0 and player.position.y>.2:
                if player.is_on_floor():floor_ticks+=1
                else:airborne_ticks+=1
                if player.CrouchSlideModule.IsSliding:slide_ticks+=1
            if tick%5==0:samples.append({"p":[player.position.x,player.position.y,player.position.z],"slide":player.CrouchSlideModule.IsSliding,"floor":player.is_on_floor()})
            if player.position.z < -run_length and player.position.y<.1 and player.is_on_floor():landed=true;break
        results.append({"angle_deg":angle,"floor_max_angle_deg":rad_to_deg(player.floor_max_angle),"run_m":run_length,
            "landed_on_recovery":landed,"descent_floor_ticks":floor_ticks,"descent_air_ticks":airborne_ticks,"descent_slide_ticks":slide_ticks,
            "peak_speed_mps":peak_speed,"landing_z":player.position.z,"samples":samples})
        print("V03_STEEP ",angle," floor=",floor_ticks," air=",airborne_ticks," slide=",slide_ticks," landed=",landed)
    key(KEY_W,false);key(KEY_CTRL,false)
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://Docs/Reviews/FlowCourseV03"))
    FileAccess.open("res://Docs/Reviews/FlowCourseV03/steep_probe.json",FileAccess.WRITE).store_string(JSON.stringify(results,"  "))
    await step(70);quit()
