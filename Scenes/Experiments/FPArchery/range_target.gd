@tool
extends StaticBody3D

@export_range(1, 50, 1, "suffix:m") var distance_mark := 9

@onready var _carriage: Node3D = $Carriage
@onready var _plate: MeshInstance3D = $Carriage/Plate
@onready var _readout: Label3D = $Readout
@onready var _surface: ShaderMaterial = _plate.get_active_material(0)
var _reaction: Tween


func _ready() -> void:
	var height := position.y if position.y > 0.05 else 1.65
	$Foot.position.y = -height + 0.095
	$Shaft.position.y = -height * 0.5
	$Shaft.scale.y = height
	_readout.text = "%d м" % distance_mark


func register_hit(world_position: Vector3) -> void:
	var point := _plate.to_local(world_position)
	var plate_size: Vector2 = (_plate.mesh as QuadMesh).size
	_surface.set_shader_parameter("contact", Vector2(point.x / plate_size.x, point.y / plate_size.y) * 2.0)
	if _reaction:
		_reaction.kill()
	_set_progress(0.0)
	_reaction = create_tween().set_parallel(true)
	_reaction.tween_method(_set_progress, 0.0, 1.0, 0.36)
	_reaction.tween_property(_carriage, "position:z", -0.074, 0.045).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_reaction.tween_property(_carriage, "position:z", 0.0, 0.18).set_delay(0.045).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)


func _set_progress(value: float) -> void:
	_surface.set_shader_parameter("hit_progress", value)
