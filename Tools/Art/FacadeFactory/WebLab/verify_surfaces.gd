extends SceneTree

func _initialize() -> void:
	var cases = {"surface_industrial_floor_99": Vector2i(1024, 1024), "surface_reactor_core_99": Vector2i(1024, 2048)}
	for name in cases:
		var material = load("res://Assets/Materials/Environment/FacadeFactory/Generated/%s.tres" % name) as ORMMaterial3D
		if material == null or not material.texture_repeat:
			push_error("Invalid generated surface material: " + name)
			quit(1)
			return
		for texture in [material.albedo_texture, material.normal_texture, material.orm_texture, material.emission_texture]:
			if texture == null or Vector2i(texture.get_size()) != cases[name]:
				push_error("Wrong texture dimensions: " + name)
				quit(1)
				return
		print("SURFACE_MATERIAL_PASS ", name, " ", cases[name], " repeat=true")
	quit(0)
