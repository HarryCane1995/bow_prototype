extends SceneTree
const SCENE_PATH = "res://Scenes/Environment/Highrise100_Showcase.tscn"
const LIGHT_DIR = "res://Resources/Environment/"
var scene: Node3D

func _initialize():call_deferred("run")

func add(parent: Node,node: Node,label: String) -> Node:
	node.name=label
	parent.add_child(node)
	node.owner=scene
	return node

func make_environment(night: bool) -> Environment:
	var env = Environment.new()
	env.resource_name = "Env_Bow_NightCity_v01" if night else "Env_Highrise100_NeutralQA"
	var material = ProceduralSkyMaterial.new()
	material.sky_top_color=Color(0.025,0.040,0.045) if night else Color(0.42,0.49,0.54)
	material.sky_horizon_color=Color(0.10,0.105,0.082) if night else Color(0.70,0.73,0.74)
	material.ground_bottom_color=Color(0.025,0.034,0.036) if night else Color(0.20,0.23,0.25)
	material.ground_horizon_color=Color(0.075,0.086,0.077) if night else Color(0.55,0.59,0.61)
	material.sky_curve=0.25
	material.sun_angle_max=0.0
	var sky = Sky.new()
	sky.sky_material=material
	env.sky=sky
	env.background_mode=Environment.BG_SKY
	env.background_energy_multiplier=0.7 if night else 0.9
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color=Color(0.45,0.58,0.62) if night else Color(0.72,0.76,0.79)
	env.ambient_light_energy=0.6 if night else 0.8
	env.reflected_light_source=Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode=Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure=1.0
	env.tonemap_white=4.0
	env.ssao_enabled=true
	env.ssao_radius=2.0
	env.ssao_intensity=1.1
	env.ssao_power=1.2
	env.ssil_enabled=false
	env.sdfgi_enabled=false
	env.glow_enabled=true
	env.glow_intensity=0.55 if night else 0.10
	env.glow_strength=0.8
	env.glow_bloom=0.015 if night else 0.0
	env.glow_hdr_threshold=1.05 if night else 1.6
	env.glow_hdr_scale=1.2
	env.glow_hdr_luminance_cap=8.0
	env.fog_enabled=night
	env.fog_light_color=Color(0.095,0.125,0.125)
	env.fog_light_energy=0.85
	env.fog_density=0.00025
	env.fog_sky_affect=0.20
	env.fog_aerial_perspective=0.2
	env.volumetric_fog_enabled=false
	assert(ResourceSaver.save(env,LIGHT_DIR+env.resource_name+".tres")==OK)
	return load(LIGHT_DIR+env.resource_name+".tres")

func mesh(parent: Node,label: String,shape: Mesh,position_at: Vector3,color: Color) -> MeshInstance3D:
	var node = MeshInstance3D.new()
	node.mesh=shape
	node.position=position_at
	var material = StandardMaterial3D.new()
	material.albedo_color=color
	material.roughness=0.9
	node.material_override=material
	add(parent,node,label)
	return node

func label3d(parent: Node,label: String,text: String,position_at: Vector3) -> void:
	var node = Label3D.new()
	node.text=text
	node.position=position_at
	node.pixel_size=0.022
	node.font_size=48
	node.billboard=BaseMaterial3D.BILLBOARD_ENABLED
	add(parent,node,label)

func run():
	DirAccess.make_dir_recursive_absolute(LIGHT_DIR)
	scene=Node3D.new()
	scene.name="Highrise100_Showcase"
	root.add_child(scene)
	var night=make_environment(true)
	var neutral=make_environment(false)
	var world=add(scene,WorldEnvironment.new(),"WorldEnvironment")
	world.environment=night
	var lights=add(scene,Node3D.new(),"GlobalLighting")
	var key=add(lights,DirectionalLight3D.new(),"DirectionalKey")
	key.rotation_degrees=Vector3(-38,-32,0)
	key.light_color=Color(0.57,0.69,0.76)
	key.light_energy=0.55
	key.light_angular_distance=1.5
	key.shadow_enabled=true
	key.directional_shadow_mode=DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	key.directional_shadow_max_distance=850
	key.directional_shadow_blend_splits=true
	key.directional_shadow_split_1=0.08
	key.directional_shadow_split_2=0.25
	key.directional_shadow_split_3=0.55
	var buildings=add(scene,Node3D.new(),"Buildings")
	var packed=load("res://Assets/Environment/Highrise100_Runtime/Highrise100.gltf") as PackedScene
	assert(packed!=null)
	var grid=packed.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	add(buildings,grid,"CatalogGrid")
	scene.set_editable_instance(grid,true)
	var manifest=JSON.parse_string(FileAccess.get_file_as_string("res://Assets/Environment/Highrise100_Runtime/export_manifest.json"))
	var span_x=0.0
	var span_z=0.0
	for r in manifest.buildings:
		span_x=maxf(span_x,r.bounds_max[0]-r.bounds_min[0])
		span_z=maxf(span_z,r.bounds_max[1]-r.bounds_min[1])
	var step_x=ceilf(span_x+80.0)
	var step_z=ceilf(span_z+80.0)
	var layout=[]
	for i in manifest.buildings.size():
		var r=manifest.buildings[i]
		var building=grid.get_node(NodePath(r.id))
		# Blender Z-up becomes Godot Y-up. Ground stays Y=0; no height scaling.
		building.position=Vector3((i%10-4.5)*step_x,0,-(floori(i/10.0)-4.5)*step_z)
		building.set_meta("height_m",r.bounds_max[2]-r.bounds_min[2])
		building.set_meta("category",r.category)
		building.set_meta("display_name",r.name)
		layout.append({"id":r.id,"position":[building.position.x,building.position.y,building.position.z],"height_m":r.bounds_max[2]-r.bounds_min[2]})
	var rig=add(scene,Node3D.new(),"CameraRig")
	var camera=add(rig,Camera3D.new(),"Camera3D")
	camera.fov=65
	camera.near=0.2
	camera.far=8000
	camera.current=true
	rig.position=Vector3(step_x*5.7,step_x*4.2+400,step_z*7)
	rig.look_at(Vector3(0,160,0))
	rig.set_script(load("res://Scripts/Environment/Highrise100/HighriseFlyCamera.gd"))
	var debug=add(scene,Node3D.new(),"Debug")
	var ground=PlaneMesh.new()
	ground.size=Vector2(step_x*10+180,step_z*10+180)
	mesh(debug,"Ground",ground,Vector3(0,-0.1,0),Color(0.09,0.12,0.13))
	var helpers=add(debug,Node3D.new(),"Helpers")
	helpers.position=Vector3(-step_x*4.5,0,step_z*4.5+span_z/2+30)
	for height in [10.0,50.0,100.0]:
		var shape=BoxMesh.new()
		shape.size=Vector3(0.6,height,0.6)
		var x=height*0.4+5
		mesh(helpers,"Scale_%dm"%height,shape,Vector3(x,height/2,0),Color(0.58,0.68,0.68))
		label3d(helpers,"Label_%dm"%height,"%d m"%height,Vector3(x,height+3,0))
	var body=CapsuleMesh.new()
	body.radius=0.19
	body.height=1.53
	mesh(helpers,"HumanBody",body,Vector3(0,0.765,0),Color(0.84,0.27,0.06))
	var head=SphereMesh.new()
	head.radius=0.135
	head.height=0.27
	mesh(helpers,"HumanHead",head,Vector3(0,1.665,0),Color(0.84,0.27,0.06))
	label3d(helpers,"HumanLabel","1.8 m",Vector3(0,3,0))
	var hud=add(debug,CanvasLayer.new(),"HUD")
	var panel=add(hud,PanelContainer.new(),"Panel")
	panel.position=Vector2(16,16)
	panel.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var status=add(panel,Label.new(),"Status")
	status.add_theme_font_size_override("font_size",15)
	status.text="Highrise100 — loading"
	status.mouse_filter=Control.MOUSE_FILTER_IGNORE
	scene.set_script(load("res://Scripts/Environment/Highrise100/Highrise100Showcase.gd"))
	scene.night_environment=night
	scene.neutral_environment=neutral
	var result=PackedScene.new()
	assert(result.pack(scene)==OK)
	assert(ResourceSaver.save(result,SCENE_PATH)==OK)
	FileAccess.open("res://Art/Environment/Highrise100/RuntimeShowcase_QA/layout.json",FileAccess.WRITE).store_string(JSON.stringify({"step_x_m":step_x,"step_z_m":step_z,"gap_min_m":80,"layout":layout},"\t"))
	print("HIGHRISE_SHOWCASE_BUILT ",SCENE_PATH," grid=",step_x,"x",step_z)
	quit()
