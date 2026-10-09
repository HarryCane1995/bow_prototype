# Level_01 directional shadow quality — 2026-09-18

Godot **4.6.3 mono**, Forward+, D3D12, NVIDIA RTX 5060. This is a shadow-settings pass only. All diagnostic overrides are process-local; no diagnostic material is saved.

## Findings

The source of the large stippled patches was the sun's **PCSS/contact-hardening shadow path at `light_angular_distance = 8` with Soft Low filtering**, without temporal AA. It was not the Surface Factory floor normal or albedo. The same pattern remained on a flat gray StandardMaterial3D with no textures, emission, normal or detail. Turning SSAO or StylizedContactDarkening off individually did not remove it. Turning angular distance to zero removed it. Smaller nonzero angular distances still left conspicuous noisy areas on this scene; changing the shadow depth atlas from 16 to 32 bits did not fix them.

The sharp cascade transition came from **`directional_shadow_blend_splits = false`**, made much more conspicuous by the noisy filtering and changing sample density. Blending and the shorter, near-weighted cascade coverage remove the obvious band in the reviewed views.

The actual world sun is `/root/Level_01/World/DirectionalLight3D`. Two imported green OmniLight3D nodes have shadows disabled. The character's separate FP/viewmodel directional lights also have shadows disabled, so they are not the floor shadow source.

Material distinction: the exported `tech_wall_627708735` retains its authored panel/value/weather variation. Its optional detail layer is disabled in the Godot material. Neutral-material and no-normal comparisons establish that the objectionable shadow pattern is independent of those maps. No generator, recipe, texture, material or import setting was changed.

## Effective settings

Defaults below were read from live Godot objects / ProjectSettings, not inferred from absent `.tscn` properties. Full dumps: `.godot/level01-shadows/audit_before.json` and `audit_after.json`.

| Property | Before | After |
|---|---:|---:|
| `directional_shadow_mode` | 2 / PSSM 4 splits | unchanged |
| `directional_shadow_max_distance` | 100 m | **80 m** |
| `directional_shadow_split_1/2/3` | 0.10 / 0.20 / 0.50 | **0.10 / 0.25 / 0.50** |
| Approximate cascade boundaries | 10 / 20 / 50 / 100 m | **8 / 20 / 40 / 80 m** |
| `directional_shadow_blend_splits` | false | **true** |
| `directional_shadow_fade_start` | 0.8 | unchanged; last fade approximately 64–80 m |
| `directional_shadow_pancake_size` | 20 | unchanged |
| `light_angular_distance` | 8° / PCSS | **0° / ordinary filtered shadows** |
| `shadow_blur` | 1.0 | unchanged |
| `shadow_bias` / `shadow_normal_bias` | 0.1 / 2.0 | unchanged |
| `shadow_opacity` | 1.0 | unchanged |
| Directional atlas `size` / `16_bits` | 4096 / true | unchanged |
| Directional `soft_shadow_filter_quality` | 2 / Soft Low | **3 / Soft Medium** |
| Positional atlas / filter | 4096, 16-bit / Soft Low | unchanged |
| Main viewport TAA / MSAA / screen-space AA | off / off / off | unchanged |
| 3D resolution scale / debanding | 1.0 / off | unchanged |
| SSAO | enabled; Medium, half-size, 2 blur passes | unchanged |
| SSAO radius / power / intensity | 1.4 / 1.35 / 2.0 | unchanged |
| SSIL / SDFGI / SSR | disabled | unchanged |
| StylizedContactDarkening | enabled, Composite, strength .55, radius .8, bias .06, fade 25–70 | unchanged |
| Fog / volumetric fog / glow / color adjustment | disabled | unchanged |
| Sun direction / color / energy / indirect energy | original transform / white / .85 / .6 | unchanged |

The filter is a **project-wide directional-shadow setting**. The sun's distance, splits and softness changes are local to Level_01. No changes to positional light filtering or other level scenes.

## Selection evidence and tradeoffs

- 40 m lost useful midrange floor shadows; 60 m faded them earlier than desired. 80 m retains a useful gameplay midrange while allocating more density near the player than the former 100 m.
- Atlas 4096 was already the effective default. An 8192 comparison after adjusting splits/blending did not solve PCSS noise and cost more. Retained 4096.
- Soft Medium and Soft High with the old 8° PCSS still showed noise. High cost about 4.88 ms of measured main-viewport GPU time in that trial, versus roughly 2.68 ms Medium. Increasing sample count is not the selected fix.
- Non-PCSS Soft Medium gives clean interiors and modestly filtered edges. No extra blur was added. Compared to before, **penumbrae are narrower and shadows are crisper**; variable PCSS penumbra softness is intentionally sacrificed to remove its unstable pattern.
- Lower bias .05 / normal bias 1 was compared on the floor and building contacts, with little visible advantage. The existing .1 / 2 pair was retained. No large bias workaround. Reviewed floor, wallrun wall, large block geometry, and the live character in F10 external view; no new obvious acne or detached-shadow issue in those views.
- Temporary TAA-on comparison reduced the stipple but did not justify changing global AA. Final movement review uses TAA off. This pass does not claim TAA-on fast-motion ghosting QA.
- This is a bounded gameplay review, not a guarantee for all camera positions or future geometry. Distant shadows still intentionally fade beyond the gameplay coverage; ordinary subpixel edge aliasing can remain with global AA disabled.

## Validation and performance

The full `Scenes/Levels/Level_01/Level_01.tscn` ran with the existing character, FP viewport, combat nodes, colliders and movement. `InputEventKey` and `InputEventMouseMotion` were sent through Godot's normal input pipeline; no velocity-driven fake animation or replacement movement motor was used. Teleports only reset the start of each test segment. Confirmed normal run **18.3 m/s**, real slide around **37 m/s**, real canonical wallrun **33 m/s**, slow pan, and a **120°** look during slide. Existing wall collision was used, with no temporary geometry. The window was additionally inspected and operated with Windows keyboard/mouse input, including an external-view character check and return to FP.

Saved movement frames show clean shadow interiors without the old crawling stipple or a conspicuous moving cascade stripe. Evidence: `movement.json`, `MOVE_*.png`, `MOVEMENT_REVIEW.mp4` under `.godot/level01-shadows/`. The video concatenates recorded test segments; repositioning is not recorded. It is supporting evidence, not a high-precision temporal benchmark.

Short same-camera comparison, **1440×900**, VSync uncapped only for measurement, full live scene including FP presentation, 240 frames per case:

| | Before | After |
|---|---:|---:|
| Median frame time | 2.649 ms | 2.349 ms |
| Approximate FPS | 378 | 426 |
| p95 frame time | 4.099 ms | 3.119 ms |
| Measured main-viewport GPU time | 1.297 ms | .856 ms |

The GPU monitor is for the main viewport, not total GPU time across every viewport. These brief local measurements are approximate and hardware/load dependent. No observed unjustified regression. VSync was restored after measurement.

Protected-file hash verification: **5,006 files checked, zero changes** across the map source, Player scene/modules, Surface Factory, exported material and floor texture folder. The pre-existing `PlayerViewModelSwayModule` missing-reference warning remains; no new runtime script errors were logged. Pre-existing unrelated working-tree changes are preserved. No commit or push.

## Artifacts and reproduction

All screenshots are engine renders. Main A/B camera is identical: `(−12, 8, 28)` looking at `(6, −.747, −6)`, FOV 70°, 1440×900. It includes the floor, large/long shadows, multiple shadow distances and lit regions.

- `.godot/level01-shadows/A_BEFORE.png`
- `.godot/level01-shadows/B_AFTER.png`
- `.godot/level01-shadows/C_DEBUG_NEUTRAL_MATERIAL.png`
- `.godot/level01-shadows/C_DEBUG_NEUTRAL_AFTER.png`
- `.godot/level01-shadows/A_CLOSE_BEFORE.png` / `B_CLOSE_AFTER.png`
- `.godot/level01-shadows/GAMEPLAY_BEFORE.png` / `GAMEPLAY_AFTER.png` (same actual player camera transform)
- `.godot/level01-shadows/MOVEMENT_REVIEW.mp4`, `movement.json`, `final_comparison.json`

These are local review outputs in Godot's ignored cache folder; copy them elsewhere if deleting `.godot`.

Recreate the bounded A/B and neutral captures:

```powershell
godot --path . --script res://Tools/Rendering/verify_level01_shadows.gd --log-file .godot/level01-shadows/capture.log
```

Replay normal-input movement review and leave the playable game at the problem floor:

```powershell
godot --path . --script res://Tools/Rendering/review_level01_shadows.gd --log-file .godot/level01-shadows/movement.log
```

The review leaves the player around `(14, −.746, 12)`, facing the floor's long shadow boundary. Mouse is released after the scripted run; click the game to resume mouse look. The normal Level_01 spawn was not changed.

## Files changed by this pass

- `Scenes/Levels/Level_01/Level_01.tscn`: four local sun-property changes only.
- `project.godot`: one directional filter setting, Soft Medium.
- Added `Tools/Rendering/verify_level01_shadows.gd` and its Godot `.uid`: isolated audit/capture helper.
- Added `Tools/Rendering/level01_shadow_cases.json`: reproducible baseline/production/neutral comparisons.
- Added `Tools/Rendering/review_level01_shadows.gd`: bounded input/performance review; its generated `.uid` may appear when the editor scans it.
- Added this document.

Property meaning was cross-checked against the [Godot 4.6 lights and shadows manual](https://docs.godotengine.org/en/4.6/tutorials/3d/lights_and_shadows.html) and [DirectionalLight3D reference](https://docs.godotengine.org/en/4.6/classes/class_directionallight3d.html). Actual values came from this engine instance.
