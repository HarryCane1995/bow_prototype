"""Local authoring adapter; raster rules stay in the canonical Python generator."""
from dataclasses import asdict
from datetime import datetime, timezone
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from PIL import Image

HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent
ROOT = FACTORY.parents[2]
sys.path.insert(0, str(FACTORY))
from facade_factory import generate, write_material, VERSION, TEXTURES, MATERIALS
from facade_presets import PRESETS, PALETTES, get_preset
from facade_art_profiles import ART_CONTROLS, normalized_art
from surface_breakup import BREAKUP_CONTROLS, DETAIL_CHANNELS, PREVIEW_CHANNELS, normalized_breakup
from palette_mixer import normalized_palette, PRESETS as PALETTE_PRESETS, ROLES as PALETTE_ROLES, INFLUENCES as PALETTE_INFLUENCES, ROLE_WEIGHTS
from surface_factory import (TILE_PARAMETERS, CYLINDER_PARAMETERS, TILE_PRESETS, CYLINDER_PRESETS,
    SURFACE_PRESETS, surface_defaults, generate_surface, SurfaceCanvas)
from surface_archetypes import CATALOG
from material_library import authored_request

CHANNELS = ("albedo", "emission", "normal", "orm", "height")
PREVIEW_SIZE = [256, 512]
EXPORT_SIZES = [[512, 1024], [1024, 2048]]
MODE_PREVIEWS = {'UNIQUE_FACADE':[256,512], 'TILEABLE_SURFACE':[256,256], 'CYLINDER_WRAP':[256,512]}
MODE_EXPORTS = {'UNIQUE_FACADE':EXPORT_SIZES, 'TILEABLE_SURFACE':[[512,512],[1024,1024]], 'CYLINDER_WRAP':EXPORT_SIZES}
LEGACY_FINGERPRINT = 'b806a9a8c6a383229fd7acafad451af065ad352f5a616e9722139e4f39ea4f69'
BAKED_FINGERPRINT = '998af938452dcc1c428ffbb73e861a1d17bd40a00885edd128c8779ae490fc23'
BREAKUP_FINGERPRINT = '56cbda157ee9299d7705eced7dada5f94595b64ba3f3028c7e8dd49aa7734242'
PRE_LIBRARY_FINGERPRINT = 'f11e4a60c33c598c96d778c0e8efa409eb44a3f0b0e9ef8c70e4c974b995403a'
FINGERPRINT = hashlib.sha256(b"".join((FACTORY / f).read_bytes() for f in
    ("facade_factory.py", "facade_presets.py", "facade_stylizer.py", "facade_art_profiles.py",
     "facade_semantics.py", "surface_factory.py", "surface_breakup.py", "palette_mixer.py", "surface_archetypes.py", "material_library.py"))).hexdigest()
PARAMETERS = {
    "window_density": [0, 1, .01, "Window density", "primary"],
    "emission_density": [0, 1, .01, "Emission density", "primary"],
    "structural_width": [2, 32, .5, "Structural width", "primary"],
    "grime_amount": [0, 1, .01, "Grime amount", "primary"],
    "retro_strength": [0, 1, .01, "Retro strength", "primary"],
    "window_aspect": [.2, 3, .05, "Window aspect", "advanced"],
    "floor_height": [16, 60, 1, "Floor height", "advanced"],
    "service_floor_frequency": [0, 1, .01, "Service floors", "advanced"],
    "dark_floor_frequency": [0, 1, .01, "Dark floors", "advanced"],
    "panel_density": [0, 1, .01, "Panel density", "advanced"],
    "signage_density": [0, 1, .01, "Signage density", "advanced"],
    "macro_contrast": [0, 1, .01, "Macro contrast", "advanced"],
    "emission_strength": [0, 8, .05, "Emission strength", "material"],
}
STYLE = {
    "posterization": [4, 256, 1, "Posterization levels"],
    "dithering": [0, 1, .01, "Dithering"],
    "color_quantization": [8, 256, 1, "Palette color count"],
    "micro_contrast": [0, 1, .01, "Micro contrast"],
    "compression_artifacts": [0, 1, .01, "Block artifacts"],
    "pixel_noise": [0, 3, .05, "Pixel noise"],
    "edge_exaggeration": [0, 1, .01, "Edge exaggeration"],
    "baked_ao_strength": [0, 1, .01, "Baked AO strength"],
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalized_request(data, resolution=None):
    if not isinstance(data, dict):
        raise ValueError("Recipe must be an object")
    seed = data.get("seed", 99)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_147_483_647:
        raise ValueError("Seed must be an integer in 0..2147483647")
    mode=data.get('surface_mode','UNIQUE_FACADE')
    if mode not in MODE_PREVIEWS: raise ValueError('Unknown surface mode')
    schema=PARAMETERS if mode=='UNIQUE_FACADE' else TILE_PARAMETERS if mode=='TILEABLE_SURFACE' else CYLINDER_PARAMETERS
    params = data.get("parameters", {})
    style = data.get("style", {})
    for values, fields in ((params, schema), (style, STYLE)):
        if not isinstance(values, dict) or set(values) - set(fields):
            raise ValueError("Unknown recipe parameter")
        for key, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{key}: finite number required")
            if not fields[key][0] <= value <= fields[key][1]:
                raise ValueError(f"{key} out of range")
            if fields[key][2]==1 and int(value)!=value: raise ValueError(f'{key}: integer required')
    for field in ("posterization", "color_quantization"):
        if field in style and int(style[field]) != style[field]:
            raise ValueError(f"{field}: integer required")
    style = {k: int(v) if k in ("posterization", "color_quantization") else v for k, v in style.items()}
    preset_name = data.get("preset", "INDUSTRIAL_TOWER")
    if not isinstance(preset_name, str):
        raise ValueError("Preset must be a name")
    if mode!='UNIQUE_FACADE' and preset_name not in (TILE_PRESETS if mode=='TILEABLE_SURFACE' else CYLINDER_PRESETS):
        raise ValueError('Preset does not belong to surface mode')
    palette = data.get("palette", get_preset(preset_name).palette if mode=='UNIQUE_FACADE' else SURFACE_PRESETS[preset_name]['palette'])
    if palette not in PALETTES:
        raise ValueError("Unknown palette family")
    tile_mode=data.get('tile_mode','FULL_2D_TILE' if mode=='TILEABLE_SURFACE' else 'HORIZONTAL_WRAP_ONLY')
    if tile_mode not in ('FULL_2D_TILE','HORIZONTAL_WRAP_ONLY') and not (mode=='UNIQUE_FACADE' and tile_mode=='UNIQUE_SHEET'): raise ValueError('Unknown tile mode')
    if mode=='TILEABLE_SURFACE' and tile_mode!='FULL_2D_TILE': raise ValueError('Tileable surfaces require full 2D tiling')
    if mode=='UNIQUE_FACADE':
        preset = get_preset(preset_name, {**params, "palette": palette}, style)
        effective = asdict(preset)
        parameters={k:effective[k] for k in PARAMETERS}
    else:
        parameters={**surface_defaults(preset_name),**params}
        preset=SurfaceCanvas(preset_name,seed,parameters,palette,tile_mode,style).p
    effective = asdict(preset)
    size = resolution if resolution is not None else data.get("resolution", MODE_PREVIEWS[mode])
    if size not in [MODE_PREVIEWS[mode], *MODE_EXPORTS[mode]]:
        raise ValueError("Unsupported resolution")
    art=normalized_art(data.get('art',{'profile':'LEGACY' if mode=='UNIQUE_FACADE' else 'BOW_BASE'}))
    if mode!='UNIQUE_FACADE' and art['profile']=='LEGACY':
        raise ValueError('New surfaces use BOW_BASE; Legacy is only for original facades')
    recipe = dict(surface_mode=mode,tile_mode=tile_mode if mode!='UNIQUE_FACADE' else 'UNIQUE_SHEET',
                  preset=preset.name, seed=seed, palette=palette,art=art,
                  parameters=parameters, style=asdict(preset.style), resolution=size,
                  breakup=normalized_breakup(data.get('breakup'),mode))
    recipe['palette_mix']=normalized_palette(data.get('palette_mix'),palette,recipe['breakup']['mode']=='LAYERED')
    if recipe['palette_mix']['enabled'] and recipe['breakup']['mode']!='LAYERED':
        raise ValueError('Palette Mixer requires the Layered pipeline')
    return preset, recipe


def make_recipe(recipe, name="", outputs=None, hashes=None):
    defaults = asdict(get_preset(recipe['preset'])) if recipe['surface_mode']=='UNIQUE_FACADE' else surface_defaults(recipe['preset'])
    return dict(schema="bowprototype.facade", schema_version=4, generator_version=VERSION,
                generator_fingerprint=FINGERPRINT, created_at=now(), name=name, **recipe,
                overrides={k: v for k, v in recipe["parameters"].items() if v != defaults[k]},
                outputs=outputs or {}, sha256=hashes or {},
                color_spaces={"albedo": "sRGB", "emission": "sRGB", "normal": "linear data",
                              "orm": "linear data", "height": "linear data",
                              "detail_albedo": "linear multiplier / neutral 128", "detail_normal": "linear data", "weather_mask": "linear data", "emission_mask":"linear data"},
                palette_role_weights=ROLE_WEIGHTS,
                detail_contract=dict(source_strength='Raw reusable layers; recipe weights are applied in preview, not encoded in detail assets',
                    albedo='micro multiplier = 1 + (RGB - 128) / 128 * micro_grain',
                    weather_mask={'R':'macro tone/dirt (0.5 neutral)', 'G':'directional grime', 'B':'micro variation'},
                    base_normal='Structural height only in both export modes',
                    retro='Optional final treatment; baked only with BAKED export',
                    material='Generated ORMMaterial3D uses base maps; separate detail is opt-in'),
                orm_channels={"R": "AO", "G": "roughness", "B": "metallic"}, normal_convention="OpenGL")


def load_recipe(data):
    if not isinstance(data, dict) or data.get("schema") != "bowprototype.facade" or data.get("schema_version") not in (1,2,3,4):
        raise ValueError("Expected a WebLab .facade.json recipe (schema version 1..4)")
    legacy=data.get('schema_version')==1 and data.get('generator_version')=='0.1.0' and data.get('generator_fingerprint')==LEGACY_FINGERPRINT
    baked=data.get('schema_version')==2 and data.get('generator_version')=='0.2.0' and data.get('generator_fingerprint')==BAKED_FINGERPRINT
    breakup=data.get('schema_version')==3 and data.get('generator_version')=='0.3.0' and data.get('generator_fingerprint')==BREAKUP_FINGERPRINT
    pre_library=data.get('schema_version')==4 and data.get('generator_version')==VERSION and data.get('generator_fingerprint')==PRE_LIBRARY_FINGERPRINT
    if not (legacy or baked or breakup or pre_library) and (data.get("generator_version") != VERSION or data.get("generator_fingerprint") != FINGERPRINT):
        raise ValueError("This recipe uses a different generator revision; exact replay cannot be guaranteed")
    # All effective values must be present; never silently substitute evolving defaults.
    mode=data.get('surface_mode','UNIQUE_FACADE')
    fields=PARAMETERS if mode=='UNIQUE_FACADE' else TILE_PARAMETERS if mode=='TILEABLE_SURFACE' else CYLINDER_PARAMETERS
    if set(data.get("parameters", {})) != set(fields) or set(data.get("style", {})) != set(STYLE):
        raise ValueError("Recipe is missing effective parameters or stylizer settings")
    if legacy: data={**data,'surface_mode':'UNIQUE_FACADE','art':{'profile':'LEGACY'}}
    if legacy or baked: data={**data,'breakup':{'mode':'LEGACY_BAKED','export_mode':'BAKED'}}
    elif set(data.get('breakup',{})) != set(normalized_breakup()):
        raise ValueError('Recipe is missing effective breakup settings')
    if legacy or baked or breakup: data={**data,'palette_mix':{'enabled':False}}
    else:
        mixer=data.get('palette_mix',{})
        if pre_library:
            # Four additive controls at one reproduce the original binding.
            expected=set(normalized_palette())-{'accent_usage','colored_balance','structural_separation','orm_influence'}
            if set(mixer)!=expected:raise ValueError('Prior palette recipe is incomplete')
            mixer=normalized_palette(mixer);data={**data,'palette_mix':mixer}
        if set(mixer)!=set(normalized_palette()) or set(mixer.get('colors',{}))!=set(PALETTE_ROLES) or set(mixer.get('material_responses',{}))!=set(PALETTE_PRESETS['NEUTRAL_COLD']['material_responses']):
            raise ValueError('Recipe is missing effective semantic palette settings')
        if any(set(values)!={'roughness','metallic','ao_response'} for values in mixer['material_responses'].values()):
            raise ValueError('Recipe is missing effective material scalar responses')
    _, recipe = normalized_request(data)
    return recipe


def config():
    presets = []
    for name, p in PRESETS.items():
        _, recipe = normalized_request({"preset": name})
        ranges = {}
        # Preset-relative ranges keep random exploration inside each grammar.
        for key in ("window_density", "emission_density", "grime_amount", "retro_strength",
                    "panel_density", "service_floor_frequency", "dark_floor_frequency"):
            default = recipe["parameters"][key]
            spread = .10 if key.endswith("frequency") else .16
            ranges[key] = [round(max(0, default - spread), 3), round(min(1, default + spread), 3)]
        ranges["structural_width"] = [max(2, p.structural_width * .8), min(32, p.structural_width * 1.2)]
        presets.append({"name": name, "defaults": recipe, "random_ranges": ranges})
    for mode,family in [('TILEABLE_SURFACE',TILE_PRESETS),('CYLINDER_WRAP',CYLINDER_PRESETS)]:
        for name in family:
            _,recipe=normalized_request(authored_request(name) if name in CATALOG else {'surface_mode':mode,'preset':name})
            recipe['resolution']=MODE_PREVIEWS[mode]
            fields=TILE_PARAMETERS if mode=='TILEABLE_SURFACE' else CYLINDER_PARAMETERS
            ranges={k:[max(s[0],recipe['parameters'][k]-(s[1]-s[0])*.15),min(s[1],recipe['parameters'][k]+(s[1]-s[0])*.15)] for k,s in fields.items() if k!='tile_scale'}
            presets.append(dict(name=name,defaults=recipe,random_ranges=ranges))
    library=[dict(name=name,**item,thumbnail='/material-library/'+item['id']+'.webp') for name,item in CATALOG.items()]
    return dict(generator_version=VERSION, presets=presets, parameters=PARAMETERS, style=STYLE,material_library=library,
                art_controls=ART_CONTROLS,art_default=normalized_art({'profile':'BOW_BASE'}),breakup_controls=BREAKUP_CONTROLS,
                palette_presets={name:normalized_palette({'preset':name,'enabled':True}) for name in PALETTE_PRESETS},
                palette_roles=list(PALETTE_ROLES),palette_influences=PALETTE_INFLUENCES,
                surface_parameters=TILE_PARAMETERS,cylinder_parameters=CYLINDER_PARAMETERS,
                preview_resolutions=MODE_PREVIEWS,export_resolutions_by_mode=MODE_EXPORTS,
                palettes=[{"id": "cold", "label": "Neutral cold"}, {"id": "industrial", "label": "Industrial green"},
                          {"id": "concrete", "label": "Dirty concrete"}], preview_resolution=PREVIEW_SIZE,
                export_resolutions=EXPORT_SIZES, export_directory=TEXTURES.relative_to(ROOT).as_posix(),
                material_directory=(MATERIALS / "Generated").relative_to(ROOT).as_posix())


class Lab:
    def __init__(self, cache=None, favorites=None, exports=None, materials=None):
        self.cache = Path(cache or HERE / ".cache")
        self.favorites = Path(favorites or HERE / "favorites")
        self.exports = Path(exports or TEXTURES)
        self.materials = Path(materials or MATERIALS / "Generated")
        for path in (self.cache, self.favorites):
            path.mkdir(parents=True, exist_ok=True)
        self.generation_lock = threading.Lock()
        self.export_lock = threading.Lock()

    def preview(self, data):
        start = time.perf_counter()
        mode=data.get('surface_mode','UNIQUE_FACADE')
        preset, recipe = normalized_request(data, MODE_PREVIEWS.get(mode))
        key = hashlib.sha256(json.dumps([FINGERPRINT, recipe], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        folder = self.cache / key
        with self.generation_lock:
            cached = (folder / "result.json").is_file()
            if not cached:
                # Fully generate in a private directory; clients never see partial maps.
                with tempfile.TemporaryDirectory(prefix="stage_", dir=self.cache) as tmp:
                    result = render_recipe(preset,recipe,Path(tmp))
                    metadata=json.loads((Path(tmp)/f'{result["stem"]}.json').read_text())
                    for channel in result['sha256']:
                        (Path(tmp) / f'{result["stem"]}_{channel}.png').rename(Path(tmp) / f"{channel}.png")
                    payload = dict(key=key, recipe=recipe, sha256=result["sha256"],
                                   seam_qa=result.get('seam_qa'),art_statistics=metadata.get('art_statistics',{}),
                                   structure_hash=metadata.get('structure_hash'),
                                   generation_ms=round((time.perf_counter() - start) * 1000, 1),
                                   maps={c: f"/cache/{key}/{c}.png" for c in result['sha256'] if c not in PREVIEW_CHANNELS},
                                   preview_maps={c.removeprefix('preview_'):f"/cache/{key}/{c}.png" for c in PREVIEW_CHANNELS if c in result['sha256']})
                    (Path(tmp) / "result.json").write_text(json.dumps(payload), encoding="utf-8")
                    shutil.copytree(tmp, folder)
            payload = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        return {**payload, "cached": cached, "elapsed_ms": round((time.perf_counter() - start) * 1000, 1)}

    def favorite(self, data):
        # Flat recipes remain accepted for older clients. The image is transport-only;
        # the persisted recipe contains a relative filename, never a data URL.
        if not isinstance(data, dict):
            raise ValueError('Favorite must be an object')
        _, recipe = normalized_request(data.get('recipe', data))
        thumbnail = None
        if 'thumbnail_data_url' in data:
            encoded = data['thumbnail_data_url']
            if not isinstance(encoded, str) or len(encoded) > 250_000:
                raise ValueError('Thumbnail must be a small PNG or WebP image')
            match = re.fullmatch(r'data:image/(?:webp|png);base64,([A-Za-z0-9+/=]+)', encoded)
            if not match:
                raise ValueError('Invalid thumbnail image')
            try:
                with Image.open(io.BytesIO(base64.b64decode(match[1], validate=True))) as image:
                    if image.size != (256, 160) or image.format not in ('PNG', 'WEBP'):
                        raise ValueError('Thumbnail must be 256 × 160 PNG or WebP')
                    output = io.BytesIO()
                    image.convert('RGB').save(output, format='WEBP', quality=88, method=4)
                    thumbnail = output.getvalue()
            except (OSError, SyntaxError) as exc:
                raise ValueError('Invalid thumbnail image') from exc
        label = f'{recipe["preset"].lower()}_{recipe["seed"]}_{uuid.uuid4().hex[:8]}'
        doc = make_recipe(recipe, label)
        created = []
        try:
            if thumbnail is not None:
                doc['thumbnail'] = f'{label}.thumb.webp'
                path = self.favorites / doc['thumbnail']
                with path.open('xb') as handle:
                    created.append(path)
                    handle.write(thumbnail)
            path = self.favorites / f'{label}.facade.json'
            with path.open('x', encoding='utf-8') as handle:
                created.append(path)
                json.dump(doc, handle, indent=2)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        return {"id": label, "recipe": doc}

    def thumbnail_path(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9_-]{1,100}\.thumb\.webp', name):
            return None
        path = self.favorites / name
        return path if path.is_file() and not path.is_symlink() else None

    def list_favorites(self):
        entries = []
        for path in sorted(self.favorites.glob("*.facade.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(doc, dict):
                    continue
                thumb = self.thumbnail_path(doc.get('thumbnail'))
                entries.append({"id": path.name.removesuffix(".facade.json"), "recipe": doc,
                                "thumbnail_url": f'/favorites/{thumb.name}' if thumb else None})
            except (ValueError, OSError):
                continue
        return entries

    def export(self, data):
        name = data.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", name):
            raise ValueError("Name: 1–64 ASCII letters, digits, _ or -; start with a letter")
        if name.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}:
            raise ValueError("This name is reserved by Windows")
        preset, recipe = normalized_request(data)
        if recipe["resolution"] not in MODE_EXPORTS[recipe['surface_mode']]:
            raise ValueError("Production export: 512×1024 or 1024×2048")
        with_material = data.get("godot_material", True)
        if not isinstance(with_material, bool):
            raise ValueError("godot_material must be boolean")
        start = time.perf_counter()
        with self.export_lock:
            self.exports.mkdir(parents=True, exist_ok=True)
            self.materials.mkdir(parents=True, exist_ok=True)
            chosen = name
            revision = 1
            def occupied(candidate):
                # Include legacy metadata/material locations in collision detection.
                return (any(self.exports.glob(candidate + "_*")) or any(self.exports.glob(candidate + ".*"))
                        or (self.materials / f"{candidate}.tres").exists() or (MATERIALS / f"{candidate}.tres").exists())
            while occupied(chosen):
                revision += 1
                chosen = f"{name}_r{revision:02}"
            created = []
            with tempfile.TemporaryDirectory(prefix="export_", dir=self.cache) as tmp:
                stage = Path(tmp)
                result = render_recipe(preset,recipe,stage)
                channels=(*CHANNELS, *DETAIL_CHANNELS) if recipe['breakup']['mode']=='LAYERED' else CHANNELS
                if 'emission_mask' in result['sha256']: channels=(*channels,'emission_mask')
                outputs = {c: f"{chosen}_{c}.png" for c in channels}
                doc = make_recipe(recipe, chosen, outputs, {c:result['sha256'][c] for c in channels})
                doc["material"] = (self.materials / f"{chosen}.tres").relative_to(ROOT).as_posix() if with_material else None
                doc["canonical_metadata"] = json.loads((stage / f'{result["stem"]}.json').read_text(encoding="utf-8"))
                (stage / "recipe.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
                if with_material:
                    write_material(stage / "material.tres", chosen, self.exports, preset)
                    if recipe['surface_mode']!='UNIQUE_FACADE':
                        target=stage/'material.tres'; text=target.read_text()
                        scale=recipe['parameters'].get('tile_scale',1)
                        text=text.replace('texture_repeat = false','texture_repeat = true').replace('uv1_scale = Vector3(1, 1, 1)',f'uv1_scale = Vector3({scale}, {scale}, 1)')
                        target.write_text(text,encoding='utf-8')
                staged = [(stage / f'{result["stem"]}_{c}.png', self.exports / outputs[c]) for c in channels]
                if recipe['surface_mode']!='UNIQUE_FACADE':
                    for extra in ('preview','tiled_preview','seam_debug'):
                        filename=f'{chosen}_{extra}.png'
                        doc['outputs'][extra]=filename
                        staged.append((stage/f'{result["stem"]}_{extra}.png',self.exports/filename))
                    (stage/'recipe.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
                if with_material:
                    staged.append((stage / "material.tres", self.materials / f"{chosen}.tres"))
                # Recipe published last is the set's completion marker. Exclusive writes
                # protect even against another local program racing this server.
                staged.append((stage / "recipe.json", self.exports / f"{chosen}.facade.json"))
                try:
                    for source, target in staged:
                        with target.open("xb") as handle:
                            created.append(target)
                            handle.write(source.read_bytes())
                except Exception:
                    for path in created:
                        path.unlink(missing_ok=True)
                    raise
        return dict(name=chosen, requested_name=name, revisioned=chosen != name, recipe=doc,
                    files=[p.relative_to(ROOT).as_posix() for p in created],
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 1))


def render_recipe(preset,recipe,output):
    if recipe['surface_mode']=='UNIQUE_FACADE':
        return generate(preset,recipe['seed'],*recipe['resolution'],output,None,art=recipe['art'],breakup=recipe['breakup'],palette_mix=recipe['palette_mix'])
    return generate_surface(recipe['preset'],recipe['seed'],*recipe['resolution'],output,
        parameters=recipe['parameters'],art=recipe['art'],palette=recipe['palette'],
        tile_mode=recipe['tile_mode'],style=recipe['style'],breakup=recipe['breakup'],palette_mix=recipe['palette_mix'])
