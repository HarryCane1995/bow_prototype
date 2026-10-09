# Surface Factory 0.4 — Semantic Palette Mixer

`STRUCTURE → MATERIAL CLASSES → PALETTE MIX → WEATHERING / DETAIL → RETRO STYLIZER`

[Open INDUSTRIAL_FLOOR seed 99, A/B/C](http://127.0.0.1:8765/?mode=TILEABLE_SURFACE&preset=INDUSTRIAL_FLOOR&compare=palette).
Three previews share the structural recipe, zero decorative weights, framing and
UVs. A = Neutral Cold, B = Industrial Green, C = restrained Warning Orange.
The panel verifies normal and height SHA-256 before showing the comparison.
EDIT / EXPORT selects a complete variant for further editing or export.

## Palette controls

Eight semantic slots each have a color picker, editable hex value and lock:
BASE, SECONDARY, DARK, ACCENT, GLASS, EMISSION_PRIMARY, EMISSION_SECONDARY,
GRIME_TINT. RANDOMIZE PALETTE samples a restrained coherent hue family and
preserves locked colors. It does not randomize the structural seed. RESET PALETTE
restores the selected palette's colors, influences, scalar responses and unlocks
all slots. An explicit MIXER ON switch preserves access to the old material color.

The four independent influences are albedo palette, emission palette, weather
tint and material variation. Material variation adds a small constant finish
offset per module; it does not remove authored shading when set to zero.

Presets: NEUTRAL_COLD, INDUSTRIAL_GREEN, DIRTY_CONCRETE, CORPORATE_CYAN,
WARNING_ORANGE, OXIDIZED_GREEN, COLD_MONO, BLACK_RED_TECH. Existing cold,
industrial and concrete source palette families remain available with Mixer off.
Changing the semantic palette never changes that structural source palette.

## Semantic binding

| Class | Allowed roles / weights | Treatment |
|---|---|---|
| PAINTED_METAL | BASE .76 / SECONDARY .20 / ACCENT .04 | Stable module-based role selection |
| RAW_METAL | DARK .15 / BASE .85 | Strong desaturation, metallic scalar retained |
| GLASS | GLASS .92 / BASE .08 | Glass roughness; original reflections and value retained |
| CONCRETE | BASE .65 / SECONDARY .35 | Partial desaturation, high roughness |
| VENT | DARK 1 | Existing louver relief and shading |
| RECESSED_VOID | DARK 1 | Existing depth contrast |
| SIGNAGE / painted hazard marks | ACCENT 1 | Dedicated sidecar mask |
| EMISSIVE | PRIMARY / SECONDARY | Existing cool/warm emission roles; no new lights |

The module selection uses existing semantic finish IDs, not the architecture RNG.
Palette RGB is multiplied by the existing material-relative value. Authored panel
variation, edges, three seam-depth classes and markings survive. Deep recesses
bind DARK; normal/subtle joins retain their relative depth against BASE. Raw
metal and concrete do not acquire saturated paint-like colors.

Emission keeps its source mask/intensity, with PRIMARY and SECONDARY following
existing emissive annotations. A recipe may contain only one class of light.
The industrial tower seed 99 contains both, used in QA. Emission strength remains
the existing separate material parameter. Palette-enabled exports also include
`*_emission_mask.png`, a scalar source-intensity map (zero remains unlit), so the
mask remains available even when a user chooses black for a light color.

ORM receives only scalar roughness, metallic and optional AO response. Each
palette carries effective responses for six material classes plus ACCENT_PAINT.
RGB swatch edits alone do not change ORM. Scalar responses are preset/recipe
settings; the current UI does not add a second scalar material editor.

GRIME_TINT is applied only during optional weathering. With weather tint zero,
dirt still attenuates value and changes roughness but adds no chromatic tint.
At one it adopts the selected grime hue. Weather masks and both detail source
maps remain byte-identical across palette edits. Retro processing remains last.

## Persistence and compatibility

Schema 4 `.facade.json` stores `palette_mix`: preset, all eight effective colors,
locks, four influences, all material scalar responses, enabled state and version.
Reload requires complete effective settings; it does not invent missing scalar
responses. Existing schema 1/2/3 recipes migrate with Mixer off and preserve their
original image hashes, including the user's `tech_wall_627708735` export.

Layered mode is required for the new pipeline order. Enabling Mixer switches to
Layered; selecting the old Legacy baked renderer turns Mixer off. No original
grammar, structural RNG namespace, periodic rasterization or normal generator
was changed. Semantic annotations are sidecars only.

## Exports, QA and files

Three production sets, 1024×1024, are saved as `floor_99_palette_A`,
`floor_99_palette_B`, `floor_99_palette_C` under
`Assets/Textures/Levels/Level_01/FacadeFactory/` with matching `.facade.json`.
Generated ORMMaterial3D files are in
`Assets/Materials/Environment/FacadeFactory/Generated/`.
Each has five base maps, three separate detail source maps, emission mask and
three review PNGs. Standard `.tres` still binds base maps only; optional detail
requires an explicit consuming detail material, as documented in
[SURFACE_BREAKUP.md](SURFACE_BREAKUP.md).

`qa_palette.py` verifies all 18 structural presets, eight palettes, normal/height
invariance, unchanged weather masks, role-specific color edits, scalar ORM
channels, emission mask/intensity, weather tint, locked randomization, favorites
and full-resolution export/reload. Evidence is in `review/palette/qa.json`,
`browser_qa.json`, `exports.json`, `ABC.png` and `handoff.json`. The new sets also
load in an isolated Godot project using their original resource paths.

New files: `../palette_mixer.py`, `web/palette_controls.js`, `qa_palette.py`,
`verify_palette.gd`, this guide and review evidence.
Updated: `../facade_semantics.py`, `../facade_factory.py`, `../surface_factory.py`,
`../surface_breakup.py`, `lab_backend.py`, `server.py`, `web/app.js`,
`web/controls.js`, `web/facade_viewer.js`, `web/index.html`, `web/styles.css`,
`qa_breakup.py`, docs and `.gitignore`.

This tool pass does not change gameplay. The separately requested Level_01 floor
assignment was handled by the floor subagent; see
`.godot/level01-floor/final_validation.json` and `Docs/blender_pipeline.md`.
