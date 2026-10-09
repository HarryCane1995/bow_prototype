extends SceneTree

func _initialize() -> void:
	for letter in ["A", "B", "C"]:
		var name = "floor_99_palette_" + letter
		var material = load("res://Assets/Materials/Environment/FacadeFactory/Generated/%s.tres" % name) as ORMMaterial3D
		if material == null or not material.texture_repeat:
			push_error("Invalid palette material: " + name)
			quit(1)
			return
		for texture in [material.albedo_texture, material.normal_texture, material.orm_texture, material.emission_texture]:
			if texture == null or Vector2i(texture.get_size()) != Vector2i(1024, 1024):
				push_error("Invalid palette texture: " + name)
				quit(1)
				return
		print("PALETTE_MATERIAL_PASS ", name)
	quit(0)
