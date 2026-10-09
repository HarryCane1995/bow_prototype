# Surface Factory 0.3 — separate surface breakup

0.4 inserts [Semantic Palette Mixer](PALETTE_MIXER.md) between material and
breakup. Schema 3 recipes retain exact output with the mixer disabled.

## Review

[INDUSTRIAL_FLOOR · seed 99 · A/B](http://127.0.0.1:8765/?mode=TILEABLE_SURFACE&preset=INDUSTRIAL_FLOOR&compare=breakup)

The link prepares A = original 0.2 baked renderer and B = clean material,
all four decorative weights zero, separate export selected. SHOW A / SHOW B
preserves the camera, UVs, layout and seed. The raw reusable detail sources are
available in the map thumbnails even when B is clean.

## Pipeline and controls

`STRUCTURE → MATERIAL → OPTIONAL WEATHERING / DETAIL`

Structure generation and its RNG namespaces are unchanged. Material assigns the
six semantic classes, three seam classes, class-specific roughness/metallic and
edge response. It retains authored markings, bolts, panel finish and real relief.
It contains no random per-pixel breakup or cloudy variation.

SURFACE BREAKUP controls are independent of the structural seed and one another:

| Layer | Treatment | Close-surface default |
|---|---|---|
| Macro Variation | One slow tone cycle across the sheet; wavelength spans multiple panels | 0.35 |
| Grime | Ledge-origin vertical streaks and light broad deposits; no height displacement | 0.25 |
| Micro Grain | Weak material-sensitive albedo/roughness grain and optional detail normal | 0.12 |
| Retro Artifacts | Optional final pixel noise, block artifacts, dither and color quantization | 0.00 |

CLEAN BASE temporarily sets these four weights to zero. RESTORE LAYERS returns
the saved weights. Editing a layer after cleaning starts a new manual setting.
This temporary restore buffer is UI state; the four effective values are saved
in the recipe. SHOW OPTIONAL LAYERS toggles composed versus exported base maps
without changing the recipe. In baked export mode, the base already has decoration.

Main NORMAL always comes from structural height. Micro normal is composed only
in the optional WebGL preview; it never contaminates the exported main normal,
even under BAKE DETAIL INTO BASE. Debug NORMAL shows that structural map.

Legacy / original baked noise preserves the previous algorithm exactly. Old
surface wear/macro variation controls remain available there; their spatial
effects move to the new breakup controls in layered mode. UNIQUE_FACADE defaults
to Legacy for backward compatibility; Layered is selectable in all three modes.
The original facade wear pass still consumes its original RNG in layered mode,
but skips painting its decorative overlay. Layout and later random choices stay
unchanged. Six facade presets, twelve surface presets and CLI batch stay intact.

## Export contract

Both options export albedo, emission, structural normal, ORM, height, recipe and
optional generated ORMMaterial3D. Surface modes also export preview, tiled preview
and seam debug PNGs.

* **EXPORT DETAIL SEPARATELY**: base albedo / ORM contain only material. Layer
  weights affect the live composed preview, not those base maps.
* **BAKE DETAIL INTO BASE**: current macro, grime, micro color/roughness and retro
  weights are baked into albedo / ORM. Main normal stays structural.

Layered exports additionally include these three maps under either option, so
micro normal remains available even when color detail is baked:

| File | Encoding / use |
|---|---|
| `*_detail_albedo.png` | Linear multiplier data, neutral byte 128. Micro-only. `1 + (RGB - 128) / 128 * micro_grain`. Do not import as sRGB color. |
| `*_detail_normal.png` | Raw optional micro normal, tangent-space OpenGL. Scale XY by the micro weight before normal blending. |
| `*_weather_mask.png` | Linear RGB: R = broad tone/dirt (0.5 neutral), G = directional grime, B = micro variation (0.5 neutral). |

These are **unweighted reusable source layers**, not a flattened image of the
currently visible decoration. CLEAN BASE therefore exports useful maps rather
than blank maps. Use recipe weights at runtime; zero means disabled. Macro uses
`(R*2-1)*0.14*macro_variation`, grime attenuation uses `G*0.40*grime`; the canonical
renderer also applies per-material gain, small grime tint and roughness response.
The detail-albedo map and weather-mask B describe the same micro signal: do not
apply both. Retro treatment stays an optional final bake; its settings are in the
recipe, not packed into the weather mask.

Generated `.tres` binds base albedo/normal/ORM/emission only. Separate detail needs
an explicit detail-capable material/shader in a consuming project. Nothing is
automatically attached to gameplay materials. Preview composition remains Python
canonical; Three.js only displays generated base or composed maps.

Recipes use schema 3 and retain full breakup settings. Known schema 1 (0.1) and
schema 2 (0.2) recipes migrate into exact Legacy replay. Unknown fingerprints
still fail closed instead of silently changing an old recipe.

## Files and QA

Production A/B sets (1024×1024):

* `Assets/Textures/Levels/Level_01/FacadeFactory/floor_99_A_legacy_baked_*`
* `Assets/Textures/Levels/Level_01/FacadeFactory/floor_99_B_clean_separate_*`
* matching `.facade.json` files in the same directory;
* `Assets/Materials/Environment/FacadeFactory/Generated/floor_99_A_legacy_baked.tres`
  and `floor_99_B_clean_separate.tres`.

`qa_breakup.py` checks all 18 old baked outputs byte-for-byte, structure/main
normal invariance across all presets, independent layers, low-frequency macro
energy, all output/preview seam boundaries, both export strategies, all three
surface modes, favorites, production recipe replay, collision protection and old
0.1/0.2 recipe compatibility. Run from the repository root:

```powershell
python Tools/Art/FacadeFactory/WebLab/qa_breakup.py
python Tools/Art/FacadeFactory/WebLab/qa_backend.py
```

Evidence: `review/breakup/qa.json`, `browser_qa.json`, A/B screenshots, Godot logs
and `handoff.json`. The Godot check uses an isolated project containing byte-exact
copies of the generated files at their production `res://` paths.

Changed implementation: `../surface_breakup.py` (new), `../facade_factory.py`,
`../surface_factory.py`, `lab_backend.py`, `server.py`, `web/index.html`,
`web/app.js`, `web/controls.js`, `web/facade_viewer.js`, `web/styles.css`.
Added QA: `capture_breakup_baseline.py`, `qa_breakup.py`, `verify_breakup.gd`.
Updated docs/housekeeping: this guide, `README.md`, `SURFACE_FACTORY.md`, `.gitignore`.

Limitations: deterministic raster detail, not scanned material; macro scale is
relative to the texture sheet rather than world meters. Micro grain density is
resolution-dependent and separately tileable. Old authored anti-slip marks and
panel joins are real structural detail and deliberately remain in CLEAN BASE.
The exported standard Godot material does not enable optional detail by itself.
