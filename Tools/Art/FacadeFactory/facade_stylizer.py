"""Restrained raster treatment. Data maps never receive color filters."""
import numpy as np
from PIL import Image, ImageFilter


def normal_from_height(height, strength=.24):
    # Image rows point DOWN. Tangent +Y points UP: hence +dH/drow (OpenGL).
    smooth = height.filter(ImageFilter.GaussianBlur(max(.55, height.width / 700)))
    h = np.asarray(smooth, dtype=np.float32) / 255
    dy, dx = np.gradient(h)
    sx, sy = height.width / 512, height.height / 1024
    n = np.stack((-dx * sx * strength * 8, dy * sy * strength * 8, np.ones_like(h)), axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(np.uint8(np.clip(n * .5 + .5, 0, 1) * 255 + .5))


def stylize(albedo, height, orm, p, seed):
    a = np.asarray(albedo, dtype=np.float32)
    s, strength = p.style, p.retro_strength
    hh, ww = a.shape[:2]
    # Local AO comes from recess/edge semantics, rather than arbitrary image noise.
    ao = np.asarray(orm, dtype=np.float32)[..., 0] / 255
    a *= (1 - (1 - ao) * s.baked_ao_strength)[..., None]
    y = np.linspace(0, 1, hh)[:, None]
    x = np.linspace(0, 1, ww)[None, :]
    macro = 1 + p.macro_contrast * (.55 - y + .22 * np.cos(x * np.pi))
    a *= macro[..., None]
    blurred = np.asarray(Image.fromarray(np.uint8(np.clip(a, 0, 255))).filter(ImageFilter.GaussianBlur(1.1)), dtype=np.float32)
    a += (a - blurred) * s.micro_contrast * strength
    heights = np.asarray(height, dtype=np.float32) / 255
    dy, dx = np.gradient(heights)
    edge = np.clip(-dx - dy, -.25, .25)
    a += edge[..., None] * s.edge_exaggeration * strength * 70
    rng = np.random.default_rng(seed)
    # Small bounded noise is the final finishing pass, never the building layout.
    a += rng.uniform(-1, 1, (hh, ww, 1)) * s.pixel_noise * strength
    block = rng.uniform(-1, 1, ((hh + 7)//8, (ww + 7)//8))
    block = np.repeat(np.repeat(block, 8, axis=0), 8, axis=1)[:hh, :ww]
    a += block[..., None] * s.compression_artifacts * strength * 8
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32)/16 - .5
    ordered = np.tile(bayer, ((hh+3)//4, (ww+3)//4))[:hh, :ww]
    step = 255 / (s.posterization - 1)
    candidate = np.round((a + ordered[..., None] * step * s.dithering) / step) * step
    a = a * (1-strength) + candidate * strength
    clean = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    quantized = clean.quantize(colors=s.color_quantization, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE).convert("RGB")
    return Image.blend(clean, quantized, strength * .7)
