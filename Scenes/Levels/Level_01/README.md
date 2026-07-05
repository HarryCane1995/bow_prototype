# Level_01

Godot wrapper scene: `res://Scenes/Levels/Level_01/Level_01.tscn`

This is the current project startup/test scene via `application/run/main_scene` in `project.godot`.

Imported blockout source: `res://Level_01_Blockout.blend`

## Workflow

Keep level geometry, visual blockout, marker empties, and collision naming in `Level_01_Blockout.blend`. Godot gameplay nodes stay in `Level_01.tscn`: player, environment, runtime marker binding, triggers, enemy containers, and debug helpers.

When the Blender level changes, overwrite/update `Level_01_Blockout.blend` and let Godot reimport it. Do not edit the generated imported scene directly.

## Supported Blender Marker Names

The runtime helper scans recursively inside `ImportedLevel` for Node3D names that match these names exactly or with Blender-style suffixes like `.001` and `_A`:

- `PlayerSpawn`
- `PlayerStart`
- `EnemySpawn`
- `GrappleAnchor`
- `KillPlane`
- `FinishTrigger`

At startup the helper logs every supported marker it finds.

## Player Spawn

Create an empty/marker in Blender named `PlayerSpawn` or `PlayerStart`. The player is moved to the first matching marker at runtime.

If no imported spawn marker exists, the wrapper uses the local `PlayerSpawn` marker in `Level_01.tscn`.

## Grapple Anchors

Create empties/markers in Blender named `GrappleAnchor`, `GrappleAnchor.001`, or `GrappleAnchor_Something`. At runtime, `ImportedLevelMarkerBinder` instantiates `res://Scenes/GrappleAnchor.tscn` under `Gameplay/GrappleAnchors` at each marker transform.

For visible blockout authoring, keep grapple anchor markers in the `30_GAMEPLAY_MARKERS` collection. The helper script `res://Tools/Blender/create_grapple_anchor_marker.py` creates/updates `GrappleAnchor_01` as a Blender Empty using the size/naming reference from `res://Scenes/GrappleAnchor.tscn`.

To add more anchors, duplicate `GrappleAnchor_01` in Blender and rename the copies `GrappleAnchor_02`, `GrappleAnchor_03`, etc. Do not add `-noimp`, `-col`, or `-colonly` suffixes. These are marker objects only; the real gameplay anchor scene is created/bound in Godot by `ImportedLevelMarkerBinder`.

## Collision

Prefer Godot's Blender/glTF collision name suffixes in Blender so the imported scene contains real static collision. For example, use the suffixes supported by the Godot importer for collision bodies/shapes instead of baking one huge trimesh over the whole level.

The wrapper checks whether imported collision nodes exist. If none are found, it enables a simple temporary safety floor under `Debug/TemporarySafetyFloor` so the scene can be test-run, and logs a warning. Replace this with proper Blender-authored collision before gameplay iteration.

## Lighting

The wrapper owns the playable-level lighting and environment. Imported `Light3D` nodes are disabled at runtime by `ImportedLevelMarkerBinder` to keep the flat FPS prototype readable. If a specific Blender light should become gameplay lighting, move that setup into the wrapper scene intentionally.
