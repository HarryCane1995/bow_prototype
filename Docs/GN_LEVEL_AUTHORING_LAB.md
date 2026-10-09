# Geometry Nodes level authoring lab

Verified in Blender 5.1.2 on 20 September 2026. This pass is a Blender-only authoring POC. Godot integration and exports were explicitly excluded.

## Open and edit

Open `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`, workspace `LEVEL_BLOCKOUT`. The live Blender session is left in Edit Mode with one Source face selected. Use ordinary modelling tools: E, G, subdivision, deletion and bevel. No Apply, Bake, reload or Python execution is needed while authoring.

Pre-change backup: `Assets/Levels/Level_Freestyle_01/Source/Backups/20260920-161317-before-GN-Lab/Level_Freestyle_01.blend`.

| Object | Role | Initial geometry |
| --- | --- | --- |
| `LEVEL_AUTHORING_SOURCE` | Editable ordinary mesh, source of truth; no modifiers | Neutral 8 × 4 m patch, 9 vertices / 4 quads |
| `LEVEL_ENVELOPE` | Editable closed volume in which generation is allowed; no gameplay or collision meaning | 8 vertices / 6 faces; X −4.6…2.8, Y −2.6…2.6, Z −0.5…2.5 m |
| `LEVEL_GENERATED_OUTPUT` | Locked preview with the GN modifier; edit its inputs, not its evaluated topology | Empty base mesh; initially 32 evaluated vertices / 24 faces |

Source and Envelope use wire display and appear in front of the preview. Generated Output uses a solid teal material and is not selectable in the viewport. Its modifier controls remain pinned in Properties while Source is edited.

Collection eyes in the Outliner provide **Show Source**, **Show Envelope** and **Show Generated** independently through `LEVEL_AUTHORING`, `LEVEL_ENVELOPE` and `LEVEL_GENERATED`. Use the eye for display debugging; excluding the input collections from the view layer can remove data needed for evaluation. `LEVEL_GUIDES` is reserved and empty.

The Outliner search is set to `LEVEL_` to expose the authoring objects. Clear this search to see other collections. The eight existing Freestyle collections are hidden with their viewport monitor switches for lab clarity, and remain intact. Their prior visibility is stored in scene property `gn_lab_previous_collection_visibility`. Re-enable their monitor switches to see the original floor and reference kit.

## Procedural dependency

The modifier on `LEVEL_GENERATED_OUTPUT` uses node group **`GN_LevelAuthoring_POC`**, stored in this `.blend`. Its 25 native nodes read Source and Envelope through separate Object Info nodes in Relative transform space, with As Instance disabled. There is no feedback dependency, source modifier, frame handler, persistent timer, baked mesh or Python-generated replacement of the editable Source.

Each enabled source face becomes an independent closed panel: subdivide → split edges → scale face → extrude along its normal → add a flipped bottom → weld. This deliberately simple effect exposes topology changes clearly. It is not a building generator or a watertight architectural shell; adjacent panels can intersect at corners.

The optional Boolean face attribute `proc_enabled` restricts generation when it exists; if absent, every usable face is enabled. Faces with area ≤ 1e−8 are ignored in the procedural branch. This specifically prevents the zero-area side faces created at the start of ordinary E extrusion from invalidating the Manifold Boolean. The Source itself retains those faces and remains editable.

The generated closed panels are intersected with Envelope. This cuts geometry at the actual volume boundary, including partially intersecting panels, rather than merely selecting panel centres. Initially unclipped output ends at X=3.8 m, and clipped output ends at X=2.8 m. `Use Envelope` bypasses the intersection for comparison.

## Controls

| Input | Default | Meaning |
| --- | --- | --- |
| Source Object | `LEVEL_AUTHORING_SOURCE` | Editable mesh dependency |
| Envelope Object | `LEVEL_ENVELOPE` | Allowed-volume dependency |
| Use Envelope | On | Enable volume intersection |
| Envelope Margin | 0 m | Approximate envelope vertex-normal offset, −2…2 m |
| Structural Scale | 0.9 | Scale each face panel, 0.1…0.99 |
| Extrusion Depth | 0.6 m | Panel depth along source normals, 0.02…3 m |
| Preview Quality | 0 | Procedural subdivision level, 0…2 |
| Robust Clipping | Off | Off: Manifold; On: Exact fallback |

Keep Preview Quality at 0 during ordinary editing. Levels 1 and 2 multiply quad face counts by approximately 4 and 16 before extrusion. There is no Seed or noise panel because this POC is deterministic.

## Verification

`Tools/Blender/GNAuthoringLab/technical_qa.py` creates disposable Source, Envelope and Output copies, uses the real node group, exercises them in Edit Mode and deletes all fixtures afterward. It does not change real Source/Envelope topology. The temporary depsgraph observer is also removed. Run it only from Object Mode in the intended Blender file.

**20/20 automated checks passed.** Evidence: `Docs/Reviews/GNAuthoringLab/technical_qa.json`.

- Source: vertex move, subdivision, discrete extrusion, region extrusion, zero-displacement extrusion, face deletion and bevel changed the evaluated output as expected.
- Envelope: contraction removed panels; a closed face extrusion restored generation space. Positive/negative margin changed the bounds.
- Counts, geometry hashes, bounds, depsgraph updates, modifier warnings, optional face selection and preview quality were checked. Final samples had no evaluated node warnings.
- Real Source and Envelope remained plain meshes with unchanged topology hashes throughout automated QA. No test objects or test collections remain.

**Real UI smoke test also passed**, separately from the API tests. UI actions used normal Blender hotkeys and selection. Read-only snapshots taken afterward are in `Docs/Reviews/GNAuthoringLab/ux_states.json`; capture does not call mesh refresh or depsgraph update operations.

| Actual UI action | Live result while still in Edit Mode |
| --- | --- |
| Source: select face, E, 1 m | Source 9→13 vertices and 4→8 faces; Output 24→48 faces, maximum Z 0.6→1.6 m |
| Source: G, X, 1 m on the extruded face | Generated sloping panels and bounds changed immediately |
| Envelope: S, X, 0.2 | Output 24→12 faces; clipping contracted to the narrow allowed volume |
| Repeat E after zero-area filter | Output remained visible at zero displacement, then updated at 1 m, with no warning visible in Properties or reported by evaluated modifier |
| Native Undo after test operations | Neutral Source and original Envelope restored; Output returned to 32 vertices / 24 faces |

The broader subdivision, deletion, bevel and envelope extrusion checks were automated on disposable meshes, as authorized in the execution clarification. Knife, inset and every possible malformed/self-intersecting input have not been exhaustively tested through the UI.

## Performance and limits

Latest local evaluation + materialization timings, 256 source quads, four updates per quality:

| Preview Quality | Manifold min…max | Mean | Clipped output faces |
| --- | --- | --- | --- |
| 0 | 5.7…17.6 ms | 8.8 ms | 326 |
| 1 | 14.8…15.3 ms | 15.1 ms | 1,224 |
| 2 | 47.5…50.2 ms | 49.2 ms | 4,356 |

The earlier Exact probe averaged about 195 / 704 / 2,843 ms at quality 0 / 1 / 2. Raw evidence is retained in `technical_qa_exact_initial.json`. These are local test timings, not a guaranteed viewport frame rate. Complex source topology, large face counts and difficult intersections cost more.

Manifold clipping requires closed manifold input volumes. Source may be open because GN builds closed panels from its faces; Envelope must define a closed volume. Deleting an Envelope face can make the inside undefined or invalidate the result. Exact is slower and can help with difficult intersections, but does not give an arbitrary open envelope a meaningful inside. Blender documents these solver differences in the [Mesh Boolean manual](https://docs.blender.org/manual/en/5.0/modeling/geometry_nodes/mesh/operations/mesh_boolean.html).

Envelope Margin is a vertex-normal displacement, not a precise signed-distance offset. Large offsets and self-intersections may invalidate the volume. Tiny/degenerate source geometry, non-planar ngons and overlapping panels have normal Boolean limitations; the zero-area filter only addresses the verified Extrude intermediate case.

## Scope and preservation

Existing 204 Freestyle objects were preserved; their geometry, transforms and collection membership matched the pre-pass snapshot. The final hash comparison of 92 protected Godot, Player, tuning, old Level_01 and Freestyle export files found no changes. Existing unrelated working-tree changes were preserved. No commit or push was made.

No level layout, corridors, buildings, game boundary, collision, Godot integration, new export, random generator, outside-region preview or custom modelling UI was added. Source is already under `.gdignore`. The existing Freestyle export whitelist excludes all four new lab collections.

`build_lab.py` is the one-time construction recipe and intentionally refuses to overwrite existing named authoring objects or their node group. Do not rerun it to regenerate a manually authored Source. `capture_ux_state.py` is an optional read-only evidence utility, not a dependency of the saved workflow.
