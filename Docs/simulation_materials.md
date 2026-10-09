# Simulation surface materials

`SIM_GRID` is a stable Blender semantic, not a requirement to draw a grid. The September 2026 exploration replaces the old neon grid with three procedural visual systems. A is the production preset pending visual review; A and B are the two finalists. C and the exact old primary shader/material remain available for comparison.

## Import contract (unchanged)

`Blender SIM_GRID slot -> direct .blend import -> SimulationMaterialPostImport.gd -> external .tres -> sim_grid.gdshader`

| Exact Blender name | External Godot material |
| --- | --- |
| `SIM_GRID` | `Assets/Materials/Simulation/sim_grid.tres` |
| `SIM_GRID_02` | `Assets/Materials/Simulation/sim_grid_02.tres` |
| `SIM_GRID_03` | `Assets/Materials/Simulation/sim_grid_03.tres` |
| `SIM_GRID_04` | `Assets/Materials/Simulation/sim_grid_04.tres` |
| `SIM_GRID_05` | `Assets/Materials/Simulation/sim_grid_05.tres` |

Paths, existing resource UIDs, exact-name matching and per-surface overrides remain intact for the five surface presets. The procedural simulation ceiling and its dedicated materials were removed from the project on 2026-09-11 at the user's request.

The primary semantic palette now uses subdued ceramic colors (neutral, cool, sage, lilac, ochre). Materials share one shader; no texture inputs are required. Changing a preset updates the imported level without rebuilding its geometry. Never edit `.godot/imported`.

## Visual systems

- **A / Ceramic modules**: staggered large panels, dark joints, occasional recessed rectangles, sparse warm/cool registration slits. World triplanar projection with normal blending. Most useful when spatial readability is the priority.
- **B / Isofield**: continuous three-dimensional scalar field, broad contour terraces and a slow, sparse amber activation wave. No triplanar seam; stationary contour geometry. Preset: `sim_isofield.tres`. The more distinctive simulation direction.
- **C / Vector strata**: broad oblique lane cuts and traveling capsule marks. Preset: `sim_vector_strata.tres`. Retained as an experiment; too repetitive and arrow-like for a whole level.
- **A0 / Legacy grid**: `sim_grid_reference.tres` and `sim_grid_reference.gdshader` preserve the old primary grid parameters/implementation. The comparator applies this one reference preset across SIM surfaces; it does not recreate all five old color presets.

Surface orientation provides a broad value cue. A small fixed diffuse-looking fill keeps solids visible under the existing level's unlit cavities. It stays below bloom intensity; accents are the emissive features. Thin marks fade with the projected pixel footprint, and distant field variation converges to a calm average. This deliberately sacrifices tiny far detail to avoid interference patterns. No displacement, screen-space dependency, texture sampling, loops, stochastic temporal noise or gameplay coupling.

## Runtime review

Open `Scenes/Debug/SimulationSurfaceReview.tscn` and run the current scene. It loads the existing Level_01 wrapper, with real player input and its normal fullscreen startup.

- **F3**: A -> B -> C -> A0; **Shift+F3**: previous.
- **Shift** retains its existing Parkour Mode role; F2/F6/F7 keep existing tuning/audio behavior.
- A preserves the per-semantic material palette. B, C and A0 temporarily apply their common comparison preset only to detected SIM_GRID surfaces.
- Production scene wrappers, default startup scene and InputMap are untouched by the review tool. The tool never writes resources or controls movement.

Optional command-line `--review-windowed` disables this wrapper's startup fullscreen for observation. It is not a background/no-focus architecture.

## Art controls

All live in the ShaderMaterial Inspector, under **ArtDirection**. There is no extra slider UI.

| Parameter | Purpose |
| --- | --- |
| `visual_system` | Select A/B/C |
| `surface_color`, `accent_color` | Body and rare signal colors |
| `structure_scale` | World-space scale in meters (2-20) |
| `structure_contrast` | Structural darkening |
| `accent_density` | Frequency of active marks/bands; zero disables them |
| `emission_strength` | Accent emission, not body brightness |
| `motion_speed` | A: breathing, B: field activation, C: mark travel; zero stops animation |
| `distortion` | B only: contour bending |

The Blender procedural node proxy is still a semantic authoring preview of the old grid; it is intentionally not pixel-identical to the new Godot rendering. Select the existing shared material in Blender; do not create `.001` semantic copies. `Tools/Blender/ensure_sim_grid_material.py` still maintains that proxy palette and is not needed to change the Godot look.

## Bounded validation

`Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend` is the existing five-wall UV-less import probe. Run `Tools/SimulationMaterials/verify_sim_grid_pipeline.gd` with a real renderer to check five external resource paths, one shared shader and a nonempty rendered palette. Its parameter reporting now uses the new art controls.

```powershell
& '<Godot mono console executable>' --path . --script res://Tools/SimulationMaterials/verify_sim_grid_pipeline.gd -- res://Tools/Blender/SimGridProbe/SimGridPipelineProbe.blend '<absolute output PNG>'
```

Runtime exploration used the existing Level_01 geometry for near/far, alongside-wall and inclined-surface camera passes, plus short real-physics Gym slices through jump, slide and wallrun for each concept. The external drivers apply visual overrides only in memory and are separate from the manual review scene. Results and screenshots are recorded in the dated visual exploration report.
