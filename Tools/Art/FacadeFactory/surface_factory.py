"""Additive periodic surface grammars. Does not call or replace facade grammar."""
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import random
import numpy as np
from PIL import Image, ImageDraw
from facade_factory import Facade, SURFACES, tint, write_material, VERSION
from facade_presets import FacadePreset, PALETTES
from facade_semantics import SemanticLayers, MaterialClass
from facade_art_profiles import apply_art, normalized_art, periodic_blur

TILE_PARAMETERS = {
    'tile_scale':[1,8,.25,'Tile scale','surface'],
    'panel_scale':[.5,2,.05,'Panel scale','surface'],
    'grout_width':[1,10,.5,'Grout width','surface'],
    'surface_wear':[0,1,.01,'Surface wear','surface'],
    'macro_variation':[0,1,.01,'Macro variation','surface'],
    'seam_visibility':[0,1,.01,'Seam visibility','surface'],
    'floor_markings_density':[0,1,.01,'Floor markings','surface'],
    'wall_module_density':[0,1,.01,'Wall module density','surface'],
}
CYLINDER_PARAMETERS = {
    'circumference_modules':[3,20,1,'Circumference modules','cylinder'],
    'vertical_band_count':[1,12,1,'Vertical band count','cylinder'],
    'ring_density':[0,1,.01,'Ring density','cylinder'],
    'vertical_seam_count':[0,20,1,'Vertical seam count','cylinder'],
    'service_hatch_density':[0,1,.01,'Service hatches','cylinder'],
    'emission_band_density':[0,1,.01,'Emission bands','cylinder'],
    'pipe_grime_flow':[0,1,.01,'Vertical grime flow','cylinder'],
}
TILE_PRESETS = {
    'TECH_WALL':dict(palette='cold',panel_scale=1,wall_module_density=.45),
    'INDUSTRIAL_FLOOR':dict(palette='industrial',panel_scale=1.3,floor_markings_density=.45,surface_wear=.66),
    'SERVICE_PANEL':dict(palette='industrial',panel_scale=1.4,wall_module_density=.68),
    'MEGABLOCK_WALL':dict(palette='concrete',panel_scale=1.4,wall_module_density=.2),
    'ROOF_SURFACE':dict(palette='cold',panel_scale=.8,wall_module_density=.15),
    'DARK_CONCRETE_TECH':dict(palette='concrete',panel_scale=1.8,wall_module_density=.16),
}
CYLINDER_PRESETS = {
    'PIPE_HEAVY':dict(palette='industrial',circumference_modules=6,vertical_band_count=3,ring_density=.85),
    'COLUMN_TECH':dict(palette='cold',circumference_modules=8,vertical_band_count=4,service_hatch_density=.42),
    'TANK_WRAP':dict(palette='industrial',circumference_modules=5,vertical_band_count=2,ring_density=.35),
    'VENT_SHAFT':dict(palette='cold',circumference_modules=6,vertical_band_count=5,service_hatch_density=.7),
    'REACTOR_CORE_WRAP':dict(palette='cold',circumference_modules=10,vertical_band_count=5,emission_band_density=.8),
    'EXOSKELETON_COLUMN':dict(palette='concrete',circumference_modules=8,vertical_band_count=4,ring_density=.6),
}
from surface_archetypes import TILE_LIBRARY, WRAP_LIBRARY, CATALOG, generate_archetype
TILE_PRESETS.update(TILE_LIBRARY)
CYLINDER_PRESETS.update(WRAP_LIBRARY)
SURFACE_PRESETS={**TILE_PRESETS,**CYLINDER_PRESETS}
BASE_TILE=dict(tile_scale=1,panel_scale=1,grout_width=3,surface_wear=.5,macro_variation=.55,seam_visibility=.45,floor_markings_density=.1,wall_module_density=.35)
BASE_CYLINDER=dict(circumference_modules=8,vertical_band_count=4,ring_density=.55,vertical_seam_count=8,service_hatch_density=.25,emission_band_density=.15,pipe_grime_flow=.65)


def surface_defaults(name):
    if name not in SURFACE_PRESETS: raise ValueError('Unknown surface preset')
    item=SURFACE_PRESETS[name]
    base=dict(BASE_TILE if name in TILE_PRESETS else BASE_CYLINDER)
    base.update({k:v for k,v in item.items() if k!='palette'})
    return base


class SurfaceCanvas(Facade):
    def __init__(self,name,seed,parameters,palette=None,tile_mode=None,style=None):
        self.name=name; self.mode='TILEABLE_SURFACE' if name in TILE_PRESETS else 'CYLINDER_WRAP'
        self.tile_mode='FULL_2D_TILE' if self.mode=='TILEABLE_SURFACE' else (tile_mode or 'HORIZONTAL_WRAP_ONLY')
        self.periodic=(True,self.tile_mode=='FULL_2D_TILE')
        self.p=FacadePreset(name=name,grammar='surface',palette=palette or SURFACE_PRESETS[name]['palette'],macro_contrast=0)
        if style:
            from dataclasses import replace
            self.p=replace(self.p,style=replace(self.p.style,**style))
        self.seed=seed; self.params=parameters; self.pal=PALETTES[self.p.palette]
        if name=='DARK_CONCRETE_TECH':
            self.pal={key:tint(value,.59) if key in ('base','concrete') else value for key,value in self.pal.items()}
        self.size=(512,512 if self.mode=='TILEABLE_SURFACE' else 1024)
        base=tint(self.pal['concrete'],.55) if name=='DARK_CONCRETE_TECH' else self.pal['base']
        self.albedo=Image.new('RGB',self.size,base); self.emission=Image.new('RGB',self.size)
        self.height=Image.new('L',self.size,128); self.orm=Image.new('RGB',self.size,(245,210,8))
        self.draws=[ImageDraw.Draw(i) for i in (self.albedo,self.emission,self.height,self.orm)]
        self.semantic=SemanticLayers(self.size,seed,name,self.pal)
        self.surface_wear=parameters.get('surface_wear',.6)
        self.pipe_grime_flow=parameters.get('pipe_grime_flow',.65)
        digest=hashlib.sha256(f'SURFACE_STRUCTURE:1:{seed}:{name}'.encode()).digest()
        self.rng=random.Random(int.from_bytes(digest[:8],'big'))

    def rect(self,box,color,surface='paint',emission=None,height=None,outline=False,edge=False):
        w,h=self.size
        for dx in (-w,0,w):
            for dy in (-h,0,h) if self.periodic[1] else (0,):
                bounds=(box[0]+dx,box[1]+dy,box[2]+dx,box[3]+dy)
                if bounds[2]<0 or bounds[0]>=w or bounds[3]<0 or bounds[1]>=h: continue
                Facade.rect(self,bounds,color,surface,emission,height,outline,edge)

    def plate(self,box,material='paint',vent=False):
        x0,y0,x1,y1=box; rng=self.rng
        base=tint(self.pal['concrete' if material=='concrete' else 'metal' if material=='metal' else 'base'],rng.uniform(.91,1.07))
        old=self.semantic.begin(box,'vent' if vent else 'panel',base)
        self.rect(box,self.pal['recess'],'recess',outline=True)
        grout=self.params.get('grout_width',2)
        self.rect((x0+grout,y0+grout,x1-grout,y1-grout),base,material,height=142)
        self.rect((x0+grout,y0+grout,x1-grout,y0+grout+1),tint(base,1.1),material,edge=True)
        if vent:
            for yy in np.arange(y0+8,y1-8,8):
                self.rect((x0+8,yy,x1-8,yy+2),tint(self.pal['recess'],1.15),'recess',height=108)
        for x in (x0+grout+5,x1-grout-6):
            for y in (y0+grout+5,y1-grout-6):
                self.rect((x,y,x+2,y+2),tint(base,.48),'metal',height=131)
        self.semantic.end(old)

    def tile_structure(self):
        p=self.params; name=self.name; rng=self.rng
        if name=='ROOF_SURFACE': cols,rows=round(8/p['panel_scale']),1
        elif name=='INDUSTRIAL_FLOOR': cols,rows=round(3/p['panel_scale']),round(3/p['panel_scale'])
        elif name=='DARK_CONCRETE_TECH': cols,rows=2,2
        else: cols,rows=round((2+p['wall_module_density']*2)/p['panel_scale']),round(3/p['panel_scale'])
        cols=max(1,cols); rows=max(1,rows); cw,ch=512/cols,512/rows
        material='concrete' if name in ('MEGABLOCK_WALL','DARK_CONCRETE_TECH') else 'metal' if name=='ROOF_SURFACE' else 'paint'
        self.rect((0,0,511,511),self.pal['concrete' if material=='concrete' else 'base'],material)
        # Half-cell offset puts some modules across the texture boundary; the same
        # module ID/finish is recorded on both sides by toroidal drawing.
        for row in range(rows):
            for col in range(cols):
                x=col*cw-cw*.28; y=row*ch-ch*.21
                self.plate((x,y,x+cw-1,y+ch-1),material)
                if name=='INDUSTRIAL_FLOOR':
                    for yy in np.arange(y+14,y+ch-10,17):
                        for xx in np.arange(x+14,x+cw-10,19):
                            self.rect((xx,yy,xx+6,yy+1),tint(self.pal['metal'],.83),'metal',height=145)
                elif name=='SERVICE_PANEL' or rng.random()<p['wall_module_density']:
                    if material!='concrete' or rng.random()<.28:
                        self.plate((x+cw*.22,y+ch*.27,x+cw*.82,y+ch*.70),'metal',vent=name in ('TECH_WALL','SERVICE_PANEL'))
                if rng.random()<p['floor_markings_density']:
                    for xx in np.arange(x+8,x+cw-15,18):
                        self.rect((xx,y+ch-13,xx+9,y+ch-8),tint(self.pal['warm'],.85),'paint',height=143)
        if name in ('TECH_WALL','DARK_CONCRETE_TECH'):
            for x in (64,74):
                self.rect((x,0,x+4,512),tint(self.pal['metal'],.66),'metal',height=159)
        if name=='ROOF_SURFACE':
            self.plate((179,163,229,227),'metal',True)
        return self

    def cylinder_structure(self):
        p=self.params; rng=self.rng; n=int(p['circumference_modules']); bands=int(p['vertical_band_count'])
        cw,bh=512/n,1024/bands
        material='metal' if self.name in ('PIPE_HEAVY','VENT_SHAFT') else 'paint'
        for band in range(bands):
            for col in range(n):
                x=col*cw-cw*.37; y=band*bh-bh*.23
                self.plate((x,y,x+cw-1,y+bh-1),material,vent=self.name=='VENT_SHAFT')
                if rng.random()<p['service_hatch_density']:
                    self.plate((x+cw*.18,y+bh*.3,x+cw*.82,y+bh*.60),'metal',self.name=='VENT_SHAFT')
                if self.name=='COLUMN_TECH' and col%3==0:
                    self.rect((x+cw*.5,y+22,x+cw*.5+3,y+bh-24),tint(self.pal['metal'],.7),'metal',height=164)
        for i in range(max(1,round(2+p['ring_density']*14))):
            y=i*1024/max(1,round(2+p['ring_density']*14))+29
            width=11 if self.name=='PIPE_HEAVY' else 5
            self.rect((0,y-2,512,y+width+2),self.pal['recess'],'recess',height=112)
            self.rect((0,y,512,y+width),tint(self.pal['metal'],.86),'metal',height=166)
            self.rect((0,y,512,y+1),tint(self.pal['metal'],1.1),'metal',height=169,edge=True)
        for i in range(int(p['vertical_seam_count'])):
            x=i*512/max(1,p['vertical_seam_count'])+17
            self.rect((x,0,x+1,1024),tint(self.pal['base'],.72),'metal',height=137)
        for i in range(bands):
            if rng.random()<p['emission_band_density']:
                y=(i+.63)*bh
                self.rect((0,y-3,512,y+7),self.pal['recess'],'recess',height=115)
                self.rect((0,y,512,y+3),tint(self.pal['accent'],.55),'glass',tint(self.pal['accent'],.48),height=125)
        if self.name=='EXOSKELETON_COLUMN':
            for band in range(bands):
                for col in range(n):
                    x=col*cw-cw*.37; y=band*bh
                    for direction in (-1,1):
                        for yy in np.arange(y,y+bh,2):
                            xx=x+direction*(yy-y)/bh*cw
                            self.rect((xx-3,yy,xx+3,yy+3),tint(self.pal['metal'],.91),'metal',height=178)
        if not self.periodic[1]:
            self.rect((0,0,512,18),tint(self.pal['metal'],.65),'metal',height=163)
            self.rect((0,1005,512,1023),tint(self.pal['metal'],.65),'metal',height=163)
        return self

    def generate(self):
        if self.name in CATALOG: return generate_archetype(self)
        return self.tile_structure() if self.mode=='TILEABLE_SURFACE' else self.cylinder_structure()


def periodic_resize(image,size,axes):
    # Export a closed periodic domain. The duplicated endpoint also makes seam
    # equality auditable byte-for-byte; interior filtering is wrap-aware.
    core_size=(size[0]-int(axes[0]),size[1]-int(axes[1]))
    core=np.asarray(image.resize(core_size,Image.Resampling.NEAREST))
    return close_domain(core,axes)


def close_domain(core,axes):
    if axes[0]: core=np.concatenate([core,core[:,:1]],axis=1)
    if axes[1]: core=np.concatenate([core,core[:1]],axis=0)
    return Image.fromarray(np.uint8(core))


def surface_normal(height,axes,strength=.24,design_size=(512,1024)):
    core=np.asarray(height)[:height.height-int(axes[1]),:height.width-int(axes[0])]
    smooth=periodic_blur(Image.fromarray(core),max(.55,height.width/700),axes)
    values=np.asarray(smooth,dtype=np.float32)/255
    dx=(np.roll(values,-1,1)-np.roll(values,1,1))*.5
    dy=(np.roll(values,-1,0)-np.roll(values,1,0))*.5 if axes[1] else np.gradient(values,axis=0)
    n=np.stack((-dx*height.width/design_size[0]*strength*8,dy*height.height/design_size[1]*strength*8,np.ones_like(values)),axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return close_domain(np.uint8(np.clip(n*.5+.5,0,1)*255+.5),axes)


def seam_qa(maps,axes):
    report={}
    for channel,image in maps.items():
        a=np.asarray(image,dtype=np.int16)
        report[channel]={'x_max_delta':int(np.abs(a[:,0]-a[:,-1]).max()),
                         'y_max_delta':int(np.abs(a[0]-a[-1]).max()) if axes[1] else None}
    return dict(axes=['X','Y'] if axes[1] else ['X'],channels=report,
                passed=all(v['x_max_delta']==0 and (v['y_max_delta'] in (None,0)) for v in report.values()))


def make_reviews(albedo,mode):
    tile=albedo.resize((256,256 if mode=='TILEABLE_SURFACE' else 512),Image.Resampling.NEAREST)
    patch=Image.new('RGB',(tile.width*3,tile.height*3))
    for y in range(3):
        for x in range(3): patch.paste(tile,(x*tile.width,y*tile.height))
    debug=patch.copy(); d=ImageDraw.Draw(debug)
    for x in (tile.width,tile.width*2): d.line((x,0,x,debug.height),fill=(231,177,67),width=1)
    for y in (tile.height,tile.height*2): d.line((0,y,debug.width,y),fill=(231,177,67),width=1)
    if mode=='TILEABLE_SURFACE': preview=patch
    else:
        source=np.asarray(albedo); yy,xx=np.mgrid[:768,:512]; nx=(xx-256)/174
        mask=np.abs(nx)<1; theta=np.arcsin(np.clip(nx,-1,1))
        u=np.mod(theta/(2*np.pi),1); v=np.clip((yy-30)/704,0,1)
        rgb=source[(v*(source.shape[0]-1)).astype(int),(u*(source.shape[1]-1)).astype(int)].astype(float)
        rgb*= (.38+.62*np.sqrt(np.clip(1-nx*nx,0,1)))[...,None]
        rgb[~(mask & (yy>=30) & (yy<734))]=[18,25,28]
        preview=Image.fromarray(np.uint8(np.clip(rgb,0,255)))
    return preview,patch,debug


def generate_surface(name,seed,width,height,output,parameters=None,art=None,palette=None,tile_mode=None,style=None,breakup=None,palette_mix=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    params=surface_defaults(name); params.update(parameters or {})
    f=SurfaceCanvas(name,seed,params,palette,tile_mode,style).generate()
    art=normalized_art(art or {'profile':'BOW_BASE'})
    if art['profile']=='LEGACY': art=normalized_art({'profile':'BOW_BASE','material_mix':0,'weathering':0})
    # Surface-specific physical controls modulate the shared global profile.
    applied=dict(art,overrides=dict(art['overrides']))
    if name in TILE_PRESETS:
        applied['overrides']['material_variation']=art['controls']['material_variation']*(.35+.65*params['macro_variation'])
        applied['overrides']['seam_contrast']=art['controls']['seam_contrast']*.35+params['seam_visibility']*.65
    from surface_breakup import normalized_breakup, clean_material, finish_layers
    breakup=normalized_breakup(breakup,f.mode)
    maps,resolved,stats=(clean_material(f,applied) if breakup['mode']=='LAYERED' else apply_art(f,applied))
    from palette_mixer import apply_palette, normalized_palette
    f.palette_mix=normalized_palette(palette_mix,f.p.palette)
    if f.palette_mix['enabled'] and breakup['mode']!='LAYERED': raise ValueError('Palette Mixer requires Layered pipeline')
    maps=apply_palette(f,maps,f.palette_mix)
    maps={k:periodic_resize(v,(width,height),f.periodic) for k,v in maps.items()}
    maps['normal']=surface_normal(maps['height'],f.periodic,design_size=f.size)
    maps=finish_layers(f,maps,breakup)
    qa=seam_qa(maps,f.periodic)
    if not qa['passed']: raise ValueError('Seam QA failed')
    stem=f'{name.lower()}_s{seed}_{width}x{height}'
    hashes={}
    for channel,image in maps.items():
        path=output/f'{stem}_{channel}.png'; image.save(path,compress_level=6)
        hashes[channel]=hashlib.sha256(path.read_bytes()).hexdigest()
    preview,patch,debug=make_reviews(maps['albedo'],f.mode)
    for key,image in [('preview',preview),('tiled_preview',patch),('seam_debug',debug)]: image.save(output/f'{stem}_{key}.png')
    metadata=dict(version=VERSION,surface_mode=f.mode,preset=name,seed=seed,resolution=[width,height],parameters=params,breakup=breakup,palette_mix=f.palette_mix,
        tile_mode=f.tile_mode,periodic_axes=qa['axes'],art=art,applied_art=resolved,art_statistics=stats,seam_qa=qa,
        structure_hash=hashlib.sha256(f.height.tobytes()+f.emission.tobytes()).hexdigest(),sha256=hashes)
    (output/f'{stem}.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return dict(stem=stem,albedo=str(output/f'{stem}_albedo.png'),preset=name,seed=seed,sha256=hashes,seam_qa=qa)
