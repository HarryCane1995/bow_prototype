"""Coherent hand-shaped 2D lobes and trajectories, then an optional retro pass.

No fluid solver and no image/cloud dependencies. RNG is sampled once per recipe;
frames evaluate the same descriptors, so changing time never shuffles the noise.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

TAU = math.tau


def mix(a, b, t):
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def rgb(value):
    return np.array([int(value[i:i+2], 16) for i in (1, 3, 5)], dtype=float)


def rgba(color, opacity=1):
    return tuple(int(v) for v in np.clip(color, 0, 255)) + (int(np.clip(opacity, 0, 1) * 255),)


def fade(t, start, end):
    return float(np.clip((end - t) / max(end - start, .0001), 0, 1))


def polygon(cx, cy, rx, ry, vertices, phase, breakup, scale):
    points = []
    for j in range(vertices):
        angle = j * TAU / vertices
        ridge = 1 + breakup * (.12 * math.sin(angle * 3 + phase) + .08 * math.cos(angle * 5 - phase))
        points.append(((cx + math.cos(angle) * rx * ridge) * scale,
                       (cy + math.sin(angle) * ry * ridge) * scale))
    return points


def palette_colors(c, count):
    # A shared palette for the whole clip avoids frame-to-frame quantizer flicker.
    anchors = [c['smoke'] * .34, c['smoke'] * .74, c['smoke'] * 1.35,
               c['secondary'] * .6, c['secondary'], c['primary'], mix(c['primary'], c['accent'], .5), c['accent']]
    return np.array([mix(anchors[int(x)], anchors[min(int(x) + 1, 7)], x % 1)
                     for x in np.linspace(0, 7, count)]).clip(0, 255)


def stylize(image, p, palette, noise):
    pixels = np.array(image)
    alpha = pixels[:, :, 3].copy()
    values = pixels[:, :, :3].astype(float)
    h, w = alpha.shape
    yy, xx = np.mgrid[:h, :w]
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 - .5
    values += bayer[yy % 4, xx % 4, None] * p['dithering_amount'] * 36
    values += noise[:, :, None] * p['noise_overlay_strength'] * 70
    blocks = noise[(yy // 4) * 4, (xx // 4) * 4]
    values *= 1 + blocks[:, :, None] * p['block_artifacts'] * .25
    levels = p['posterization_levels'] - 1
    values = np.round(np.clip(values, 0, 255) / 255 * levels) / levels * 255
    # Small bounded working raster: <=256² × 32 colors, only for visible pixels.
    visible = alpha > 0
    differences = values[visible, None, :] - palette[None, :, :]
    chosen = np.argmin(np.sum(differences * differences, axis=2), axis=1)
    pixels[:, :, :3] = 0
    pixels[visible, :3] = palette[chosen].astype(np.uint8)
    return Image.fromarray(pixels, 'RGBA')


def frames(recipe):
    p, size = recipe['parameters'], recipe['resolution']
    work = size // p['pixel_scale']
    rng = np.random.default_rng(recipe['seed'])
    c = {k: rgb(v) for k, v in recipe['colors'].items()}
    lobes = rng.uniform(0, 1, (20, 7))
    sparks = rng.uniform(0, 1, (48, 5))
    noise = rng.uniform(-1, 1, (work, work))
    palette = palette_colors(c, p['palette_color_count'])
    count = recipe['frame_count']
    vertices = int(17 - 8 * p['chunkiness'])
    lobe_count = int(16 - 6 * p['chunkiness'])
    color_frames, emission_frames = [], []
    for index in range(count):
        frame = (index // p['frame_stepping']) * p['frame_stepping']
        t = frame / max(count - 1, 1) * p['duration']
        final_fade = fade(t, p['duration'] * p['fade_timing'], p['duration'])
        image = Image.new('RGBA', (work, work))
        emissive = Image.new('RGBA', (work, work))
        if index == count - 1:
            color_frames.append(image.resize((size, size), Image.Resampling.NEAREST))
            emission_frames.append(emissive.resize((size, size), Image.Resampling.NEAREST))
            continue
        growth = 1 - math.exp(-(t + .035) * p['expansion_speed'] * 5)
        smoke_t = max(0, t - .11)
        smoke_life = min(p['smoke_duration'], p['duration'] - .11)
        smoke_opacity = min(1, smoke_t * 6) * fade(smoke_t, smoke_life * (.25 + .5 * p['smoke_linger']), smoke_life)
        smoke = Image.new('RGBA', (work, work)); sd = ImageDraw.Draw(smoke)
        for j, lobe in enumerate(lobes[:lobe_count]):
            angle = j / lobe_count * TAU + (lobe[0] - .5) * .65
            spread = .06 + .14 * growth * p['smoke_spread']
            cx = .5 + math.cos(angle) * spread * (1 - .35 * p['directionality'])
            cy = .66 + math.sin(angle) * spread * .58 - smoke_t / p['duration'] * (.18 + .15 * p['vertical_bias'])
            radius = (.07 + lobe[1] * .055) * (.4 + .9 * growth)
            opacity = smoke_opacity * p['smoke_amount'] * final_fade
            base = c['smoke'] * (1.28 - p['smoke_darkness']) * (.78 + lobe[2] * .35)
            pts = polygon(cx, cy, radius, radius * (1.1 - .28 * p['roundness']), vertices, lobe[3] * 6, .7, work)
            sd.polygon(pts, fill=rgba(base * (1 - p['edge_exaggeration'] * .5), opacity))
            sd.polygon(polygon(cx - radius * .14, cy - radius * .19, radius * .82, radius * .75,
                               vertices, lobe[3] * 6, .7, work), fill=rgba(base * 1.28, opacity))
            sd.polygon(polygon(cx - radius * .2, cy - radius * .35, radius * .53, radius * .37,
                               vertices - 1, lobe[3] * 6, .6, work), fill=rgba(base * 1.5, opacity))
        image = Image.alpha_composite(image, smoke)
        # Ring is drawn beneath the fire; its interior stays transparent.
        ring_life = min(.55, p['duration'] * .45)
        if p['ring_size'] > 0 and t < ring_life:
            ring = Image.new('RGBA', (work, work)); rd = ImageDraw.Draw(ring)
            radius = (.025 + .4 * (t / ring_life) ** .65) * p['ring_size']
            opacity = fade(t, .08, ring_life) * .8
            pts = polygon(.5, .82, radius, radius * .23, 24, 0, .04, work)
            rd.line(pts + [pts[0]], fill=rgba(c['accent'], opacity), width=max(1, round(work * p['ring_thickness'] * opacity)))
            image = Image.alpha_composite(image, ring); emissive = Image.alpha_composite(emissive, ring)
        fire_life = min(p['fire_duration'], p['duration'])
        fire_age = t / fire_life
        fire = Image.new('RGBA', (work, work)); fd = ImageDraw.Draw(fire)
        if fire_age < 1 and p['fire_intensity'] > 0:
            opacity = fade(fire_age, .55, 1) * min(1, p['fire_intensity']) * final_fade
            for j, lobe in enumerate(lobes[:lobe_count]):
                angle = j / lobe_count * TAU + (lobe[0] - .5) * .9
                spread = (.025 + .115 * growth) * (.8 + lobe[4] * .3)
                cx = .5 + math.cos(angle) * spread * (1 - p['directionality'] * .4)
                cy = .66 + math.sin(angle) * spread * (.8 + p['roundness'] * .2) - growth * p['vertical_bias'] * .13
                radius = (.052 + lobe[1] * .062) * (.5 + .85 * growth) * (1 - .48 * fire_age)
                ry = radius * (1 + (1 - p['roundness']) * .6)
                phase = lobe[3] * 6 + fire_age * (lobe[5] - .5) * 2
                bright = np.clip((1 - fire_age * .9) ** p['fire_contrast'] * p['fire_intensity'], 0, 1.3)
                base = mix(c['secondary'], c['primary'], min(1, bright))
                fd.polygon(polygon(cx, cy, radius, ry, vertices, phase, p['flame_breakup'], work),
                           fill=rgba(c['secondary'] * (1 - p['edge_exaggeration'] * .6), opacity))
                fd.polygon(polygon(cx - radius * .05, cy - ry * .12, radius * .82, ry * .8,
                                   vertices, phase, p['flame_breakup'], work), fill=rgba(base, opacity))
                fd.polygon(polygon(cx - radius * .1, cy - ry * .15, radius * .5, ry * .58,
                                   vertices - 1, phase, p['flame_breakup'], work),
                           fill=rgba(mix(base, c['accent'], min(1, bright * .9)), opacity))
            # Irregular hot core joins the lobes into one legible silhouette.
            radius = p['core_size'] * .14 * growth * fade(fire_age, .1, .8)
            if radius > .003:
                fd.polygon(polygon(.5, .665 - growth * .04, radius, radius * 1.2, 9, 1.6,
                                   p['flame_breakup'], work), fill=rgba(c['accent'] * p['core_brightness'], opacity))
        if 0 <= t < p['flash_duration'] and p['core_size'] > 0:
            radius = (.035 + .17 * p['core_size']) * fade(t, 0, p['flash_duration'])
            points = []
            for j in range(16):
                a = j * TAU / 16
                r = radius * (1 if j % 2 == 0 else .24)
                points.append(((.5 + math.cos(a) * r) * work, (.71 + math.sin(a) * r) * work))
            fd.polygon(points, fill=rgba(c['accent'] * p['core_brightness'], min(1, p['core_brightness'])))
        # A few delayed satellite bursts, reusing coherent seeded descriptors.
        delay_t = t - p['secondary_delay']
        if 0 < delay_t < fire_life * .65:
            for lobe in lobes[:round(p['secondary_burst_amount'] * 7)]:
                angle = lobe[0] * TAU
                distance = .13 + .08 * growth
                radius = .045 * math.sin(delay_t / (fire_life * .65) * math.pi)
                fd.polygon(polygon(.5 + math.cos(angle) * distance, .61 + math.sin(angle) * distance * .7,
                                   radius, radius * 1.3, 7, lobe[1] * 6, .9, work),
                           fill=rgba(c['primary'], final_fade * .85))
        image = Image.alpha_composite(image, fire); emissive = Image.alpha_composite(emissive, fire)
        accents = Image.new('RGBA', (work, work)); ad = ImageDraw.Draw(accents)
        if delay_t > 0:
            for j, spark in enumerate(sparks):
                is_spark = j < p['sparks_count']
                is_debris = j >= 32 and j < 32 + round(p['debris_amount'] * 16)
                if not is_spark and not is_debris:
                    continue
                life = .28 + spark[2] * (.55 if is_spark else 1.0)
                age = delay_t / life
                if age >= 1:
                    continue
                angle = -math.pi * (.08 + .84 * spark[0])
                vx = math.cos(angle) * (.17 + spark[1] * .32)
                vy = math.sin(angle) * (.25 + spark[1] * .43)
                x = .5 + vx * age; y = .73 + vy * age + .23 * age * age
                opacity = fade(age, .4, 1) * final_fade
                if is_spark:
                    tail = .014 + p['sparks_length'] * .14
                    ad.line([(x * work, y * work), ((x - vx * tail) * work, (y - (vy + .46 * age) * tail) * work)],
                            fill=rgba(mix(c['primary'], c['accent'], 1 - age), opacity), width=max(1, round(work / 128)))
                else:
                    ad.polygon(polygon(x, y, .006 + spark[3] * .008, .007, 4, age * 5, 0, work),
                               fill=rgba(c['smoke'] * .65, opacity))
        image = Image.alpha_composite(image, accents)
        # Only bright particles emit. Smoke and debris never become an emissive veil.
        ea = np.array(accents); strength = ea[:, :, :3].max(axis=2) > c['smoke'].max()
        ea[~strength] = 0
        emissive = Image.alpha_composite(emissive, Image.fromarray(ea, 'RGBA'))
        image = stylize(image, p, palette, noise)
        emissive = stylize(emissive, p, palette, noise)
        color_frames.append(image.resize((size, size), Image.Resampling.NEAREST))
        emission_frames.append(emissive.resize((size, size), Image.Resampling.NEAREST))
    return color_frames, emission_frames


def assemble(recipe, output, sequence=False, emission=True):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    colors, lights = frames(recipe)
    n, size, gutter = len(colors), recipe['resolution'], 2
    cols = math.ceil(math.sqrt(n)); rows = math.ceil(n / cols); cell = size + gutter * 2
    rectangles = [[(i % cols) * cell + gutter, (i // cols) * cell + gutter, size, size] for i in range(n)]
    for name, images in [('color', colors)] + ([('emission', lights)] if emission else []):
        sheet = Image.new('RGBA', (cols * cell, rows * cell))
        for i, frame in enumerate(images):
            sheet.paste(frame, rectangles[i][:2])
            if sequence:
                (output / name).mkdir(exist_ok=True)
                frame.save(output / name / f'{name}_{i:04d}.png')
        sheet.save(output / f'{name}_sheet.png')
    # Transparent hero frame + a labelled dark contact sheet for external review.
    hero = min(n - 2, max(1, round(.23 / recipe['parameters']['duration'] * n)))
    colors[hero].save(output / 'preview.png')
    contact = Image.new('RGB', (size * 4, (size + 22) * 2), '#151c20'); draw = ImageDraw.Draw(contact)
    for slot, i in enumerate(np.linspace(0, n - 1, 8).round().astype(int)):
        x, y = (slot % 4) * size, (slot // 4) * (size + 22)
        contact.paste(colors[i], (x, y), colors[i])
        draw.text((x + 6, y + size + 4), f'{i:02d} / {i / recipe["parameters"]["fps"]:.2f}s', fill='#a8b1ad')
    contact.save(output / 'contact_sheet.png')
    return dict(cols=cols, rows=rows, frame_count=n, frame_size=size, cell_size=cell, gutter=gutter,
                rectangles=rectangles, fps=recipe['parameters']['fps'],
                playback_duration=n / recipe['parameters']['fps'],
                alpha='straight', order='row-major, top-left origin', filter='nearest', mipmaps=False,
                emission=emission, sequence=sequence, hero_frame=hero,
                canvas_world_size=recipe['parameters']['explosion_size'], pivot=[.5, .82],
                color_space='sRGB; alpha linear', last_frame='fully transparent')
