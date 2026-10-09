extends Node3D
## Self-contained art preview player. No gameplay dependencies or global input actions.
signal finished
@export var fps: float = 16.0
@export var frame_count: int = 32
@export var autoplay: bool = true
@export var loop: bool = false
@export var loop_delay: float = 0.6
var elapsed := 0.0
var playing := false
var paused := false
var current_frame := 0
var sent_finished := false
var instance_material: ShaderMaterial

func _ready() -> void:
	instance_material = $Billboard.material_override.duplicate() as ShaderMaterial
	$Billboard.material_override = instance_material
	set_frame(0)
	if autoplay:
		restart()

func restart() -> void:
	elapsed = 0.0
	playing = true
	paused = false
	sent_finished = false
	set_frame(0)

func set_frame(index: int) -> void:
	current_frame = clampi(index, 0, frame_count - 1)
	if instance_material:
		instance_material.set_shader_parameter("frame_index", float(current_frame))

func _process(delta: float) -> void:
	if not playing or paused:
		return
	elapsed += delta
	set_frame(int(floor(elapsed * fps)))
	if elapsed >= frame_count / fps:
		if not sent_finished:
			sent_finished = true
			finished.emit()
		if loop:
			if elapsed >= frame_count / fps + loop_delay:
				restart()
		else:
			playing = false
