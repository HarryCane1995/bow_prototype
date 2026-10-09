extends SceneTree
## Only owned runtime PNG import settings. Never writes generated .godot cache.
func _initialize():
	var args = OS.get_cmdline_user_args()
	var directory = args[0] if args.size()>0 else "res://Assets/Environment/Highrise100_Runtime/Textures"
	var count = 0
	for name in DirAccess.get_files_at(directory):
		if not name.ends_with(".png"):continue
		var path = directory.path_join(name)+".import"
		var config = ConfigFile.new()
		var loaded = config.load(path)
		if loaded != OK:
			config.set_value("remap","importer","texture")
			config.set_value("remap","type","CompressedTexture2D")
		config.set_value("params","compress/mode",2)
		config.set_value("params","compress/normal_map",1 if name.ends_with("_normal.png") else 0)
		config.set_value("params","mipmaps/generate",true)
		config.set_value("params","process/normal_map_invert_y",false)
		config.set_value("params","process/hdr_as_srgb",false)
		config.set_value("params","process/fix_alpha_border",false)
		config.set_value("params","detect_3d/compress_to",0)
		assert(config.save(path)==OK)
		count+=1
	print("HIGHRISE_OWNED_TEXTURE_IMPORT_SETTINGS ",count)
	quit()
