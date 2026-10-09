"""Build the 50 authored recipes, compact production maps and bounded QA.

python Tools/Art/FacadeFactory/build_material_library.py
All owned outputs are listed in the manifest. Existing gameplay assets untouched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'WebLab'))
from lab_backend import normalized_request, make_recipe, load_recipe, render_recipe, FINGERPRINT
from material_library import authored_request
from surface_archetypes import CATALOG
from surface_factory import seam_qa, make_reviews

OUTPUT=ROOT/'Assets/ProceduralArt/Materials'
SOURCES=ROOT/'Tools/Art/Library/materials'
REVIEWS=ROOT/'Tools/Art/ArtPass/review'
CHANNELS=('albedo','normal','orm','height','emission')


def guard():
    free=shutil.disk_usage(ROOT).free
    if free<15*1024**3:raise RuntimeError('Material batch stopped: disk below 15 GiB')
    return free<25*1024**3


def uri(path):return 'res://'+Path(path).relative_to(ROOT).as_posix()


def write_material(directory,name):
    channels=('albedo','normal','orm','emission')
    refs='\n'.join(f'[ext_resource type="Texture2D" path="{uri(directory/(c+".png"))}" id="{i+1}"]' for i,c in enumerate(channels))
    (directory/'material.tres').write_text(f'''[gd_resource type="ORMMaterial3D" load_steps=5 format=3]

{refs}

[resource]
resource_name = "{name}"
albedo_texture = ExtResource("1")
normal_enabled = true
normal_texture = ExtResource("2")
normal_scale = 0.55
orm_texture = ExtResource("3")
ao_enabled = true
ao_light_affect = 0.18
emission_enabled = true
emission = Color(1, 1, 1, 1)
emission_operator = 1
emission_texture = ExtResource("4")
emission_energy_multiplier = 1.15
texture_filter = 5
texture_repeat = true
''',encoding='utf-8')


def compact_thumb(image,wrap=False):
    if wrap:
        image=make_reviews(image,'CYLINDER_WRAP')[0]
    thumb=Image.new('RGB',(192,192),(17,24,27))
    image=image.copy();image.thumbnail((192,192),Image.Resampling.LANCZOS)
    thumb.paste(image,((192-image.width)//2,(192-image.height)//2))
    return thumb


def sheet(items,path,title,cols=4,tile=256):
    rows=(len(items)+cols-1)//cols
    canvas=Image.new('RGB',(cols*tile,rows*(tile+37)+54),(17,23,27));d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
    titlefont=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',18)
    d.text((14,16),title,font=titlefont,fill=(188,203,198))
    for i,(name,img) in enumerate(items):
        x=(i%cols)*tile;y=54+(i//cols)*(tile+37)
        img=img.copy();img.thumbnail((tile-12,tile-12),Image.Resampling.LANCZOS)
        canvas.paste(img,(x+(tile-img.width)//2,y+(tile-img.height)//2))
        d.text((x+7,y+tile+3),name.replace('_',' ')[:30],font=font,fill=(183,191,185))
    path.parent.mkdir(parents=True,exist_ok=True);canvas.save(path,quality=88)


def generation(request,directory):
    preset,recipe=normalized_request(request)
    result=render_recipe(preset,recipe,directory)
    result['structure_hash']=json.loads((directory/(result['stem']+'.json')).read_text(encoding='utf-8'))['structure_hash']
    maps={c:Image.open(directory/(result['stem']+'_'+c+'.png')).copy() for c in CHANNELS}
    return recipe,result,maps


def run():
    start=time.monotonic();free_before=shutil.disk_usage(ROOT).free
    parser=argparse.ArgumentParser();parser.add_argument('--only',nargs='*');args=parser.parse_args()
    selected=args.only or list(CATALOG)
    OUTPUT.mkdir(parents=True,exist_ok=True);SOURCES.mkdir(parents=True,exist_ok=True);REVIEWS.mkdir(parents=True,exist_ok=True)
    records=[];qa=[];all_thumbs=[]
    with tempfile.TemporaryDirectory(prefix='bow-materials-') as temp:
        temporary=Path(temp)
        for i,name in enumerate(selected):
            reduced=guard();item=CATALOG[name];target=OUTPUT/item['id'];target.mkdir(exist_ok=True)
            request=authored_request(name)
            if reduced:request['resolution']=[512,512] if item['category']!='wrap' else [512,1024]
            # Reuse one transient directory. Only generator-owned files reside here.
            for p in temporary.iterdir():
                if p.is_file():p.unlink()
            recipe,result,maps=generation(request,temporary)
            hashes={}
            for c,img in maps.items():
                # Preserve canonical PNG bytes, so WebLab replay SHA matches too.
                shutil.copyfile(temporary/(result['stem']+'_'+c+'.png'),target/(c+'.png'))
                hashes[c]=hashlib.sha256((target/(c+'.png')).read_bytes()).hexdigest()
            write_material(target,name)
            thumb=compact_thumb(maps['albedo'],item['category']=='wrap');thumb.save(target/'preview.webp',quality=86,method=6)
            all_thumbs.append((item['id'],thumb))
            metadata=make_recipe(recipe,name,outputs={c:uri(target/(c+'.png')) for c in CHANNELS},hashes=hashes)
            metadata.update(library=dict(**item,preset=name),material=uri(target/'material.tres'))
            recipe_path=SOURCES/(item['id']+'.facade.json');recipe_path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
            loaded=load_recipe(json.loads(recipe_path.read_text(encoding='utf-8')))
            assert loaded==recipe,'Recipe round trip changed effective settings'
            axes=(True,item['category']!='wrap');seams=seam_qa(maps,axes)
            normal=np.asarray(maps['normal'],dtype=float)/255*2-1
            normal_error=float(np.abs(np.linalg.norm(normal,axis=2)-1).max())
            assert seams['passed'] and normal_error<.015
            qa.append(dict(preset=name,seam=seams,normal_unit_error=normal_error,recipe_round_trip=True,
                resolution=list(maps['albedo'].size),sha256=hashes,structure_hash=result.get('structure_hash')))
            records.append(dict(**item,preset=name,resolution=list(maps['albedo'].size),material=uri(target/'material.tres'),
                recipe=recipe_path.relative_to(ROOT).as_posix(),preview=(target/'preview.webp').relative_to(ROOT).as_posix(),sha256=hashes))
            print(f'{i+1:02d}/{len(selected)} {name} PASS',flush=True)
        # Representative replay, seed response, palette isolation and layer off.
        behavioral=[]
        for name in ('WALL_TECH_SPINE','FLOOR_GRATED','CEILING_TECH','WRAP_REACTOR_CORE','ACCENT_CONTROL_CONSOLE'):
            if name not in selected:continue
            req=authored_request(name);r,a,base=generation(req,temporary)
            _,b,again=generation(req,temporary)
            assert a['sha256']==b['sha256'],'Replay is not deterministic'
            changed={**req,'seed':req['seed']+1};_,c,seed=generation(changed,temporary)
            assert a['sha256']['albedo']!=c['sha256']['albedo'],'Seed does not change finish'
            pal={**req,'palette_mix':{**req['palette_mix'],'preset':'WARNING_ORANGE','accent_usage':.1,'colored_balance':.35}}
            _,d,color=generation(pal,temporary)
            assert all(base[c].tobytes()==color[c].tobytes() for c in ('height','normal')),'Palette contaminated geometry data'
            assert base['albedo'].tobytes()!=color['albedo'].tobytes()
            clean={**req,'breakup':{**req['breakup'], 'grime':0,'micro_grain':0,'macro_variation':0,'retro_artifacts':0}}
            _,e,cleanmaps=generation(clean,temporary)
            assert all(base[c].tobytes()==cleanmaps[c].tobytes() for c in ('height','normal')),'Layer affected structural geometry'
            assert base['albedo'].tobytes()!=cleanmaps['albedo'].tobytes()
            behavioral.append(dict(preset=name,exact_replay=True,seed_response=True,palette_isolation=True,clean_layer_control=True))
    # Persist bounded review only. No intermediate generation is left in project.
    best=['wall_tech_spine','wall_corporate','wall_reactor_housing','wall_vent_bank','floor_diamond_deck','floor_grated',
        'floor_hazard_crossing','ceiling_light_baffle','accent_control_console','accent_access_door','accent_datacenter','accent_dark_monolith']
    def albedo(key):return Image.open(OUTPUT/key/'albedo.png').convert('RGB')
    if not args.only:
        sheet([(key,albedo(key)) for key in best],REVIEWS/'materials_best_12.jpg','BOW / INDUSTRIAL MATERIALS / 12 REPRESENTATIVES')
        tiles=['floor_grated','wall_megablock','floor_diamond_deck','ceiling_ventilation']
        sheet([(key,make_reviews(albedo(key),'TILEABLE_SURFACE')[1]) for key in tiles],REVIEWS/'materials_tiles_4.jpg','BOW / FULL X + Y REPEAT / 3 x 3',cols=2,tile=420)
        wraps=['wrap_heavy_pipe','wrap_reactor_core','wrap_exoskeleton','wrap_conduit_cluster']
        sheet([(key,make_reviews(albedo(key),'CYLINDER_WRAP')[0]) for key in wraps],REVIEWS/'materials_wraps_4.jpg','BOW / CYLINDER WRAP / X CONTINUITY',cols=4,tile=320)
    sheet(all_thumbs,REVIEWS/'materials_catalog_50.jpg','BOW / 50 AUTHORED INDUSTRIAL RECIPES',cols=10,tile=160)
    unique=len({r['sha256']['height'] for r in records})
    if len(selected)==50:assert unique==50,'Recipes must have distinct structural height fields'
    report=dict(schema='bowprototype.material-library.qa',passed=True,count=len(records),distinct_structures=unique,
        category_counts=dict(Counter(r['category'] for r in records)),behavioral=behavioral,materials=qa,
        free_before=free_before,free_after=shutil.disk_usage(ROOT).free,elapsed_seconds=round(time.monotonic()-start,1),
        output_bytes=sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()),fingerprint=FINGERPRINT,
        godot_validation='Pending lead import and material load; see ArtPass runtime report')
    (OUTPUT/'manifest.json').write_text(json.dumps(dict(schema='bowprototype.material-library',version=1,materials=records),indent=2)+'\n',encoding='utf-8')
    (REVIEWS/'materials_qa.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('materials','behavioral')},indent=2))


if __name__=='__main__':run()
