extends SceneTree

func _initialize() -> void:
	var names = ["industrial_99_weblab", "industrial_99_weblab_r02"]
	for i in range(names.size()):
		var path = "res://Assets/Materials/Environment/FacadeFactory/Generated/%s.tres" % names[i]
		var material = load(path) as ORMMaterial3D
		if material == null:
			push_error("Could not load " + path)
			quit(1)
			return
		var expected = Vector2i(512, 1024) if i == 0 else Vector2i(1024, 2048)
		for texture in [material.albedo_texture, material.emission_texture, material.normal_texture, material.orm_texture]:
			if texture == null or Vector2i(texture.get_size()) != expected:
				push_error("Unexpected texture size in " + path)
				quit(1)
				return
		print("WEBLAB_MATERIAL_OK ", names[i], " ", expected)
	quit(0)
