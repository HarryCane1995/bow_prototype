# Highrise100 — Godot showcase

27 September 2026. **Technical QA: PASS.** Final artistic assessment remains with the user.

## Open and fly

Open `Scenes/Environment/Highrise100_Showcase.tscn` and press F6, or run Godot with:

```text
--path <BowPrototype-project-folder> res://Scenes/Environment/Highrise100_Showcase.tscn
```

The default is `Env_Bow_NightCity_v01`. The project main scene is unchanged.

| Control | Action |
|---|---|
| WASD + mouse | Fly and look |
| E / Space; Q | Up; down |
| Shift; Ctrl | 5× fast; 0.2× slow |
| Mouse wheel | Adjust flight speed |
| F1 | Night / Neutral QA |
| Home | Overview |
| PgDn / PgUp | Focus next / previous building |
| H | Focus the single scale reference area |
| Esc; right mouse | Release/toggle mouse; capture mouse |

## Assets and scene

- Editable source: `Art/Environment/Highrise100/Highrise100.blend`.
- Verified backup: `Art/Environment/Highrise100/RuntimeShowcase_QA/Backup/Highrise100.blend`.
- Source and backup SHA-256: `3d998fac3a85743b6bf052f6d366496f080026f8b7e38b3c27d1ee2e69105dd6`.
- Runtime: `Assets/Environment/Highrise100_Runtime/Highrise100.gltf`, its single `.bin`, `Textures/` and `export_manifest.json`.
- Showcase: `Scenes/Environment/Highrise100_Showcase.tscn`.
- Environments: `Resources/Environment/Env_Bow_NightCity_v01.tres` and `Env_Highrise100_NeutralQA.tres`.
- Viewer scripts: `Scripts/Environment/Highrise100/HighriseFlyCamera.gd` and `Highrise100Showcase.gd`.
- Export/build/check tools: `Tools/Environment/Highrise100/Runtime/`.
- Evidence: `Art/Environment/Highrise100/RuntimeShowcase_QA/`.

One glTF retains **HR001–HR100 as 100 separate roots**, without copying texture sets per building. The wrapper stores their grid positions and metadata, with one editable imported instance. No source rebuild, source save, material recipe change, transform application or height normalization was performed.

The 10×10 grid steps are **229 × 208 m**, derived from real bounds plus separation. Every building starts at Godot Y=0 (Blender Z=0). Pairwise XZ AABB tests found no intersections. Actual heights are **174.85–527.33 m**. The one helper area has a 1.8 m human marker and 10/50/100 m poles. Camera clipping is 0.2–8000 m. No collisions are present.

## Material contract, checked in the running renderer

**46 shared material resources: 43 textured recipes + 3 intentional flat materials.** There are **172 image resources/files** (43 × albedo/normal/ORM/emission), representing 165 distinct file-content hashes; a few constant maps share identical pixels across recipes. No identical full material recipes were duplicated. All 172 runtime PNGs match their source hashes. Height maps are not used by the source shader and are not added to this runtime pass.

| Input | Actual Godot setup |
|---|---|
| Albedo | `source_color` shader sampler: sRGB color decoding |
| Normal | Data sampler, explicit normal-map import, scale 0.32, no Y inversion |
| ORM | One shared texture resource in three slots, sampled as data |
| AO | Red channel |
| Roughness | Green channel |
| Metallic | Blue channel |
| Emission | `source_color` sampler: sRGB color decoding, source map retained |

The native StandardMaterial3D shader source was captured and checked for **all 43 textured materials**. See `RuntimeShowcase_QA/NativeShaders/` and `runtime_gpu.json`. The importer connected the maps correctly; no replacement material system or post-import material remapping was needed. Material resources remain shared during scene-local emission scaling.

Headless import initially gave the subset PNGs 2D defaults. `prepare_texture_imports.gd` explicitly sets mipmaps and VRAM compression for the owned runtime textures, and normal-map mode for `*_normal.png`. This was validated on the ten-building subset before the full import. These are source `.import` settings; generated `.godot/imported` files were not edited. Godot's actual generated sampler flags agree with its [4.6 StandardMaterial3D implementation](https://github.com/godotengine/godot/blob/4.6-stable/scene/resources/material.cpp).

**Current runtime: 2311 material surfaces, 2280 textured + 31 intentional flat, 30,500 triangles.** Every surface has UVs and tangents. The 31 flat surfaces use the existing glass/signal/warm material recipes; they are not missing textures.

## Why the old test was 73/75

Both the historical `GodotSanity/Samples.blend` and its actual Godot import were inspected:

| Surface | Material | Explanation |
|---|---|---|
| `HR029_DisplayRail`, slot 0 | `H100_signal` | Intentionally solid cyan emissive rail |
| `HR029_DisplayRail.001`, slot 0 (Godot `_001`) | `H100_warm` | Intentionally solid warm emissive rail |

There were 75 surfaces, of which these two have authored scalar colors/emission instead of texture maps. No missing map, bad slot or exporter loss was found. Evidence: `historical_73_of_75_source.json` and `historical_73_of_75_godot.json`.

## Lighting

Night uses a graphite/dirty cyan-green procedural sky with a muted brown horizon, cool ambient fill, one soft cool directional key, Filmic tonemapping, controlled glow and exponential distance haze. Directional shadows use four cascades with an 850 m distance. SSAO is enabled; SSIL, volumetric fog, SDFGI and VoxelGI are not used. Night emission multiplier is 1.8; Neutral QA is 0.35. Neutral QA has brighter neutral lighting and no haze.

The sky is a cheap authored color gradient, without stars or a volumetric cloud simulation. This is a first lighting preset. No screen stylization, VHS, dithering or chromatic aberration was added.

## Verification and representative captures

Subset testing preceded the full export. Full headless and graphics-enabled tests both passed. The graphics run loaded all 100 roots, checked scale/ground placement/no overlaps, UVs/tangents, actual materials and channels, imported texture flags, native shaders and zero collisions. No missing textures or shader/runtime errors were recorded. Scripted engine input verified W movement (21.25 m over 0.25 s), mouse-look and the F1 environment toggle, without Computer Use or OS input automation. Headless cannot retain captured mouse mode; the GPU test covers that requirement.

Ten representative buildings received automated material/import checks and actual Godot captures:

| Category | ID |
|---|---|
| Corporate | HR003 |
| Megablock | HR007 |
| Industrial | HR013 |
| Residential | HR018 |
| Billboard | HR027 |
| Needle | HR036 |
| Maintenance | HR057 |
| Exoskeleton | HR064 |
| Civic | HR083 |
| Hero | HR100 |

See `RuntimeShowcase_QA/Captures/`: neutral captures for those ten, two overviews and a night HR027 view. The earlier UV pass remains the detailed source-space orientation/stretch assessment; no UVs were edited by this pass. Automated import checks and captured frames do not replace the user's final visual judgment.

## Performance snapshot

Godot **4.6.3 Mono**, Forward+ / D3D12, **NVIDIA GeForce RTX 5060**, **1600×1000**, VSync disabled for measurement only. Each sample follows a 2 s warm-up and covers at least 5 s / 180 frames. All 100 buildings remain loaded. Draw/visible-object counters include render passes, shadows, helpers and HUD; “visible objects” is not the building count. These are brief local samples, not a benchmark guarantee.

| View | FPS | Mean frame | p95 frame | Draw calls | Visible render objects |
|---|---:|---:|---:|---:|---:|
| Night overview | 167.5 | 5.97 ms | 7.90 ms | 2580 | 2779 |
| Neutral overview | 172.4 | 5.80 ms | 7.67 ms | 2580 | 2773 |
| Night near HR027 | 154.8 | 6.46 ms | 8.26 ms | 3576 | 3777 |

Godot's whole-scene texture-memory counter was **232.7 MiB**, render-buffer counter **21.7 MiB**, video-memory counter **1080.6 MiB**. These include renderer resources/targets and are not the disk size of the building textures. Reported frame intervals are measured across engine frames; the engine's separately sampled process-time monitor is retained as raw evidence in JSON.

## Limits and preservation

- Blender warned that some source n-gons could not export tangents. Godot's importer generated the missing tangents: **2311/2311** surfaces have them. No source triangulation/rebuild was performed; rendered triangle count remains 30,500.
- Source exploratory geometry and texture resolution are retained. No new LOD, collision, parallax or expensive GI system was introduced.
- The full project's editor scan reported an existing absent `Scripts/Levels/ProxyChunkPreview.gd` reference and Mono/editor shutdown messages. The standalone showcase runtime logs are clean. Those unrelated files were not repaired.
- Source/backup hashes match. All **160** protected gameplay, level, tuning and generator files match the pre-pass baseline. `project.godot` is unchanged.
- No Level_Freestyle/Player/combat integration; no Computer Use, commit or push.

Complete machine-readable verification and backup hashes: `RuntimeShowcase_QA/final_verification.json`. Saved inspection reports, import logs, GPU logs and captured shader source are in that same directory.

## Reproduce after an intentional source update

Keep a new backup/baseline for each new source revision; `snapshot.py` deliberately refuses to replace an existing backup. Inspect with `inspect_source.py` in background Blender, test `export_runtime.py --subset`, then export the full runtime with `export_runtime.py`. Both use the existing saved source without saving it. Use Godot's `prepare_texture_imports.gd` before editor import, then `build_showcase.gd` and `verify_showcase.gd` (headless, followed by a GPU run with `-- --showcase-qa`). `finalize_report.py` compares current files against that pass's baseline. Do not regenerate buildings or overwrite manual source edits to refresh this showcase.
