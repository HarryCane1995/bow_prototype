extends Node
## Opt-in review wrapper. Only surface overrides change; the imported level is intact.

@export_file("*.tscn") var level_scene := "res://Scenes/Levels/Level_01/Level_01.tscn"
const PRESETS := [
	preload("res://Assets/Materials/Simulation/sim_grid.tres"),
	preload("res://Assets/Materials/Simulation/sim_isofield.tres"),
	preload("res://Assets/Materials/Simulation/sim_vector_strata.tres"),
	preload("res://Assets/Materials/Simulation/sim_grid_reference.tres"),
]
const NAMES := ["A / CERAMIC MODULES", "B / ISOFIELD", "C / VECTOR STRATA", "A0 / LEGACY GRID"]
var selected := 0
var surfaces: Array[Dictionary] = []
var level: Node
var label: Label

func _ready() -> void:
	DisplayServer.window_set_title("SIM SURFACE REVIEW")
	level = load(level_scene).instantiate()
	if "--review-windowed" in OS.get_cmdline_user_args():
		var startup := level.get_node_or_null("StartupWindowModeController")
		if startup != null:
			startup.set("EnableStartupWindowMode", false)
	add_child(level)
	_collect(level)
	var canvas := CanvasLayer.new()
	canvas.layer = 10
	add_child(canvas)
	label = Label.new()
	label.position = Vector2(22, 18)
	label.add_theme_font_size_override("font_size", 19)
	label.add_theme_color_override("font_color", Color(0.95, 0.94, 0.85))
	label.add_theme_color_override("font_shadow_color", Color(0.02, 0.02, 0.025))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	canvas.add_child(label)
	select_variant(0)
	print("SIM_REVIEW_READY surfaces=%d input=real" % surfaces.size())
	# Let the imported marker binder finish first. This is only a review spawn;
	# production spawns and the player's input/physics implementation stay intact.
	await get_tree().process_frame
	var player := level.get_node_or_null("Player") as Node3D
	if player != null:
		player.global_position = Vector3(23, 1, 10)
		player.rotation.y = 0.64
		player.reset_physics_interpolation()

func _collect(node: Node) -> void:
	if node is MeshInstance3D and node.mesh != null:
		for surface in node.mesh.get_surface_count():
			var material: Material = node.get_active_material(surface)
			if material is ShaderMaterial and material.shader != null and material.shader.resource_path.ends_with("/sim_grid.gdshader"):
				surfaces.append({"mesh": node, "surface": surface, "original": material})
	for child in node.get_children():
		_collect(child)

func select_variant(index: int) -> void:
	selected = posmod(index, PRESETS.size())
	for entry in surfaces:
		# A retains the existing semantic palette. Comparators use a common art preset.
		entry.mesh.set_surface_override_material(entry.surface, entry.original if selected == 0 else PRESETS[selected])
	if label != null:
		label.text = "SIM SURFACE   %s\nF3: next   Shift+F3: previous   |   Shift: parkour" % NAMES[selected]
	print("SIM_REVIEW_VARIANT=" + NAMES[selected])

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F3:
		select_variant(selected + (-1 if event.shift_pressed else 1))
		get_viewport().set_input_as_handled()
