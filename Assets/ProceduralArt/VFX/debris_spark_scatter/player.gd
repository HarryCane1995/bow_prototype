extends Node3D
## Analytic mesh VFX player. Geometry never faces the camera.
signal finished
@export_file("*.json") var manifest_path: String
@export var autoplay: bool = true
@export var loop: bool = false
@export var loop_delay: float = 0.65
var elapsed := 0.0
var duration := 2.4
var playing := false
var paused := false
var sent_finished := false
var components: Array = []
var materials: Dictionary = {}

func _ready() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	duration = float(manifest.duration)
	materials = manifest.recipe.layers
	var size: float = manifest.recipe.parameters.overall_scale
	$Layers.scale = Vector3.ONE * size
	for description in manifest.parts:
		var node: MeshInstance3D = get_node("Layers/" + description.layer + "/" + description.name)
		components.append({"node": node, "data": description})
	seek(0.0)
	if autoplay:
		restart()

func vec(values: Array) -> Vector3:
	return Vector3(values[0], values[1], values[2])

func restart() -> void:
	elapsed = 0.0
	playing = true
	paused = false
	sent_finished = false
	seek(0.0)

func seek(seconds: float) -> void:
	elapsed = clampf(seconds, 0.0, duration)
	apply_time(elapsed)

func apply_time(seconds: float) -> void:
	for item in components:
		var node: MeshInstance3D = item.node
		var d: Dictionary = item.data
		var material: Dictionary = materials[d.layer]
		var age: float = (seconds - float(d.start)) / float(d.life)
		node.visible = material.enabled and age >= 0.0 and age < 1.0 and seconds < duration
		if not node.visible:
			continue
		var u := clampf(age, 0.0, 1.0)
		var growth := (1.0 - exp(-4.0 * float(d.speed) * u)) / (1.0 - exp(-4.0 * float(d.speed)))
		node.scale = vec(d.scale0).lerp(vec(d.scale1), growth)
		node.position = vec(d.origin) + vec(d.travel) * growth + Vector3(0, -float(d.gravity) * u * u, 0)
		node.quaternion = Quaternion(d.rotation[0], d.rotation[1], d.rotation[2], d.rotation[3]) * Quaternion(Vector3.UP, float(d.spin) * u)
		var fade := clampf((u - float(d.fade_start)) / (1.0 - float(d.fade_start)), 0.0, 1.0)
		if material.fade_curve == "EASE_OUT":
			fade = 1.0 - (1.0 - fade) * (1.0 - fade)
		elif material.fade_curve == "SMOOTH":
			fade = fade * fade * (3.0 - 2.0 * fade)
		var alpha := (1.0 - fade) * minf(1.0, u / 0.04 + 0.15)
		node.set_instance_shader_parameter("life_alpha", alpha)
		node.set_instance_shader_parameter("effect_time", seconds)
		node.set_instance_shader_parameter("tint_mix", float(d.tint))

func _process(delta: float) -> void:
	if not playing or paused:
		return
	elapsed += delta
	apply_time(elapsed)
	if elapsed >= duration:
		if not sent_finished:
			sent_finished = true
			finished.emit()
		if loop:
			if elapsed >= duration + loop_delay:
				restart()
		else:
			playing = false
