# Seeded Geometry Nodes blockout — v01

20 September 2026 · Blender 5.1.2 · **Blender-only authoring experiment**

Source: `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`.
Workspace: `LEVEL_BLOCKOUT`. Main group: **`GN_LevelBlockout_Generator_v01`**.
The saved handoff uses Seed **211**, a neutral material, selected `LEVEL_CUTTER`, and the output modifier pinned in Properties.

![Saved authoring workspace](Reviews/GNLevelBlockout/handoff.png)

## Ordinary authoring workflow

1. Select `LEVEL_FIELD`: an ordinary four-vertex, one-face quad, initially **220 × 176 m**, centered at world origin. Use `S X`, `S Y` in Object Mode or Edit Mode; moving individual corners is supported for a convex quad. Field geometry is projected to XY, with the floor at Z=0.
2. Change **Seed** in the pinned modifier. It changes macro zones, category placement, occupancy, rotations, regional heights/scales and optional elevated connections. Identical Field, Seed, Cutter and controls produce identical evaluated geometry.
3. Select `LEVEL_CUTTER`, Tab, then move/scale vertices or extrude faces to form a **closed volume**. Geometry inside that volume disappears live. `Use Cutter` compares against the uncut result; an empty cutter is harmless.
4. Return to Field to adjust the footprint. No node editing, Apply, Bake or Python update is required.

`LEVEL_GENERATED_OUTPUT` is the single procedural result. It is selection-locked to keep authoring objects easy to pick. `PLAYER_SPAWN` is a simple helper at (0, 0, 0.05), just above its Z=0 floor. Field and Cutter have wire display; the selected Cutter is orange. In Edit Mode Blender also displays the selected mesh faces as an overlay.

## Controls and spatial grammar

| Control | Saved value | Meaning |
|---|---:|---|
| Seed | 211 | Complete deterministic layout selection; group interface default is 17 |
| Density | 0.72 | Fraction of regions receiving substantial structures |
| Verticality | 0.68 | Ascent/drop heights and optional upper connections |
| Openness | 0.30 | Bias toward open macro regions |
| Route Complexity | 0.65 | Secondary ledges, bypasses and inter-region bridges |
| Traversal Difficulty | 0.45 | Comfortable through near-observed-limit metric spans |
| Grapple Presence | 0.55 | Frequency of high-point crossing courts; zero removes this category |
| Height Range | 12 m | Upper cap on structural ascent dimensions |
| Spawn Safe Radius | 8 m | Clear origin reserve with protected floor |
| Use Cutter | On | Subtract the closed manual exclusion volume |
| Preview Quality | 0 | 0 = Manifold; 1 = Exact fallback |
| Debug Traversal Colors | Off | Optional category colors |

The two remaining object inputs reference Field and Cutter. No independent width/length or low-level noise controls are needed. A Cutter Margin was intentionally omitted rather than presenting an approximate offset as a reliable distance.

Generation proceeds from paired **88 m macro regions** (open, dense, raised, lowered, vertical, corridor) to **44 m candidate regions**, then to metric-sized features. Regions use spatial IDs and independent random streams derived from the one Seed. Seeded X scale is 0.86–1; Z scale is 0.68–1 except categories with fixed human clearances. Whole regions must fit inside the Field, checked at their center and four corners. This leaves clean floor edges instead of clipping arbitrary half-buildings.

The base floor gives multiple directions and bypasses. Optional 3 m wide upper bridges connect neighbouring regions, with end decks and ramps. There is no ordered sequence of movement stations. Internal instances are realized only for aggregate geometry/boolean operations; the scene does not acquire thousands of obstacle objects.

| Category | Geometry and intended opportunity |
|---|---|
| OPEN_FLOW_AREA | Quiet floor, optional low ledges and blocks |
| JUMP_GAP | Running-jump gap, wide launch/landing platforms and recovery pit |
| AIR_JUMP_GAP | Longer gap scaled from measured air/double jump |
| SLIDE_JUMP_GAP | Gap scaled from measured slide jump |
| SLIDE_CLEARANCE | 1.25 m clear low passage, side walls and exit platform |
| WALLRUN_STRIP | Metric-length wall beside a gap, optional ledge |
| WALL_JUMP_CHANNEL | Paired walls with a gap based on lateral wall-jump reach |
| WINDOW_OPENING | Sill, side walls and lintel; 2.1 m clear opening |
| RAMP_ASCENT | Broad raised platform, slope and side ledge |
| STEPPED_ASCENT | Seven broad steps, upper platform and alternate ramp |
| PILLAR_COURT | Five columns, varying heights, optional bridge/block |
| SHAFT_DROP | Pit, bottom floor, recovery ledges and optional crossing |
| MULTI_LEVEL | Several platforms, intermediate landing, ramp and upper bypass |
| GRAPPLE_CROSSING | Gap, landing pads and elevated column/cap target opportunity |
| OVERHANG_PASSAGE | 2.3 m clear covered passage and ramp to the roof |

All 15 categories occurred across the five QA seeds. Category IDs remain in evaluated geometry for inspection. Grapple structures are geometry only, not runtime anchors.

## Current movement evidence and scale policy

The generator reads the **20 September 2026, 15:54:56** measurement snapshot from `Docs/Reviews/LevelFreestyle01/metrics_snapshot.json`; the explanatory table is [LEVEL_FREESTYLE_01_METRICS.md](LEVEL_FREESTYLE_01_METRICS.md). Its driver is `Tools/Levels/Freestyle01/verify_and_measure.gd`.

Before using these measurements, `metrics.py` verified SHA-256 for all ten canonical inputs against the current working tree: `Scenes/Player.tscn`, the default tuning resource and tuning class, current Jump/WallRun/CrouchSlide/InputGesture/SlingshotGrapple modules, `MainCharacterV4.cs`, and `project.godot`. All matched. Evidence: [movement_metrics.json](Reviews/GNLevelBlockout/movement_metrics.json). This pass reused verified same-build measurements; it did not run another Godot playtest.

| Observation | Horizontal travel / range | Rise or relevant detail |
|---|---:|---|
| Standing start + forward jump | 8.534 m | 2.423 m rise |
| Running jump | 12.505 m | 2.423 m rise |
| Air/double jump | 23.035 m | 5.603 m rise |
| Slide jump | 14.741 m | 2.423 m rise |
| Wallrun trajectory | 44.320 m | 4.214 m rise; whole jump-to-floor trajectory, 80 wall ticks |
| Wallrun → wall-jump chain | 36.719 m | 10.507 m rise; **9.53 m lateral reach** |
| Wall movement → air jump | 42.640 m | 13.384 m rise; **7.77 m lateral reach** |
| Grapple acquisition | 50 m | 3D camera-to-anchor range; aim/LOS still required |
| Representative grapple landings | 55.474 / 64.961 / 77.665 m | Tests with 15 / 30 / 45 m horizontal anchor stations, +10 m height; ~0.73 s control delay |
| Capsule | 0.9 m diameter | Standing 1.8 m; crouch/slide 1.1 m |
| Running speed / gravity | 18.3 m/s | 49 m/s² |

These are **observed trajectories, not proven global maxima**. Whole-chain travel is never used as the spacing between two wall-jump walls. The 220 m field takes approximately 12 seconds to cross unobstructed at run speed; a route with changes of direction and elevations is longer.

Comfortable band: **0.50–0.65**; challenging: **0.65–0.82**; near observed limit: **0.82–0.90**. The difficulty factor is `0.52 + 0.38 × Traversal Difficulty`. Jump gaps reserve one capsule diameter before applying that factor and regional scale: `(observed travel − 0.9 m) × factor × regional X scale`. Fixed slide/window/standing clearances are not compressed by seeded Z scaling. Individual step rises and regional ascent heights are bounded by their relevant observed vertical envelopes.

## Spawn and exclusion contract

No structure region may enter the origin reserve; the admission test also includes the region footprint radius. A native floor pad is unioned at the origin, and a protected cylinder is removed from the effective Cutter before subtraction. Therefore even a large Cutter covering the center cannot remove the spawn floor. Thirteen downward rays across the reserve checked floor Z=0 and absence of blocking overhead geometry for each QA seed and the center-covering Cutter test.

The origin guarantee takes priority if the Field is moved away or shrunk below the spawn area: the protected pad can then extend outside the Field. Keep the Field around origin for the intended layout.

The Cutter uses native Mesh Boolean Difference against the aggregate floor/structures. Closed concave L-shaped geometry, Edit Mode movement and a closed face extrusion were tested. It removes the floor too: an exclusion is an empty authoring region, not a gameplay-safe courtyard floor. The origin reserve is the deliberate exception.

## Five-seed technical comparison

All rows use the same 220 × 176 m Field and default controls, **Use Cutter off** for comparable complete-module dimensions. XY bounds are identical: X=[−110,110], Y=[−88,88]. The saved handoff has Cutter on, so its counts differ.

| Seed | Vertices | Faces | Z minimum → maximum, m | Distinct region categories |
|---:|---:|---:|---:|---:|
| 17 | 1704 | 1163 | −3.658 → 7.046 | 7 |
| 41 | 2196 | 1445 | −5.450 → 8.794 | 9 |
| 73 | 1340 | 913 | −3.932 → 8.772 | 6 |
| 109 | 1704 | 1172 | −4.019 → 8.770 | 8 |
| 211 | 1872 | 1303 | −5.815 → 7.259 | 10 |

Counts below are **regions**, not primitive objects. Optional upper bridges are additional MULTI_LEVEL-tagged parts and are not counted as regions.

| Category | 17 | 41 | 73 | 109 | 211 |
|---|---:|---:|---:|---:|---:|
| OPEN_FLOW_AREA | 6 | 5 | 12 | 5 | 4 |
| JUMP_GAP | 1 | 2 | 1 | 2 | 1 |
| AIR_JUMP_GAP | 0 | 0 | 0 | 1 | 1 |
| SLIDE_JUMP_GAP | 2 | 2 | 1 | 1 | 1 |
| SLIDE_CLEARANCE | 0 | 0 | 0 | 0 | 3 |
| WALLRUN_STRIP | 0 | 1 | 0 | 0 | 0 |
| WALL_JUMP_CHANNEL | 3 | 0 | 0 | 1 | 0 |
| WINDOW_OPENING | 0 | 2 | 0 | 0 | 1 |
| RAMP_ASCENT | 2 | 0 | 1 | 2 | 0 |
| STEPPED_ASCENT | 1 | 0 | 0 | 0 | 2 |
| PILLAR_COURT | 0 | 3 | 0 | 0 | 0 |
| SHAFT_DROP | 0 | 1 | 0 | 0 | 2 |
| MULTI_LEVEL | 0 | 0 | 1 | 3 | 0 |
| GRAPPLE_CROSSING | 3 | 1 | 2 | 3 | 2 |
| OVERHANG_PASSAGE | 0 | 1 | 0 | 0 | 1 |

Dimensions were measured from tagged **evaluated vertex coordinates**, projected into each region's orientation, rather than simply accepting stored desired-size attributes.

| Seed | Running gaps, m | Slide-jump gaps, m | Air gaps, m | Grapple candidate 3D distances, m |
|---:|---:|---:|---:|---:|
| 17 | 8.007 | 8.293–8.844 | — | 21.975–25.153 |
| 41 | 6.965–7.552 | 8.304–8.945 | — | 24.491 |
| 73 | 7.218 | 8.909 | — | 23.874–24.761 |
| 109 | 6.937–7.391 | 9.082 | 13.575 | 23.761–24.482 |
| 211 | 7.102 | 9.556 | 14.735 | 22.246–24.214 |

Additional measured samples: wallrun wall **29.597 m** (Seed 41), wall-jump channels **5.963 m** (17/109), step rises **0.385–0.471 m** (17/211), slide clearance **1.25 m**, standing overhang clearance **2.30 m**. Raycasts confirmed that the tested gaps actually penetrate the floor and paired gap landings have matching heights. No dimension violations or modifier warnings were found in these samples or the difficulty endpoint samples.

## QA, performance and actual UI evidence

**56/56 automated checks passed.** [technical_qa.json](Reviews/GNLevelBlockout/technical_qa.json) contains full counts, hashes, dimensions, warnings, spawn rays, timing and depsgraph IDs. Disposable `TEST_*` copies received Field resize/skew/Object scaling, Cutter movement/extrusion/concave replacement/empty geometry, parameter endpoints and clipping bypass tests. All test objects/meshes were removed. Production Field and Cutter were not rewritten by the QA script.

Seed 17 repeated with an identical geometry hash; all five seed hashes differ. Field and Cutter changes propagated through depsgraph to evaluated Output without Apply/Bake. Parameter endpoint tests verified actual output changes; zero Grapple Presence removed grapple courts. Fast/Exact timings include dependency evaluation and materializing the evaluated mesh, measured for three seed changes with Cutter enabled:

| Preview mode | Minimum | Maximum | Mean |
|---|---:|---:|---:|
| 0 — Manifold | 15.66 ms | 31.07 ms | 21.23 ms |
| 1 — Exact | 1027.47 ms | 1194.81 ms | 1119.76 ms |

These are local evaluation samples, not a viewport FPS guarantee. Keep Preview Quality **0** for authoring. Exact is a slow fallback.

The short **real Computer Use** test used Blender selection, Tab, S/X/numeric entry, the Seed control and Undo. This is separate from API QA:

- Field Edit Mode `S X 0.8`: output visibly rebuilt during the modal operation; width **220 → 176 m**, faces **1317 → 858**, then Undo restored the geometry.
- UI Seed **211 → 212**: visibly different internal composition while Field was still in Edit Mode. At the UI test's Density 0.73, faces **1347 → 1231** and the evaluated hash changed.
- Cutter selected in the viewport, Tab, `S 2`: visible clipping changed during Edit Mode; faces **1231 → 1142**. Undo restored the exact pre-scale output hash.
- Saved handoff restored Seed 211, Density 0.72, original Field/Cutter mesh geometry and neutral material; output **1896 vertices / 1317 faces**, matching the initial handoff geometry hash.

Read-only observations: [ux_states.json](Reviews/GNLevelBlockout/ux_states.json). Early entries labelled with intended Seed actions still have Seed 211 because those attempted actions did not change Seed; the successful entry is `ui_seed_numeric` with Seed 212. The temporary observer never tagged/updated geometry and was removed after the test. The UX test verified scaling, not a real UI face extrusion; closed face extrusion was exercised by disposable API QA.

## Preserved data, changed files and limitations

Preserved `GN_LevelAuthoring_POC`, `LEVEL_AUTHORING_SOURCE`, `LEVEL_ENVELOPE`, and its old preview renamed **`POC_GENERATED_OUTPUT`**. Their collections remain hidden. All **207** original objects match pre-pass geometry/transform/collection fingerprints, allowing that one intentional name change. All **92** protected disk files match their pre-pass SHA-256, including runtime/Player inputs and existing exports. Evidence: [preservation.json](Reviews/GNLevelBlockout/preservation.json).

Pre-change live-state backup (including pre-existing unsaved edits): `Assets/Levels/Level_Freestyle_01/Source/Backups/20260920-165036-before-Seeded-Blockout/Level_Freestyle_01.blend`. `previous-disk.blend` in that directory also preserves the earlier disk version.

This pass changes the authoring `.blend`, adds `Tools/Blender/LevelBlockout/{metrics,nodes,vocabulary,build,qa,capture_ux}.py`, this report and `Docs/Reviews/GNLevelBlockout/`, and extends `Docs/blender_pipeline.md`. Source/review folders retain `.gdignore`. Existing Godot scenes, exports, mechanics and tuning are untouched. `build.py` is a guarded one-time construction recipe and refuses to replace an existing Field/group; it is **not** an update button for manually edited authoring data.

Known prototype limits:

- Field must be a simple **convex XY footprint**; Z is projected away. Concave/self-intersecting Field shapes are not supported. The Cutter can be concave but must remain closed/manifold; open or self-intersecting cutters are not guaranteed.
- The 44 m modular grammar is visible. Internal structures appear/disappear at cell thresholds while the floor changes continuously. Candidate counts are capped at 12 × 12, so very large fields become relatively open. The current composition is intentionally a sparse blockout, not architecture or a procedural city.
- Some joined primitive volumes and upper connections intersect. This is not a clean watertight final collision asset. Metrics checks cover representative tagged features; they do not prove every route, approach, landing, overhead interaction, grapple line of sight, or arbitrary seed/parameter combination. No full-level passability guarantee is made.
- Low Verticality reduces variable ascent/drop structures; fixed clearance passages and some walls remain human-sized. The spawn admission buffer is conservative and can leave substantially more open space than the nominal radius.
- The origin floor pad can extend outside an undersized/displaced Field. Cutter exclusions remove ordinary floor too; origin floor remains protected.
- Exact boolean is too slow for normal interactive editing. Manifold depends on valid closed inputs. Determinism was verified within this Blender build; cross-version topology identity is not promised.

Deferred as requested: **Godot integration/export, collision, runtime grapple anchors, enemies, final architecture, Surface Factory, materials/art pass, props, mission planning and a complete traversal solver**. No commit or push.
