"""Semantic color binding, independent of architecture, weather masks and normals."""
import colorsys
import copy
import math
import random
import re
import numpy as np
from PIL import Image
from facade_semantics import MaterialClass, SeamClass
from facade_art_profiles import MATERIAL_RESPONSE

ROLES = ('BASE','SECONDARY','DARK','ACCENT','GLASS','EMISSION_PRIMARY','EMISSION_SECONDARY','GRIME_TINT')
PALETTE_VERSION = '1.0'
INFLUENCES = {
    'albedo_influence':[0,1,.01,'Albedo Palette Influence'],
    'emission_influence':[0,1,.01,'Emission Palette Influence'],
    'weather_tint_influence':[0,1,.01,'Weather Tint Influence'],
    'material_variation_influence':[0,1,.01,'Material Variation Influence'],
    'accent_usage':[0,1,.01,'Accent color usage'],
    'colored_balance':[0,1,.01,'Neutral to colored balance'],
    'structural_separation':[0,1,.01,'Structural color separation'],
    'orm_influence':[0,1,.01,'Palette material response (ORM)'],
}
ROLE_WEIGHTS = {
    'PAINTED_METAL': {'BASE':.76,'SECONDARY':.20,'ACCENT':.04},
    'RAW_METAL': {'DARK':.15,'BASE':.85},
    'GLASS': {'GLASS':.92,'BASE':.08},
    'CONCRETE': {'BASE':.65,'SECONDARY':.35},
    'VENT': {'DARK':1.}, 'RECESSED_VOID': {'DARK':1.},
    'SIGNAGE': {'ACCENT':1.},
    'EMISSIVE': {'EMISSION_PRIMARY':.75,'EMISSION_SECONDARY':.25},
}
SWATCHES = {
    'NEUTRAL_COLD': ('#657780','#889496','#19262e','#839e9f','#283e4c','#93c8d2','#b9b38a','#4b4840'),
    'INDUSTRIAL_GREEN': ('#626f5e','#818774','#20291f','#b0a070','#263d35','#a5c8a6','#d0b276','#4e4934'),
    'DIRTY_CONCRETE': ('#77766a','#929084','#252c2b','#aa976e','#343e40','#bdc6b8','#d0b184','#514737'),
    'CORPORATE_CYAN': ('#5b7079','#859699','#182830','#5b9b9f','#233f4c','#78c4cb','#aabdaf','#3d4b48'),
    'WARNING_ORANGE': ('#706c63','#918675','#222727','#b9753f','#2c3d42','#c8b08b','#cb8b50','#584631'),
    'OXIDIZED_GREEN': ('#51675e','#7b8170','#1e2927','#829c83','#273e3b','#a4c3b2','#c0b186','#4a4b35'),
    'COLD_MONO': ('#697277','#8c969a','#20272b','#a3afb2','#303e46','#b3c5ce','#8ca8b5','#45494b'),
    'BLACK_RED_TECH': ('#303a40','#515d60','#141c20','#924942','#24353d','#b86254','#bd996d','#443a34'),
}
SCALARS = {m.name: {'roughness':values[1], 'metallic':values[2], 'ao_response':1.}
           for m,values in MATERIAL_RESPONSE.items()}
SCALARS['ACCENT_PAINT'] = dict(roughness=.74, metallic=.035, ao_response=1.)
PRESETS = {name:dict(colors=dict(zip(ROLES,colors)),material_responses=copy.deepcopy(SCALARS)) for name,colors in SWATCHES.items()}
PRESETS['WARNING_ORANGE']['material_responses']['ACCENT_PAINT']['roughness']=.70
PRESETS['OXIDIZED_GREEN']['material_responses']['RAW_METAL'].update(roughness=.64,metallic=.65)
PRESETS['BLACK_RED_TECH']['material_responses']['PAINTED_METAL']['roughness']=.71
FAMILY_PRESET = {'cold':'NEUTRAL_COLD','industrial':'INDUSTRIAL_GREEN','concrete':'DIRTY_CONCRETE'}


def normalized_palette(data=None, family='cold', enabled=False):
    if data is None: data={}
    fields={'enabled','preset','colors','locks','material_responses','version',*INFLUENCES}
    if not isinstance(data,dict) or set(data)-fields: raise ValueError('Unknown palette mixer field')
    name=data.get('preset',FAMILY_PRESET[family])
    if name not in PRESETS: raise ValueError('Unknown semantic palette preset')
    result=dict(enabled=data.get('enabled',enabled),preset=name,version=PALETTE_VERSION,
        colors=copy.deepcopy(PRESETS[name]['colors']),locks={key:False for key in ROLES},
        material_responses=copy.deepcopy(PRESETS[name]['material_responses']),
        albedo_influence=1.,emission_influence=1.,weather_tint_influence=.25,material_variation_influence=1.)
    result.update(accent_usage=1.,colored_balance=1.,structural_separation=1.,orm_influence=1.)
    if not isinstance(result['enabled'],bool): raise ValueError('palette enabled must be boolean')
    for group in ('colors','locks','material_responses'):
        values=data.get(group,{})
        if not isinstance(values,dict) or set(values)-set(result[group]): raise ValueError(f'Unknown palette {group}')
        for key,value in values.items():
            if group=='colors':
                if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value): raise ValueError('Palette colors require #RRGGBB')
                result[group][key]=value.lower()
            elif group=='locks':
                if not isinstance(value,bool): raise ValueError('Palette locks require boolean')
                result[group][key]=value
            else:
                if not isinstance(value,dict) or set(value)-{'roughness','metallic','ao_response'}: raise ValueError('Unknown material scalar')
                for prop,number in value.items():
                    checked(number,f'{key}.{prop}',2 if prop=='ao_response' else 1)
                    result[group][key][prop]=number
    for key in INFLUENCES:
        if key in data: checked(data[key],key); result[key]=data[key]
    return result


def checked(value,key,maximum=1):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=maximum:
        raise ValueError(f'Palette {key}: expected 0..{maximum}')


def randomize_palette(data, random_seed):
    p=normalized_palette(data); rng=random.Random(random_seed)
    hue=rng.random(); hue_shift=rng.uniform(-.10,.10)
    # Shared hue family, neutral base, one warm/cool restrained accent.
    for i,role in enumerate(ROLES):
        if p['locks'][role]: continue
        saturation=rng.uniform(.07,.18) if role in ('BASE','SECONDARY','DARK') else rng.uniform(.18,.42)
        value=rng.uniform(.28,.49) if role=='BASE' else rng.uniform(.43,.61) if role=='SECONDARY' else rng.uniform(.07,.17) if role=='DARK' else rng.uniform(.13,.27) if role=='GLASS' else rng.uniform(.21,.34) if role=='GRIME_TINT' else rng.uniform(.46,.72)
        color=colorsys.hsv_to_rgb((hue+(hue_shift if i%2 else 0))%1,saturation,value)
        p['colors'][role]='#'+''.join(f'{round(channel*255):02x}' for channel in color)
    return p


def color(hex_value):
    return np.array([int(hex_value[i:i+2],16) for i in (1,3,5)],dtype=np.float32)


def apply_palette(f,maps,data):
    p=normalized_palette(data,f.p.palette)
    if not p['enabled']: return maps
    sem=f.semantic; ids=np.asarray(sem.material); module=np.asarray(sem.module); seams=np.asarray(sem.seam)
    a=np.asarray(maps['albedo'],dtype=np.float32); source_orm=np.asarray(maps['orm'],dtype=np.float32);orm=source_orm.copy()
    luminance=np.array([.2126,.7152,.0722],dtype=np.float32)
    source_luma=a@luminance
    mixed=a.copy(); role_mask=np.zeros(ids.shape,dtype=np.uint8)
    finishes=np.array([.1]+[m['finish'] for m in sem.modules],dtype=np.float32)[module]
    for material,(old_role,rough,metal,variation,edge) in MATERIAL_RESPONSE.items():
        mask=ids==material
        reference=max(1,float(np.array(f.pal[old_role])@luminance))
        shading=np.clip(source_luma/reference,.03,2.8)
        # Preserve authored module value/edge/shading; this is not a global tint.
        cutoff=0.
        for role,weight in ROLE_WEIGHTS[material.name].items():
            selected=mask & (finishes>=cutoff) & (finishes<cutoff+weight+1e-6); cutoff+=weight
            target=color(p['colors'][role])
            if role=='ACCENT':target=color(p['colors']['BASE'])*(1-p['accent_usage'])+target*p['accent_usage']
            if role=='SECONDARY':target=color(p['colors']['BASE'])*(1-p['structural_separation'])+target*p['structural_separation']
            if material==MaterialClass.RAW_METAL: target=target*.15+(target@luminance)*.85
            elif material==MaterialClass.CONCRETE: target=target*.55+(target@luminance)*.45
            # This controls extra module finish variance, never baked shading.
            local_shade=shading*(1+(finishes-.5)*.12*p['material_variation_influence'])
            mixed[selected]=(target*local_shade[...,None])[selected]
            role_mask[selected]=ROLES.index(role)+1
        scalar=p['material_responses'][material.name]
        orm[...,1][mask]=np.clip(orm[...,1][mask]+255*(scalar['roughness']-rough),0,255)
        orm[...,2][mask]=np.clip(orm[...,2][mask]+255*(scalar['metallic']-metal),0,255)
        orm[...,0][mask]=255-(255-orm[...,0][mask])*scalar['ao_response']
    # Joins retain their original relative depth. Only deep voids bind DARK.
    seam_base=np.asarray(sem.seam_base,dtype=np.float32)@luminance
    ratio=source_luma/np.maximum(seam_base,1)
    for seam in SeamClass:
        selected=seams==seam; role='DARK' if seam==SeamClass.DEEP_RECESS else 'BASE'
        mixed[selected]=(color(p['colors'][role])*ratio[...,None])[selected]
    signage=np.asarray(sem.signage)>0
    if signage.any():
        shade=np.clip(source_luma/max(1,float(np.array(f.pal['warm'])@luminance)),.1,1.7)
        accent=color(p['colors']['BASE'])*(1-p['accent_usage'])+color(p['colors']['ACCENT'])*p['accent_usage']
        mixed[signage]=(accent*shade[...,None])[signage]
        role_mask[signage]=ROLES.index('ACCENT')+1
        response=p['material_responses']['ACCENT_PAINT']
        orm[...,1][signage]=response['roughness']*255
        orm[...,2][signage]=response['metallic']*255
    influence=p['albedo_influence']
    mixed=(mixed@luminance)[...,None]*(1-p['colored_balance'])+mixed*p['colored_balance']
    maps['albedo']=Image.fromarray(np.uint8(np.clip(a*(1-influence)+mixed*influence,0,255)+.5))
    orm=source_orm*(1-p['orm_influence'])+orm*p['orm_influence']
    maps['orm']=Image.fromarray(np.uint8(np.clip(orm,0,255)+.5))
    emission=np.asarray(maps['emission'],dtype=np.float32)
    mask=emission.max(axis=-1); roles=np.asarray(sem.emission_role)
    target=np.zeros_like(emission)
    for index,role in ((1,'EMISSION_PRIMARY'),(2,'EMISSION_SECONDARY')):
        rgb=color(p['colors'][role]); rgb=rgb/max(1,float(rgb.max()))
        selected=(mask>0)&((roles==index) if index==2 else (roles!=2))
        target[selected]=(mask[...,None]*rgb)[selected]
    blend=p['emission_influence']
    blended=emission*(1-blend)+target*blend
    # Color interpolation must not silently dim the separate source intensity.
    blended*= (mask/np.maximum(blended.max(axis=-1),1))[...,None]
    maps['emission']=Image.fromarray(np.uint8(np.clip(blended,0,255)+.5))
    maps['emission_mask']=Image.fromarray(np.uint8(mask))
    return maps
