# Procedural simulation ceiling

`Level_01_Blockout.blend` contains one decorative Geometry Nodes object named `ENV_SimCeiling_GN` in the `ENV_Simulation` collection. It is positioned at Blender `(2, 35, 72)` above the current training route and has no collision, navigation, physics, or gameplay nodes.

## Modifier controls

Select `ENV_SimCeiling_GN` and open the Modifiers tab. The `Simulation Ceiling` modifier exposes:

| Control | Default | Purpose |
| --- | ---: | --- |
| Size X | 110 m | Width of the ceiling array |
| Size Y | 170 m | Length of the ceiling array in Blender's horizontal plane |
| Cell Size | 7.5 m | Grid spacing and approximate block footprint |
| Gap | 0.55 m | Controlled gap between neighboring blocks |
| Base Thickness | 5.5 m | Average hanging block depth |
| Height Variation | 6.5 m | Low-frequency clustered relief plus small cell variation |
| Vertical Offset Variation | 1.8 m | Additional up/down placement variation |
| Horizontal Jitter | 0.35 m | Small aligned-plan displacement |
| Density | 0.96 | Rare deterministic omissions; keep high for a solid ceiling mass |
| Seed | 11 | Deterministic layout seed |

The node tree is `GN_SimCeiling`. It builds a regular mesh grid, converts vertices to points, computes clustered noise plus seeded per-cell variation, instances a reusable unit cube, assigns `SIM_GRID_CEILING`, and realizes only at the final Godot export boundary.

Do not apply the modifier. Changing the controls or seed updates the ceiling procedurally in Blender. Keep Density high and Horizontal Jitter small so the result reads as one architectural megastructure rather than an asteroid field.

## Material pipeline

Blender semantic `SIM_GRID_CEILING` maps during post-import to `res://Assets/Materials/Simulation/sim_grid_ceiling.tres`. The resource uses the existing `sim_grid.gdshader`; no additional shader implementation exists. Its starting preset is dark blue-black with a cold cyan grid, 3.2 m cells, thin lines, moderate-low emission, slow scan, and little noise.

## Import fallback

Godot's direct `.blend` importer was tested with `blender/meshes/export_geometry_nodes_instances=true`. It expanded the ceiling into 334 separate runtime mesh nodes. The production configuration therefore keeps that option disabled and the GN tree uses a final `Realize Instances` node. Authoring remains instanced and procedural upstream, while Godot receives one ceiling mesh with one mapped surface.

Run the runtime verifier with a real renderer:

```powershell
& "C:\Users\harry\Desktop\Godot_v4.6.3-stable_mono_win64\Godot_v4.6.3-stable_mono_win64_console.exe" `
  --display-driver windows --rendering-driver d3d12 --position -10000,-10000 `
  --log-file .godot/sim-ceiling-verify.log --path . `
  --script res://Tools/SimulationMaterials/verify_sim_ceiling.gd -- `
  res://Level_01_Blockout.blend res://.godot/sim-ceiling-runtime.png
```
