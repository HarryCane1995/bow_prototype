extends "res://Tools/Blender/FlowCourseV03/verify_godot.gd"
func run():
    OUT="res://Docs/Reviews/FlowCourseV03"
    Engine.max_fps=60;root.size=Vector2i(1280,720)
    level=load("res://Scenes/Levels/Level_Freestyle_GN_V03.tscn").instantiate();root.add_child(level);current_scene=level
    await step(45);player=level.get_node("Player")
    await capture("godot_spawn")
    var camera:=Camera3D.new();level.add_child(camera);camera.position=Vector3(120,135,150);camera.look_at(Vector3(0,7,0));camera.far=800;camera.fov=52;camera.make_current()
    level.get_node("CanvasLayer").visible=false
    for canvas in player.find_children("*","CanvasLayer",true,false):canvas.visible=false
    await step(8);await capture("godot_overview")
    current_scene=null;level.queue_free();player=null;level=null;await step(8);print("V03_FINAL_CAPTURE_OK");quit()
