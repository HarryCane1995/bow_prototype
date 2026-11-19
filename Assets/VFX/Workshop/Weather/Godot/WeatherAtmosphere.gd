extends Node3D
## Optional Godot 4 companion for weather tiles 30, 31, 33, 35 and 36.
## Keep this node upright at the precipitation centre with its origin on the floor.

var camera: Camera3D
var original: Environment
var weather: Environment
var volume := FogVolume.new()
var mist := FogMaterial.new()
var flash := OmniLight3D.new()
var flags := PackedByteArray()
var strength := 1
var strike_frame := 0.0
var strike_origin := Vector3.ZERO

func _ready() -> void:
	flags.resize(10)
	volume.shape = RenderingServer.FOG_VOLUME_SHAPE_ELLIPSOID
	volume.size = Vector3(40, 2.8, 40)
	volume.position.y = 0.15
	mist.albedo = Color(0.65, 0.71, 0.69)
	mist.edge_fade = 0.78
	volume.material = mist
	volume.visible = false
	add_child(volume)
	flash.light_color = Color(0.85, 0.89, 1.0)
	flash.omni_range = 29
	flash.light_energy = 0
	add_child(flash)
	flash.top_level = true

func attach(target: Camera3D) -> void:
	var phase := strike_frame
	detach()
	strike_frame = phase
	camera = target
	original = camera.environment
	var base := original if original else camera.get_world_3d().environment
	weather = base.duplicate() if base else Environment.new()
	apply(flags, strength)

func detach() -> void:
	if is_instance_valid(camera) and camera.environment == weather:
		camera.environment = original
	camera = null
	original = null
	weather = null
	volume.visible = false
	flash.light_energy = 0
	reset_strike()

func _exit_tree() -> void:
	detach()

func reset_strike() -> void:
	strike_frame = 0
	flash.light_energy = 0

func apply(enabled: PackedByteArray, intensity: int) -> void:
	flags = enabled.duplicate()
	strength = clampi(intensity, 0, 2)
	if not is_instance_valid(camera): return
	var ground := flags[3] != 0
	var bank := flags[4] != 0
	var snow := flags[6] != 0
	var dust := flags[8] != 0
	var storm := flags[9] != 0
	var depth := bank or snow or dust or storm
	if not storm: reset_strike()
	camera.environment = weather if ground or depth else original
	volume.visible = ground and RenderingServer.get_current_rendering_method() == "forward_plus"
	weather.volumetric_fog_enabled = volume.visible
	weather.volumetric_fog_density = 0.0
	weather.volumetric_fog_length = 40.0
	mist.density = [0.10, 0.20, 0.33][strength]
	weather.fog_enabled = depth
	if depth:
		var density := 0.014
		var tint := Color(0.44, 0.49, 0.53)
		if bank:
			density = 0.070
			tint = Color(0.63, 0.67, 0.66)
		elif dust:
			density = 0.046
			tint = Color(0.60, 0.49, 0.37)
		elif snow:
			density = 0.041
			tint = Color(0.72, 0.76, 0.76)
		weather.fog_mode = Environment.FOG_MODE_EXPONENTIAL
		weather.fog_light_color = tint
		weather.fog_light_energy = 0.83
		weather.fog_density = density * [0.57, 1.0, 1.52][strength]
		weather.fog_sky_affect = 0.67

func advance(delta: float) -> void:
	if not is_instance_valid(camera) or not flags[9]: return
	var previous := strike_frame
	strike_frame = fmod(strike_frame + 60 * delta, 207.0)
	if previous < 78 and strike_frame >= 78:
		strike_origin = to_global(Vector3(-3, 3.4, -5))
	var age := strike_frame - 78
	var pulse := 0.0
	if age >= 0 and age < 5: pulse = 1.0 - age / 5.0
	if age >= 8 and age < 13: pulse = 0.70 * (1.0 - (age-8) / 5.0)
	if pulse > 0: flash.global_position = strike_origin
	flash.light_energy = pulse * [3.5, 6.0, 8.0][strength]
