# Procedural simulation ceiling

`Level_01_Blockout.blend` contains one decorative Geometry Nodes object named `ENV_SimCeiling_GN` in the `ENV_Simulation` collection. It is positioned at Blender `(2, 35, 181)` above the current training route and has no collision, navigation, physics, or gameplay nodes.

## Modifier controls

Select `ENV_SimCeiling_GN` and open the Modifiers tab. The `Simulation Ceiling` modifier exposes:

| Control | Default | Purpose |
| --- | ---: | --- |
| Size X | 1000 m | Width of the ceiling array |
| Size Y | 1000 m | Length of the ceiling array in Blender's horizontal plane |
| Cell Size | 8 m | Grid spacing and approximate block footprint |
| Gap | 1 m | Controlled gap between neighboring blocks |
| Base Thickness | 18.5 m | Average hanging block depth |
| Height Variation | 50 m | Low-frequency clustered relief plus small cell variation |
| Vertical Offset Variation | 2.94 m | Additional up/down placement variation |
| Horizontal Jitter | 2.02 m | Small aligned-plan displacement |
| Density | 1 | Deterministic occupancy |
| Seed | 140 | Deterministic layout seed |
| Edge Angle | 90 degrees | Target angle between adjacent faces for luminous structural edges |
| Edge Angle Tolerance | 5 degrees | Stable tolerance around the target angle; no exact float comparison |
| Edge Radius | 0.08 m | World-space radius of the emissive curve profile |

The node tree is `GN_SimCeiling`. It preserves the regular grid, clustered noise, seeded per-cell variation, density, and block scaling. The block faces use `SIM_CEILING_DARK`. After the existing instances are scaled and realized, `Edge Angle` is compared to the target with `abs(angle - target) < tolerance`; only those real mesh edges pass through `Mesh to Curve` and `Curve to Mesh`. The resulting edge geometry uses `SIM_EDGE_CEILING`, then joins the dark faces for export.

Do not apply the modifier. Changing the controls or seed updates the ceiling procedurally in Blender. Keep Density high and Horizontal Jitter small so the result reads as one architectural megastructure rather than an asteroid field.

## Material pipeline

The post-import semantic mappings are:

- `SIM_CEILING_DARK` -> `res://Assets/Materials/Simulation/sim_ceiling_dark.tres` (`StandardMaterial3D`, nearly black, matte, no emission);
- `SIM_EDGE_CEILING` -> `res://Assets/Materials/Simulation/sim_edge_ceiling.tres` (dedicated cyan emissive shader with no grid, scan, or noise).

`SIM_GRID_CEILING` remains available and unchanged but is no longer assigned to the ceiling output. Edge color and emission are adjusted in `sim_edge_ceiling.tres`; geometric thickness is adjusted with the `Edge Radius` modifier input.

## Import fallback

Godot's direct `.blend` importer expands un-realized Geometry Nodes instances into separate runtime mesh nodes. The production configuration therefore keeps instance export disabled. The authoring graph retains `Ceiling Block Instances`, but realizes once before hard-edge extraction. This is also necessary for a constant `Edge Radius`: building a beveled wire prototype before non-uniform instance scaling would distort the profile thickness on horizontal edges.

The edge profile is three-sided and uncapped. At ceiling viewing distances it reads as a uniform emissive line while limiting the full 15,876-block array to 1,270,080 evaluated Blender vertices and 666,792 polygons. Godot imports one ceiling mesh with two surfaces, not thousands of nodes.

Run the runtime verifier with a real renderer:

```powershell
& "C:\Users\harry\Desktop\Godot_v4.6.3-stable_mono_win64\Godot_v4.6.3-stable_mono_win64_console.exe" `
  --display-driver windows --rendering-driver d3d12 --position -10000,-10000 `
  --log-file .godot/sim-ceiling-verify.log --path . `
  --script res://Tools/SimulationMaterials/verify_sim_ceiling.gd -- `
  res://Level_01_Blockout.blend res://.godot/sim-ceiling-runtime.png
```
