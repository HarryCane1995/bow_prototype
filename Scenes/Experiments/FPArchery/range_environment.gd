@tool
extends Node3D

const FLOOR_SURFACE := preload("res://Assets/ProceduralArt/Materials/floor_utility_cuts/material.tres")
const ACOUSTIC_SURFACE := preload("res://Assets/ProceduralArt/Materials/wall_transit_acoustic/material.tres")

@export_group("Range finishes")
@export var structural_metal: Material
@export var painted_metal: Material
@export var floor_paint: Material
@export var strip_light: Material
@export var amber_paint: Material


func _ready() -> void:
	var ground := _tile_material(FLOOR_SURFACE, 0.25)
	ground.albedo_color = Color(0.74, 0.82, 0.87)
	ground.normal_scale = 0.40
	$Shell/Floor.material_override = ground
	if has_node("WallCassettes"):
		return
	var panels: Array[Transform3D] = []
	var frames: Array[Transform3D] = []
	var guards: Array[Transform3D] = []
	var lamps: Array[Transform3D] = []
	var floor_marks: Array[Transform3D] = []
	var amber_marks: Array[Transform3D] = []

	for index in 6:
		var z := 1.2 - 4.05 * index
		for side: float in [-1.0, 1.0]:
			panels.append(_box(Vector3(side * 8.87, 2.54, z), Vector3(0.16, 3.16, 3.89)))
			guards.append(_box(Vector3(side * 8.78, 0.49, z), Vector3(0.38, 0.94, 4.0)))
			frames.append(_box(Vector3(side * 8.69, 2.45, z - 1.93), Vector3(0.31, 4.79, 0.18)))
			frames.append(_box(Vector3(side * 8.14, 5.45, z - 1.93), Vector3(0.34, 2.1, 0.21), side * 0.59))
			guards.append(_box(Vector3(side * 7.2, 6.40, z), Vector3(1.28, 0.40, 4.0)))
			lamps.append(_box(Vector3(side * 7.15, 6.185, z), Vector3(0.32, 0.048, 3.65)))
			lamps.append(_box(Vector3(side * 8.715, 4.21, z + 0.18), Vector3(0.058, 0.065, 2.86)))
			frames.append(_box(Vector3(side * 3.4, 6.57, z), Vector3(0.58, 0.18, 4.02)))
			lamps.append(_box(Vector3(side * 3.4, 6.463, z), Vector3(0.19, 0.043, 3.68)))
		frames.append(_box(Vector3(0, 6.64, z - 1.93), Vector3(16.0, 0.21, 0.17)))

	for index in 9:
		var x := -7.76 + 1.94 * index
		panels.append(_box(Vector3(x, 2.15, -21.77), Vector3(1.89, 3.16, 0.27)))
		guards.append(_box(Vector3(x, 0.34, -21.53), Vector3(1.89, 0.56, 0.49)))
	guards.append(_box(Vector3(0, 3.90, -21.82), Vector3(17.6, 0.29, 0.42)))
	lamps.append(_box(Vector3(0, 3.96, -21.585), Vector3(17.1, 0.037, 0.04)))
	amber_marks.append(_box(Vector3(-7.95, 4.97, -21.81), Vector3(0.09, 0.97, 0.06)))

	for side: float in [-1.0, 1.0]:
		for x: float in [2.32, 7.24]:
			floor_marks.append(_box(Vector3(side * x, 0.005, -11.2), Vector3(0.033, 0.009, 18.15)))
		for index in 8:
			var z := -2.12 - index * 2.5
			floor_marks.append(_box(Vector3(side * 2.51, 0.006, z), Vector3(0.38, 0.01, 0.036)))
		amber_marks.append(_box(Vector3(side * 4.85, 0.010, -2.11), Vector3(4.82, 0.012, 0.083)))
		amber_marks.append(_box(Vector3(side * 2.44, 0.010, -2.23), Vector3(0.09, 0.012, 0.31)))

	_batch("WallCassettes", _tile_material(ACOUSTIC_SURFACE, 0.37), panels)
	_batch("ExposedFrame", structural_metal, frames)
	_batch("Guards", painted_metal, guards)
	_batch("RecessedLights", strip_light, lamps, false)
	_batch("LaneMarkings", floor_paint, floor_marks, false)
	_batch("FiringLine", amber_paint, amber_marks, false)


func _tile_material(source: BaseMaterial3D, tiles_per_meter: float) -> BaseMaterial3D:
	var surface := source.duplicate() as BaseMaterial3D
	surface.uv1_triplanar = true
	surface.uv1_world_triplanar = true
	surface.uv1_scale = Vector3.ONE * tiles_per_meter
	return surface


func _box(center: Vector3, dimensions: Vector3, roll := 0.0) -> Transform3D:
	return Transform3D(Basis(Vector3.BACK, roll) * Basis.from_scale(dimensions), center)


func _batch(batch_name: String, surface: Material, transforms: Array[Transform3D], shadows := true) -> void:
	var cube := BoxMesh.new()
	cube.material = surface
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = cube
	batch.instance_count = transforms.size()
	for index in transforms.size():
		batch.set_instance_transform(index, transforms[index])
	var pieces := MultiMeshInstance3D.new()
	pieces.name = batch_name
	pieces.multimesh = batch
	if not shadows:
		pieces.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(pieces)
