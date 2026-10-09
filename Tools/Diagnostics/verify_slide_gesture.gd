extends SceneTree
## Controlled integration regression. Uses real Player modules/tuning and physical-key
## InputEvents. The temporary flat fixture is test-only; case D loads unmodified Level_01.
const OUT = "res://.godot/movement-traces/slide-gesture-regression"
var player
var slide
var world: Node3D
var failures: Array = []
var results: Array = []
var ctrl_down_count := 0
var case_name := "setup"

func _initialize():
    call_deferred("run")

func expect(ok: bool, message: String):
    if not ok:
        failures.append(case_name + ": " + message)
        push_error(case_name + ": " + message)

func key(code: Key, pressed: bool):
    var event := InputEventKey.new()
    event.keycode = code
    event.physical_keycode = code
    event.pressed = pressed
    if code == KEY_CTRL and pressed:
        ctrl_down_count += 1
    Input.parse_input_event(event)
    Input.flush_buffered_events()

func step(count: int = 1):
    for i in count:
        await physics_frame
        await process_frame

func begin_case(name: String):
    case_name = name
    player.MovementTrace.MarkRegressionCase(name)

func end_case():
    results.append({"case": case_name, "physics_tick": Engine.get_physics_frames(),
        "failures_so_far": failures.size(), "ctrl_down_total": ctrl_down_count})

func reset_flat():
    key(KEY_CTRL, false)
    key(KEY_SPACE, false)
    key(KEY_W, false)
    await step(90) # Let the unchanged slide duration/cooldown finish naturally.
    player.global_position = Vector3(0, 0.02, 0)
    player.rotation = Vector3.ZERO
    player.CameraPivot.rotation = Vector3.ZERO
    player.velocity = Vector3.ZERO
    player.reset_physics_interpolation()
    await step(10)
    expect(player.IsGrounded, "fixture must be grounded")
    key(KEY_W, true)
    await step(24)

func press_slide():
    key(KEY_CTRL, true)
    await step()
    expect(slide.IsSliding, "fresh grounded Ctrl DOWN must acquire immediately")
    expect(slide.IsSlideGestureConsumed, "successful Slide must consume gesture")
    expect(slide.TraceBuffer == 0 and not slide.IsAirborneSlideIntentArmed,
        "successful Slide must clear airborne intent")

func wait_buffered_entry(max_ticks: int = 75) -> bool:
    for i in max_ticks:
        await step()
        if slide.IsSliding:
            expect(slide.IsSlideGestureConsumed, "buffered acquisition must consume gesture")
            expect(slide.TraceBuffer == 0, "buffer must be clear after buffered acquisition")
            return true
    return false

func hold_without_slide(ticks: int):
    for i in ticks:
        await step()
        expect(not slide.IsSliding, "held consumed gesture acquired another Slide")
        expect(slide.TraceBuffer == 0, "held consumed gesture rearmed airborne buffer")

func make_flat_fixture():
    world = Node3D.new()
    world.name = "SlideGestureFixture"
    root.add_child(world)
    current_scene = world
    var floor_body := StaticBody3D.new()
    floor_body.name = "TestOnlyFlatFloor"
    var collision := CollisionShape3D.new()
    var box := BoxShape3D.new()
    box.size = Vector3(1200, 1, 1200)
    collision.shape = box
    floor_body.add_child(collision)
    floor_body.position.y = -0.5
    world.add_child(floor_body)
    player = load("res://Scenes/Player.tscn").instantiate()
    player.name = "Player"
    player.position = Vector3(0, 0.1, 0)
    world.add_child(player)
    slide = player.get_node("PlayerCrouchSlideModule")
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    await step(10)

func run():
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
    create_timer(80).timeout.connect(func(): push_error("slide regression timeout"); quit(2))
    Engine.max_fps = 60
    await make_flat_fixture()

    await reset_flat()
    begin_case("A_NORMAL_SLIDE")
    await press_slide()
    await step(70)
    expect(not slide.IsSliding, "Slide must finish at normal duration")
    end_case()

    await reset_flat()
    begin_case("B_HOLD_AFTER_TIMER")
    await press_slide()
    await step(62)
    expect(not slide.IsSliding, "timer should have expired")
    await hold_without_slide(40)
    end_case()

    await reset_flat()
    begin_case("C_AIR_BUFFER")
    key(KEY_SPACE, true)
    await step()
    key(KEY_SPACE, false)
    await step(4)
    expect(not player.IsGrounded, "must be airborne before Ctrl")
    key(KEY_CTRL, true)
    await step()
    expect(slide.IsAirborneSlideIntentArmed and slide.TraceBuffer > 0, "air DOWN must arm intent")
    expect(await wait_buffered_entry(), "held air DOWN must acquire once on landing")
    await step(62)
    await hold_without_slide(20)
    end_case()

    await reset_flat()
    begin_case("E_SLIDE_JUMP")
    await press_slide()
    await step(30) # Existing cooldown has already elapsed, so it cannot mask re-entry.
    key(KEY_SPACE, true)
    await step()
    expect(player.JumpModule.JumpConsumedThisTick, "jump must be consumed in this tick")
    expect(player.velocity.y > 0, "slide jump must retain positive Y impulse")
    expect(not slide.IsSliding, "slide jump must not reacquire in same tick")
    key(KEY_SPACE, false)
    await hold_without_slide(5)
    end_case()

    begin_case("F_REPEATED_JUMP_HELD_CTRL")
    for attempt in 4:
        await hold_without_slide(38)
        key(KEY_SPACE, true)
        await step()
        expect(not slide.IsSliding, "jump spam must not reacquire Slide")
        expect(slide.TraceBuffer == 0, "jump spam must not rearm consumed intent")
        key(KEY_SPACE, false)
    await hold_without_slide(45)
    end_case()

    await reset_flat()
    begin_case("G_DELIBERATE_REENTRY")
    await press_slide()
    await step(60)
    expect(not slide.IsSliding, "first Slide must have ended")
    # Both raw edges between physics ticks: preserve fast deliberate chaining.
    key(KEY_CTRL, false)
    var gesture_before = slide.SlideGestureId
    var press_tick := Engine.get_physics_frames()
    key(KEY_CTRL, true)
    await step()
    expect(slide.SlideGestureId == gesture_before + 1, "new raw DOWN must create new gesture")
    expect(slide.IsSliding, "new press must acquire on first eligible physics tick")
    expect(Engine.get_physics_frames() == press_tick + 1, "G measurement must be first next tick")
    await step(64)
    end_case()

    await reset_flat()
    begin_case("H_AIRBORNE_SECOND_GESTURE")
    await press_slide()
    await step(30)
    key(KEY_SPACE, true)
    await step()
    key(KEY_SPACE, false)
    expect(not slide.IsSliding, "first Slide must exit for slide jump")
    key(KEY_CTRL, false)
    await step()
    key(KEY_CTRL, true)
    await step()
    expect(slide.IsAirborneSlideIntentArmed, "fresh air gesture after slide-jump must arm")
    expect(await wait_buffered_entry(), "second gesture must permit one landing Slide")
    await step(64)
    await hold_without_slide(15)
    end_case()

    await reset_flat()
    begin_case("I_SIMULTANEOUS_JUMP_CTRL")
    key(KEY_SPACE, true)
    key(KEY_CTRL, true)
    await step()
    expect(player.JumpModule.JumpConsumedThisTick, "actual jump must be marked")
    expect(not slide.IsSliding, "fresh Ctrl must not mistake stale floor after Jump for landing")
    expect(slide.IsAirborneSlideIntentArmed, "simultaneous jump+Ctrl must retain landing intent")
    key(KEY_SPACE, false)
    expect(await wait_buffered_entry(), "simultaneous intent must acquire at actual landing")
    await step(64)
    end_case()

    await reset_flat()
    begin_case("J_AIR_BUFFER_TTL")
    player.global_position = Vector3(0, 50, 0)
    player.velocity = Vector3(0, 0, -18.3)
    await step(3)
    key(KEY_CTRL, true)
    await step()
    expect(slide.IsAirborneSlideIntentArmed, "long-fall gesture must initially arm")
    await step(62)
    expect(slide.TraceBuffer == 0 and not slide.IsAirborneSlideIntentArmed, "held must not renew expired TTL")
    await hold_without_slide(45)
    end_case()

    # D uses the same imported window/colliders and live tuning as the human trace.
    key(KEY_CTRL, false)
    key(KEY_W, false)
    world.queue_free()
    await step(2)
    world = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
    root.add_child(world)
    current_scene = world
    await step(5)
    player = world.get_node("Player")
    slide = player.get_node("PlayerCrouchSlideModule")
    player.global_position = Vector3(116.96, -0.6763, -15.42)
    player.rotation = Vector3.ZERO
    player.CameraPivot.rotation = Vector3.ZERO
    player.velocity = Vector3.ZERO
    player.reset_physics_interpolation()
    await step(5)
    begin_case("D_REAL_LEVEL01_WINDOW")
    # Seed only the incoming momentum from the recorded approach. From here real
    # movement/Jump/Slide/MoveAndSlide run normally; no fixture collision changes.
    player.velocity = Vector3(0, 0, -18.3)
    key(KEY_W, true)
    key(KEY_SPACE, true)
    await step()
    key(KEY_SPACE, false)
    await step(3)
    key(KEY_CTRL, true)
    await step()
    expect(await wait_buffered_entry(90), "real window trajectory must acquire intended Slide")
    for i in 62:
        await step()
        expect(slide.TraceBuffer == 0, "active Slide at real window rearmed buffer")
    await hold_without_slide(40)
    end_case()

    key(KEY_CTRL, false)
    key(KEY_W, false)
    await step(30) # Allow existing audio fade to finish.
    player.MovementTrace.MarkRegressionCase("END")
    player.MovementTrace.StopRecording("controlled A-H regression completed")
    var report = {"passed": failures.is_empty(), "failures": failures, "cases": results,
        "synthetic_ctrl_down_count": ctrl_down_count, "input_source": "InputEventKey Ctrl; controlled, not human"}
    FileAccess.open(OUT + "/runtime_assertions.json", FileAccess.WRITE).store_string(JSON.stringify(report, "  "))
    print("SLIDE_GESTURE_REGRESSION ", JSON.stringify(report))
    quit(0 if failures.is_empty() else 1)
