# BowPrototype agent instructions

Read `Docs/CODEX_RULES.md` before broad code or scene changes. Preserve unrelated working-tree changes and keep imported level wrappers lightweight.

## Blender and Godot asset workflow

- Blender MCP is available for this project. For map geometry, models, UVs, textures, or Blender materials, inspect the corresponding `.blend` source first and prefer Blender MCP / Blender Python API over UI-coordinate clicks.
- The canonical Level_01 map source is `res://Level_01_Blockout.blend`. Godot imports it directly as a `PackedScene`, and `res://Scenes/Levels/Level_01/Level_01.tscn` instances it as `ImportedLevel`.
- Editable sources are `.blend` files and repository textures. `.godot/imported/*` and Godot's imported scene are generated; never edit them. There is no production Level_01 `.glb` in the selected pipeline. If a generated `.glb/.gltf` fallback is introduced later, never edit it instead of its `.blend` source.
- Keep Level_01 textures under `res://Assets/Textures/Levels/Level_01/` and store Blender paths as `//Assets/Textures/Levels/Level_01/...`; do not add user-specific absolute paths or pack large images without a documented reason.
- After a Blender change: save `Level_01_Blockout.blend`, run/retrigger Godot import, load the imported scene, and run the map. A 3D asset task is not complete until the result is verified in Godot.
- Do not destructively rebuild the root map, mass-apply transforms, or overwrite the Godot wrapper without an explicit request. Geometry/UV/base materials belong in Blender; C# logic, runtime triggers, signals, player settings, and other Godot-specific nodes stay in Godot.
- Full conventions, MCP material examples, reimport commands, validation, limitations, and troubleshooting are in `Docs/blender_pipeline.md`. Update that document, and this section if the rule changes, when a new pipeline limitation is confirmed.
