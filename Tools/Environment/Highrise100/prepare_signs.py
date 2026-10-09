"""Existing deterministic Billboard Factory: six original tenant/media panels."""
from pathlib import Path
import sys,json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(ROOT/'Tools/Art/BillboardFactory'))
from billboard_factory import preset,render,fingerprint
records=[r for r in json.loads((OUT/'materials.json').read_text()) if not r['key'].startswith('sign_')]
for i,name in enumerate(('PANEL_AD','CORPORATE_PANEL','DIRTY_LIGHTBOX','VERTICAL_NEON','HORIZONTAL_BILLBOARD','INACTIVE_BILLBOARD')):
    key=f'sign_{i}';req=preset(name,925700+i*31);req['parameters']['aspect']=[.55,2.7,1.4,.4,3.1,2.8][i]
    recipe,maps=render(req,512);size=maps['orm'].size
    maps['normal']=Image.new('RGB',size,(128,128,255));maps['height']=Image.new('L',size,128)
    target=OUT/'Textures'/key;target.mkdir(exist_ok=True);hashes={}
    for ch,im in maps.items():im.save(target/(ch+'.png'));hashes[ch]=hashlib.sha256((target/(ch+'.png')).read_bytes()).hexdigest()
    recipe.update(generator_fingerprint=fingerprint(),outputs={ch:f'Textures/{key}/{ch}.png' for ch in maps},sha256=hashes)
    path='Recipes/'+key+'.billboard.json';(OUT/path).write_text(json.dumps(recipe,indent=2))
    records.append(dict(key=key,recipe=path,mode='UNIQUE_PANEL',seed=recipe['seed'],preset=name,parameters=recipe['parameters'],sha256=hashes))
(OUT/'materials.json').write_text(json.dumps(records,indent=2))
print('SIGN_MATERIALS',6)
