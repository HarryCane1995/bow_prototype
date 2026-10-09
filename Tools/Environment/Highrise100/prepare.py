"""Bounded material snapshot using the project's canonical Surface/Facade Factory."""
from pathlib import Path
import sys, json, shutil, hashlib, tempfile
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(ROOT/'Tools/Art/FacadeFactory/WebLab'))
from lab_backend import normalized_request, render_recipe, make_recipe

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'.gdignore').write_text('')
    for name in ('Textures','Recipes','Previews','QA','Logs','GodotSanity'):(OUT/name).mkdir(exist_ok=True)
    source_paths=['Level_01_Blockout.blend','Level_CyberCity_Blockout.blend','Scenes/Levels/Level_01/Level_01.tscn','Scenes/Player.tscn','project.godot','Art/Environment/Skyscrapers/Skyscraper_Kit.blend']
    baseline={'free_bytes':shutil.disk_usage(ROOT).free,'protected_sha256':{p:sha(ROOT/p) for p in source_paths}}
    if not (OUT/'QA/baseline.json').exists():(OUT/'QA/baseline.json').write_text(json.dumps(baseline,indent=2))
    records=[]
    families=['CORPORATE_MONOLITH','MEGABLOCK','INDUSTRIAL_TOWER','EXOSKELETON_TOWER','OFFICE_GRID','LANDMARK_TECH']
    with tempfile.TemporaryDirectory(prefix='highrise100-textures-') as temp:
        temp=Path(temp)
        for f,preset in enumerate(families):
            for variant in range(4):
                if shutil.disk_usage(ROOT).free < 30*1024**3: raise RuntimeError('Conservative 30 GiB floor reached')
                key=f'f{f}_{variant}'
                target=OUT/'Textures'/key;target.mkdir(exist_ok=True)
                request=dict(preset=preset,seed=925000+f*101+variant*17,resolution=[512,1024],
                    parameters=dict(emission_density=[.12,.30,.54,.73][variant],floor_height=[22,28,36,44][variant],
                        window_aspect=[.55,.85,1.45,2.1][variant],grime_amount=[.12,.26,.43,.59][variant],retro_strength=.35),
                    art=dict(profile='BOW_BASE',material_mix=.8,weathering=.27),
                    breakup=dict(mode='LAYERED',export_mode='BAKED',macro_variation=.18,grime=.19,micro_grain=.025,retro_artifacts=.12))
                p,recipe=normalized_request(request)
                result=render_recipe(p,recipe,temp)
                hashes={}
                for channel in ('albedo','normal','orm','height','emission'):
                    src=temp/(result['stem']+'_'+channel+'.png'); dst=target/(channel+'.png')
                    shutil.copyfile(src,dst);hashes[channel]=sha(dst)
                meta=make_recipe(recipe,key,outputs={c:f'Textures/{key}/{c}.png' for c in hashes},hashes=hashes)
                (OUT/'Recipes'/(key+'.facade.json')).write_text(json.dumps(meta,indent=2))
                records.append(dict(key=key,recipe='Recipes/'+key+'.facade.json',mode='UNIQUE_FACADE',seed=recipe['seed'],preset=preset,parameters=recipe['parameters'],sha256=hashes))
                for path in temp.iterdir():
                    if path.is_file():path.unlink()
                print('MATERIAL',key,flush=True)
    surfaces=['wall_dark_concrete','wall_reinforced','wall_maintenance','wall_corporate','wall_vent_bank','wall_service_rack','wall_reactor_housing','wall_tech_spine','floor_rooftop','floor_metal_deck','wrap_heavy_pipe','wrap_tank_shell','accent_datacenter','accent_emissive_panel','accent_hazard_skin','accent_billboard_support']
    for key in surfaces:
        source=ROOT/'Assets/ProceduralArt/Materials'/key
        target=OUT/'Textures'/key;target.mkdir(exist_ok=True)
        recipe=json.loads((ROOT/'Tools/Art/Library/materials'/(key+'.facade.json')).read_text())
        hashes={}
        for channel in ('albedo','normal','orm','height','emission'):
            src=source/(channel+'.png');dst=target/(channel+'.png');shutil.copyfile(src,dst);hashes[channel]=sha(dst)
        recipe['source_recipe']='Tools/Art/Library/materials/'+key+'.facade.json'
        recipe['outputs']={c:f'Textures/{key}/{c}.png' for c in hashes};recipe['sha256']=hashes
        (OUT/'Recipes'/(key+'.facade.json')).write_text(json.dumps(recipe,indent=2))
        records.append(dict(key=key,recipe='Recipes/'+key+'.facade.json',mode=recipe['surface_mode'],seed=recipe['seed'],preset=recipe['preset'],parameters=recipe['parameters'],sha256=hashes))
    (OUT/'materials.json').write_text(json.dumps(records,indent=2))
    # A small material overview is derived from real canonical albedo maps.
    board=Image.new('RGB',(1280,5*185+50),(20,27,32));draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
    draw.text((16,15),'BOW / HIGHRISE 100 / 40 SHARED PROCEDURAL RECIPES',font=font,fill='white')
    for i,r in enumerate(records):
        x=i%8*160;y=50+i//8*185;im=Image.open(OUT/'Textures'/r['key']/'albedo.png');im.thumbnail((148,156))
        board.paste(im,(x+(160-im.width)//2,y));draw.text((x+4,y+158),r['key'][:22],font=font,fill=(190,202,211))
    board.save(OUT/'Materials.jpg',quality=92)
    print('MATERIALS_COMPLETE',len(records),flush=True)
if __name__=='__main__': main()
