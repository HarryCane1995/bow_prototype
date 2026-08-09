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

## Coordinate, transform, and naming conventions

- Author in Blender meters: one Blender unit is one meter.
- Blender authoring axes are `+Z` up and `-Y` forward. Godot uses `+Y` up and `-Z` forward; the direct importer/glTF conversion owns the axis conversion. Do not pre-rotate the entire map to compensate.
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
