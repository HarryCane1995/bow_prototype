# Local Proxy V05 — variety and traversal spans

Implemented and verified in Blender 5.1.2 on 2026-09-21. Main group: `GN_LevelProxyGenerator_v05`.

Source: [Level_Freestyle_01.blend](../Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend). Select `LEVEL_PROXY`, then use normal Edit Mode tools. Controls are on the source: **N → V05 Local**, or **Object Properties → Custom Properties**. The convenience panel can be registered from embedded Text `V05_CONTROLS_PANEL.py`; the generator and its native SUM drivers work with Auto Run Python disabled.

The user's live authoring edits were preserved. Saved source: **132 vertices / 128 faces**, closed manifold, no modifiers. V05 changes the procedural filling, never rebuilds the authored source. The previous V04 group and hidden reference outputs remain available.

## Movement evidence and span classes

All **10 canonical source/tuning SHA-256 hashes** match the verified snapshot measured on **2026-09-20 at 15:54:56**. No Godot test was rerun. Evidence: [movement_metrics.json](Reviews/LocalProxyV05/movement_metrics.json).

**Observed horizontal air/double-jump reach: 23.035152 m.** This is the recorded trajectory distance, not a proven global maximum.

| Observed movement | Horizontal distance |
|---|---:|
| Standing/ground jump | 8.534 m |
| Running jump | 12.505 m |
| Air/double jump | **23.035 m** |
| Slide jump | 14.741 m |
| Wallrun trajectory | 44.320 m |
| Wall-jump chain | 36.719 m |
| Wall-jump + air chain | 42.640 m |
| Grapple acquisition range | 50.000 m |

Wall-jump lateral measurement is 9.53 m; wall-jump rise is 10.507 m. Running speed is 18.3 m/s. These distances do not turn a generated route into a validated traversal chain.

| SPAN CLASS | OBSERVED PLAYER METRIC | GENERATOR RANGE | EXAMPLE GENERATED DISTANCE |
|---|---|---|---|
| A — BASIC_JUMP | Running jump 12.505 m | 45–70%: **5.627–8.754 m** | **6.116 m**, Seed 17 |
| B — AIR_JUMP | Air/double jump 23.035 m | 58–78%: **13.360–17.967 m** | **16.014 m**, Seed 17 |
| C — NEAR_LIMIT | Air/double jump 23.035 m | 84–94%: **19.350–21.653 m** | **20.175 m**, Seed 73 |
| D — GRAPPLE_REQUIRED | Air/double 23.035 m; acquisition 50 m | 110–145%: **25.339–33.401 m** | **28.202 m**, Seed 17; helper **18.447 m** from approach |

The multiplier bands are V05 design margins around verified measurements, not new gameplay measurements. They are independent of the earlier snapshot's generic range-policy labels. Traversal Difficulty skews distances inside the class band. Short patches only choose classes that fit. Catch lengths increase with class: **5.5 / 7.5 / 10 / 12 m**.

Examples come from a disposable horizontal 20 × 480 × 12 m proxy, local bounds X −10..10, Y 0..480, Z −0.7..11.3. They are reproducible diagnostic examples, not claims about every patch in the user's current source.

## Beyond-double-jump rule

Every intentionally selected D span exceeds the observed air/double threshold. It must have a required helper and a receiving catch. The helper is placed approximately 57% across the gap, up to 8 m above the approach plane. The acquisition check uses a conservative **46 m** bound inside the configured 50 m range.

The native graph checks the helper, approach and catch samples against the actual proxy and enabled Cutter. D also requires sufficient width and height. If the helper/catch setup fails, the graph freezes a fallback flag, changes D to Basic, shortens the gap, and extends the receiving catch within the same phrase footprint. In the Cutter fixture, removing the required candidate changed **28.202 m D → 8.428 m Basic**.

Required helpers are **large magenta markers**, radius 0.52 m; optional helpers are **small amber markers**, radius 0.24 m. Required markers survive `Grapple Bias = 0`. Both outputs are clipped to the actual proxy and optional Cutter.

This is spatial intent for a Blender blockout. No runtime GrappleAnchor, collision, line-of-sight solver, grapple trajectory simulation or full traversability solver was created. An arbitrarily destructive Cutter or self-intersecting source still requires author review.

## Geometry library

Hidden collection **`V05_GAMEPLAY_MESH_LIBRARY`** contains **42 canonical low-poly meshes**, six per family. All 42 are closed meshes; all 42 remain geometrically distinct after normalizing their bounds independently per axis, so they are not scale-only copies. All 42 were actually selected in the fixture seed sweep.

| Family | Six archetypes |
|---|---|
| LANDING | Rectangle, trapezoid, clipped corners, asymmetric bay, L pocket, split recovery |
| PLATFORM | Hex pad, tri-cut pad, boomerang, offset double, T catch, spear slab |
| WALL | Stepped strip, kinked wall, stagger pair, converging pair, broken run, jump pincer |
| RAMP | Clean wedge, offset entry, flared exit, dogleg descent, wedge landing, chute lips |
| BRIDGE | Diagonal plate, dogleg link, staggered chain, fork connection, unequal rails, offset transfer |
| SPEED | Flared runway, S lane, chute recovery, descent gap, split speed lanes, banked shelf |
| VERTICAL | Alternating stack, central step crowns, wall-pair ascent, offset balconies, sparse catch, cross transfer |

[Visual overview of all 42 meshes](Reviews/LocalProxyV05/V05_LIBRARY_OVERVIEW.png) · [Library manifest](Reviews/LocalProxyV05/library_manifest.json).

Object Info nodes reference these actual canonical meshes. Local seed chooses a shape, while local frame, controlled yaw and offset place it. Selection depends on family suitability and available space. Floating geometry is allowed; no obligatory support or stair grammar was introduced.

Shapes normally use **uniform scale 0.65–1.35**. A shape that cannot fit at the minimum scale is skipped; repetitions and neutral metric connectors supply the continuous path. Ramps have an explicit angle exception: uniform scale up to 1, with additional local-X factor `cot(angle)` = **1.0..0.364** for 45–70°. Other shapes are not stretched arbitrarily to fill a long patch. Neutral run/catch connectors carry `variant_id = -1` and are not counted in the 42 forms.

## Straight length variation and local stability

`Length Variation` defaults to **0.82**. It blends a regular 21.96 m run with seeded short/medium/long/very-long durations derived from **18.3 m/s × 0.55 / 1.2 / 2.4 / 4.4 seconds**, plus bounded within-class jitter. Native accumulation places consecutive **run + separate gap + catch** phrases. The final incomplete phrase becomes continuous fill rather than an oversized gap.

| Length Variation | Measured run lengths, Seed 17 | Standard deviation |
|---|---:|---:|
| 0 | 21.960 m throughout | 0.000 m |
| 0.82 | 11.580–70.208 m | 17.091 m |
| 1 | 9.301–80.799 m | 21.847 m |

Long runways use continuous metric connectors with repeated library motifs. Their length does not increase the jump gap. Patches shorter than a desired long run use their available local length.

The V04 local section decomposition, coordinate frames, vertical lattice and actual envelope were retained in `GN_V05_LocalSections_FromV04` (204 nodes). V05 adds the new grammar (1303 nodes). Patch identity is spatial and section identity derives from patch identity plus local ordinal; native integer hashes avoid float precision loss. Per-tile variant identity is distinct from section identity. No whole-proxy bounding-box normalization controls generation.

Append tests for a vertical extension, angled extension and wide-after-narrow extension preserved old **geometry hashes, bounds, variant choices and rhythm records**. Adding a disconnected island also preserved the existing island. Editing/subdividing/dissolving an old patch itself may change that patch's identity and fill; stability applies to untouched patches away from the junction.

## Debugging and inspection

`Debug Span Colors` is **off by default**. Enabled colors: Basic blue, Air green, Near Limit orange, Required magenta. Continuous/vertical fill stays gray.

Attributes include `section_id`, `local_seed`, `variant_family`, `variant_id`, `span_class`, `span_distance`, `required_traversal`, `grapple_required`, `local_forward`, `section_length`, `sequence_start`, `variant_uniform_scale`. Required helpers additionally carry `source_span`, `anchor_distance_from_approach`, `anchor_height`, `landing_distance`.

Internal Output Mode values: 0 surfaces, 1 helpers, 2 span diagnostic points, 3 cleaned envelope, 4 raw surfaces, 5 helper diagnostic points, 6 rhythm points. The two production hosts use 0 and 1. Boolean-created cap elements can have default attributes; inspect the diagnostic output for authoritative per-span records.

## Automated QA and performance

Tests used independent disposable meshes/bmesh operations and a copy of the current authored source. No production-source topology was written by a Python generator.

| Check | Result / evidence |
|---|---|
| A–C: run length variation | Regular at 0, broad controlled variation at 0.82 and 1; consecutive phrases start at zero and have no unintended uncovered intervals |
| D: distinct mesh forms | 42 distinct normalized meshes; all 42 and all seven families used across seed/shape fixtures; measured uniform scale 0.6644–1.3500 |
| E: append stability | Vertical, angled, wide extension and disconnected-island checks pass |
| F–H: span bands | All four classes observed; examples lie within their specified bands; C stays below the observed air threshold |
| I–J: required helpers | D has a helper within range and 12 m catch; Bias 0 retains it; Cutter guard shortens rejected D |
| Actual gaps | Ten Seed-17 BVH measurements on generated surfaces match declared Basic/Air/D gap distances |
| K: proxy containment | Current authored-copy surfaces: **20,846 samples, 0 outside**; helpers: **3,312 samples, 0 outside**; extension and island fixtures also pass |
| L: modifiers | No GN modifier warnings; both production host drivers valid |
| Edit Mode dependency | API/bmesh change while mode is `EDIT_MESH` changes evaluated output without Apply/Bake; human hotkey test remains unperformed |
| Controls | Seed changes geometry and returns deterministically; Difficulty changes span distances; Density changes geometry |
| Saved-file independence | Background reopen with Auto Run Python disabled reproduces both live output hashes; 42 library objects and embedded instructions survive |

Containment uses double-precision winding plus a planar/barycentric boundary test and independent Exact `output minus proxy`. Tolerance is **0.3 mm**. On the final authored copy, Difference left eight vertices/six coplanar faces with volume 8.53e−14 m³ and equivalent thickness 4.51e−14 m; no exterior vertices or face centers. Helpers left an empty Difference. This is a numerical boundary residue, not a claim that the surface Difference is literally empty.

Timings are six dirty-edit evaluations of both generated hosts on the **132-vertex / 128-face** authored copy, including depsgraph update and evaluated geometry access:

| Mode | Median | Maximum |
|---|---:|---:|
| Preview Quality 0 — Manifold | **24.60 ms** | **26.12 ms** |
| Preview Quality 1 — Exact | **972.91 ms** | **1013.85 ms** |

These are API evaluation timings, not measured interactive viewport FPS. Exact is visibly more expensive on this larger proxy. The handoff uses Preview 0.

Saved evaluated output: **2878 vertices / 2071 faces**; helpers: **432 vertices / 720 faces**. Handoff: Seed 17, Length Variation 0.82, Debug Span Colors off, Cutter off, LEVEL_PROXY selected.

Evidence files: [spans and rhythm](Reviews/LocalProxyV05/spans_rhythm.json), [library/controls](Reviews/LocalProxyV05/vocabulary_controls.json), [authored containment/performance](Reviews/LocalProxyV05/authored_performance.json), [saved-file verification](Reviews/LocalProxyV05/saved_file_verification.json), [preservation audit](Reviews/LocalProxyV05/handoff.json).

The original 232 objects were audited: only the two authorized host modifier stacks changed; the source mesh changed through the user's live authoring. No originals were deleted and no unrelated mesh/transform changes remain. Hidden world-matrix caches were checked against persisted transforms from an independently opened backup. All **268 monitored Godot-related file hashes** stayed unchanged. Background Blender emits unrelated installed InstaMAT startup warnings, but exits successfully and reports no GN warnings.

## Manual tests and limits

Full [19-test checklist](Reviews/LocalProxyV05/V05_MANUAL_TEST_CHECKLIST.txt) and [quickstart](Reviews/LocalProxyV05/V05_QUICKSTART.txt) are also embedded as Blender Text blocks `V05_MANUAL_TEST_CHECKLIST` and `V05_QUICKSTART`.

Start with tests **15–19**: a long straight extrusion at Variation 0 / 0.82 / 1; Seeds 17 / 42 / 73 for distinct shapes; debug Air and Near Limit gaps; a Required gap whose magenta marker survives Bias 0; then append an extrusion and compare old variants. Tests 1–14 cover normal Edit Mode, turns, shafts, Cutter, disconnected islands and containment.

Keep the proxy closed, outward-facing, non-self-intersecting, in metres with unit object scale. Quad extrusions are the supported main workflow; complex n-gons can underfill. An open source intentionally produces no output until closed. Local patch remeshing can reroll local content. Horizontal jump classes are restricted to nearly horizontal frames (`abs(forward.z) <= 0.02`); inclined patches receive continuous speed/descent fill instead of treating slope length as a measured horizontal jump. This is a blockout grammar, not a proof of reachability for every pair of generated platforms.

Visual inspection used an API-rendered library overview and Blender MCP viewport screenshots. The later permission to use CU was not needed. Human hotkey/playability tests remain for the user. **No Godot launch/export/collisions/runtime anchors, no commit, no push.**

Implementation: `Tools/Blender/LocalProxyV05/` (`library.py`, `foundation.py`, `generator.py`, `build.py`, `qa.py`, `containment.py`, `panel.py`, handoff/verification helpers). Ordinary editing requires none of these scripts to run. Backup before implementation: `Docs/Reviews/LocalProxyV05/before_v05_20260921_023735.blend`.
