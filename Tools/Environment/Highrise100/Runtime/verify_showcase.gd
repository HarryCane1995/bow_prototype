extends SceneTree
const QA = "res://Art/Environment/Highrise100/RuntimeShowcase_QA/"
const REPRESENTATIVES = ["HR003","HR007","HR013","HR018","HR027","HR036","HR057","HR064","HR083","HR100"]
class ShaderCapture extends Node:
	var code := ""
	func _inspect_shader(shader: RID) -> void:
		code=RenderingServer.shader_get_code(shader)

var stage: Node3D
var report: Dictionary

func _initialize():call_deferred("run")

func bounds(building: Node3D) -> AABB:
	var result = AABB()
	var first = true
	for mesh in building.find_children("*","MeshInstance3D",true,false):
		var box = mesh.global_transform*mesh.get_aabb()
		result=box if first else result.merge(box)
		first=false
	return result

func performance_sample(mode: String) -> Dictionary:
	stage.set_neutral(mode=="neutral")
	var warm_until=Time.get_ticks_msec()+2000
	while Time.get_ticks_msec()<warm_until:await process_frame
	var elapsed=[]
	var cpu=[]
	var draw=[]
	var objects=[]
	var previous=Time.get_ticks_usec()
	var sample_until=Time.get_ticks_msec()+5000
	while Time.get_ticks_msec()<sample_until or elapsed.size()<180:
		await process_frame
		var now=Time.get_ticks_usec()
		elapsed.append((now-previous)/1000.0)
		previous=now
		cpu.append(float(Performance.get_monitor(Performance.TIME_PROCESS))*1000.0)
		draw.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		objects.append(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME))
	elapsed.sort()
	var total=0.0
	var draws=0.0
	var objs=0.0
	var process_total=0.0
	for v in elapsed:total+=v
	for v in draw:draws+=v
	for v in objects:objs+=v
	for v in cpu:process_total+=v
	var count=elapsed.size()
	return {"mode":mode,"frames":count,"duration_ms":total,"mean_frame_ms":total/count,"median_frame_ms":elapsed[count/2],"p95_frame_ms":elapsed[floori(count*0.95)],"mean_fps":count*1000.0/total,"mean_process_ms":process_total/count,"mean_draw_calls":draws/count,"mean_visible_objects":objs/count,"texture_memory_bytes":Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED),"render_buffer_bytes":Performance.get_monitor(Performance.RENDER_BUFFER_MEM_USED),"video_memory_bytes":Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)}

func screenshot(name: String) -> void:
	for i in range(4):await process_frame
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(QA+"Captures/"+name+".png")==OK)

func run():
	var data=JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Environment/Highrise100_Runtime/export_manifest.json"))
	stage=load("res://Scenes/Environment/Highrise100_Showcase.tscn").instantiate()
	root.add_child(stage)
	stage.rig.controls_enabled=false
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	var grid=stage.grid
	var rows=[]
	var boxes={}
	var materials={}
	var textures={}
	var errors=[]
	var surfaces=0
	var triangles=0
	var uv_surfaces=0
	var tangent_surfaces=0
	var textured_surfaces=0
	var flat=[]
	for r in data.buildings:
		var building=grid.get_node_or_null(NodePath(r.id))
		if building==null:
			errors.append(r.id+": missing root")
			continue
		if absf(building.position.y)>0.001:errors.append(r.id+": not at ground origin")
		if building.scale.distance_to(Vector3.ONE)>0.001:errors.append(r.id+": scale changed")
		var box=bounds(building)
		boxes[r.id]=box
		if absf(box.size.y-(r.bounds_max[2]-r.bounds_min[2]))>0.05:errors.append(r.id+": height mismatch")
		rows.append({"id":r.id,"category":r.category,"position":str(building.position),"bounds":str(box),"height_m":box.size.y})
		for mesh in building.find_children("*","MeshInstance3D",true,false):
			for s in mesh.mesh.get_surface_count():
				surfaces+=1
				var arrays=mesh.mesh.surface_get_arrays(s)
				triangles+=arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX]!=null else arrays[Mesh.ARRAY_VERTEX].size()/3
				if arrays[Mesh.ARRAY_TEX_UV]!=null and arrays[Mesh.ARRAY_TEX_UV].size()>0:uv_surfaces+=1
				if arrays[Mesh.ARRAY_TANGENT]!=null and arrays[Mesh.ARRAY_TANGENT].size()>0:tangent_surfaces+=1
				var m=mesh.get_active_material(s)
				if not m is StandardMaterial3D:
					errors.append(str(mesh.name)+": missing/nonstandard material")
					continue
				if materials.has(m.resource_name) and materials[m.resource_name]!=m:errors.append(m.resource_name+": duplicate material instance")
				materials[m.resource_name]=m
				if m.albedo_texture==null:
					flat.append({"mesh":mesh.name,"material":m.resource_name,"surface":s})
					continue
				textured_surfaces+=1
				for texture in [m.albedo_texture,m.normal_texture,m.ao_texture,m.roughness_texture,m.metallic_texture,m.emission_texture]:
					if texture==null or texture.get_width()==0:errors.append(m.resource_name+": missing texture")
					else:textures[texture.resource_path]=texture
				if not m.normal_enabled or not is_equal_approx(m.normal_scale,0.32):errors.append(m.resource_name+": normal contract")
				if not m.ao_enabled or m.ao_texture_channel!=0 or m.roughness_texture_channel!=1 or m.metallic_texture_channel!=2:errors.append(m.resource_name+": ORM channels")
				if m.ao_texture!=m.roughness_texture or m.ao_texture!=m.metallic_texture:errors.append(m.resource_name+": ORM texture duplication")
				if not m.emission_enabled:errors.append(m.resource_name+": emission disabled")
				if m.resource_name.begins_with("H100_sign_") and m.texture_repeat:errors.append(m.resource_name+": sign clamp lost")
	for a in boxes:
		for b in boxes:
			if a>=b:continue
			var left: AABB=boxes[a]
			var right: AABB=boxes[b]
			if left.position.x<right.end.x and left.end.x>right.position.x and left.position.z<right.end.z and left.end.z>right.position.z:errors.append(a+" intersects "+b)
	var image_imports={}
	for path in textures:
		var config=ConfigFile.new()
		if config.load(path+".import")!=OK:errors.append(path+": import settings missing")
		var is_normal=path.ends_with("_normal.png")
		var normal_mode=config.get_value("params","compress/normal_map",-1)
		var mipmaps=config.get_value("params","mipmaps/generate",false)
		if not mipmaps or (is_normal and normal_mode!=1):errors.append(path+": 3D import flags")
		image_imports[path]={"mipmaps":mipmaps,"normal_mode":normal_mode,"compression":config.get_value("params","compress/mode",-1),"normal_y_flip":config.get_value("params","process/normal_map_invert_y",false)}
	var collisions=stage.find_children("*","CollisionObject3D",true,false).size()+stage.find_children("*","CollisionShape3D",true,false).size()
	if collisions!=0:errors.append("Unexpected collisions")
	if rows.size()!=100 or triangles!=30500 or surfaces!=uv_surfaces or surfaces!=tangent_surfaces:errors.append("Count/geometry/UV sanity")
	if materials.size()!=46 or textures.size()!=172:errors.append("Material or texture count mismatch")
	report={"buildings_loaded":rows.size(),"buildings":rows,"material_count":materials.size(),"unique_texture_count":textures.size(),"surfaces":surfaces,"textured_surfaces":textured_surfaces,"flat_surfaces":flat,"triangles":triangles,"uv_surfaces":uv_surfaces,"tangent_surfaces":tangent_surfaces,"collisions":collisions,"image_imports":image_imports,"errors":errors,"renderer":RenderingServer.get_current_rendering_method(),"driver":RenderingServer.get_current_rendering_driver_name(),"adapter":RenderingServer.get_video_adapter_name(),"engine":Engine.get_version_info().string,"resolution":str(root.size),"representatives":REPRESENTATIVES,"input_automated_test":{},"native_shaders":{}}
	# Exercise the actual camera handlers, never OS input or computer-use APIs.
	stage.rig.controls_enabled=true
	var start=stage.rig.global_position
	Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
	var mouse_capture_supported=Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
	var press=InputEventKey.new()
	press.keycode=KEY_W
	press.physical_keycode=KEY_W
	press.pressed=true
	Input.parse_input_event(press)
	Input.flush_buffered_events()
	var w_seen=Input.is_physical_key_pressed(KEY_W)
	stage.rig._process(0.25)
	var release=InputEventKey.new()
	release.keycode=KEY_W
	release.physical_keycode=KEY_W
	release.pressed=false
	Input.parse_input_event(release)
	Input.flush_buffered_events()
	var moved=stage.rig.global_position.distance_to(start)
	var original_rot=stage.rig.rotation
	var motion=InputEventMouseMotion.new()
	motion.relative=Vector2(100,25)
	stage.rig._unhandled_input(motion)
	var rotated=not stage.rig.rotation.is_equal_approx(original_rot)
	var toggle=InputEventKey.new()
	toggle.physical_keycode=KEY_F1
	toggle.pressed=true
	stage._unhandled_input(toggle)
	report.input_automated_test={"mouse_capture_supported":mouse_capture_supported,"physical_w_detected":w_seen,"forward_movement_m":moved,"mouse_rotation_changed":rotated,"neutral_toggle":stage.neutral}
	if (mouse_capture_supported and (moved<1 or not rotated)) or not stage.neutral:errors.append("Camera/mode input check failed")
	if DisplayServer.get_name()!="headless" and not mouse_capture_supported:errors.append("Windowed mouse capture failed")
	stage.rig.controls_enabled=false
	stage.rig.transform=stage.overview_transform
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	stage.set_neutral(false)
	var visual=DisplayServer.get_name()!="headless"
	if visual:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
		report.vsync="disabled for measurement"
		DirAccess.make_dir_recursive_absolute(QA+"Captures")
		DirAccess.make_dir_recursive_absolute(QA+"NativeShaders")
		var capture=ShaderCapture.new()
		root.add_child(capture)
		capture.add_to_group("_native_shader_source_visualizer")
		for name in materials:
			var m=materials[name]
			if m.albedo_texture==null:continue
			capture.code=""
			m.inspect_native_shader_code()
			await process_frame
			await process_frame
			var code: String=capture.code
			var albedo_ok=code.contains("texture_albedo : source_color")
			var emission_ok=code.contains("texture_emission : source_color")
			var normal_ok=code.contains("texture_normal : hint_roughness_normal") and not code.contains("texture_normal : source_color")
			var orm_ok=code.contains("texture_roughness : hint_roughness_g") and not code.contains("texture_metallic : source_color") and not code.contains("texture_ambient_occlusion : source_color")
			report.native_shaders[name]={"albedo_srgb":albedo_ok,"emission_srgb":emission_ok,"normal_data":normal_ok,"orm_data":orm_ok,"code_length":code.length()}
			if not (albedo_ok and emission_ok and normal_ok and orm_ok):errors.append(name+": native shader sampling check")
			FileAccess.open(QA+"NativeShaders/"+name+".gdshader.txt",FileAccess.WRITE).store_string(code)
		report.performance=[]
		for mode in ["night","neutral"]:
			report.performance.append(await performance_sample(mode))
			await screenshot("Overview_"+mode)
		for id in REPRESENTATIVES:
			stage.focus_building(int(id.substr(2))-1)
			await screenshot(id+"_neutral")
		stage.set_neutral(false)
		stage.focus_building(26)
		report.performance.append(await performance_sample("night_close_HR027"))
		await screenshot("HR027_night")
		stage.rig.transform=stage.overview_transform
	report.active_preset=stage.world.environment.resource_name
	report.passed=errors.is_empty()
	report.visual_captured=visual
	FileAccess.open(QA+("runtime_gpu.json" if visual else "runtime_headless.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("HIGHRISE_SHOWCASE_QA ",JSON.stringify({"passed":report.passed,"buildings":rows.size(),"materials":materials.size(),"textures":textures.size(),"surfaces":surfaces,"triangles":triangles,"errors":errors,"visual":visual}))
	quit(0 if report.passed else 1)
