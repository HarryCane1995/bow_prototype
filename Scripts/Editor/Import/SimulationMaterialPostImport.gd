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
}


func _post_import(scene: Node) -> Object:
	var replaced_surfaces := 0
	var matched_nodes := 0
	var stack: Array[Node] = [scene]

	while not stack.is_empty():
		var node: Node = stack.pop_back()
		for child in node.get_children():
			stack.push_back(child)

		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
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

	print("SimulationMaterialPostImport: replaced %d surface(s) on %d mesh node(s)." % [replaced_surfaces, matched_nodes])
	return scene
