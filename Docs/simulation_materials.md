# Simulation material pipeline

BowPrototype simulation surfaces use semantic Blender materials for authoring and repository-owned Godot `ShaderMaterial` presets at runtime. The five supported visual variants use exact, case-sensitive names from `SIM_GRID` through `SIM_GRID_05` and share one shader implementation.

## Data flow

`Blender SIM_GRID slot -> direct .blend import -> SimulationMaterialPostImport.gd -> sim_grid.tres -> sim_grid.gdshader`

Blender's node graph is a proxy preview only. On every Godot import, `Scripts/Editor/Import/SimulationMaterialPostImport.gd` walks imported mesh surfaces, reads each source material's `resource_name`, and applies the mapped external material as a surface override. This avoids manual reassignment and keeps the runtime shader independent from generated `.godot/imported` data.

Current palette mapping:

| Blender semantic | Runtime material | Runtime shader |
| --- | --- | --- |
| `SIM_GRID` | `res://Assets/Materials/Simulation/sim_grid.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |
| `SIM_GRID_02` | `res://Assets/Materials/Simulation/sim_grid_02.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |
| `SIM_GRID_03` | `res://Assets/Materials/Simulation/sim_grid_03.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |
| `SIM_GRID_04` | `res://Assets/Materials/Simulation/sim_grid_04.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |
| `SIM_GRID_05` | `res://Assets/Materials/Simulation/sim_grid_05.tres` | `res://Assets/Materials/Simulation/sim_grid.gdshader` |

The import script is configured in both `Level_01_Blockout.blend.import` and the test fixture's `.blend.import`. Production geometry is unchanged until an artist assigns `SIM_GRID` to a surface in Blender.

## Assigning palette materials in Blender

1. Open and inspect `Level_01_Blockout.blend` through Blender MCP or Blender's normal UI.
2. Select the target mesh and open Material Properties.
3. In an existing or new material slot, choose `SIM_GRID`, `SIM_GRID_02`, `SIM_GRID_03`, `SIM_GRID_04`, or `SIM_GRID_05` from the dropdown. Do not click **New**, duplicate them, or accept numbered copies such as `SIM_GRID_02.001`.
4. For selected faces only, enter Edit Mode, select the faces, choose the intended palette slot, and click **Assign**.
5. Save `Level_01_Blockout.blend`, then reimport it in Godot.

`Tools/Blender/ensure_sim_grid_material.py` creates or repairs the shared proxy palette. It preserves an existing primary `SIM_GRID`, refuses numbered duplicates, and does not assign new variants to production meshes.

## Starting palette

| Variant | Color direction | Cell | Line | Emission | Scan speed / strength | Noise |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `SIM_GRID` | user-tuned dark green | 1.6 | 0.005 | 3.85 | 1.95 / 2.0 | 0.225 |
| `SIM_GRID_02` | clean ice-blue | 2.4 | 0.008 | 1.8 | 0.2 / 0.2 | 0.006 |
| `SIM_GRID_03` | dense matrix green | 0.55 | 0.018 | 2.5 | 1.1 / 0.75 | 0.08 |
| `SIM_GRID_04` | calm dark violet | 2.0 | 0.02 | 1.2 | 0.65 / 1.35 | 0.02 |
| `SIM_GRID_05` | noisy amber/orange-red | 1.25 | 0.015 | 2.8 | 0.45 / 0.55 | 0.14 |

These are visual level-design starting points, not gameplay semantics. Tune each `.tres` independently in Godot; do not duplicate `sim_grid.gdshader`.

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

`Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend` contains five identical UV-less walls, one per semantic material. `Scenes/Debug/SimGridPalette.tscn` instances that imported probe with a camera, lighting, and labels so all variants can be compared without touching Level_01. Reimport must report five replacements without creating extra slots. Run the rendering verifier from the repository root with a real renderer:

```powershell
& "C:\Users\harry\Desktop\Godot_v4.6.3-stable_mono_win64\Godot_v4.6.3-stable_mono_win64_console.exe" `
  --display-driver windows --rendering-driver d3d12 --position -10000,-10000 `
  --log-file .godot/sim-grid-verify.log --path . `
  --script res://Tools/SimulationMaterials/verify_sim_grid_pipeline.gd -- `
  res://Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend `
  res://.godot/sim-grid-palette-runtime.png
```

Success prints `SIM_GRID_PALETTE_VERIFY` with five meshes, one surface/runtime override per mesh, zero UV entries, five external material paths, one shared shader path, and non-zero render luminance. Use normal D3D12 rendering for this visual check; Godot's headless dummy renderer cannot validate the shader output.

Open `res://Scenes/Debug/SimGridPalette.tscn` in Godot and run the current scene (`F6`) to compare color, cell scale, line width, emission, scan, and noise side by side.

After any production assignment, also run the standard Level_01 import checks, build the C# solution, and launch the wrapper as documented in `Docs/blender_pipeline.md`.
