"""Structure -> material -> optional breakup. No structural RNG is consumed here.

Raw detail assets are reusable, independently of preview weights (including CLEAN
BASE). Only preview_normal combines normals; the exported normal is structural.
"""
import hashlib
import math
import numpy as np
from PIL import Image, ImageDraw
from facade_art_profiles import normalized_art, MATERIAL_RESPONSE, periodic_blur
from facade_semantics import MaterialClass, SeamClass

BREAKUP_VERSION = '1.0'
BREAKUP_CONTROLS = {
    'macro_variation': [0, 1, .01, 'Macro Variation'],
    'grime': [0, 1, .01, 'Grime'],
    'micro_grain': [0, 1, .01, 'Micro Grain'],
    'retro_artifacts': [0, 1, .01, 'Retro Artifacts'],
}
DETAIL_CHANNELS = ('detail_albedo', 'detail_normal', 'weather_mask')
PREVIEW_CHANNELS = ('preview_albedo', 'preview_orm', 'preview_normal')


def normalized_breakup(data=None, mode='UNIQUE_FACADE'):
    defaults = dict(mode='LEGACY_BAKED' if mode=='UNIQUE_FACADE' else 'LAYERED',
                    export_mode='SEPARATE', macro_variation=.35, grime=.25,
                    micro_grain=.12, retro_artifacts=0.)
    if data is None: data = {}
    if not isinstance(data, dict) or set(data)-set(defaults)-{'version'}:
        raise ValueError('Unknown surface breakup setting')
    result = {**defaults, **data}
    if result['mode'] not in ('LEGACY_BAKED', 'LAYERED'):
        raise ValueError('Unknown breakup mode')
    if result['export_mode'] not in ('BAKED', 'SEPARATE'):
        raise ValueError('Unknown detail export mode')
    for key in BREAKUP_CONTROLS:
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or not 0<=value<=1:
            raise ValueError(f'breakup.{key}: expected 0..1')
    result['version'] = BREAKUP_VERSION
    return result


def clean_material(f, art_data):
    """Semantic material response and authored marks, without spatial noise."""
    art = normalized_art(art_data)
    # A layered facade uses the same semantic material stage as other surfaces.
    if art['profile']=='LEGACY': art = normalized_art({'profile':'BOW_BASE'})
    c = art['controls']; sem = f.semantic
    ids = np.asarray(sem.material); seams = np.asarray(sem.seam)
    edges = np.asarray(sem.edge,dtype=np.float32)/255
    outlines = np.asarray(sem.outline,dtype=np.float32)/255
    a = np.asarray(f.albedo,dtype=np.float32).copy()
    orm = np.asarray(f.orm,dtype=np.float32).copy()
    finishes = np.ones(len(sem.modules)+1,dtype=np.float32)
    for m in sem.modules:
        finishes[m['id']] = 1+(m['finish']-.5)*c['module_irregularity']*.10
    finish = finishes[np.asarray(sem.module)]
    for material,(palette,rough,metal,variation,edge_gain) in MATERIAL_RESPONSE.items():
        mask = ids==material
        base = np.array(f.pal[palette],dtype=np.float32)
        blend = edges*(1-c['baked_lighting_strength'])*(1-edge_gain*.55)
        a[mask] = ((a*(1-blend[...,None])+base*blend[...,None])*finish[...,None])[mask]
        orm[...,1][mask] = (rough+edges*(1-edge_gain)*.08)[mask]*255
        orm[...,2][mask] = metal*255
    seam_base = np.asarray(sem.seam_base,dtype=np.float32)
    for seam,depth in ((SeamClass.DEEP_RECESS,.78),(SeamClass.NORMAL_SEAM,.55),(SeamClass.SUBTLE_JOIN,.18)):
        mask = seams==seam
        contrast = .62+.38*c['seam_contrast'] if seam==SeamClass.DEEP_RECESS else c['seam_contrast']*(.75+.25*c['panel_outline_strength']*outlines)
        multiplier = (1-depth*contrast*.90)*finish
        a[mask] = (seam_base*multiplier[...,None])[mask]
        orm[...,0][mask] = 255*(1-depth*.38)
        orm[...,1][mask] = 238 if seam==SeamClass.DEEP_RECESS else 209
        orm[...,2][mask] = 0
    luminance = a @ np.array([.2126,.7152,.0722],dtype=np.float32)
    a = luminance[...,None]+(a-luminance[...,None])*c['saturation']
    a *= (1-(1-orm[...,0]/255)*f.p.style.baked_ao_strength*c['baked_lighting_strength'])[...,None]
    stats = dict(material_classes={m.name:int((ids==m).sum()) for m in MaterialClass},
        seam_classes={s.name:int((seams==s).sum()) for s in SeamClass},
        structural_modules=len(sem.modules), pipeline='STRUCTURE > MATERIAL > OPTIONAL BREAKUP')
    return dict(albedo=rgb(a),emission=f.emission,height=f.height,orm=rgb(orm)),art,stats


def rgb(a):
    return Image.fromarray(np.uint8(np.clip(a,0,255)+.5))


def layer_rng(f, label):
    digest = hashlib.sha256(f'BREAKUP:{BREAKUP_VERSION}:{f.seed}:{f.p.name}:{label}'.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8],'big'))


def slow_field(f, size, label):
    """One cycle across the sheet: the wavelength spans several structural panels."""
    w,h = size; y,x = np.mgrid[:h,:w].astype(np.float32)
    rng = layer_rng(f,label); px,py,pz = rng.uniform(0,2*np.pi,3)
    return np.clip(.5+.22*np.cos(2*np.pi*x/w+px)+.18*np.cos(2*np.pi*y/h+py)+.10*np.cos(2*np.pi*(x/w+y/h)+pz),0,1)


def layer_sources(f, size):
    """RGB mask: unweighted macro tone/dirt, directional grime, micro variation."""
    w,h=size; axes=getattr(f,'periodic',(False,False))
    macro = slow_field(f,size,'macro')
    grime = slow_field(f,size,'dirt')*.16
    streak = Image.new('L', f.albedo.size); draw=ImageDraw.Draw(streak)
    dw,dh=f.albedo.size; rng=layer_rng(f,'streaks')
    for m in f.semantic.modules:
        x0,y0,x1,y1=m['box']
        for _ in range(2):
            x=float(rng.uniform(x0,x1)); length=float(rng.uniform(22,110)); width=float(rng.uniform(1.5,4))
            for ox in (-dw,0,dw) if axes[0] else (0,):
                for oy in (-dh,0,dh) if axes[1] else (0,):
                    draw.polygon([(x-width+ox,y1+oy),(x+width+ox,y1+oy),(x+width*.2+ox,y1+length+oy)],fill=int(rng.uniform(100,230)))
    streak=np.asarray(periodic_blur(streak,1.4,axes).resize(size,Image.Resampling.BILINEAR),dtype=np.float32)/255
    grime += streak*(.35+.65*getattr(f,'pipe_grime_flow',1))
    grain = layer_rng(f,'micro').normal(0,.19,(h,w)).astype(np.float32)
    grain = np.clip(.5+grain,0,1)
    # Grain is a separate repeatable texture; it never enters structural height.
    micro_height = np.asarray(periodic_blur(rgb(grain*255),.55,(True,True)),dtype=np.float32)/255
    dx=(np.roll(micro_height,-1,1)-np.roll(micro_height,1,1))*.5
    dy=(np.roll(micro_height,-1,0)-np.roll(micro_height,1,0))*.5
    normal=np.stack((-dx*.7,dy*.7,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    return macro,np.clip(grime,0,1),grain,normal


def close_edges(image, axes):
    a=np.array(image)
    if axes[0]: a[:,-1]=a[:,0]
    if axes[1]: a[-1]=a[0]
    return Image.fromarray(a)


def finish_layers(f, maps, data):
    """Keep main normal immutable in both export modes. Produce composed previews."""
    b = normalized_breakup(data, getattr(f,'mode','UNIQUE_FACADE'))
    if b['mode']=='LEGACY_BAKED': return maps
    size=maps['albedo'].size; w,h=size
    macro,grime,grain,micro_normal=layer_sources(f,size)
    ids=np.asarray(f.semantic.material.resize(size,Image.Resampling.NEAREST))
    gain=np.ones((h,w),dtype=np.float32)
    for material,(_,_,_,variation,_) in MATERIAL_RESPONSE.items(): gain[ids==material]=variation
    a=np.asarray(maps['albedo'],dtype=np.float32).copy()
    orm=np.asarray(maps['orm'],dtype=np.float32).copy()
    macro_strength=b['macro_variation']; grime_strength=b['grime']; micro_strength=b['micro_grain']
    macro_tone=(macro*2-1)*.14*macro_strength*gain
    dirt=grime*grime_strength*gain
    micro=(grain*2-1)*.035*micro_strength*gain
    a*= (1+macro_tone-dirt*.40+micro)[...,None]
    a+=dirt[...,None]*np.array([2.,.5,-2.])
    palette=getattr(f,'palette_mix',{})
    if palette.get('enabled'):
        from palette_mixer import color
        # Remove the old fixed tint, retain dirt attenuation and all scalar maps.
        a-=dirt[...,None]*np.array([2.,.5,-2.])
        tint=color(palette['colors']['GRIME_TINT'])
        tint_luma=max(1,float(tint@np.array([.2126,.7152,.0722])))
        target=a*(tint/tint_luma)
        blend=np.clip(dirt*palette['weather_tint_influence']*.85,0,1)[...,None]
        a=a*(1-blend)+target*blend
    orm[...,1]+=dirt*28+micro*100
    orm[...,2]*=1-dirt*.4
    retro=b['retro_artifacts']; style=f.p.style
    if retro:
        rng=layer_rng(f,'retro')
        pixel=rng.normal(0,style.pixel_noise*5,(h,w))
        blocks=np.asarray(rgb(rng.uniform(-1,1,(max(2,h//8),max(2,w//8)))*30+128).resize(size,Image.Resampling.NEAREST),dtype=np.float32)-128
        bayer=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]],dtype=np.float32)/16-.5
        dither=np.tile(bayer,(math.ceil(h/4),math.ceil(w/4)))[:h,:w]
        step=255/(style.posterization-1)
        treated=a+(pixel+blocks*style.compression_artifacts+dither*step*style.dithering)[...,None]
        treated=np.round(treated/step)*step
        quantized=rgb(treated).quantize(colors=style.color_quantization,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB')
        a=a*(1-retro)+np.asarray(quantized,dtype=np.float32)*retro
    # Whiteout blend only for optional preview. Production _normal never changes.
    base=np.asarray(maps['normal'],dtype=np.float32)/255*2-1
    detail=micro_normal.copy(); detail[...,:2]*=micro_strength*gain[...,None]
    combined=np.dstack((base[...,:2]+detail[...,:2],base[...,2]*detail[...,2]))
    combined/=np.linalg.norm(combined,axis=-1,keepdims=True)
    maps.update(preview_albedo=rgb(a),preview_orm=rgb(orm),preview_normal=rgb((combined*.5+.5)*255),
        detail_albedo=rgb(np.repeat((128+(grain*2-1)*4.48)[...,None],3,axis=2)),
        detail_normal=rgb((micro_normal*.5+.5)*255),weather_mask=rgb(np.stack((macro,grime,grain),axis=-1)*255))
    if micro_strength==0: maps['preview_normal']=maps['normal'].copy()
    axes=getattr(f,'periodic',(False,False))
    for key in (*DETAIL_CHANNELS,*PREVIEW_CHANNELS):
        # All detail maps can repeat independently, even for a unique facade.
        maps[key]=close_edges(maps[key],(True,True) if key.startswith('detail_') else axes)
    if b['export_mode']=='BAKED':
        maps['albedo']=maps['preview_albedo']; maps['orm']=maps['preview_orm']
    return maps
