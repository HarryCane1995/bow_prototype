# Blender to Godot pipeline

This is the verified Level_01 asset workflow for BowPrototype. It describes the repository state tested on 2026-08-07, not a generic Blender guide.

## Verified toolchain

- Godot: `4.6.3.stable.mono.official.7d41c59c4`
- Blender: `5.1.2`
- .NET SDK: `9.0.200`
- Godot import metadata: `res://Level_01_Blockout.blend.import`, `importer="scene"`, `importer_version=1`
- Relevant importer options: Blender materials, UVs, normals, tangents, modifiers, punctual lights, and custom properties are enabled; Godot also has `meshes/ensure_tangents=true`.

`blender`, `godot`, and `dotnet` are available on this workstation. Blender MCP connects to the installed Blender add-on when Blender is running with its normal user configuration.

## Canonical files and ownership

| Role | Path | Ownership |
| --- | --- | --- |
| Editable Level_01 source | `res://Level_01_Blockout.blend` | Blender source of truth |
| Level textures | `res://Assets/Textures/Levels/Level_01/` | Editable repository assets |
| Godot wrapper | `res://Scenes/Levels/Level_01/Level_01.tscn` | Godot gameplay and level composition |
| Runtime marker bridge | `res://Scripts/Levels/ImportedLevelMarkerBinder.cs` | Godot runtime logic |
| Import metadata | `res://Level_01_Blockout.blend.import` | Generated/maintained by Godot; do not hand-edit |
| Imported scene cache | `res://.godot/imported/Level_01_Blockout.blend-*.scn` | Generated; never edit or commit as source |

`project.godot` starts `res://Scenes/Levels/Level_01/Level_01.tscn`. The wrapper declares `res://Level_01_Blockout.blend` as a `PackedScene` and instances it under `ImportedLevel`. Player, environment, runtime marker binding, containers, HUD, and other game-specific nodes remain beside it in the wrapper. Reimporting the Blender asset therefore replaces imported geometry without rebuilding the gameplay scene.

Other Blender/GLB assets in the repository, including `res://BlenderAssets/Bow.blend` and files under `res://Assets/Models/Bow/`, are separate bow/viewmodel sources and outputs. They are not the Level_01 map source.

## Import decision

The canonical production path is:

`Blender MCP -> Level_01_Blockout.blend -> Godot direct .blend import -> Level_01.tscn wrapper -> in-project verification`

Godot's direct `.blend` importer invokes Blender's glTF export path internally. The current `.blend.import` settings and installed versions were tested successfully. A safe A/B probe was authored through Blender MCP with a UV-mapped cube, an unpacked repository-relative Base Color texture, and `Image Texture -> Principled BSDF -> Material Output`:

- direct `.blend` import produced `PipelineProbeMesh`, `M_PipelineProbe`, `StandardMaterial3D`, and a `CompressedTexture2D` of `1254x1254`;
- a sibling exported `.glb` produced the same result;
- the production `Level_01_Blockout.blend` imported `L01_Arena01_TestBuilding_01 / Atlas` with a `1254x1254` texture.

Direct import remains selected because it already feeds the lightweight wrapper, passed the same material/texture test as `.glb`, and avoids a second generated file that can drift from the source. The temporary probe assets were removed after validation.

Do not switch to `.glb/.gltf` silently. A fallback is justified only after a repeatable direct-import failure or a confirmed material/export incompatibility. If that happens, keep `.blend` as the source, generate the export under a clearly named generated-assets directory, automate the export, point the wrapper at the generated file, and update this document plus `AGENTS.md`. Never hand-edit the generated export.

## Current source structure

`Level_01_Blockout.blend` uses metric units with `scale_length=1.0` and meters. Its established collections are:

- `00_REF`: references and authoring guides;
- `10_LEVEL_VISUAL`: visible level meshes and current Blender lights;
- `20_COLLISION`: collision-only meshes;
- `30_GAMEPLAY_MARKERS`: marker empties such as `GrappleAnchor_01`;
- `40_ROUTE_NOTES`: authoring notes;
- `90_TRASH_DISABLED`: retained disabled work, not production content.

Current visible meshes use `UVMap`. The source currently has no object modifiers, but the importer is configured to evaluate modifiers. The scene contains several intentionally non-applied legacy object scales; do not normalize them in bulk.

The current atlas Base Color file is:

- `res://Assets/Textures/Levels/Level_01/level_01_atlas_base_color.png`

The repository still contains `level_01_road_base_color.png` because the current `.blend` retains an image datablock for it, but no imported mesh currently exposes the old `L01_Arena01_Road / Material` verification target. Removing that datablock and source texture must be a deliberate Blender edit, not filesystem cleanup. Active atlas image datablocks are unpacked, use `sRGB`, and load at `1254x1254`. Legacy material names (`Atlas`, numbered `Atlas.*`) are retained because renaming/consolidating them would be a separate destructive relink. New materials must use the naming rules below.

## Editing through Blender MCP

1. Start Blender normally so the existing MCP add-on runs. Do not use `--factory-startup` or `bpy.ops.wm.read_factory_settings()` in the connected process: both disable the add-on and disconnect MCP.
2. Through MCP, inspect `bpy.data.filepath` and `bpy.data.is_dirty` before opening another file. Do not discard an unsaved user scene.
3. Resolve the repository root for the current workspace and open `<repo>/Level_01_Blockout.blend` through `bpy.ops.wm.open_mainfile(...)` only when it is safe. Never store that machine-specific invocation path in the `.blend`.
4. Inspect the relevant collection, object, mesh, UV layers, material slots, modifiers, and image paths before editing.
5. Make the smallest change, save the same `.blend`, and verify all image paths with `bpy.path.abspath(image.filepath)` plus `os.path.isfile(...)`.
6. Reimport and validate in Godot using the commands below.

MCP can create/read materials, nodes, images, UVs, custom properties, and save the file through Blender Python. A minimal compatible Base Color assignment is:

```python
import bpy

relative_path = "//Assets/Textures/Levels/Level_01/example_base_color.png"
image = bpy.data.images.load(bpy.path.abspath(relative_path), check_existing=True)
image.filepath = relative_path
image.colorspace_settings.name = "sRGB"

material = bpy.data.materials.get("M_Level01_Example") or bpy.data.materials.new("M_Level01_Example")
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
bsdf = nodes.get("Principled BSDF")
texture = nodes.get("BaseColor_Texture") or nodes.new("ShaderNodeTexImage")
texture.name = "BaseColor_Texture"
texture.image = image
links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, check_existing=False)
```

Before running this example, verify that the target material already has the expected output/Principled nodes and avoid adding duplicate links blindly.

## Texture and material rules

- Store level textures under `Assets/Textures/Levels/Level_01/`; use `//Assets/Textures/Levels/Level_01/...` inside the root `.blend`.
- Do not use an absolute user-profile path, a Downloads-relative path, or another machine-specific location. Do not pack large images by default.
- Use stable channel suffixes: `_base_color`, `_normal`, `_roughness`, `_metallic`, `_alpha`, `_emission`.
- Use `M_Level01_<Purpose>` for new materials and `T_Level01_<Purpose>_<Channel>` for Blender image datablock names.
- Base Color and Emission color textures use `sRGB`. Normal, Roughness, Metallic, masks, and other data textures use `Non-Color`.
- Connect a normal image through `ShaderNodeNormalMap` to the Principled `Normal` input; never connect normal RGB directly to the shader.
- Use UV mapping for persistent level surfaces. The supported simple chain is `Texture Coordinate (UV) -> optional static Mapping -> Image Texture -> Principled BSDF`. Do not rely on Generated/Object coordinates when a stable UV layout is required.
- Prefer the glTF-transferable Principled subset: Base Color, Metallic, Roughness, Normal, Emission, Alpha, and standard UV texture transforms. Verify the imported `StandardMaterial3D` after every new channel.
- Arbitrary procedural nodes, Blender-only shader operations, complex node groups, and many renderer-specific effects do not transfer as equivalent Godot materials. Bake them to repository textures, intentionally reproduce them as a Godot `ShaderMaterial`, or simplify the Blender material. Document the exception.
- For Alpha, connect the intended alpha channel and verify the imported transparency mode in Godot; a node link alone is not sufficient proof.

## Level_01 Surface Factory floor (2026-09-18)

The arena floor `L01_Arena01_TestFloor_01` uses the existing export
`FacadeFactory/tech_wall_627708735` through the Blender material
`M_Level01_Floor_TechWall_627708735`. `SimulationMaterialPostImport.gd` maps this
specific source material to the exported `ORMMaterial3D` under
`Assets/Materials/Environment/FacadeFactory/Generated/`; this preserves the exact
ORM, structural normal, emission settings and repeat sampler. No global
replacement of `SIM_GRID_02` is involved. Other surfaces retain their materials.

The source floor UVs are world XY / 6; both its static Mapping node and the
exported Godot material use scale 1.5. The final tile footprint is 4 x 4 meters.
The export's separate detail maps remain opt-in and are not added to the main
normal. `Tools/Environment/apply_level01_floor.py` makes a timestamped source
backup under `.godot/level01-floor/` and checks for concurrent source writes
before saving. `verify_level01_floor.gd` checks the exact runtime material,
texture sizes, UV density, floor collision and the playable wrapper; `--capture`
also records two views of the actual map. No wrapper or gameplay edit is needed.

## Coordinate, transform, and naming conventions

- Author in Blender meters: one Blender unit is one meter.
- Blender authoring axes are `+Z` up and `-Y` model front. glTF maps these to `+Y` up and `+Z` model front in Godot; `-Z` is the Godot camera forward direction. The direct importer/glTF conversion owns the axis conversion. Do not pre-rotate the entire map to compensate. For oriented models use the model-front convention, not the camera-forward convention.
- Never mass-apply transforms to existing content. For a new finalized static mesh, apply Rotation/Scale only when doing so will not break UVs, modifiers, matching collision meshes, animation, or intentional instancing. Usually keep Location unapplied.
- Keep origins deliberate and stable. Static architecture normally uses a predictable local/base origin; hinged, rotating, or interactive pivots belong at the actual pivot. Do not batch-reset origins.
- Visible objects: `L01_<Area>_<Purpose>_<NN>`. New materials: `M_Level01_<Purpose>`. New image datablocks: `T_Level01_<Purpose>_<Channel>`. Use the established numbered marker names such as `GrappleAnchor_01`.
- Keep non-destructive modifiers editable. The direct importer evaluates enabled modifiers; verify the imported mesh before applying any modifier in the source.
- Export/import normals and tangents. Keep custom split normals when they are intentional; do not recalculate the whole map as routine cleanup.

## Collision, markers, and excluded helpers

- Visible meshes belong in `10_LEVEL_VISUAL`.
- Collision-only meshes belong in `20_COLLISION` and use the Godot suffix `ObjectName_COL-colonly`. Keep collision topology simple and matched to the intended visible object.
- Gameplay marker empties belong in `30_GAMEPLAY_MARKERS`. Supported runtime names include `PlayerSpawn`/`PlayerStart`, `GrappleAnchor*`, `EnemySpawn*`, `KillPlane`, and `FinishTrigger`. Blender stores only the marker transform/metadata; `ImportedLevelMarkerBinder` creates runtime gameplay objects.
- Reference, route-note, and trash collections are organizational conventions, not a guaranteed export filter. Any helper object that must not reach Godot must use the supported `-noimp` suffix and be verified absent after import. Do not put `-noimp`, `-col`, or `-colonly` on gameplay markers.
- C# scripts, signals, triggers, player configuration, interactive scenes, and other gameplay logic remain in the Godot wrapper/resources.

## Reimport and verification

From the repository root, save the `.blend` first and then run:

```powershell
godot --headless --editor --path . --import --quit
```

Godot also reimports changed sources when the editor is open. Do not edit `.blend.import` or `.godot/imported/*` to force a result.

Verify a known mesh, material, and Base Color texture in the imported map:

```powershell
godot --headless --log-file .godot/blender-pipeline-atlas.log --path . --script res://Tools/Blender/verify_scene_import.gd -- res://Level_01_Blockout.blend L01_Arena01_TestBuilding_01 Atlas
```

The verifier must exit `0` and print `BLENDER_PIPELINE_VERIFY` with the expected node/material plus a non-zero texture size. Change the expected node/material arguments when intentionally replacing those legacy assets.

Then validate code and the playable wrapper:

```powershell
dotnet build Bow_prototype.sln --no-restore
godot --headless --log-file .godot/blender-pipeline-map.log --path . --quit-after 5
```

Review output for import errors, missing resources, marker/collision warnings, and new C# exceptions. A system-only root-certificate warning can appear in the restricted validation environment; it is not an asset success signal and does not replace the explicit verifier result.

## Troubleshooting

- **MCP cannot connect:** confirm Blender is running normally and the existing add-on is active. Restart the test Blender process if a factory reset disabled the add-on; do not install a second MCP server.
- **Texture is `0x0` or missing:** inspect `image.filepath`, `bpy.path.abspath(...)`, `os.path.isfile(...)`, and color space. Move/copy the intended source into the repository and save a `//...` path.
- **Godot does not reimport:** confirm source modification time, run the headless import command, inspect `.blend.import`, and confirm `blender --version` works for the same environment.
- **Material differs in Godot:** reduce to the supported Principled subset and inspect the imported `StandardMaterial3D`. Bake or recreate unsupported procedural effects; do not claim node parity without inspection.
- **Gameplay nodes disappear:** the imported asset has been used as a replacement for the wrapper. Restore the wrapper composition and instance the imported `PackedScene` under `ImportedLevel`.
- **A helper appears in Godot:** collection placement alone did not exclude it. Add `-noimp` and reimport.
- **A CLI validation crashes while another Godot instance runs:** rerun checks sequentially with distinct `--log-file` paths; do not launch parallel Godot validations against the same user data/log directory.

## Completion criteria for 3D asset tasks

A task is complete only when the correct `.blend` source was edited and saved, repository-relative texture paths resolve after reopen, Godot reimport succeeds, the imported node/material/texture is inspected, the Level_01 wrapper runs without new project errors, and all new limitations or exceptions are documented here.

## Separate humanoid base pipeline (2026-09-11)

The explicitly requested humanoid test assets use `Assets/Characters/BaseHumanoid/Source/Humanoid_Base.blend` as the editable source and two generated GLBs under `Assets/Characters/BaseHumanoid/Exports/`. This is a scoped character workflow, not a switch of the Level_01 direct-import pipeline. `Source/.gdignore` prevents importing the authoring layout as a duplicate runtime asset; the lightweight `Humanoid_Base_Test.tscn` instances the generated male/female GLBs only.

Use `Tools/Blender/HumanoidBase/export_base.py` after manual source edits. It resets presentation offsets in memory, evaluates the editable subdivision surface before the linear Armature modifier, exports one 53-bone rig and one skinned mesh per file, and disables animations. It does not rebuild or save over the source. Do not edit generated GLBs; `build_base.py` is the protected initial creation recipe, not the routine update path.

Verified with Blender 5.1.2 and Godot 4.6.3: +Z Blender up / -Y front maps to +Y Godot up / +Z model front; both imported rigs retain the same 53 names/parents and 53 skin binds, four weights per exported vertex, unit scales, ground at Y=0, and heights 1.80/1.70 m. No model-axis compensation rotation is needed. This corrects the earlier wording that conflated camera forward and model front; see [Godot model export conventions](https://docs.godotengine.org/en/4.4/tutorials/assets_pipeline/importing_3d_scenes/model_export_considerations.html).

Run `verify_import.gd`, then `Humanoid_Base_Test.tscn`; `capture_godot.gd -- --skin-probe` provides a temporary imported-skeleton deformation check. Source and exports remain in rest pose without Actions/NLA/animation clips. Linear skinning deliberately matches glTF; extreme shoulder/crouch compression is still rough and does not claim corrective-shape quality. See the asset README and review evidence for details. No Player integration belongs to this pass.

### Authorized BH_01 V2 POC (2026-09-12)

Hybrid presentation (2026-09-18) now uses two explicit scenes: `MainCharacter1POV.tscn` and `MainCharacter3POV.tscn`. The FP scene has only TORSO/ARMS mesh slots, its own skeleton/library/viewport, and real CyberBow art. `FirstPersonBodySource` reads the named regions, skin, joints and clips from the existing baked import at scene load, also in the editor; it does not save another mesh export or depend on generated GLB subresource IDs. Reload the scene after re-exporting BH01. The full-body scene inherits the unchanged V2 world setup. World Actions, `.blend`, capture/export and the pre-IK gameplay camera pipeline remain unchanged. See [Hybrid presentation scenes](HYBRID_PRESENTATION_SCENES.md) for routing, composition, toggles and remaining placeholder limitations. The earlier [V3 POC report](MAIN_CHARACTER_V3_HYBRID.md) is historical.

The later locomotion authoring pass adds explicit full-range `V2_EXTRA_ACTIONS`: Wallrun Left/Right and Run. Idle/Slide still capture frame 1 as one-second holds. Extra clips use Action start/end, scene FPS and `Action.use_cyclic`; the control rig and its interpolation are evaluated in Blender, then baked onto the same 54 runtime joints including the camera socket. See [V2 locomotion authoring](V2_LOCOMOTION_AUTHORING.md) for commands and the Run container.

Confirmed import limitations: keep `animation/remove_immutable_tracks=false`. Otherwise a track equal to rest can be removed from one clip and leave a previous clip's bone transform active (observed after Slide). `V2AnimationPostImport.gd` reads `.animations.json` for loop/hold and exact length. The exporter also embeds clip metadata in GLB animation extras so loop-only changes invalidate Godot's source hash. Bezier/constraint motion is sampled at 60 Hz or higher; constant boundaries use a 1 ms transition to survive Blender's close-key deduplication. These are baked runtime samples, not editable Blender control curves.

The subsequent V2 request explicitly authorizes isolated Player presentation integration. `Humanoid_Male_PoseLab.blend` remains the authoring source; `capture_v2.py` captures evaluated Idle/Slide into an isolated snapshot and `export_v2.py` creates `BH01_Male_V2.glb` with the original 53 deform bones plus the non-deforming `FP_CAMERA_SOCKET`, four visibility regions and eight-weight skinning. The socket is retained under `chest` with no vertex weights; all other source control/mechanism bones, cameras, guides and reference bow are excluded. Export-copy meshes must clear `hide_select` before selecting: copies inherit the PoseLab selection restriction and otherwise silently disappear from selection-only GLB export. Both glTF mesh count and Godot bone/pose checks are required. See [Main Character V2 POC](MAIN_CHARACTER_V2_POC.md) for regeneration, grip-axis calibration, toggles and runtime evidence. The Level_01 pipeline is unchanged.

V2 camera calibration version 2 travels alongside the GLB in `BH01_Male_V2.camera.json`: one shared WORLD/VIEWMODEL offset from the animated socket origin, expressed in skeleton axes, with effective FOV/sensor fit/source aspect. There is no runtime per-pose camera table. PoseLab `FP_Camera_Anchor` uses position-only Copy Location from the socket plus an editable local offset; socket rotation never controls the look direction. Runtime manually advances the animation, reads the fresh socket global pose, and positions the existing gameplay camera while preserving its look parents. VIEWMODEL data is retained without enabling legacy rendering. Reload the scene after capture/export. Perspective lens shift and inconsistent per-pose offsets are rejected until supported. When serializing a Godot `Transform3D` into `.tscn`, write **basis rows**, not `Basis.x/y/z` columns: the previous grip serializer transposed orientation while leaving origin correct. `verify_v2_camera.gd` checks actual runtime projections, bow transforms, transition frame order and fallback against captured source data. See the camera section of the V2 report for comparison frames and exact scope.

## Level_01 industrial art dressing (2026-09-18)

`70_LEVEL01_ART` in the canonical source owns the additive industrial dressing.
See `Docs/LEVEL01_ART_DRESSING.md` and `Tools/Environment/Level01Art/`.
The post-import hook resolves only `M_Level01_Art_*` names in Level_01 to the
external ORM resources in `Assets/Materials/Environment/Level01Art/`.
All Blender image paths remain relative under the Level_01 texture directory.
Runtime ambient VFX and local service lights remain in `ArtAtmosphere.tscn`.

Confirmed import limitation: textures first discovered through this custom
material resolver initially received 2D import defaults (`mipmaps/generate=false`).
After the first import, run `prepare_imports.py` and import again. It sets explicit
3D mipmaps and VRAM compression for the owned image copies, with normal-map mode
only on normal channels. Never edit generated `.ctex` or imported scene files.

Partitioning a `-col` box into material surfaces can reorder its collision
triangles. Verify geometric equivalence (planes, corners, winding and face area),
not raw triangle order. The unchanged source geometry and transforms are also
checked against the pre-pass snapshot. On Windows, Blender may serialize native
backslashes in otherwise valid `//` relative image paths; validation normalizes
separators before testing the root and resolving the file.

## V4 split authoring / runtime (20 September 2026)

See [SPLIT_PRESENTATION_V4.md](SPLIT_PRESENTATION_V4.md) for complete slots, export commands, scenes and validation. PoseLab now contains independent BH01_1POV / BH01_3POV scenes with compatible but separate control rigs, indexed Actions and fixed authoring cameras. Legacy source scene and unindexed Actions remain. setup_split.py is a one-time additive migration and refuses to replace existing indexed authoring. Normal iteration uses capture_split.py with explicit SPLIT_BRANCH, then export_split.py --branch 1POV/3POV. Separate generated GLBs contain ARMS only / full body respectively and separate clips. The proven export_v2.py baker accepts optional rig/body/scene/regions/Idle selection while preserving default V2 behavior. Keep immutable tracks and the animation metadata import hook.

Blender limitation confirmed: reassigning a copied object's parent resets matrix_parent_inverse. Restore it explicitly when remapping a bow/nock hierarchy; otherwise the bow shifts and right-hand IK changes despite identical Action keys. Camera-specific FP framing is exported in .presentation.json from fixed CAM_1POV, independently of animated sockets. Runtime FP wrist stabilization/bow scale remain separate presentation controls. Do not write split poses or exports back into the preserved V2 pipeline.

## Freestyle Geometry Nodes authoring lab (20 September 2026)

The separately authorized Blender-only POC lives in `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`. See [GN_LEVEL_AUTHORING_LAB.md](GN_LEVEL_AUTHORING_LAB.md) for the manual Source → native GN Output dependency, editable clipping Envelope, backup, controls, 20 automated checks and real Edit Mode UI evidence. This pass explicitly excludes Godot integration; existing Freestyle exports and the Level_01 direct `.blend` pipeline are unchanged. New lab collections are outside the current export whitelist.

Confirmed Blender 5.1 limitations: Mesh Boolean in INTERSECT mode takes both geometries through its enabled multi-input `Mesh` socket; `Mesh 1` is disabled. Manifold is substantially faster than Exact on this panel fixture but requires closed manifold volumes. Native E extrusion temporarily produces zero-area side faces at zero displacement; filter those in the procedural branch before building panels, never rewrite the manual Source. Envelope Margin uses approximate vertex-normal displacement, not a precise distance-field offset. Keep Envelope closed and Preview Quality low while editing; details and measured limits are in the lab report.

### Seeded Field + Cutter blockout experiment (20 September 2026)

The later Blender-only experiment adds `GN_LevelBlockout_Generator_v01` to the same Freestyle source. See [GN_LEVEL_BLOCKOUT_GENERATOR.md](GN_LEVEL_BLOCKOUT_GENERATOR.md). A single convex XY quad `LEVEL_FIELD` drives native seeded macro regions and metric-sized traversal geometry; closed `LEVEL_CUTTER` subtracts geometry while preserving the fixed origin floor. The old POC group and authoring meshes remain hidden; its preview is renamed `POC_GENERATED_OUTPUT`. The 207 original object fingerprints and 92 protected file hashes were preserved. This is an explicit user-authorized exception to normal Godot completion checks: no import/export or runtime changes were requested or performed.

Confirmed in Blender 5.1.2: sequential `links.new` insertion into Geometry to Instance's multi-input socket produced a reversed instance palette. Build the links in reverse category order and validate evaluated category IDs against the chosen module IDs; labels alone do not prove the mapping. For a slab extrusion, explicitly link the Offset vector and use Offset Scale 1; the earlier unlinked default-vector setup with Scale 0 produced zero thickness. Inspect actual evaluated bounds/volume. The current Field is a convex 2D domain, not a general polygon clipping system. Native Manifold evaluated this fixture in 16–31 ms, versus 1.03–1.19 s for Exact. Closed concave Cutter shape/topology changes and real Edit Mode Field/Cutter scaling were verified; open/self-intersecting volumes are outside the contract. Construction scripts must never be used to overwrite manual Field or Cutter edits.

### V02 volume blockout and authorized Godot preview (20 September 2026)

Current generation grammar is documented in [V02_GAMEPLAY_SPACE_CORRECTION.md](V02_GAMEPLAY_SPACE_CORRECTION.md): floating slabs and bridges, isolated movement walls, no automatic bearing posts, and sparse optional lower access flights. Volume, Cutter, controls, bands and spawn contract are preserved. The corrected Seed 17 snapshot has 2242 triangles; the 4718-triangle verification below records the preceding structural version. Prior review evidence remains intact.

See [GN_LEVEL_BLOCKOUT_V02.md](GN_LEVEL_BLOCKOUT_V02.md). The later V02 uses an editable XYZ box, stacked structural zones and one full-3D Cutter. The user subsequently authorized importing the current result with collisions. `Tools/Blender/LevelBlockoutV02/export_godot.py` exports the evaluated result to the separate `Level_Freestyle_01_GN_V02.glb`; `Scenes/Levels/Level_Freestyle_GN_V02.tscn` instances it alongside the canonical Player. The former Freestyle exports, main scene and Level_01 direct-import pipeline remain unchanged. The old Freestyle export button does not include V02.

The exporter uses a temporary scene, explicit `use_active_scene=True` plus selection filtering, and validates the GLB node whitelist. Selection filtering alone can export selected objects from other Blender scenes. Temporary Principled material copies carry the viewport graybox colors into glTF without altering source materials. Godot `-col` generates one static concave triangle collider from the final cut mesh. All 4718 triangles matched the rendered import with a maximum vertex difference of 0.080 mm; exact quantized dictionary equality is unsuitable at rounding boundaries. Godot imports glTF custom properties under node metadata `extras`.

Additional native-GN findings: a Random Value result is a field even with a constant ID; use a single-point Attribute Statistic reduction when a construction input needs one value. Empty Cutter geometry should explicitly bypass Boolean for stable unchanged output. API viewport changes need `region_3d.update()` before a screenshot. V02 Volume means world-axis AABB and must contain the fixed origin reserve; arbitrary concave clipping and full traversal/LOS solving are outside the current contract.

### V03 sequential flow course (20 September 2026)

The separate `GN_LevelBlockout_Generator_v03` / `LEVEL_FLOW_OUTPUT` adds a 15-section directed traversal chain to the same Freestyle source; V02 remains intact and hidden. See [FLOW_COURSE_V03.md](FLOW_COURSE_V03.md) for presets, section IDs, chunk saving and validation. Export only through `Tools/Blender/FlowCourseV03/export_godot.py` into its separate V03 GLB and lightweight `Level_Freestyle_GN_V03.tscn` wrapper. Fifteen independently selectable `-col` meshes retain exact triangle collision; a canonical grapple marker is bound by the existing runtime binder. Preview guides never become collision.

Confirmed limits: the current Player remains grounded on tested 35/45-degree descents, while 55/70-degree slopes act as airborne drop chutes with recovery. Headless display does not retain captured mouse mode for this aiming test; use a graphics-enabled fixture for real mouse-look + E grapple acquisition. Added corner catch pads have default values for attributes written inside the shared segment group: read movement metadata from an actual grammar face, not blindly from the first polygon. Section export re-centres geometry on its ENTRY and stores a relative EXIT; saved static chunk scenes were reloaded for verification.

## V06 current snapshot for human Freestyle coverage

The separately authorized V06 bridge is `Tools/Blender/GodotSnapshot/export_current.py`.
It freezes the current evaluated output into `Assets/Levels/Level_Freestyle_01/Generated/GN_Blockout_Current.glb` and matching JSON, using a temporary scene and removing all temporary data before saving the editable source. Current files overwrite in place; the generator and Proxy are not rebuilt.

`Scenes/Levels/Level_Freestyle_01.tscn` now uses a removable `GN_Blockout_Current` branch. Static concave collision comes from the imported mesh; canonical GrappleAnchor instances and passive human coverage use the manifest. The existing canonical Player and V4 presentation are preserved. The user explicitly approved the test spawn at Godot `(140, 0.05, 5.40)` because the previous origin spawn had no generated floor below it.

See `Docs/GN_TO_GODOT_QUICKSTART.md` for export, F6, F3 coverage, F1 reset and session logs. `Tools/Levels/GNSnapshot/verify.gd -- --coverage-check` is structural QA only; unreached analysis must wait for an explicit human-test-completed request. This does not change the canonical Level_01 direct `.blend` pipeline.

## Highrise100 standalone showcase (27 September 2026)

The separately authorized Highrise100 review export uses `Art/Environment/Highrise100/Highrise100.blend` as its untouched source and `Assets/Environment/Highrise100_Runtime/Highrise100.gltf` plus one binary and shared external PNGs as generated runtime assets. `Scenes/Environment/Highrise100_Showcase.tscn` arranges all 100 roots with no collisions or Player integration. This does not change Level_01's direct `.blend` workflow. See [HIGHRISE100_SHOWCASE.md](HIGHRISE100_SHOWCASE.md) for provenance, controls, material validation and measurements.

The ten-building subset confirmed that initial headless PNG import can retain 2D mipmap/compression defaults even when the glTF material slots are correct. `Tools/Environment/Highrise100/Runtime/prepare_texture_imports.gd` sets explicit 3D settings on owned PNG `.import` files before reimport; do not edit generated caches. Godot preserved ORM R/G/B and color/data sampling in all 43 textured recipes. Some source n-gons lacked exported tangents; Godot generated tangents for every imported surface without source geometry edits.
