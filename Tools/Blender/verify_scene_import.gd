extends SceneTree


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 3:
		push_error("Usage: godot --headless --path . --script res://Tools/Blender/verify_scene_import.gd -- <scene> <node> <material>")
		quit(2)
		return

	var scene_path := args[0]
	var expected_node := args[1]
	var expected_material := args[2]
	var packed := load(scene_path) as PackedScene
	if packed == null:
		push_error("Could not load PackedScene: %s" % scene_path)
		quit(3)
		return

	var root := packed.instantiate()
	var mesh_instance := _find_node(root, expected_node) as MeshInstance3D
	if mesh_instance == null or mesh_instance.mesh == null:
		push_error("Missing mesh node: %s" % expected_node)
		root.free()
		quit(4)
		return

	var material: Material
	for surface_index in mesh_instance.mesh.get_surface_count():
		var candidate := mesh_instance.get_active_material(surface_index)
		if candidate != null and candidate.resource_name == expected_material:
			material = candidate
			break

	if material == null:
		push_error("Missing material: %s" % expected_material)
		root.free()
		quit(5)
		return

	var texture: Texture2D
	if material is StandardMaterial3D:
		texture = material.albedo_texture
	if texture == null:
		push_error("Material has no imported Base Color texture: %s" % expected_material)
		root.free()
		quit(6)
		return

	var result := {
		"scene": scene_path,
		"node": mesh_instance.name,
		"surface_count": mesh_instance.mesh.get_surface_count(),
		"material": material.resource_name,
		"material_type": material.get_class(),
		"texture_type": texture.get_class(),
		"texture_size": [texture.get_width(), texture.get_height()],
	}
	print("BLENDER_PIPELINE_VERIFY=" + JSON.stringify(result))
	root.free()
	quit(0)


func _find_node(node: Node, target_name: String) -> Node:
	if node.name == target_name:
		return node
	for child in node.get_children():
		var found := _find_node(child, target_name)
		if found != null:
			return found
	return null
