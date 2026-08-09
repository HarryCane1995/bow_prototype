@tool
class_name FogSeaController
extends Node3D

@export_category("Fog Sea Controller")

@export_group("Master")
@export var fog_sea_enabled := true:
	set(value):
		fog_sea_enabled = value
		visible = value

@export_range(0.0, 1.0, 0.01) var master_opacity := 1.0:
	set(value):
		master_opacity = value
		_apply_shared_shader_parameters()

@export_group("Downward Coverage")
@export_range(0.0, 1.0, 0.01) var downward_fill_start := 0.18:
	set(value):
		downward_fill_start = minf(value, downward_fill_end)
		_apply_shared_shader_parameters()

@export_range(0.0, 1.0, 0.01) var downward_fill_end := 0.55:
	set(value):
		downward_fill_end = maxf(value, downward_fill_start)
		_apply_shared_shader_parameters()

@export_range(0.0, 1.0, 0.01) var downward_fill_strength := 1.0:
	set(value):
		downward_fill_strength = value
		_apply_shared_shader_parameters()

@export_group("01 Top")
@export var top_material: ShaderMaterial:
	set(value):
		top_material = value
		_assign_material(&"FogSea_Top", value)
		_apply_shared_shader_parameters()

@export_group("02 Top Lower")
@export var top_lower_material: ShaderMaterial:
	set(value):
		top_lower_material = value
		_assign_material(&"FogSea_TopLower", value)
		_apply_shared_shader_parameters()

@export_group("03 Detail")
@export var detail_material: ShaderMaterial:
	set(value):
		detail_material = value
		_assign_material(&"FogSea_Detail", value)
		_apply_shared_shader_parameters()

@export_group("04 Detail Lower")
@export var detail_lower_material: ShaderMaterial:
	set(value):
		detail_lower_material = value
		_assign_material(&"FogSea_DetailLower", value)
		_apply_shared_shader_parameters()

@export_group("05 Mid")
@export var mid_material: ShaderMaterial:
	set(value):
		mid_material = value
		_assign_material(&"FogSea_Mid", value)
		_apply_shared_shader_parameters()

@export_group("06 Mid Lower")
@export var mid_lower_material: ShaderMaterial:
	set(value):
		mid_lower_material = value
		_assign_material(&"FogSea_MidLower", value)
		_apply_shared_shader_parameters()

@export_group("07 Far")
@export var far_material: ShaderMaterial:
	set(value):
		far_material = value
		_assign_material(&"FogSea_Far", value)
		_apply_shared_shader_parameters()

@export_group("08 Far Lower")
@export var far_lower_material: ShaderMaterial:
	set(value):
		far_lower_material = value
		_assign_material(&"FogSea_FarLower", value)
		_apply_shared_shader_parameters()


func _ready() -> void:
	visible = fog_sea_enabled
	_assign_all_materials()
	_apply_shared_shader_parameters()


func _assign_all_materials() -> void:
	_assign_material(&"FogSea_Top", top_material)
	_assign_material(&"FogSea_TopLower", top_lower_material)
	_assign_material(&"FogSea_Detail", detail_material)
	_assign_material(&"FogSea_DetailLower", detail_lower_material)
	_assign_material(&"FogSea_Mid", mid_material)
	_assign_material(&"FogSea_MidLower", mid_lower_material)
	_assign_material(&"FogSea_Far", far_material)
	_assign_material(&"FogSea_FarLower", far_lower_material)


func _assign_material(node_name: StringName, material: ShaderMaterial) -> void:
	if not is_node_ready() or material == null:
		return
	var layer := get_node_or_null(NodePath(String(node_name))) as MeshInstance3D
	if layer != null:
		layer.material_override = material


func _apply_shared_shader_parameters() -> void:
	for material in _get_layer_materials():
		material.set_shader_parameter("master_opacity", master_opacity)
		material.set_shader_parameter("downward_fill_start", downward_fill_start)
		material.set_shader_parameter("downward_fill_end", downward_fill_end)
		material.set_shader_parameter("downward_fill_strength", downward_fill_strength)


func _get_layer_materials() -> Array[ShaderMaterial]:
	var materials: Array[ShaderMaterial] = []
	for material in [
		top_material,
		top_lower_material,
		detail_material,
		detail_lower_material,
		mid_material,
		mid_lower_material,
		far_material,
		far_lower_material,
	]:
		if material != null:
			materials.append(material)
	return materials
