# Flow Course V03

20 September 2026. Separate native Geometry Nodes generator `GN_LevelBlockout_Generator_v03`, object `LEVEL_FLOW_OUTPUT`, collection `V03_FLOW_COURSE` in `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`.

V03 builds one directed, folded course from the origin. Fifteen ordered sections share entry/exit positions and heights; larger catch pads join bends. The rectangular `LEVEL_VOLUME` supplies live world-axis bounds. Seed changes handedness, bend positions and local wall/platform angles. Optional side islands split and rejoin near section 13. There are no bearing posts or automatically justified support structures.

V02, v01, POC, their meshes and existing Godot previews remain available. V02 output is hidden for this handoff. The live source was backed up before adding V03 in `Source/Backups/20260920-183316-before-flow-v03/`.

## Start here

The saved source is **Balanced, Seed 17**, full route. `LEVEL_VOLUME` is selected; the V03 modifier is pinned in Properties. Edit the ordinary Volume/Cutter meshes with Tab. Generation is native GN: no handlers, Apply, Bake or Python topology rewriting are involved in normal use.

| Example | Seed | Layout Mode | Centreline length | Intended rhythm |
|---|---:|---:|---:|---|
| Balanced | 17 | 0 | 605.3 m | Jump, walls, pockets, climb, islands, grapple, descent, slide |
| Vertical | 41 | 1 | 615.9 m | Three wall-jump climbs, airborne catch, shorter drops |
| Speed | 109 | 2 | 616.8 m | Continuous ascent ramps feed stronger descents and a low slide lane |

Mode 3 is Arena Mix. The mode determines the sequence grammar; Seed varies the geometry within it. These are a bounded course family, not arbitrary route-topology generation.

See `Docs/Reviews/FlowCourseV03/balanced_seed17.png`, `vertical_seed41.png`, `speed_seed109.png`, and `balanced_top.png`. Preview section colors distinguish types; cyan Flow Guide shows progression and is excluded from both game and section exports.

## Implemented sections

Twelve types exist across the modes: ENTRY, GAP_JUMP, WALLRUN, WALL_JUMP_SHAFT, SLIDE_CHUTE, STEEP_DESCENT, GRAPPLE_CATCH, MIXED_PLATFORMS, ARENA_POCKET, MULTI_ROUTE, RECOVERY, RAMP_ASCENT.

Balanced IDs 00–14:

`ENTRY → GAP → WALLRUN → ARENA → SHAFT → MIXED → GRAPPLE → DESCENT → SLIDE → WALLRUN → ARENA → SHAFT → DESCENT → MULTI_ROUTE → RECOVERY`

The shared `V03_TraversalSegment` group constructs local geometry. The main group computes directed legs and accumulating elevations, transforms each section, clips it, applies colors and writes FACE attributes: `flow_section`, `flow_kind`, `flow_entry`, `flow_exit`, `flow_anchor`, `flow_length`, `flow_height_change`, plus movement metadata. Cut faces receive section ownership after Boolean processing. ID 00 always contains the origin reserve; there is no full-domain safety floor.

## Controls and movement limits

- **Verticality** controls wall-jump and island rise; heights stay within the volume reserve. **Traversal Difficulty** scales gap and wall-pair distances against current measured movement.
- **Openness** controls lane width; **Density** controls optional arena/branch walls. **Route Complexity** enables one or two short side routes.
- **Grapple Presence** above 0.1 enables the dedicated grapple segment; below it that slot becomes a running jump. The GLB exports a real anchor marker that the existing Godot binder converts into the canonical `GrappleAnchor` scene.
- **Wall Angle Jitter**, 0–30 degrees, bounds local yaw randomness. Wallrun and wall-jump walls use smaller fractions of that budget; islands and arena walls also rotate. Seeded diagonal legs add controlled changes of direction.
- **Steep Angle**, 35–70 degrees, changes actual wedge geometry. Default **45°**. Current unchanged Player maintained grounded descent at 35° and 45° in the dedicated fixture. At 55° and 70° it lost contact and landed on recovery: those settings are **airborne drop chutes**, not continuous grounded slide. Strong descents include a catch length budget for up to 40 m/s incoming carry.
- **Use Cutter** enables subtraction. It is initially **off in the three examples** because the shared V02 cutter intersects the new route. Its position and topology were preserved. Enabling or reshaping it can deliberately sever a course. **Preview Quality** 0 uses Manifold; 1 uses Exact.

Metrics were checked against ten current source hashes, including canonical Player, tuning and movement modules. Observed running jump is 12.51 m, air-jump range 23.04 m, wallrun 44.32 m, wall-jump rise 10.51 m, grapple acquisition 50 m. These are observed trajectories, not mathematical maxima. Balanced's running-jump gap is 5.58 m, slide clearance 1.25 m, and raised grapple catch is reachable in the measured test.

The envelope contract remains an axis-aligned bounding box containing the origin reserve, as in V02. Tested input resizing/topology changes update immediately through the depsgraph. Extreme compression, every control combination, arbitrary concave volumes, automatic obstacle-avoidance routing and complete route solvability are outside this pass. A new Cutter/Seed edit still needs a playtest.

## Isolate and save a chunk

1. Set **Section Preview** to 1–15. This isolates stable section ID 00–14; 0 restores the complete course.
2. Open the 3D View sidebar, **Flow V03**, and click **Save isolated section .blend**.
3. Files go to `Assets/Levels/Level_Freestyle_01/Sections/Source/` with section/type/seed/time in the name. Each contains an ordinary evaluated mesh, an ENTRY marker at local origin and a relative EXIT marker. Grapple sections retain an anchor marker. This is a reusable static snapshot, not another live generator.

The optional panel is registered in the current Blender session. After reopening, run the embedded text **V03_TOOLS_RUN_ONCE** (Alt+P in Text Editor) to restore its buttons. Modifier controls and live generation work without it. Script entry point: `Tools/Blender/FlowCourseV03/chunks.py::save_chunk(id)`.

Saved wallrun ID02 and arena ID03 examples are listed in `Docs/Reviews/FlowCourseV03/saved_chunks.json`; both files were actually reloaded and their meshes/entry/exit markers verified. No full asset library was created.

## Godot preview and verification

Open **`Scenes/Levels/Level_Freestyle_GN_V03.tscn`** and run the current scene. The main project scene was not changed. It contains the canonical Player, existing marker binder and a scene-specific readout. F1 restarts through the existing Player behavior.

`Tools/Blender/FlowCourseV03/export_godot.py` exports the currently evaluated full route to `Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01_GN_V03.glb`. Run it through Blender Python after edits, with Section Preview 0, then let Godot reimport. Export is explicit; Blender changes do not automatically rewrite the GLB. Each of the 15 meshes has a `-col` suffix and section metadata; guides, Volume and Cutter are excluded. Temporary Principled materials preserve the viewport colors. The saved chunk assets and authoring source are excluded from automatic Godot import.

Evidence under `Docs/Reviews/FlowCourseV03/`:

- **31 GN checks passed**: three modes, stable IDs, continuous entry/exit chain, deterministic Seed, isolation, disposable Volume/Cutter topology changes, empty cutter bypass, optional density and slope changes. Default update plus evaluated-mesh read: approximately **59–81 ms** for these examples on this machine; not a full GUI framerate benchmark.
- **9 additional contracts passed**: spawn floor/clear sky, bounds, actual 35/45/70° face normals, covering-cutter spawn protection, Exact Boolean and saved-chunk reload.
- **89 Godot checks passed in a graphics-enabled run**: all 748 exported triangles survived; per-section collision matches the visual mesh within 1 mm; 122 floor, 496 wall and 4 slope ray probes hit. All 30 declared section endpoints have actual floor at the expected height.
- Physical InputEvents with unchanged Player crossed the running gap, low slide lane, 45° descent and grapple break. Grapple launched from the real bound anchor and landed 51.57 m along its section on the elevated catch.
- Additional wall test traversed wallrun ID02 (45 wall ticks) and both wall-jump shafts ID04/11 (25 wall ticks and one wall-jump input each), landing near/beyond their exits on the upper floor. See `wall_moves.json`.
- **217 old object fingerprints, four previous node groups and 94 protected files preserved**, including Player, tuning, project settings, V02 GLB and scene.

These are representative automated movement cases with initial case placement, not a human end-to-end completion of every preset. The headless run could not capture mouse look for grapple, so the definitive test used a graphics-enabled process. An early headless process also reported a Mono finalizer failure during shutdown; the final graphics run and final capture completed without that error. The existing legacy viewmodel aim-reference warning remains unrelated to V03.

## Files added or changed

- Updated asset: `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend` (additive V03 data and handoff workspace).
- Added generated V03 GLB/import settings and two section `.blend` snapshots under that level's `Exports/` and `Sections/`.
- Added `Scenes/Levels/Level_Freestyle_GN_V03.tscn`, `Scripts/Levels/FlowCoursePreview.gd` and its UID.
- Added authoring/export/panel/QA scripts in `Tools/Blender/FlowCourseV03/` and evidence in `Docs/Reviews/FlowCourseV03/`.
- Added this guide and a scoped note in `Docs/blender_pipeline.md`.

No gameplay implementation, older generator code, old preview, commit or push was changed/performed.
