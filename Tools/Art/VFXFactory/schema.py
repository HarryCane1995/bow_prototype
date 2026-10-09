"""Versioned, deterministic PSX explosion recipe; independent of surface grammar."""
import copy
import hashlib
import math
from pathlib import Path
import re

VERSION = '0.1.0'
HERE = Path(__file__).resolve().parent
# name: minimum, maximum, step, default, label, group
CONTROLS = {
    'duration': [.5, 4, .05, 2, 'Duration · seconds', 'TIMING'],
    'fps': [6, 24, 1, 16, 'Frames per second', 'TIMING'],
    'explosion_size': [1, 8, .1, 4, 'Explosion size · metres', 'SHAPE'],
    'expansion_speed': [.4, 2.5, .05, 1.15, 'Expansion speed', 'SHAPE'],
    'flash_duration': [.02, .5, .01, .13, 'Flash duration · seconds', 'TIMING'],
    'fire_duration': [.15, 3, .05, .85, 'Fire duration · seconds', 'TIMING'],
    'smoke_duration': [.2, 4, .05, 1.8, 'Smoke duration · seconds', 'TIMING'],
    'fade_timing': [.25, .95, .01, .62, 'Final fade starts', 'TIMING'],
    'secondary_delay': [0, 1, .02, .14, 'Secondary delay · seconds', 'TIMING'],
    'roundness': [0, 1, .01, .48, 'Roundness', 'SHAPE'],
    'directionality': [0, 1, .01, .22, 'Upward directionality', 'SHAPE'],
    'vertical_bias': [-.5, 1, .01, .3, 'Vertical bias', 'SHAPE'],
    'chunkiness': [0, 1, .01, .65, 'Chunkiness', 'SHAPE'],
    'ring_size': [0, 1, .01, .78, 'Ring size · zero disables', 'SHAPE'],
    'ring_thickness': [.01, .14, .005, .025, 'Ring thickness', 'SHAPE'],
    'core_size': [0, 1, .01, .6, 'Core size', 'SHAPE'],
    'fire_intensity': [0, 2, .05, 1, 'Fire intensity', 'SMOKE / FIRE'],
    'flame_breakup': [0, 1, .01, .62, 'Flame breakup', 'SMOKE / FIRE'],
    'fire_contrast': [.4, 2, .05, 1.2, 'Fire contrast', 'SMOKE / FIRE'],
    'core_brightness': [0, 2, .05, 1.2, 'Core brightness', 'SMOKE / FIRE'],
    'smoke_amount': [0, 1, .01, .8, 'Smoke amount', 'SMOKE / FIRE'],
    'smoke_spread': [.3, 1.5, .05, 1, 'Smoke spread', 'SMOKE / FIRE'],
    'smoke_darkness': [0, 1, .01, .58, 'Smoke darkness', 'SMOKE / FIRE'],
    'smoke_linger': [0, 1, .01, .65, 'Smoke linger', 'SMOKE / FIRE'],
    'sparks_count': [0, 48, 1, 18, 'Sparks count', 'SECONDARY'],
    'sparks_length': [0, 1, .01, .42, 'Sparks length', 'SECONDARY'],
    'debris_amount': [0, 1, .01, .25, 'Debris amount', 'SECONDARY'],
    'secondary_burst_amount': [0, 1, .01, .25, 'Secondary bursts', 'SECONDARY'],
    'posterization_levels': [3, 32, 1, 10, 'Posterization levels', 'RETRO STYLIZATION'],
    'palette_color_count': [6, 32, 1, 16, 'Palette color count', 'RETRO STYLIZATION'],
    'dithering_amount': [0, 1, .01, .18, 'Ordered dithering', 'RETRO STYLIZATION'],
    'pixel_scale': [1, 4, 1, 1, 'Pixel scale', 'RETRO STYLIZATION'],
    'frame_stepping': [1, 4, 1, 1, 'Frame hold / choppiness', 'RETRO STYLIZATION'],
    'block_artifacts': [0, 1, .01, .05, 'Block artifacts', 'RETRO STYLIZATION'],
    'edge_exaggeration': [0, 1, .01, .25, 'Edge exaggeration', 'RETRO STYLIZATION'],
    'noise_overlay_strength': [0, .3, .005, 0, 'Noise overlay', 'RETRO STYLIZATION'],
}
PALETTES = {
    'BOW_EMBER': dict(primary='#d97832', secondary='#843727', smoke='#55534e', accent='#ffe6a5'),
    'IRON_FIRE': dict(primary='#c6522c', secondary='#682725', smoke='#41484e', accent='#ffc975'),
    'PALE_REACTOR': dict(primary='#83ada8', secondary='#3a686b', smoke='#424b52', accent='#e4e7b7'),
}


def fingerprint():
    return hashlib.sha256(b''.join((HERE / f).read_bytes() for f in
        ('schema.py', 'explosion.py', 'godot_export.py'))).hexdigest()


def normalize(data):
    if not isinstance(data, dict):
        raise ValueError('VFX recipe must be an object')
    if data.get('effect', 'PSX_EXPLOSION') != 'PSX_EXPLOSION':
        raise ValueError('First pass supports PSX_EXPLOSION only')
    if data.get('schema', 'bowprototype.vfx') != 'bowprototype.vfx' or data.get('schema_version', 1) != 1:
        raise ValueError('Unsupported VFX recipe schema')
    if data.get('generator_version', VERSION) != VERSION:
        raise ValueError('VFX generator version mismatch')
    seed = data.get('seed', 99)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise ValueError('Seed must be an integer in 0..2147483647')
    resolution = data.get('resolution', 128)
    if isinstance(resolution, bool) or resolution not in (64, 128, 256):
        raise ValueError('Frame resolution must be 64, 128 or 256')
    params = data.get('parameters', {})
    if not isinstance(params, dict) or set(params) - set(CONTROLS):
        raise ValueError('Unknown VFX parameter')
    effective = {}
    for key, (low, high, step, default, *_rest) in CONTROLS.items():
        value = params.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key}: expected {low}..{high}')
        if step == 1 and int(value) != value:
            raise ValueError(f'{key}: integer required')
        effective[key] = int(value) if step == 1 else float(value)
    palette = data.get('palette', 'BOW_EMBER')
    if palette not in PALETTES:
        raise ValueError('Unknown VFX palette')
    colors = data.get('colors', PALETTES[palette])
    if not isinstance(colors, dict) or set(colors) != set(PALETTES[palette]):
        raise ValueError('VFX colors need primary, secondary, smoke and accent slots')
    if not all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in colors.values()):
        raise ValueError('VFX colors must be #RRGGBB')
    return dict(schema='bowprototype.vfx', schema_version=1, generator_version=VERSION,
                effect='PSX_EXPLOSION', seed=seed, resolution=resolution, parameters=effective,
                palette=palette, colors={k: v.lower() for k, v in colors.items()},
                frame_count=max(2, round(effective['duration'] * effective['fps'])))


def config():
    return dict(controls=CONTROLS, palettes=copy.deepcopy(PALETTES), defaults=normalize({}),
                resolutions=[64, 128, 256], version=VERSION,
                export_directory='Assets/VFX/Explosions/PSXExplosion')
