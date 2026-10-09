extends SceneTree

func _initialize() -> void:
	for name in ["floor_99_A_legacy_baked", "floor_99_B_clean_separate"]:
		var material = load("res://Assets/Materials/Environment/FacadeFactory/Generated/%s.tres" % name) as ORMMaterial3D
		if material == null or not material.texture_repeat:
			push_error("Invalid material: " + name)
			quit(1)
			return
		for texture in [material.albedo_texture, material.normal_texture, material.orm_texture, material.emission_texture]:
			if texture == null or Vector2i(texture.get_size()) != Vector2i(1024, 1024):
				push_error("Invalid base texture: " + name)
				quit(1)
				return
		print("BREAKUP_MATERIAL_PASS ", name)
	for channel in ["detail_albedo", "detail_normal", "weather_mask"]:
		var texture = load("res://Assets/Textures/Levels/Level_01/FacadeFactory/floor_99_B_clean_separate_%s.png" % channel) as Texture2D
		if texture == null or Vector2i(texture.get_size()) != Vector2i(1024, 1024):
			push_error("Invalid detail texture: " + channel)
			quit(1)
			return
		print("BREAKUP_DETAIL_PASS ", channel)
	quit(0)
