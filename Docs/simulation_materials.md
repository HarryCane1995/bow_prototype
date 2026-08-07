# Simulation material pipeline

BowPrototype simulation surfaces use a semantic Blender material for authoring and a repository-owned Godot `ShaderMaterial` at runtime. The first supported semantic is the exact, case-sensitive name `SIM_GRID`.

## Data flow

`Blender SIM_GRID slot -> direct .blend import -> SimulationMaterialPostImport.gd -> sim_grid.tres -> sim_grid.gdshader`

Blender's node graph is a proxy preview only. On every Godot import, `Scripts/Editor/Import/SimulationMaterialPostImport.gd` walks imported mesh surfaces, reads each source material's `resource_name`, and applies the mapped external material as a surface override. This avoids manual reassignment and keeps the runtime shader independent from generated `.godot/imported` data.

Current mapping:

| Blender semantic | Runtime material | Runtime shader |
| --- | --- | --- |
| `SIM_GRID` | `res://Assets/Materials/Simulation/sim_grid.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |

The import script is configured in both `Level_01_Blockout.blend.import` and the test fixture's `.blend.import`. Production geometry is unchanged until an artist assigns `SIM_GRID` to a surface in Blender.

## Assigning SIM_GRID in Blender

1. Open and inspect `Level_01_Blockout.blend` through Blender MCP or Blender's normal UI.
2. Select the target mesh and open Material Properties.
3. In an existing or new material slot, choose the already existing exact `SIM_GRID` datablock from the dropdown. Do not click **New**, duplicate it, or accept names such as `SIM_GRID.001`.
4. For selected faces only, enter Edit Mode, select the faces, choose the `SIM_GRID` slot, and click **Assign**.
5. Save `Level_01_Blockout.blend`, then reimport it in Godot.

`Tools/Blender/ensure_sim_grid_material.py` can create or repair the canonical proxy material. It refuses numbered `SIM_GRID.*` duplicates and does not assign the material to production meshes.

## Runtime controls

`sim_grid.tres` exposes:

- `base_color` and `grid_color`: dark surface and cyan-green line colors;
- `cell_size`: world-space grid cell size in meters;
- `line_width`: line width as a fraction of a cell;
- `emission_strength`: grid emission multiplier;
- `scan_speed` and `scan_strength`: animated scan rate and contribution;
- `noise_strength`: weak procedural brightness variation.

The Godot shader projects the pattern from world position and blends three planar projections using the world normal. It requires no UV channel and uses derivatives for anti-aliased lines. Object rotation and non-uniform scale therefore do not stretch the cells as UV or object-space mapping would.

The Blender proxy uses procedural Wave, Geometry, and Noise nodes with a timeline driver. It is intended to communicate the dark base, cyan grid, emission, scan, and noise while authoring. It is not pixel-identical to Godot: Godot uses runtime world coordinates, `TIME`, and screen-space derivatives, while Blender evaluates its own node graph and frame number. Curved or smoothly shaded surfaces blend planar projections in both implementations and may look softer around normal transitions.

## Adding a future SIM material

Keep the mechanism explicit:

1. Create one stable Blender semantic such as `SIM_WALLRUN` and its proxy preview.
2. Add the Godot shader and external `.tres` under `Assets/Materials/Simulation/`.
3. Add one exact-name entry to `MATERIAL_REPLACEMENTS` in `SimulationMaterialPostImport.gd`.
4. Add a focused import fixture or extend the verifier only for behavior the new material needs.

Do not add numbered semantic copies, path guessing, or gameplay behavior to the importer.

## Verification

`Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend` contains three shared-material, UV-less surfaces: a floor, a wall, and a rotated non-uniformly scaled mesh. Reimport must report three replacements without creating extra slots. Run the rendering verifier from the repository root with a real renderer:

```powershell
& "C:\Users\harry\Desktop\Godot_v4.6.3-stable_mono_win64\Godot_v4.6.3-stable_mono_win64_console.exe" `
  --display-driver windows --rendering-driver d3d12 --position -10000,-10000 `
  --log-file .godot/sim-grid-verify.log --path . `
  --script res://Tools/SimulationMaterials/verify_sim_grid_pipeline.gd -- `
  res://Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend `
  res://.godot/sim-grid-runtime.png
```

Success prints `SIM_GRID_PIPELINE_VERIFY` with three meshes, one surface/runtime override per mesh, zero UV entries, the external material and shader paths, and non-zero render luminance. Use normal D3D12 rendering for this visual check; Godot's headless dummy renderer cannot validate the shader output.

After any production assignment, also run the standard Level_01 import checks, build the C# solution, and launch the wrapper as documented in `Docs/blender_pipeline.md`.
