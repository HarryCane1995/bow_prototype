# GitHub checkpoint — 2026-10-10

Baseline: `e19982db1e432d4f8c7e764532689d5b908137c6`, branch `main`.
The working branch and freshly fetched `origin/main` matched at preflight; the
index was empty. The separate audio worktree was left untouched.

During validation, the open editor saved newer Highrise emission overrides
(Night 4.65 / Neutral 0.9) and resource UIDs. The user explicitly requested
leaving these fresh edits local. This checkpoint retains the tested prior
contents of `Scenes/Environment/Highrise100_Showcase.tscn`,
`Resources/Environment/Env_Bow_NightCity_v01.tres` and
`Resources/Environment/Env_Highrise100_NeutralQA.tres`; the working files are
not overwritten. Those three files intentionally remain modified after commit.

## Preserved development state

- Canonical Player movement, slide gesture fix, parkour/wallrun intent and
  surface rearm, grapple, bow, RMB input/state foundation and procedural audio.
- V4 split 1POV/3POV presentation with V3/V2/legacy retained; authored PoseLab
  scenes/Actions, Blender sources, exports, metadata and import hooks.
- Level_01 and CyberCity Blender sources/wrappers; Freestyle V06 source and
  current evaluated snapshot; earlier V02/V03/V04 runtime scenes, section
  sources, LocalProxy V04/V05/V06 and construction/export/QA tools.
- Facade/Surface/Material Intelligence, billboard and VFX tooling, browser
  viewer and vendor license, material recipes/maps and runtime libraries.
- Highrise100 source, 100 definitions, 76 material recipes, all 380 source
  maps, one representative silhouette contact sheet, runtime glTF/bin and
  its 172 maps. Runtime texture copies have different required relative paths;
  they are intentional alongside the Blender preparation inputs.
- Reusable metrics/library fixtures and manual test guidance. Historical
  per-pass documentation remains dated evidence rather than a fresh QA claim.

## Excluded local material

Godot/build/Python caches, Blender backups, timestamped source backups, large
QA dumps, historical screenshots/renders, Highrise preview galleries/sanity
projects, the PureRef/downloaded-photo collections, downloaded-animation labs
and an unintegrated Hunyuan scratch import are excluded. Authored procedural
library thumbnails and the ten images required by the web review are retained.
Excluded files were not removed from disk. `.gitignore` uses scoped paths and
exceptions for the small reusable fixtures and exporter metadata.

The required Ferndale Studio 10 HDRI is 81.32 MiB, the only selected file over
25/50 MiB. Its size/MD5 match official CC0 metadata; see
[THIRD_PARTY_ASSETS.md](../THIRD_PARTY_ASSETS.md). No selected file exceeds
100 MiB, and no new Git LFS workflow is introduced.

## Checkpoint-specific corrections

- README now distinguishes implemented runtime, experimental tools and plans.
- Highrise README describes the portable source/runtime subset and omitted
  historical galleries.
- Added the missing `Scripts/Levels/ProxyChunkPreview.gd`, a title/label-only
  script for the preserved experimental V04 wrapper. Gameplay remains in Player.
- Existing ceiling-resource/tool deletions were already present at preflight
  and documented in `ENV_SKYSCRAPER_PASS.md`; no live references remain.

The checkpoint does not rebuild assets, change authored animation/geometry,
integrate a new character or refactor gameplay.

## Source portability and limits

Read-only Blender 5.1.2 inspection found no linked libraries or missing runtime
source textures: Level_01 has 181 relative image references, CyberCity five,
Highrise100 172 external FILE images. Humanoid/PoseLab/FP source assets have no
external images/libraries. PoseLab retains three scenes and 74 Actions.

Freestyle V06 has 2,550 nodes and 1,106 evaluated triangles. The snapshot's
proxy/evaluated geometry fingerprints, controls and GLB hash match the saved
source; its whole-file source checksum predates later Blender serialization.
No regeneration is needed to preserve the current geometry. All ten measured
movement-source hashes in the retained metrics fixture match current files.

Hero silhouette/mask assets are isolated unapproved authoring studies, with no
Player dependency. Concept PNG redistribution provenance is unknown and these
images are excluded. Silhouette already has a stale image-empty guide path;
mask's optional image-empty guide is also absent after clone. These are not
surface textures; editable geometry remains available. Their manual `.blend`
sources were preserved without path edits.

Highrise `Runtime/export_runtime.py` retains its two small saved-source guard
inputs (`baseline.json`, `source_inspection.json`). Historical inspection and
report scripts may require omitted QA archives; old manifest preview links
may also be absent. Open/append the saved source or run the retained runtime
showcase without rebuilding. A full procedural rebuild can overwrite manual
changes and is outside checkpoint validation.

## Validation

Toolchain: Godot `4.6.3.stable.mono.official.7d41c59c4`, Blender `5.1.2`,
.NET SDK `9.0.200`, target framework `net8.0`.

Validation uses an exported copy of the selected Git index outside the working
directory, without the original `.godot` cache or excluded local files. The
working directory's C# build and the selected copy's restore/build pass with
zero warnings/errors. Resource-literal/glTF dependency checks, known-secret
patterns and conflict-marker checks pass. This is minimal checkpoint QA;
human traversal and exhaustive regression are outside scope.

Fresh headless editor import/parse completed with exit code 0 and no errors.
Seven scene startup/shutdown checks (120 frames each) passed: Level_01,
Movement Gym, current Freestyle, preserved Proxy V04, Highrise100 showcase,
ArtPassReview and Humanoid_Base_Test. Highrise logged 100 buildings and 46
materials. Player scenes retain the documented legacy viewmodel warning about
`ViewModelCamera3D`/`ArrowTipMarker`; it did not fail startup or the V4 path.
Mouse capture, visual quality and complete traversal were not revalidated.

`git diff --check` on accumulated new files reports inherited formatting in
two legacy Freestyle wrappers, `capture_ux.py`, `mesh_vfx_app.js` and the
vendored `RoomEnvironment.js`. These nonfunctional whitespace warnings were
preserved with the authored/vendor content rather than reformatted.
