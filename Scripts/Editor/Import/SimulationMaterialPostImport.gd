@tool
extends EditorScenePostImport

const MATERIAL_REPLACEMENTS := {
	"SIM_GRID": preload("res://Assets/Materials/Simulation/sim_grid.tres"),
	"SIM_GRID_02": preload("res://Assets/Materials/Simulation/sim_grid_02.tres"),
	"SIM_GRID_03": preload("res://Assets/Materials/Simulation/sim_grid_03.tres"),
	"SIM_GRID_04": preload("res://Assets/Materials/Simulation/sim_grid_04.tres"),
	"SIM_GRID_05": preload("res://Assets/Materials/Simulation/sim_grid_05.tres"),
	"SIM_GRID_CEILING": preload("res://Assets/Materials/Simulation/sim_grid_ceiling.tres"),
	"SIM_CEILING_DARK": preload("res://Assets/Materials/Simulation/sim_ceiling_dark.tres"),
	"SIM_EDGE_CEILING": preload("res://Assets/Materials/Simulation/sim_edge_ceiling.tres"),
	"CITY_FAR_WINDOWS": preload("res://Assets/Materials/Environment/city_far_windows.tres"),
	"CITY_FAR_ACCENT": preload("res://Assets/Materials/Environment/city_far_accent.tres"),
}

const FOG_VOLUME_PREFIX := "VOLUME_FOG_"
const FOG_VOLUME_SHAPE_BOX := 3
const CITY_FOG_MATERIAL := preload("res://Assets/Materials/Simulation/fog_volume_city.tres")


func _post_import(scene: Node) -> Object:
	var replaced_surfaces := 0
	var matched_nodes := 0
	var fog_markers: Array[MeshInstance3D] = []
	var stack: Array[Node] = [scene]

	while not stack.is_empty():
		var node: Node = stack.pop_back()
		for child in node.get_children():
			stack.push_back(child)

		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		if mesh_instance.name.begins_with(FOG_VOLUME_PREFIX):
			fog_markers.append(mesh_instance)
			continue

		var node_matched := false
		for surface_index in mesh_instance.mesh.get_surface_count():
			var source_material := mesh_instance.mesh.surface_get_material(surface_index)
			if source_material == null:
				continue

			var replacement: Material = MATERIAL_REPLACEMENTS.get(source_material.resource_name)
			if replacement == null:
				continue

			mesh_instance.set_surface_override_material(surface_index, replacement)
			replaced_surfaces += 1
			node_matched = true

		if node_matched:
			matched_nodes += 1

	var converted_fog_markers := 0
	for marker in fog_markers:
		if _replace_fog_marker(marker, scene):
			converted_fog_markers += 1

	print(
		"SimulationMaterialPostImport: replaced %d surface(s) on %d mesh node(s); converted %d fog marker(s)."
		% [replaced_surfaces, matched_nodes, converted_fog_markers]
	)
	return scene


func _replace_fog_marker(marker: MeshInstance3D, scene_root: Node) -> bool:
	var parent := marker.get_parent()
	if parent == null or marker.mesh == null:
		return false

	var marker_bounds := marker.mesh.get_aabb()
	var marker_scale := marker.transform.basis.get_scale().abs()
	var marker_name := marker.name
	var volume := FogVolume.new()
	volume.name = marker_name + "_RUNTIME"
	volume.shape = FOG_VOLUME_SHAPE_BOX
	volume.size = Vector3(
		marker_bounds.size.x * marker_scale.x,
		marker_bounds.size.y * marker_scale.y,
		marker_bounds.size.z * marker_scale.z
	)
	volume.material = CITY_FOG_MATERIAL
	volume.transform = Transform3D(
		marker.transform.basis.orthonormalized(),
		marker.transform * marker_bounds.get_center()
	)

	var child_index := marker.get_index()
	var volume_owner := marker.owner if marker.owner != null else scene_root
	parent.add_child(volume)
	volume.owner = volume_owner
	parent.move_child(volume, child_index)
	parent.remove_child(marker)
	marker.free()
	volume.name = marker_name
	return true
