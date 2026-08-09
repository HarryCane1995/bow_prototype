extends Node3D

const CONCRETE_MATERIAL := preload(
	"res://Assets/Materials/ConcretePanelWall/ConcretePanelWall_Material.tres"
)
const TECH_DARK_MATERIAL := preload(
	"res://Assets/Materials/Architecture/CyberCity_ConcreteTower_TechDark.tres"
)


func _ready() -> void:
	var imported_model := get_node("ImportedModel")
	var concrete_mesh_count := 0
	var tech_mesh_count := 0
	var collision_shape_types: Array[String] = []
	for node in imported_model.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.name.begins_with("Concrete_") or mesh_instance.name.begins_with("TEST_"):
			mesh_instance.material_override = CONCRETE_MATERIAL
			concrete_mesh_count += 1
		elif mesh_instance.name.begins_with("Tech_"):
			mesh_instance.material_override = TECH_DARK_MATERIAL
			tech_mesh_count += 1
	for node in imported_model.find_children("*", "CollisionShape3D", true, false):
		var collision_shape := node as CollisionShape3D
		if collision_shape.shape != null and not collision_shape_types.has(collision_shape.shape.get_class()):
			collision_shape_types.append(collision_shape.shape.get_class())

	print(
		"CYBERCITY_CONCRETE_TOWER_READY concrete_meshes=%d tech_meshes=%d static_bodies=%d collision_shapes=%s"
		% [
			concrete_mesh_count,
			tech_mesh_count,
			imported_model.find_children("*", "StaticBody3D", true, false).size(),
			collision_shape_types,
		]
	)
