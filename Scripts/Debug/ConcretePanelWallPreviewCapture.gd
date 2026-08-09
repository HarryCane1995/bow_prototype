extends Node3D

const TARGET_MESH_NAME := &"CITY_Building_02"
const OUTPUT_DIRECTORY := "res://.godot/concrete_panel_wall_preview"
const CONCRETE_MATERIAL := preload(
	"res://Assets/Materials/ConcretePanelWall/ConcretePanelWall_Material.tres"
)

@onready var _level: Node3D = $ImportedLevel
@onready var _camera: Camera3D = $PreviewCamera


func _ready() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	_camera.make_current()

	var target := _level.find_child(String(TARGET_MESH_NAME), true, false) as MeshInstance3D
	if target == null or target.mesh == null:
		push_error("ConcretePanelWallPreviewCapture: target mesh was not found.")
		get_tree().quit(2)
		return

	var local_aabb := target.mesh.get_aabb()
	var center := target.global_transform * local_aabb.get_center()
	var scale := target.global_transform.basis.get_scale().abs()
	var size := local_aabb.size * scale
	target.material_override = CONCRETE_MATERIAL
	var material := target.material_override as StandardMaterial3D
	print(
		"CONCRETE_PANEL_WALL_CAPTURE target=%s center=%s size=%s filter=%s uv_scale=%s normal_scale=%.2f"
		% [target.name, center, size, material.texture_filter, material.uv1_scale, material.normal_scale]
	)

	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT_DIRECTORY))
	await _capture_wide(target, center, size)
	await _capture_close(target, center, size)
	get_tree().quit(0)


func _capture_wide(target: MeshInstance3D, center: Vector3, size: Vector3) -> void:
	_camera.fov = 45.0
	var camera_position := center + Vector3(size.x * 0.9, size.y * 0.04, size.y * 1.35)
	_camera.global_transform = Transform3D(Basis.IDENTITY, camera_position).looking_at(center, Vector3.UP)
	_print_camera_diagnostics("wide", target, center)
	await _save_frame("godot_concrete_panel_wall_building.png")


func _capture_close(target: MeshInstance3D, center: Vector3, size: Vector3) -> void:
	var surface_center := center + Vector3(0, -size.y * 0.18, size.z * 0.5)
	_camera.fov = 48.0
	var camera_position := surface_center + Vector3(2.4, 1.2, 7.0)
	_camera.global_transform = Transform3D(Basis.IDENTITY, camera_position).looking_at(
		surface_center, Vector3.UP
	)
	_print_camera_diagnostics("close", target, surface_center)
	await _save_frame("godot_concrete_panel_wall_close.png")


func _print_camera_diagnostics(label: String, target: MeshInstance3D, focus: Vector3) -> void:
	var desired_direction := (_camera.global_position.direction_to(focus)).normalized()
	var camera_forward := (-_camera.global_transform.basis.z).normalized()
	print(
		"CONCRETE_PANEL_WALL_CAMERA label=%s current=%s target_visible=%s behind=%s screen=%s forward_dot=%.4f position=%s focus=%s"
		% [
			label,
			get_viewport().get_camera_3d() == _camera,
			target.is_visible_in_tree(),
			_camera.is_position_behind(focus),
			_camera.unproject_position(focus),
			camera_forward.dot(desired_direction),
			_camera.global_position,
			focus,
		]
	)


func _save_frame(file_name: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var output_path := OUTPUT_DIRECTORY.path_join(file_name)
	var error := image.save_png(ProjectSettings.globalize_path(output_path))
	if error != OK:
		push_error("Could not save preview screenshot %s: %s" % [output_path, error])
	else:
		print("CONCRETE_PANEL_WALL_SCREENSHOT=" + output_path)
