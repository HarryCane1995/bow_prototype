extends SceneTree
## Human handoff only: load the real map and place the player before the recorded window.
## No key/action injection, movement driver, tuning or collision changes.
func _initialize():
    call_deferred("run")

func run():
    var level = load("res://Scenes/Levels/Level_01/Level_01.tscn").instantiate()
    root.add_child(level)
    current_scene = level
    # Let the existing marker binder and combat spawn finish their startup placement.
    for i in 5:
        await physics_frame
        await process_frame
    var player = level.get_node("Player")
    player.global_position = Vector3(116.96, -0.6763, -15.42)
    player.rotation = Vector3.ZERO
    player.CameraPivot.rotation = Vector3.ZERO
    player.velocity = Vector3.ZERO
    player.reset_physics_interpolation()
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    print("SLIDE_HUMAN_RETEST_READY input=real scene=Level_01 area=CB_CrossWindowSill position=", player.global_position)
