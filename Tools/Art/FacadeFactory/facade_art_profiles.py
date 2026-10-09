"""Global art direction after structural generation, shared by every grammar.

Art randomness has its own stable namespace. No architecture RNG or coordinates
are modified. LEGACY is a byte-exact bypass of this stage.
"""
from dataclasses import dataclass, asdict, replace
import hashlib
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from facade_semantics import MaterialClass, SeamClass
from facade_stylizer import stylize

ART_VERSION = '1.0'
ART_CONTROLS = {
    'panel_outline_strength': [0, 1, .01, 'Panel outline strength'],
    'seam_contrast': [0, 1, .01, 'Seam contrast'],
    'material_variation': [0, 1, .01, 'Material variation'],
    'macro_grime_strength': [0, 1, .01, 'Macro grime strength'],
    'macro_grime_scale': [1, 12, .25, 'Macro grime scale'],
    'saturation': [0, 1.5, .01, 'Saturation'],
    'baked_lighting_strength': [0, 1, .01, 'Baked lighting strength'],
    'detail_contrast': [0, 1, .01, 'Detail contrast'],
    'module_irregularity': [0, 1, .01, 'Module finish irregularity'],
}


@dataclass(frozen=True)
class ArtProfile:
    panel_outline_strength: float
    seam_contrast: float
    material_variation: float
    macro_grime_strength: float
    macro_grime_scale: float
    saturation: float
    baked_lighting_strength: float
    detail_contrast: float
    module_irregularity: float


def normalized_art(data=None):
    if data is None:
        data = {'profile': 'LEGACY'}
    if not isinstance(data, dict) or data.get('profile', 'BOW_BASE') not in ('LEGACY', 'BOW_BASE'):
        raise ValueError('Art profile must be LEGACY or BOW_BASE')
    mix, weather = data.get('material_mix', 1.0), data.get('weathering', .6)
    for name, value in [('material_mix', mix), ('weathering', weather)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f'art.{name}: expected 0..1')
    overrides = data.get('overrides', {})
    if not isinstance(overrides, dict) or set(overrides) - set(ART_CONTROLS):
        raise ValueError('Unknown global art control')
    for key, value in overrides.items():
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or not ART_CONTROLS[key][0] <= value <= ART_CONTROLS[key][1]:
            raise ValueError(f'art.{key}: out of range')
    # Increasing level/color COUNTS reduces posterization/quantization severity.
    profile = ArtProfile(panel_outline_strength=.85-.74*mix, seam_contrast=.9-.42*mix,
        material_variation=.08+.31*mix+.31*weather,
        macro_grime_strength=.03+.10*mix+.52*weather, macro_grime_scale=3.0,
        saturation=1-.30*mix-.08*weather, baked_lighting_strength=.85-.67*mix,
        detail_contrast=.82-.48*mix, module_irregularity=.05+.27*mix+.50*weather)
    controls = {k: round(v,4) for k,v in asdict(replace(profile, **overrides)).items()}
    return dict(profile=data.get('profile','BOW_BASE'), version=ART_VERSION,
                material_mix=mix, weathering=weather, overrides=dict(overrides), controls=controls)


def effective_stylizer(preset, art):
    if art['profile'] == 'LEGACY':
        return preset
    mix, c = art['material_mix'], art['controls']
    s = preset.style
    return replace(preset, macro_contrast=preset.macro_contrast*c['baked_lighting_strength'],
        style=replace(s, edge_exaggeration=s.edge_exaggeration*(1-.95*mix),
            posterization=round(s.posterization+(256-s.posterization)*mix),
            color_quantization=round(s.color_quantization+(256-s.color_quantization)*mix),
            micro_contrast=s.micro_contrast*c['detail_contrast'],
            baked_ao_strength=s.baked_ao_strength*c['baked_lighting_strength'],
            dithering=s.dithering*(1-.9*mix), compression_artifacts=s.compression_artifacts*(1-.9*mix)))


# Palette reference, roughness, metallic, color variation, diffuse edge response.
# Painted metal has a dielectric coating; exposed raw metal alone is highly metallic.
MATERIAL_RESPONSE = {
    MaterialClass.PAINTED_METAL: ('base', .76, .035, 1.0, .25),
    MaterialClass.RAW_METAL: ('metal', .49, .82, .58, .80),
    MaterialClass.GLASS: ('glass', .23, 0.0, .16, .14),
    MaterialClass.CONCRETE: ('concrete', .94, 0.0, 1.28, .07),
    MaterialClass.VENT: ('metal', .82, .38, .80, .32),
    MaterialClass.RECESSED_VOID: ('recess', .98, 0.0, .15, 0.0),
}


def art_rng(seed, preset):
    digest = hashlib.sha256(f'BOW_ART:{ART_VERSION}:{seed}:{preset}'.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], 'big'))


def noise_field(rng, size, cells_x, cells_y, periodic=(False,False)):
    if any(periodic):
        w,h=size; y,x=np.mgrid[:h,:w].astype(np.float32)
        x/=w; y/=h
        result=np.zeros((h,w),dtype=np.float32)
        for _ in range(9):
            fx=int(rng.integers(1,max(2,cells_x+1))); fy=int(rng.integers(1,max(2,cells_y+1)))
            result += np.cos(x*fx*2*np.pi+rng.uniform(0,6.28))*np.cos(y*fy*2*np.pi+rng.uniform(0,6.28))
        return np.clip(.5+result/10,0,1)
    values = np.uint8(rng.uniform(0,255,(max(2,cells_y),max(2,cells_x))))
    image = Image.fromarray(values).resize(size, Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32)/255


def apply_art(facade, art_data):
    art = normalized_art(art_data)
    p, seed = facade.p, facade.seed
    if art['profile'] == 'LEGACY':
        return dict(albedo=stylize(facade.albedo,facade.height,facade.orm,p,seed & 0xFFFFFFFFFFFFFFFF),
                    emission=facade.emission,height=facade.height,orm=facade.orm), art, {}
    c, mix, weather = art['controls'], art['material_mix'], art['weathering']
    sem = facade.semantic
    periodic=getattr(facade,'periodic',(False,False))
    ids = np.asarray(sem.material)
    seams = np.asarray(sem.seam)
    module_ids = np.asarray(sem.module)
    outline = np.asarray(sem.outline,dtype=np.float32)/255
    edges = np.asarray(sem.edge,dtype=np.float32)/255
    a = np.asarray(facade.albedo,dtype=np.float32).copy()
    orm = np.asarray(facade.orm,dtype=np.float32).copy()
    size = facade.albedo.size; w,h = size
    rng = art_rng(seed,p.name)
    variation = noise_field(rng,size,7,13,periodic)*2-1
    scale = c['macro_grime_scale']
    grime = noise_field(rng,size,round(scale),round(scale*2.3),periodic)
    grime = np.clip((grime-.28)*1.6,0,1)
    # Broad moisture/soot mottling, not per-pixel random dirt.
    discolor = noise_field(rng,size,4,9,periodic)*2-1
    streak_img = Image.new('L',size); draw = ImageDraw.Draw(streak_img)
    finishes = np.ones(len(sem.modules)+1,dtype=np.float32)
    replacements = np.zeros(len(sem.modules)+1,dtype=np.float32)
    for module in sem.modules:
        ident = module['id']; x0,y0,x1,y1 = module['box']
        finishes[ident] = 1+(module['finish']-.5)*c['module_irregularity']*(.15+.25*weather)
        if module['kind'] != 'window' and rng.random() < weather*.18:
            replacements[ident] = float(rng.uniform(.55,1))
        for _ in range(2):
            x=float(rng.uniform(x0,x1)); length=float(rng.uniform(18,95))
            width=float(rng.uniform(2,6)); alpha=int(rng.uniform(65,180))
            for ox in (-w,0,w) if periodic[0] else (0,):
                for oy in (-h,0,h) if periodic[1] else (0,):
                    draw.polygon([(x-width+ox,y1+oy),(x+width+ox,y1+oy),(x+width*.3+ox,y1+length+oy),(x-width*.15+ox,y1+length*.8+oy)],fill=alpha)
    streak = np.asarray(periodic_blur(streak_img,2.2,periodic),dtype=np.float32)/255
    if hasattr(facade,'surface_wear'):
        weather=min(1,weather*.6+facade.surface_wear*.4)
        grime*=.45+.75*facade.surface_wear
        streak*=getattr(facade,'pipe_grime_flow',1)
    moisture = np.clip(grime*.8+streak*(.12+.88*weather),0,1)*c['macro_grime_strength']
    finish = finishes[module_ids]
    repair = replacements[module_ids]*c['module_irregularity']
    for material, (palette,rough,metal,var_gain,edge_gain) in MATERIAL_RESPONSE.items():
        mask = ids == material
        base = np.array(facade.pal[palette],dtype=np.float32)
        # Suppress the authored bright outline paint. Keep windows, signage,
        # hazard marks and genuine recessed voids identifiable.
        edge_mix = edges*(1-c['baked_lighting_strength'])*(1-edge_gain*.55)
        adjusted = a*(1-edge_mix[...,None])+base*edge_mix[...,None]
        a[mask] = adjusted[mask]
        variance = (1+variation*c['material_variation']*.20*var_gain)*finish
        attenuation = 1-moisture*(.45 if material == MaterialClass.GLASS else .56)
        response = variance*attenuation
        a[mask] *= response[mask,None]
        tint = discolor[...,None]*np.array([6.5,2,-5.0])*weather*var_gain
        a[mask] += tint[mask]
        if material in (MaterialClass.PAINTED_METAL, MaterialClass.CONCRETE, MaterialClass.RAW_METAL):
            repaired = base*np.array([1.06,1.025,.97])
            blend = repair*.55
            a[mask] = (a*(1-blend[...,None])+repaired*blend[...,None])[mask]
        orm[...,1][mask] = np.clip(rough+variation*.06*var_gain*c['material_variation']+moisture*.18+edges*(1-edge_gain)*.08,0,1)[mask]*255
        orm[...,2][mask] = np.clip(metal*(1-moisture*.65)-repair*.06,0,1)[mask]*255
    # Seams receive physical depth classes, local finish and a slow varying
    # contrast along the join. A panel border is not an empty room.
    seam_base = np.asarray(sem.seam_base,dtype=np.float32)
    seam_stats = {}
    for seam, depth in ((SeamClass.DEEP_RECESS,.78),(SeamClass.NORMAL_SEAM,.55),(SeamClass.SUBTLE_JOIN,.18)):
        mask = seams == seam
        if seam == SeamClass.DEEP_RECESS:
            contrast = .62+.38*c['seam_contrast']
        else:
            contrast = c['seam_contrast']*(.75+.25*c['panel_outline_strength']*outline)
        multiplier = 1-depth*contrast*(.80+.20*(variation+1)/2)
        target = seam_base*multiplier[...,None] if isinstance(multiplier,np.ndarray) else seam_base*multiplier
        target *= (1-moisture*.45)[...,None]*finish[...,None]
        a[mask] = target[mask]
        orm[...,0][mask] = (255*(1-depth*.38))
        orm[...,1][mask] = (238 if seam==SeamClass.DEEP_RECESS else 209)
        orm[...,2][mask] = 0
        seam_stats[seam.name] = int(mask.sum())
    luminance = a @ np.array([.2126,.7152,.0722],dtype=np.float32)
    a = luminance[...,None]+(a-luminance[...,None])*c['saturation']
    # Detail contrast is local only, so it cannot change the building grammar.
    blurred = np.asarray(periodic_blur(Image.fromarray(np.uint8(np.clip(a,0,255))),.8,periodic),dtype=np.float32)
    a = blurred+(a-blurred)*(.55+.55*c['detail_contrast'])
    albedo = Image.fromarray(np.uint8(np.clip(a,0,255)))
    orm_image = Image.fromarray(np.uint8(np.clip(orm,0,255)))
    effective = effective_stylizer(p,art)
    if any(periodic):
        # Pointwise quantization and periodic blur preserve the torus. The legacy
        # stylizer's nonperiodic vignette/noise cannot enter a repeating surface.
        values=np.asarray(albedo,dtype=np.float32)
        values*= (1-(1-np.asarray(orm_image)[...,0]/255)*effective.style.baked_ao_strength)[...,None]
        step=255/(effective.style.posterization-1)
        values=values*(1-effective.retro_strength)+np.round(values/step)*step*effective.retro_strength
        albedo=Image.fromarray(np.uint8(np.clip(values,0,255)))
        quantized=albedo.quantize(colors=effective.style.color_quantization,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB')
        albedo=Image.blend(albedo,quantized,effective.retro_strength*.7)
    else:
        albedo = stylize(albedo,facade.height,orm_image,effective,seed & 0xFFFFFFFFFFFFFFFF)
    stats = dict(material_classes={m.name:int((ids==m).sum()) for m in MaterialClass},
                 seam_classes=seam_stats, replacement_modules=int((replacements>0).sum()),
                 effective_style=asdict(effective.style), structural_modules=len(sem.modules))
    return dict(albedo=albedo,emission=facade.emission,height=facade.height,orm=orm_image), art, stats


def periodic_blur(image, radius, axes):
    if not any(axes):
        return image.filter(ImageFilter.GaussianBlur(radius))
    array=np.asarray(image); pad=max(4,math.ceil(radius*4))
    padding=[(pad,pad),(pad,pad)]+([(0,0)] if array.ndim==3 else [])
    # Wrap X independently of Y so the controlled cylinder ends stay independent.
    array=np.pad(array,[(0,0),(pad,pad)]+([(0,0)] if array.ndim==3 else []),mode='wrap' if axes[0] else 'edge')
    array=np.pad(array,[(pad,pad),(0,0)]+([(0,0)] if array.ndim==3 else []),mode='wrap' if axes[1] else 'edge')
    return Image.fromarray(array).filter(ImageFilter.GaussianBlur(radius)).crop((pad,pad,pad+image.width,pad+image.height))
