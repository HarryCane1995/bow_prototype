# V02: floating gameplay space

20 September 2026. Narrow correction to the existing `GN_LevelBlockout_Generator_v02`, saved with **Seed 17**. Authoring source, Volume, Cutter, controls, band heights, spawn reservation and movement snapshot remain the same.

## What changed

- Removed every automatically generated platform bearing post and high-landing pier. Nothing is added merely to support a slab or bridge.
- Removed the staircase/ramp chain from every upper floor. A seeded lower access route is now optional (probability `0.10 + 0.38 * Route Complexity`), and is omitted when its slope would exceed the safe envelope. It has only the landings it actually needs. Upper floors have no automatic staircase.
- Upper plates no longer attach to a facade. Their footprints vary independently, with offsets bounded by the measured air-jump distance and the existing difficulty factor. Footprints are smaller while the existing band population is retained.
- Ground-to-top bearing facades became shorter isolated wall planes, often suspended above lower surfaces. Their lengths use the wallrun metric. The existing lower wallrun strips, wall-jump pair, slide opening and shaft geometry remain gameplay elements.
- High grapple-candidate landings float without columns. Existing inter-zone bridges retain their seeded adjacency and endpoint selection; their endpoints follow the shifted plates.
- Corrected the local wall-jump landing elevation to use its **actual lower approach height**, rather than global Z. A lowered zone therefore does not silently add its pit depth to the intended wall-jump rise.

There is no new control, new platform asset palette, structural solver or full level rebuild. The graph authoring script regenerated the owned V02 node recipe; it did not rewrite any manual authoring mesh.

## Same-camera comparison

All six Blender images use the same perspective, lens 50 mm, distance 290, target (0,0,10), and Seed-dependent geometry at unchanged controls. Current Cutter is enabled in these comparisons.

| Seed | Upper slabs | Automatic support groups, before → after | Stair/ramp flights, before → after | Inter-zone bridge groups |
|---|---:|---:|---:|---:|
| 17 | 23 → 23 | 24 → **0** | 23 → **0** | 9 → 9 |
| 41 | 11 → 11 | 11 → **0** | 11 → **1** | 6 → 6 |
| 109 | 16 → 16 | 18 → **0** | 16 → **2** | 0 → 0 |

Counts refer to surviving evaluated `(zone, band, part)` groups; a support group could previously contain two posts. For Seed 17, upper plate top area decreased from 44,357 to 32,707 m² (**26%**), and wall surface area from 32,783 to 8,547 m² (**74%**). All 23 sampled slab undersides have more than 4 m of air below the sample. These are sampled clearances, not a proof that every square metre is unobstructed.

| Seed | Before | After |
|---|---|---|
| 17 | ![Seed 17 before](Reviews/V02GameplayCorrection/before_17.png) | ![Seed 17 after](Reviews/V02GameplayCorrection/after_17.png) |
| 41 | ![Seed 41 before](Reviews/V02GameplayCorrection/before_41.png) | ![Seed 41 after](Reviews/V02GameplayCorrection/after_41.png) |
| 109 | ![Seed 109 before](Reviews/V02GameplayCorrection/before_109.png) | ![Seed 109 after](Reviews/V02GameplayCorrection/after_109.png) |

## Metrics and verification

- **32/32 regression checks:** actual XYZ bounds, seed determinism, Volume deformation, Cutter shape/topology/islands/empty input, spawn protection, no global ceiling, band response, metric dimensions and depsgraph updates. Disposable test copies only. [technical_qa.json](Reviews/V02GameplayCorrection/technical_qa.json)
- **36/36 correction checks:** no support geometry, unchanged band population and bridge grammar, sparse optional flights, reduced facade/plate coverage, air under sampled plates, suspended wall bases, wallrun length budget, adjacent band rise and 3D opportunity envelope, local wall-jump approach-to-landing rise. [grammar_qa.json](Reviews/V02GameplayCorrection/grammar_qa.json)
- Heights remain 6.36/12.72/19.08/25.44/31.80 m for Seed 17; 4 upper bands remain in Seeds 41 and 109. Preview samples: **22.1–42.1 ms**, mean 31.5 ms.
- **217/217 object fingerprints unchanged**, including all manual meshes, transforms and collection membership. Every modifier input value and object reference is preserved. **92/92 protected files unchanged**, including Player, tuning, old levels and prior Freestyle exports. [preservation.json](Reviews/V02GameplayCorrection/preservation.json)

The metric checks validate geometric opportunities, not a complete traversal solver. A height below measured wall-jump rise is not by itself proof of a successful jump: approach, wall contact, timing, landing space and LOS still matter. Adjacent surfaces fit within the reserved 3D grapple envelope, but runtime grapple anchors have not been added. Disconnected upper spaces are intentional; no stairs were inserted just to guarantee pedestrian access.

## Existing Godot preview

The previously authorized V02 snapshot and its triangle collision were refreshed using the same exporter and unchanged wrapper `Scenes/Levels/Level_Freestyle_GN_V02.tscn`. Seed 17 now exports **1215 vertices, 813 polygons, 2242 triangles**. No Player or runtime mechanic was changed. [Export manifest](Reviews/V02GameplayCorrection/godot_export.json), [runtime verification](Reviews/V02GameplayCorrection/godot_qa.json).

**25/25 Godot checks PASS**, including the rendered run: exact triangle correspondence within 1 mm (maximum vertex difference 0.081 mm), bounds/scale, protected spawn, actual Player jump/landing, upper-level landings, capsule wall blocking and **93/93 surface rays**. The former mandatory-ramp assertion was removed because this grammar explicitly allows no stair/ramp access. Seed 17 had no suitable optional ramp standing-test point; that case is recorded as skipped, not passed. It was not necessary to add a ramp to satisfy the test.

An already running game keeps its loaded snapshot; restart that preview to load the corrected geometry. Blender remains at Seed 17 with `LEVEL_VOLUME` ready and output controls pinned.

## Changed files and backup

Generation changes: `Tools/Blender/LevelBlockoutV02/region.py` and the Density tooltip/contract in `build.py`. The existing `rebuild_graph.py` applied only the graph portion. Evidence helpers: `review_gameplay.py`, `qa_gameplay.py`; QA/export scripts accept a separate report directory so previous review evidence remains intact. `verify_godot.gd` permits the intentionally reduced ramp population during its surface sampling.

Saved `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`, regenerated `Exports/Level_Freestyle_01_GN_V02.glb`, and updated report/pipeline documentation. Original scene/gameplay wrappers were not modified. Full before-source backup: `Source/Backups/20260920-181617-before-gameplay-grammar/Level_Freestyle_01.blend`. Before-recipe copies and evaluated geometry summaries are in `Docs/Reviews/V02GameplayCorrection/`.

No commit or push. No additional art, supports, navigation, enemies or gameplay systems were introduced.
