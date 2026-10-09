extends Node3D
## One catalog, two scene-local lighting modes. Imported materials remain shared.
@export var night_environment: Environment
@export var neutral_environment: Environment
@export_range(0.0,8.0,0.05) var night_emission_multiplier: float = 1.8
@export_range(0.0,2.0,0.05) var neutral_emission_multiplier: float = 0.35
@export var start_in_neutral: bool = false
@onready var world: WorldEnvironment = $WorldEnvironment
@onready var key_light: DirectionalLight3D = $GlobalLighting/DirectionalKey
@onready var grid: Node3D = $Buildings/CatalogGrid
@onready var rig: Node3D = $CameraRig
@onready var status: Label = $Debug/HUD/Panel/Status
var materials: Dictionary = {}
var emission_baseline: Dictionary = {}
var buildings: Array[Node3D] = []
var neutral := false
var selected := -1
var update_clock := 0.0
var overview_transform: Transform3D

func _ready() -> void:
	overview_transform = rig.transform
	for child in grid.get_children():
		if child is Node3D and str(child.name).begins_with("HR"):buildings.append(child)
	buildings.sort_custom(func(a: Node3D,b: Node3D):return str(a.name)<str(b.name))
	for mesh in grid.find_children("*","MeshInstance3D",true,false):
		for i in mesh.mesh.get_surface_count():
			var material = mesh.get_active_material(i)
			if material is BaseMaterial3D:
				var id = material.get_instance_id()
				if not materials.has(id):
					materials[id] = material
					emission_baseline[id] = material.emission_energy_multiplier
	set_neutral(start_in_neutral)
	if DisplayServer.get_name() != "headless":DisplayServer.window_set_title("Bow Prototype | Highrise100 Showcase | F1 Neutral / Night")
	print("HIGHRISE_SHOWCASE_READY buildings=%d materials=%d preset=%s" % [buildings.size(),materials.size(),world.environment.resource_name])

func set_neutral(enabled: bool) -> void:
	neutral = enabled
	world.environment = neutral_environment if enabled else night_environment
	key_light.light_color = Color(0.94,0.97,1.0) if enabled else Color(0.57,0.69,0.76)
	key_light.light_energy = 1.55 if enabled else 0.55
	for id in materials:
		materials[id].emission_energy_multiplier = emission_baseline[id]*(neutral_emission_multiplier if enabled else night_emission_multiplier)
	_update_status()

func _unhandled_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:return
	match event.physical_keycode:
		KEY_F1:set_neutral(not neutral)
		KEY_HOME:
			selected=-1
			rig.transform=overview_transform
		KEY_PAGEDOWN:focus_building((selected+1)%buildings.size())
		KEY_PAGEUP:focus_building((selected-1+buildings.size())%buildings.size())
		KEY_H:
			var helper = $Debug/Helpers.global_position
			rig.aim_from(helper+Vector3(65,55,140),helper+Vector3(12,35,0))
		_:return
	get_viewport().set_input_as_handled()

func focus_building(index: int) -> void:
	selected = index
	var building = buildings[index]
	var height = float(building.get_meta("height_m",250.0))
	var target = building.global_position+Vector3(0,height*0.50,0)
	rig.aim_from(target+Vector3(height*0.40,height*0.18,height*0.95),target)
	_update_status()

func _process(delta: float) -> void:
	update_clock += delta
	if update_clock>=0.3:
		update_clock=0
		_update_status()

func _update_status() -> void:
	if not is_instance_valid(status) or not is_instance_valid(rig):return
	var nearest = ""
	var best = INF
	for b in buildings:
		var center = b.global_position+Vector3(0,float(b.get_meta("height_m",250.0))*0.5,0)
		var distance = rig.global_position.distance_to(center)
		if distance<best:
			best=distance
			nearest=str(b.name)+" / "+str(b.get_meta("category",""))
	status.text = "HIGHRISE100  |  %s  |  %d buildings  |  %d FPS\nWASD + mouse  ·  E/Space up / Q down  ·  Shift fast / Ctrl slow  ·  Wheel speed\nF1 lighting  ·  Home overview  ·  PgUp/PgDn building  ·  H scale helpers  ·  Esc release mouse\n%s  |  speed %.0f m/s" % ["NEUTRAL QA" if neutral else "BOW NIGHT CITY v01",buildings.size(),Engine.get_frames_per_second(),nearest,rig.move_speed_mps]
