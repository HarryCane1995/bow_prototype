"""Mesh explosion authoring contract. Geometry and materials remain separate."""
import copy
import math
import re
from mesh_archetypes import EFFECTS, SHAPE_CONTROLS, defaults as effect_defaults

VERSION = '0.2.0'
CONTROLS = {
    'overall_scale': [.25, 4, .05, 1, 'Overall scale', 'GLOBAL'],
    'duration': [.5, 6, .05, 2.4, 'Duration · seconds', 'GLOBAL'],
    'core_size': [.1, 2, .05, .65, 'Core size', 'CORE'],
    'core_brightness': [0, 5, .1, 1.6, 'Core brightness', 'CORE'],
    'core_lifetime': [.05, 1, .01, .23, 'Core lifetime · seconds', 'CORE'],
    'petal_count': [3, 24, 1, 9, 'Petal count', 'PETALS / FIRE'],
    'petal_length': [.3, 4, .05, 1.8, 'Petal length', 'PETALS / FIRE'],
    'petal_width': [.1, 1.8, .05, .65, 'Petal width', 'PETALS / FIRE'],
    'petal_curl': [0, 1.5, .05, .75, 'Petal curl', 'PETALS / FIRE'],
    'petal_spread': [0, 2, .05, .8, 'Petal spread', 'PETALS / FIRE'],
    'petal_irregularity': [0, 1, .01, .38, 'Petal irregularity', 'PETALS / FIRE'],
    'petal_lifetime': [.15, 2, .05, .85, 'Fire lifetime · seconds', 'PETALS / FIRE'],
    'ring_radius': [.5, 6, .1, 3.3, 'Ring radius', 'RING'],
    'ring_thickness': [.03, .8, .01, .18, 'Ring thickness', 'RING'],
    'ring_speed': [.3, 3, .05, 1.4, 'Ring expansion speed', 'RING'],
    'ring_tilt': [-75, 75, 1, 0, 'Ring tilt · degrees', 'RING'],
    'ring_vertical_offset': [0, 3, .05, .06, 'Ring vertical offset', 'RING'],
    'shard_count': [0, 48, 1, 16, 'Shard count', 'SHARDS'],
    'shard_length': [.1, 2, .05, .65, 'Shard length', 'SHARDS'],
    'shard_spread': [.3, 5, .1, 2.6, 'Shard spread', 'SHARDS'],
    'shard_speed': [.3, 3, .05, 1.4, 'Shard speed', 'SHARDS'],
    'smoke_count': [1, 24, 1, 8, 'Smoke count', 'SMOKE'],
    'smoke_puff_size': [.2, 2, .05, .65, 'Smoke puff size', 'SMOKE'],
    'smoke_expansion_speed': [.2, 2, .05, .7, 'Smoke expansion speed', 'SMOKE'],
    'smoke_darkness': [0, 1, .01, .5, 'Smoke darkness', 'SMOKE'],
    'smoke_linger': [.3, 5, .1, 1.9, 'Smoke linger · seconds', 'SMOKE'],
    'smoke_delay': [0, 1, .02, .2, 'Smoke delay · seconds', 'SMOKE'],
    'dust_spread': [.5, 5, .1, 2.2, 'Ground puff spread', 'GROUND PUFF'],
    'low_poly_amount': [0, 1, .01, .82, 'Low-poly amount', 'RETRO STYLE'],
    'vertex_wobble': [0, .2, .005, .025, 'Vertex wobble', 'RETRO STYLE'],
    'posterization': [2, 12, 1, 5, 'Lighting posterization', 'RETRO STYLE'],
    'palette_quantization': [0, 1, .01, .35, 'Palette quantization', 'RETRO STYLE'],
    'alpha_dithering': [0, 1, .01, .7, 'Alpha dithering strength', 'RETRO STYLE'],
    'chunkiness': [0, 1, .01, .65, 'Chunkiness', 'RETRO STYLE'],
    'silhouette_exaggeration': [0, 1, .01, .55, 'Silhouette exaggeration', 'RETRO STYLE'],
}
CONTROLS.update(SHAPE_CONTROLS)
LAYER_GROUPS = {'core': 'CORE', 'petals': 'PETALS / FIRE', 'ring': 'RING',
                'shards': 'SHARDS', 'smoke': 'SMOKE', 'dust': 'GROUND PUFF'}


def material(color, color_b, opacity, emission, blend='ALPHA', enabled=True, unshaded=False):
    return dict(enabled=enabled, color=color, color_b=color_b, opacity=opacity, emission=emission,
                blend=blend, unshaded=unshaded, soft_alpha=.15, depth_write=blend=='DITHER',
                cull_back=False, fade_curve='SMOOTH')


LAYERS = {
    'core': material('#ffe9aa', '#fff8d8', .95, 1.2, 'ADDITIVE', unshaded=True),
    'petals': material('#db943f', '#9b3928', .7, .35),
    'ring': material('#e7bd76', '#9e5b37', .65, .3, 'ADDITIVE', unshaded=True),
    'shards': material('#eab46a', '#a95930', .9, .3, 'ADDITIVE'),
    'smoke': material('#77736a', '#3b4142', .6, 0, 'DITHER'),
    'dust': material('#716b5a', '#3a3935', .3, 0, enabled=False),
}


def normalize(data):
    if not isinstance(data, dict) or data.get('schema', 'bowprototype.mesh_vfx') != 'bowprototype.mesh_vfx':
        raise ValueError('Expected a mesh VFX recipe')
    if data.get('schema_version', 1) != 1 or data.get('generator_version', VERSION) not in ('0.1.0', VERSION):
        raise ValueError('Unsupported mesh VFX recipe version')
    effect = data.get('effect', 'MESH_EXPLOSION_3D')
    if effect not in EFFECTS:
        raise ValueError('Unknown 3D effect archetype')
    preset = effect_defaults(effect)
    seed = data.get('seed', 99)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise ValueError('Seed must be an integer in 0..2147483647')
    values = data.get('parameters', {})
    if not isinstance(values, dict) or set(values) - set(CONTROLS):
        raise ValueError('Unknown mesh parameter')
    params = {}
    for key, (low, high, step, default, *_rest) in CONTROLS.items():
        value = values.get(key, preset['parameters'].get(key, default))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key}: expected {low}..{high}')
        if step == 1 and int(value) != value:
            raise ValueError(f'{key}: integer required')
        params[key] = int(value) if step == 1 else float(value)
    incoming = data.get('layers', {})
    if not isinstance(incoming, dict) or set(incoming) - set(LAYERS):
        raise ValueError('Unknown mesh layer')
    layers = copy.deepcopy(LAYERS)
    if effect != 'MESH_EXPLOSION_3D':
        for key, override in preset['layers'].items():
            layers[key].update(override)
        # Electric and optical shells are narrow luminous solids, not fire alpha shells.
        if effect not in ('SMOKE_BURST', 'DEBRIS_SCATTER'):
            layers['petals'].update(blend='ADDITIVE', opacity=.9, unshaded=True, emission=.9, soft_alpha=0)
        if effect == 'DEBRIS_SCATTER':
            layers['shards'].update(blend='DITHER', depth_write=True, opacity=1., emission=0.)
            layers['petals'].update(blend='ADDITIVE', unshaded=True, emission=.7)
        if effect == 'SMOKE_BURST':
            layers['smoke'].update(blend='ALPHA', depth_write=False, opacity=.6, soft_alpha=.45)
    for key, defaults in layers.items():
        override = incoming.get(key, {})
        if not isinstance(override, dict) or set(override) - set(defaults):
            raise ValueError(f'{key}: unknown material setting')
        defaults.update(override)
        for field in ('enabled', 'unshaded', 'depth_write', 'cull_back'):
            if not isinstance(defaults[field], bool):
                raise ValueError(f'{key}.{field}: boolean required')
        for field in ('color', 'color_b'):
            if not isinstance(defaults[field], str) or not re.fullmatch(r'#[a-fA-F0-9]{6}', defaults[field]):
                raise ValueError(f'{key}.{field}: #RRGGBB required')
            defaults[field] = defaults[field].lower()
        for field, high in [('opacity', 1), ('emission', 5), ('soft_alpha', 1)]:
            value = defaults[field]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= high:
                raise ValueError(f'{key}.{field}: expected 0..{high}')
            defaults[field] = float(value)
        if defaults['blend'] not in ('ALPHA', 'DITHER', 'ADDITIVE') or defaults['fade_curve'] not in ('LINEAR', 'EASE_OUT', 'SMOOTH'):
            raise ValueError(f'{key}: unsupported blend or fade curve')
    return dict(schema='bowprototype.mesh_vfx', schema_version=1, generator_version=VERSION,
                effect=effect, seed=seed, parameters=params, layers=layers)


def config():
    return dict(controls=CONTROLS, layer_groups=LAYER_GROUPS, defaults=normalize({}),
                effects={key: dict(**meta, recipe=normalize(effect_defaults(key))) for key,meta in EFFECTS.items()},
                export_directory='Assets/ProceduralArt/VFX', version=VERSION)
