extends SceneTree
## Controlled current-build measurements in the actual authoring scene.
## Only initial case placement is synthetic. Flight uses physical InputEvents / MoveAndSlide.
const SCENE = 'res://Scenes/Levels/Level_Freestyle_01.tscn'
const OUT = 'res://.godot/freestyle-01'
var level
var player
var failures: Array = []
var checks: Array = []
var measurements: Dictionary = {}
var config: Dictionary = {}

func _initialize(): call_deferred('run')
func expect(ok, message):
    checks.append({'check':message, 'passed':bool(ok)})
    if not ok:
        failures.append(message)
        push_error(message)
func step(count=1):
    for i in count:
        await physics_frame
        await process_frame
func key(code, pressed):
    var event = InputEventKey.new()
    event.keycode = code
    event.physical_keycode = code
    event.pressed = pressed
    Input.parse_input_event(event)
    Input.flush_buffered_events()
func mouse(button, pressed):
    var event = InputEventMouseButton.new()
    event.button_index = button
    event.pressed = pressed
    Input.parse_input_event(event)
    Input.flush_buffered_events()
func tap(code):
    key(code,true)
    await step()
    key(code,false)
func fresh(pos=Vector3(0,.05,0)):
    for code in [KEY_W,KEY_A,KEY_D,KEY_S,KEY_CTRL,KEY_SHIFT,KEY_SPACE,KEY_E]: key(code,false)
    mouse(MOUSE_BUTTON_LEFT,false)
    mouse(MOUSE_BUTTON_RIGHT,false)
    if not is_instance_valid(level):
        level = load(SCENE).instantiate()
        root.add_child(level)
        current_scene = level
        await step(4)
        player = level.get_node('Player')
    else:
        # Reuse one live scene. Let timers and airborne states end naturally before
        # resetting the next case's placement; do not churn shared Mono rig resources.
        await step(100)
        var motion=InputEventMouseMotion.new()
        motion.relative=Vector2(0,player.CameraPivot.rotation.x/player.LookModule.MouseSensitivity)
        Input.parse_input_event(motion)
    player.global_position = pos
    player.velocity = Vector3.ZERO
    player.rotation = Vector3.ZERO
    player.reset_physics_interpolation()
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    await step(10)
func vec(v): return [v.x,v.y,v.z]
func record():
    return {'position':vec(player.global_position), 'velocity':vec(player.velocity),
        'ground':player.IsGrounded, 'on_floor':player.is_on_floor(), 'slide':player.CrouchSlideModule.IsSliding,
        'wall':player.WallRunModule.IsWallRunning,
        'wall_side':int(player.WallRunModule.ActiveWallSide),
        'grapple':int(player.SlingshotGrappleModule.CurrentState)}
func capture(filename):
    if DisplayServer.get_name() == 'headless': return
    await RenderingServer.frame_post_draw
    root.get_texture().get_image().save_png(OUT+'/'+filename+'.png')

func jump_case(name, runup=0, slide=false, air_tick=-1, wall_x=0.0, wall_jump_tick=-1):
    await fresh(Vector3(wall_x,.05,0))
    if runup>0:
        key(KEY_W,true)
        await step(runup)
    if slide:
        key(KEY_CTRL,true)
        await step(5)
        expect(player.CrouchSlideModule.IsSliding, name+': slide entered')
    if wall_x!=0:
        key(KEY_SHIFT,true)
        await step()
    var samples = [record()]
    var start: Vector3 = player.global_position
    key(KEY_W,true)
    key(KEY_SPACE,true)
    var was_air=false
    var wall_seen=false
    for tick in 240:
        await step()
        samples.append(record())
        if player.WallRunModule.IsWallRunning: wall_seen=true
        if not player.IsGrounded: was_air=true
        if tick==0: key(KEY_SPACE,false)
        if tick==air_tick or tick==wall_jump_tick: key(KEY_SPACE,true)
        if tick==air_tick+1 or tick==wall_jump_tick+1: key(KEY_SPACE,false)
        if was_air and player.is_on_floor() and tick>4: break
    var max_y: float=start.y
    var wall_ticks=0
    for sample in samples:
        max_y=max(max_y,float(sample.position[1]))
        if sample.wall: wall_ticks+=1
    var displacement: Vector3 = player.global_position-start
    measurements[name]={'range_m':Vector2(displacement.x,displacement.z).length(),
        'displacement':vec(displacement),'rise_m':max_y-start.y,
        'air_seconds':(samples.size()-1)/60.0,'wall_ticks':wall_ticks,
        'samples':samples,'runup_ticks':runup,'air_input_tick':air_tick,
        'wall_jump_input_tick':wall_jump_tick,'initial_placement_only':true}
    expect(was_air and player.is_on_floor(),name+': airborne and physically landed')
    if wall_x!=0: expect(wall_seen,name+': canonical wallrun entered')
    print('FREESTYLE_METRIC ',name,' ',measurements[name].range_m,'m rise=',measurements[name].rise_m)

func grapple_case(distance, x):
    await fresh(Vector3(x,.05,distance-45))
    var anchor = level.get_node('ImportedLevel/DEV_MECHANICS_REFERENCE/GrappleAnchors/Runtime_GrappleAnchor_'+str(distance if distance!=52 else 45))
    var direction: Vector3=(anchor.global_position-player.Camera.global_position).normalized()
    player.rotation.y=atan2(-direction.x,-direction.z)
    var motion=InputEventMouseMotion.new()
    motion.relative=Vector2(0,(player.CameraPivot.rotation.x-asin(direction.y))/player.LookModule.MouseSensitivity)
    Input.parse_input_event(motion)
    await step(3)
    var camera_distance: float=player.Camera.global_position.distance_to(anchor.global_position)
    var start: Vector3=player.global_position
    var samples=[record()]
    key(KEY_E,true)
    var active=false
    var launched=false
    var exit_velocity=[]
    var launch_position=[]
    var previous_state=0
    for tick in 260:
        await step()
        if tick==0: key(KEY_E,false)
        var sample=record()
        samples.append(sample)
        if sample.grapple==1: active=true
        if previous_state==2 and sample.grapple==3:
            launched=true
            exit_velocity=sample.velocity
            launch_position=sample.position
        previous_state=sample.grapple
        if active and launched and player.is_on_floor(): break
        if distance==52 and tick>5: break
    var displacement: Vector3=player.global_position-start
    measurements['grapple_'+str(distance)]={'acquired':active,'camera_distance_m':camera_distance,
        'horizontal_station_m':distance,'anchor_height_m':10,'exit_velocity':exit_velocity,
        'launch_position':launch_position,'landing_range_m':Vector2(displacement.x,displacement.z).length(),
        'samples':samples,'input':'single physical E, no WASD after acquisition'}
    expect(active==(distance<50),'grapple '+str(distance)+': acquisition range')
    if distance<50: expect(launched and player.is_on_floor(),'grapple '+str(distance)+': launch and physically land')
    print('FREESTYLE_GRAPPLE ',distance,' acquired=',active,' range=',measurements['grapple_'+str(distance)].landing_range_m)

func run():
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
    create_timer(170).timeout.connect(func():push_error('Freestyle verifier timed out');quit(2))
    Engine.max_fps=60
    root.mode=Window.MODE_WINDOWED
    root.size=Vector2i(1280,720)
    root.title='BowPrototype | Freestyle measurement'
    await fresh()
    expect(player.IsGrounded,'spawn grounded on imported floor')
    expect(get_nodes_in_group('player').size()==1,'one canonical Player')
    expect(get_nodes_in_group('grapple_anchor').size()==3,'three canonical anchors bound')
    var imported = level.get_node('ImportedLevel')
    expect(imported.find_children('*noimp*','',true,false).is_empty(),'no metric helpers imported')
    var floor_mesh=imported.find_child('BuildFloor',true,false)
    expect(floor_mesh!=null and floor_mesh is MeshInstance3D,'floor imported as mesh')
    if floor_mesh:
        expect((floor_mesh.global_transform * floor_mesh.get_aabb()).size.is_equal_approx(Vector3(200,.5,200)),'1m scale and 200m floor AABB')
    for prop in player.ActiveTuningProfile.get_property_list():
        var value=player.ActiveTuningProfile.get(prop.name)
        if value is float or value is int or value is bool or value is String:
            config[prop.name]=value
    config['GravityMultiplier']=player.JumpModule.GravityMultiplier
    config['ProjectGravity']=ProjectSettings.get_setting('physics/3d/default_gravity')
    config['PhysicsTicks']=Engine.physics_ticks_per_second
    config['CanonicalTrajectory']=player.WallRunModule.UseCanonicalTrajectory
    config['CanonicalInitialUpSpeed']=player.WallRunModule.CanonicalInitialUpSpeed
    config['StandingColliderHeight']=player.CrouchSlideModule.StandingColliderHeight
    config['CrouchingColliderHeight']=player.CrouchSlideModule.CrouchingColliderHeight
    config['PostLaunchControlDelay']=player.SlingshotGrappleModule.PostLaunchControlDelay
    await capture('spawn')
    await tap(KEY_F3)
    expect(not level.dev_reference_enabled and get_nodes_in_group('grapple_anchor').is_empty(),'F3 disables reference anchors')
    for node in level.get_node('ImportedLevel/DEV_MECHANICS_REFERENCE').find_children('*','CollisionObject3D',true,false):
        expect(node.collision_layer==0 and node.collision_mask==0,'F3 disables collision '+str(node.name))
    await tap(KEY_F3)
    expect(get_nodes_in_group('grapple_anchor').size()==3,'F3 restores reference anchors')
    await tap(KEY_F5)
    expect(not level.readout_enabled,'F5 hides authoring readout')
    await tap(KEY_F5)
    var v2=player.get_node('MainCharacterV2')
    var v3=player.get_node('MainCharacterV3')
    var v4=player.get_node_or_null('MainCharacterV4')
    expect((v4.Active and v4.FpVisible) if v4 else (v3.Active and v3.FpVisible),'current canonical 1POV active')
    await tap(KEY_F10); await step(3)
    expect((v4.ExternalView and not v4.FpVisible) if v4 else (v2.ExternalView and not v3.FpVisible),'F10 external 3POV')
    await capture('external')
    await tap(KEY_F10)
    if v4:
        await tap(v4.ToggleSplitKey); await step(3)
        expect(not v4.Active and v3.Active,'configured V4 key selects V3 reference')
    await tap(KEY_F11); await step(3)
    expect(not v3.Active,'F11 V2 fallback')
    await tap(KEY_F11)
    await tap(KEY_F9); await step(3)
    expect(not v2.Enabled,'F9 legacy fallback')
    await tap(KEY_F9); await step(3)
    expect(v3.Active,'F9 restores hybrid')
    if v4:
        await tap(v4.ToggleSplitKey); await step(3)
        expect(v4.Active and v4.FpVisible,'configured V4 key restores canonical split')
        config['V4ToggleKey']=int(v4.ToggleSplitKey)
    var before=level.get_child_count()
    mouse(MOUSE_BUTTON_LEFT,true); await step(); mouse(MOUSE_BUTTON_LEFT,false); await step(2)
    expect(level.get_child_count()>before,'LMB spawns projectile')
    var combat=player.get_node('PlayerRmbCombat')
    mouse(MOUSE_BUTTON_RIGHT,true)
    expect(combat.IsParryWindowOpen,'RMB opens parry window')
    await step(2); mouse(MOUSE_BUTTON_RIGHT,false)
    expect(combat.StateName=='Melee','RMB tap commits melee')
    await step(36)
    mouse(MOUSE_BUTTON_RIGHT,true); await step(62)
    expect(combat.PowerReady,'RMB hold reaches power ready')
    mouse(MOUSE_BUTTON_RIGHT,false); await step(2)
    expect(combat.StateName=='PowerShotRelease','RMB hold releases logical power shot')
    await step(35)
    var smoke_only='--sanity-only' in OS.get_cmdline_user_args()
    if not smoke_only:
        await jump_case('standing',0)
        await jump_case('running',30)
        await jump_case('double',30,false,18)
        await jump_case('slide_jump',30,true)
        await jump_case('wallrun_left',12,false,-1,63.5)
        await jump_case('wallrun_right',12,false,-1,66.5)
        await jump_case('wall_jump',12,false,-1,63.5,18)
        await jump_case('wall_air_jump',12,false,45,63.5,18)
        for pair in [[15,45],[30,80],[45,95],[52,95]]:
            await grapple_case(pair[0],pair[1])
    # New physical Ctrl gesture is required; holding consumed Ctrl cannot rearm.
    await fresh()
    key(KEY_W,true); await step(24)
    key(KEY_CTRL,true); await step()
    expect(player.CrouchSlideModule.IsSliding,'ground Ctrl starts slide')
    await step(30)
    await tap(KEY_SPACE)
    expect(not player.CrouchSlideModule.IsSliding and player.velocity.y>0,'slide jump exits slide')
    var reentered=false
    for i in 90:
        await step()
        if player.CrouchSlideModule.IsSliding: reentered=true
    expect(not reentered and player.CrouchSlideModule.TraceBuffer==0,'held consumed Ctrl never rearms after landing')
    key(KEY_CTRL,false); key(KEY_CTRL,true); await step()
    expect(player.CrouchSlideModule.IsSliding,'deliberate release then press starts second slide')
    await fresh(Vector3(63.5,.05,0))
    key(KEY_W,true); await step(12); await tap(KEY_SPACE); await step(12)
    expect(not player.WallRunModule.IsWallRunning,'without Shift no contextual wallrun')
    key(KEY_SHIFT,true); await step(3)
    print('SHIFT_PROBE ',record(),' ',player.WallRunModule.GetDebugText(),' intent=',player.ParkourIntentModule.IsActive)
    expect(player.WallRunModule.IsWallRunning,'Shift acquires canonical wallrun')
    key(KEY_SHIFT,false); await step(2)
    expect(not player.WallRunModule.IsWallRunning,'releasing Shift exits wallrun')
    await fresh(Vector3(74,.05,8))
    await capture('reference_kit')
    var result={'date':Time.get_datetime_string_from_system(),'scene':SCENE,
        'method':'graphical runtime; synthetic physical input; initial case placement only; not human playtest or maximum search',
        'config':config,'checks':checks,'failures':failures,'measurements':measurements}
    FileAccess.open(OUT+('/sanity.json' if smoke_only else '/measurements.json'),FileAccess.WRITE).store_string(JSON.stringify(result,'  '))
    print('FREESTYLE_VERIFY ', 'PASS' if failures.is_empty() else 'FAIL', ' failures=',failures)
    quit(0 if failures.is_empty() else 1)
