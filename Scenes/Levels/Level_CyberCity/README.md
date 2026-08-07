# Level_CyberCity

Godot wrapper: `res://Scenes/Levels/Level_CyberCity/Level_CyberCity.tscn`

Editable Blender source: `res://Level_CyberCity_Blockout.blend`

This level intentionally reuses the existing `Scenes/Player.tscn`, tuning profile, grapple anchor scene, HUD scripts, and Runtime Tuning Panel. Gameplay implementations are not duplicated.

## Blender authoring

- `10_LEVEL_VISUAL/TEMP_TEST_GEOMETRY` contains the disposable spawn platform and wall-run wall.
- `20_COLLISION` contains matching `-colonly` collision meshes.
- `30_GAMEPLAY_MARKERS` contains `PlayerSpawn` and the temporary `GrappleAnchor_01` hook target.
- `90_REFERENCE-noimp` is reserved for non-imported authoring references.

The Blender file contains selectable material datablocks for all current simulation semantics:

- `SIM_GRID`
- `SIM_GRID_02`
- `SIM_GRID_03`
- `SIM_GRID_04`
- `SIM_GRID_05`
- `SIM_GRID_CEILING`
- `SIM_CEILING_DARK`
- `SIM_EDGE_CEILING`

Assign one of those material names, save the `.blend`, and let Godot reimport it. `SimulationMaterialPostImport.gd` replaces matching Blender materials with the shared external `.tres` resources.

The temporary geometry is deliberately simple and may be deleted once rooftop geometry provides a safe spawn surface, a wall-run test surface, collision, and at least one usable hook target.
