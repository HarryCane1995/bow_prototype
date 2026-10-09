extends SceneTree
## Bounded import/physics check. No player tuning, scene or resource writes.
var world: Node3D

func _init() -> void:
	call_deferred("validate")

func validate() -> void:
	world = load("res://Level_01_Blockout.blend").instantiate()
	root.add_child(world)
	await physics_frame
	await physics_frame
	var towers: Array[Node] = []
	var all_nodes := walk(world)
	var collisions := 0
	var meshes := 0
	var triangles := 0
	var materials := {}
	var roof_ray_height := 600.0
	for node in all_nodes:
		assert(not str(node.name).contains("ENV_SimCeiling"), "Ceiling should not import")
		if not str(node.name).begins_with("L01_Skyline_"):
			continue
		if node.get_parent() == world:
			towers.append(node)
		if node is MeshInstance3D:
			meshes += 1
			var bounds: AABB = node.global_transform * node.mesh.get_aabb()
			roof_ray_height = maxf(roof_ray_height, bounds.end.y + 50.0)
			assert(bounds.end.x < -192 or bounds.position.x > 192 or bounds.end.z < -195 or bounds.position.z > 192,
				"Skyline entered the protected playable area")
			for s in node.mesh.get_surface_count():
				var mat = node.get_active_material(s)
				materials[mat.resource_name] = mat.get_class()
				var arrays = node.mesh.surface_get_arrays(s)
				triangles += arrays[Mesh.ARRAY_INDEX].size() / 3 if arrays[Mesh.ARRAY_INDEX] != null else arrays[Mesh.ARRAY_VERTEX].size() / 3
		if node is StaticBody3D:
			collisions += 1
	assert(towers.size() == 10, "Expected ten tower roots")
	assert(collisions == 95, "Missing simplified collision bodies")
	var rays := []
	for tower in towers:
		var p: Vector3 = tower.global_position
		var query := PhysicsRayQueryParameters3D.create(Vector3(p.x, roof_ray_height, p.z), p + Vector3(0, -2, 0))
		var hit: Dictionary = root.world_3d.direct_space_state.intersect_ray(query)
		assert(not hit.is_empty(), "No roof collision for " + str(tower.name))
		assert(str(hit.collider.name).begins_with(str(tower.name)), "Roof ray hit unrelated geometry")
		rays.append({"tower":tower.name,"body":str(hit.collider.name),"height":hit.position.y,"normal_y":hit.normal.y})
	var result := {"towers":towers.size(),"visual_meshes":meshes,"render_triangles":triangles,
		"simplified_bodies":collisions,"materials":materials,"roof_rays":rays,
		"route_envelope_clear":true,"ceiling_absent":true}
	var f := FileAccess.open("res://Art/Environment/Skyscrapers/runtime_validation.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(result,"\t"))
	print("SKYLINE_VALIDATION ", JSON.stringify(result))
	quit()

func walk(node: Node) -> Array[Node]:
	var nodes: Array[Node] = [node]
	for child in node.get_children():
		nodes.append_array(walk(child))
	return nodes
