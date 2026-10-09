extends "res://Tools/Blender/FlowCourseV03/verify_godot.gd"
func run():
    OUT="res://Docs/Reviews/FlowCourseV03"
    Engine.max_fps=60
    root.size=Vector2i(1280,720)
    create_timer(80).timeout.connect(func():quit(2))
    report=JSON.parse_string(FileAccess.get_file_as_string(OUT+"/godot_export.json"));sections=report.sections
    level=load("res://Scenes/Levels/Level_Freestyle_GN_V03.tscn").instantiate();root.add_child(level);current_scene=level
    await step(45);player=level.get_node("Player")
    var results:=[]
    for sid in [2,4,11]:
        var s: Dictionary=sections[sid]
        var shaft: bool=sid!=2
        var along:=float(s.length)*.235 if shaft else 4.0
        var wall_center: float=-(float(s.wall_pair_gap)+.7)*.5 if shaft else -3.1
        var yaw: float=-float(s.wall_yaw)*(.22 if shaft else .65)
        var lateral: float=wall_center+tan(yaw)*(along-float(s.length)*(.5 if shaft else .42))+.95
        await reset_at(s,along,lateral)
        key(KEY_W,true);key(KEY_SHIFT,true)
        await step(3)
        key(KEY_SPACE,true);await step();key(KEY_SPACE,false)
        var wall_ticks:=0
        var wall_jumps:=0
        var cooldown:=0
        var landed:=false
        var peak:=player.position.y
        var samples:=[]
        for tick in 210:
            await step()
            cooldown-=1
            key(KEY_SPACE,false)
            peak=maxf(peak,player.position.y)
            if player.WallRunModule.IsWallRunning:
                wall_ticks+=1
                if shaft and cooldown<=0 and wall_ticks>=12:
                    key(KEY_SPACE,true);wall_jumps+=1;cooldown=25
            if shaft and player.is_on_floor() and progress(s)>float(s.length)*.3 and cooldown<=0:
                key(KEY_SPACE,true);cooldown=30
            if tick%4==0:samples.append({"p":xyz(player.position),"wall":player.WallRunModule.IsWallRunning,"ground":player.is_on_floor()})
            if progress(s)>float(s.length)-7 and player.is_on_floor():landed=true;break
            if player.position.y<start_of(s).y-8:break
        results.append({"id":sid,"wall_ticks":wall_ticks,"jump_inputs":wall_jumps,"landed_at_exit":landed,"peak_rise":peak-start_of(s).y,"progress":progress(s),"final":xyz(player.position),"samples":samples})
        print("V03_WALL ",sid," ticks=",wall_ticks," jumps=",wall_jumps," landed=",landed," progress=",progress(s))
    FileAccess.open(OUT+"/wall_moves.json",FileAccess.WRITE).store_string(JSON.stringify(results,"  "))
    current_scene=null;level.queue_free();level=null;player=null;await step(8);quit()
