# Industrial material library — autonomous art pass

The pass adds **50 authored structural recipes** to the existing Surface Factory:
12 wall/panel, 12 floor/walkway, 6 ceiling, 10 cylindrical wraps and 10 specialized
skins. They are separate constructions, not fifty seed variations. The original
six facade and twelve surface presets remain available.

## Open and use

- WebLab: expand **INDUSTRIAL LIBRARY · 50 RECIPES** in the surface editor. Filter
  by family, choose a thumbnail, then use existing seed, parameter randomization,
  A/B pin, favorite, load recipe and export controls.
- Canonical replay recipes: `Tools/Art/Library/materials/*.facade.json`.
- Runtime assets: `Assets/ProceduralArt/Materials/<id>/material.tres` and its five
  PNG maps. `manifest.json` lists every exact resource and source recipe.
- Review: `Tools/Art/ArtPass/review/materials_catalog_50.jpg`,
  `materials_best_12.jpg`, `materials_tiles_4.jpg`, `materials_wraps_4.jpg`.
- Regenerate all: `python Tools/Art/FacadeFactory/build_material_library.py`.
  Production PNG bytes are copied from the canonical renderer; replay retains
  their SHA-256. Batch PNGs use 512×512, wraps 512×1024. A preview is 192² WebP.

The five runtime channels are albedo and emission (sRGB), normal, ORM, height
(linear data). ORM is R=ambient occlusion, G=roughness, B=metallic. Normals use
OpenGL convention. The supplied repeat-enabled `ORMMaterial3D` uses four texture
resources; height is supplied for tooling and does not imply runtime displacement.

## Style and reference use

The local PureRef board `Art/Environment/BOW_ENVIRONMENT_DNA` was used for
construction and visual language: quiet large planes, directional services,
serviceable hatches, practical isolated lamps, neutral coatings and local warning
paint. Its overview and working grammar were inspected. Individual recipe records
name the board IDs that inspired their construction. Reference pixels are never
sampled, copied, embedded or shipped as production textures.

The new recipes are implemented in `surface_archetypes.py`, and the authored
palette/finish defaults are in `material_library.py`. Assemblies use the same
semantic material buffers, toroidal drawing, physical channels and export adapter
as the original generator. Grammar and finishing RNG remain independent.

## Controls

Structure remains separate from finish: panel/module scale, grout, seam contrast,
module density, ring density, vertical seams, hatch density and emission bands.
Some motifs have intentional fixed construction dimensions; a scale slider can
change their surrounding panelization without resizing the central instrument.

Layered finish retains separate **macro variation, grime, micro grain and retro
artifacts**. The library defaults are restrained: grime 0.14 (floors 0.22), micro
grain 0.025, macro variation 0.18 and retro artifacts off. CLEAN BASE sets all four
layer strengths to zero. Global art settings retain outline strength, material
variation, detail contrast, saturation and baked-lighting strength.

Palette controls now include:

| Control | Effect |
| --- | --- |
| Albedo palette influence | Blends semantic color binding against authored color |
| Emission palette influence | Changes emission hue while retaining intensity mask |
| Weather tint influence | Colors existing grime without changing its mask |
| Material variation influence | Controls independent module finish color variance |
| Accent color usage | Blends marked accents and accent modules toward base color |
| Neutral to colored balance | Desaturates the palette contribution toward luminance |
| Structural color separation | Blends secondary module color toward base color |
| Palette material response (ORM) | Blends material-class scalar responses, never RGB tint |

Normal and height never receive palette color. Grime and micro overlays do not
modify the structural normal or height. BAKED library output includes finish in
albedo/ORM; WebLab can switch to SEPARATE and export raw reusable detail layers.
The compact shipped batch omits redundant detail maps because they regenerate
from each complete recipe. The palette response slider uses material masks and
roughness/metallic/AO settings rather than a colored normal or colored ORM texture.

## Validation and limits

`materials_qa.json` records every recipe's round-trip, all five map seam deltas,
normal-vector error, distinct structure hashes and five representative replay /
seed / palette / clean-layer checks. All tiled surfaces close X+Y; wraps close X.
Top and bottom of ordinary wraps intentionally have coupling bands. WebLab also
supports FULL_2D_TILE for wraps. Edge equality is a bounded texture test; it does
not mean every arbitrary cropped UV island has an invisible seam.

Existing `WebLab/qa_surfaces.py` and `qa_palette.py` exercise canonical export,
favorites, old facade baselines, v1 replay and semantic channel isolation. The
immediately prior version-4 palette fingerprint is explicitly supported by adding
the four new controls at their identity value, 1. Unknown generator revisions
remain rejected rather than silently changing a recipe.

Godot loading/runtime evidence belongs to the shared ArtPass review report. The
contact sheets are procedural texture and cylinder projections, not claims of a
completed level application. Perforation/grilles are opaque diffuse/normal skins;
they do not cut holes in geometry. Deep braces/conduits remain shallow shading and
must become meshes when silhouette or parallax matters. No level, player,
character, Blender source or gameplay behavior is changed by this material pass.

## Storage discipline

Batch checks free space before each recipe. Below 25 GiB it stays at bounded 512px
production resolution; below 15 GiB it stops. It keeps one temporary generation
directory and removes that directory on completion. No frame sequences, reference
copies or per-seed duplicates are retained. It replaces only its own manifest and
the named generated library outputs; it never removes pre-existing project assets.
