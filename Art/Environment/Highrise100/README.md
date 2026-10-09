# Highrise100 — exploratory building library

This checkpoint preserves an editable Blender library for kitbashing: 100
asset-marked building collections across 20 procedural families. It is an
exploratory art tool, with no collision, interiors, LOD or gameplay integration.

## Preserved sources

- [Highrise100.blend](Highrise100.blend): the saved editable source. Append
  `HRxxx` collections through Blender's File → Append workflow. Each building
  root is at its local base origin; presentation scenes are separate.
- [manifest.json](manifest.json) and `Cards/HRxxx.json`: the 100 building
  definitions, parameters, roles, bounds and material assignments.
- [materials.json](materials.json), `Recipes/` and `Textures/`: 76 material
  recipe records and 380 PNG maps. Original maps and derived `*_uv` maps are
  retained so the preparation/rebuild chain has its inputs. Not every recipe
  or channel is used by the currently saved source.
- [ContactSheet_All.jpg](ContactSheet_All.jpg): one representative silhouette
  sheet. It comes from the earlier exploration pass; geometry was preserved
  by the later UV/material pass. It is not a current material-quality gallery.
- [Generator tools](../../../Tools/Environment/Highrise100/): architecture
  definitions, material preparation, UV rules and optional review utilities.

The saved source was inspected read-only in Blender 5.1.2 for the
2026-10-10 checkpoint: all 172 external FILE image datablocks resolve through
relative `//Textures/...` paths; no missing texture or linked-library
references were found. The source SHA-256 was unchanged by inspection:
`3d998fac3a85743b6bf052f6d366496f080026f8b7e38b3c27d1ee2e69105dd6`.
Keep the source beside its `Textures/` directory. `.gdignore` prevents importing
this authoring collection as a duplicate gameplay asset.

## Runtime showcase

Open [Highrise100_Showcase.tscn](../../../Scenes/Environment/Highrise100_Showcase.tscn)
in Godot 4.6.3 Mono and run the current scene (F6). The independent viewer uses
[Highrise100_Runtime](../../../Assets/Environment/Highrise100_Runtime/), a glTF
with one binary and 172 shared PNG maps. Those runtime copies are required by
the glTF's own relative paths. The viewer has Night and Neutral QA lighting;
WASD/mouse fly, E/Q move vertically, F1 switches lighting and Home resets the
view. It does not replace the project's playable main scene.

[HIGHRISE100_SHOWCASE.md](../../../Docs/HIGHRISE100_SHOWCASE.md) records the dated
2026-09-27 technical pass and its limits. Its references to local evidence are
historical; the checkpoint does not include the full evidence archive.

## Rebuild and local evidence

Blender 5.1.2 and Python 3.11 with
[FacadeFactory requirements](../../../Tools/Art/FacadeFactory/requirements.txt)
are the recorded toolchain. The procedural preparation order is `prepare.py`,
`prepare_signs.py`, `prepare_uv_tiles.py`, then Blender `build_library.py`.
A full rebuild replaces the procedural library and can overwrite manual edits;
opening, appending or using the saved library does not require a rebuild.

Downloaded architecture/game references and the PureRef image board are not
required to open the library, generate maps or run the showcase. Their image
pixels are not used as material inputs and are excluded from this checkpoint.

Preview galleries, contact-sheet variants, temporary renders, candidate/subset
Blender copies, backups, sanity projects, cache and the large historical QA
archives remain local. Consequently, old preview paths retained in manifests
and historical review helpers may point to files absent after clone. This
checkpoint preserves source, definitions, materials and the runtime showcase;
it does not claim to preserve the complete historical image gallery.
