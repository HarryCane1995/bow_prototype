@tool
class_name EmissiveLogoBillboard3D
extends Node3D

@export_category("Emissive Logo Billboard")

@export_group("Logo")
@export var logo_texture: Texture2D:
	set(value):
		logo_texture = value
		_apply_billboard_settings()

@export var billboard_size := Vector2(12.0, 6.0):
	set(value):
		billboard_size = Vector2(maxf(value.x, 0.01), maxf(value.y, 0.01))
		_apply_billboard_settings()

@export_group("Emission")
@export_color_no_alpha var emission_color := Color(0.72, 0.94, 1.0):
	set(value):
		emission_color = value
		_apply_billboard_settings()

@export_range(0.0, 16.0, 0.1) var emission_intensity := 4.0:
	set(value):
		emission_intensity = value
		_apply_billboard_settings()

@export_range(0.0, 1.0, 0.01) var opacity := 0.9:
	set(value):
		opacity = value
		_apply_billboard_settings()

@export_group("Visibility")
@export_range(0.0, 10000.0, 10.0, "suffix:m") var max_draw_distance := 5000.0:
	set(value):
		max_draw_distance = value
		_apply_billboard_settings()

var _material_instance: ShaderMaterial


func _ready() -> void:
	_apply_billboard_settings()


func _apply_billboard_settings() -> void:
	if not is_inside_tree():
		return
	var mesh_instance := get_node_or_null("Billboard") as MeshInstance3D
	if mesh_instance == null:
		return
	var quad_mesh := mesh_instance.mesh as QuadMesh
	if quad_mesh != null:
		quad_mesh.size = billboard_size
	if _material_instance == null:
		var source_material := mesh_instance.material_override as ShaderMaterial
		if source_material == null:
			return
		_material_instance = source_material.duplicate() as ShaderMaterial
		_material_instance.resource_local_to_scene = true
		mesh_instance.material_override = _material_instance
	_material_instance.set_shader_parameter("logo_texture", logo_texture)
	_material_instance.set_shader_parameter("emission_color", emission_color)
	_material_instance.set_shader_parameter("emission_intensity", emission_intensity)
	_material_instance.set_shader_parameter("opacity", opacity)
	mesh_instance.visibility_range_end = max_draw_distance
