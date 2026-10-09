extends SceneTree
var errors: Array[String] = []
var out := "res://.godot/art-pass-review/"

func _init() -> void:call_deferred("run")
func check(ok: bool, message: String) -> void:
	if not ok:
		errors.append(message)
		push_error(message)

func run() -> void:
	DirAccess.make_dir_recursive_absolute(out)
	root.size = Vector2i(1100,760)
	var materials: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/ProceduralArt/Materials/manifest.json"))
	var signs: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://Assets/ProceduralArt/Billboards/manifest.json"))
	check(materials.materials.size()==50,"50 materials")
	check(signs.items.size()==12,"12 billboards")
	for entry in materials.materials:
		var mat := load(entry.material) as ORMMaterial3D
		check(mat!=null,"material resource: "+entry.id)
		if mat==null:continue
		check(mat.normal_enabled,"normal enabled: "+entry.id)
		for tex in [mat.albedo_texture,mat.normal_texture,mat.orm_texture,mat.emission_texture]:
			check(tex is Texture2D,"loaded texture: "+entry.id)
			if tex is Texture2D:check(tex.get_width()==entry.resolution[0] and tex.get_height()==entry.resolution[1],"texture dimensions: "+entry.id)
	for entry in signs.items:
		var scene := load(entry.scene) as PackedScene
		check(scene!=null,"sign scene: "+entry.id)
		if scene==null:continue
		var sign := scene.instantiate()
		var panel: MeshInstance3D = sign.get_node("Panel")
		var mat := panel.material_override as ORMMaterial3D
		check(mat!=null and mat.emission_enabled,"sign emission material: "+entry.id)
		check(mat.emission_operator==BaseMaterial3D.EMISSION_OP_MULTIPLY,"emission multiplication: "+entry.id)
		check(mat.albedo_texture!=null and mat.emission_texture!=null and mat.orm_texture!=null,"sign maps: "+entry.id)
		check(is_equal_approx(mat.emission_energy_multiplier,float(entry.recipe.parameters.emission_strength)),"emission recipe parity: "+entry.id)
		check(sign.get_node("Support").visible==entry.recipe.support_frame,"support parity: "+entry.id)
		sign.free()
	var review: Node3D = load("res://Scenes/Debug/ArtPassReview.tscn").instantiate()
	root.add_child(review)
	current_scene = review
	await process_frame
	if "--capture" in OS.get_cmdline_user_args():
		for shape in range(5):
			review.shape_pick.select(shape)
			var index := 30 if shape>=3 else 0
			review.pick.select(index)
			review.show_entry(index)
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out+"material_shape_"+str(shape)+".png")
		for index in [0,2,4,8,12,15,20,24,30,33,37,44]:
			review.shape_pick.select(3 if index in [30,33,37] else 0)
			review.pick.select(index)
			review.show_entry(index)
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out+"material_"+str(index)+".png")
		review.select_category("Billboards")
		for index in range(12):
			review.pick.select(index)
			review.show_entry(index)
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out+"billboard_"+str(index)+".png")
	var report := {"result":"PASS" if errors.is_empty() else "FAIL","materials":materials.materials.size(),"billboards":signs.items.size(),"captures":"--capture" in OS.get_cmdline_user_args(),"errors":errors}
	var file := FileAccess.open(out+"runtime_report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t")+"\n")
	print("ART_LIBRARY_QA="+JSON.stringify(report))
	quit(0 if errors.is_empty() else 1)
