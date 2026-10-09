"""Billboard adapter with content-addressed previews and versioned exports."""
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
import time
from lab_backend import HERE, ROOT
sys.path.insert(0,str(ROOT/'Tools/Art/BillboardFactory'))
import billboard_factory as factory

def config():return factory.config()

def load_recipe(data):
    if data.get('generator_fingerprint',factory.fingerprint())!=factory.fingerprint():
        raise ValueError('Billboard generator changed; recipe needs an explicit version migration')
    return factory.normalize(data)

class BillboardLab:
    def __init__(self):
        self.cache=HERE/'.cache/billboards';self.favorites=HERE/'billboard-favorites'
        self.exports=ROOT/'Assets/ProceduralArt/Billboards';self.lock=threading.RLock()

    def preview(self,data):
        start=time.perf_counter();recipe=factory.normalize(data)
        key=hashlib.sha256(json.dumps([factory.fingerprint(),recipe],sort_keys=True).encode()).hexdigest()
        target=self.cache/key
        with self.lock:
            cached=(target/'preview.webp').exists()
            if not cached:
                factory.guard(4*1024**2);_,maps=factory.render(recipe,512);target.mkdir(parents=True,exist_ok=True)
                for k,im in maps.items():im.save(target/f'{k}.png')
                im=factory.preview(maps,recipe['parameters']['emission_strength']);im.thumbnail((256,192));im.save(target/'preview.webp',quality=85)
        return dict(key=key,recipe=recipe,cached=cached,elapsed_ms=round((time.perf_counter()-start)*1000),
                    maps={k:f'/billboard-cache/{key}/{k}.png' for k in ('albedo','emission','orm')},thumbnail=f'/billboard-cache/{key}/preview.webp')

    def library(self):
        result=[]
        for key,item in config()['archetypes'].items():
            result.append({'id':key,'label':item['label'],'recipe':item['recipe'],
                           'thumbnail':f'/billboard-library/{key.lower()}/preview.webp'})
        if self.favorites.exists():
            for path in sorted(self.favorites.glob('*.json')):
                try:
                    doc=json.loads(path.read_text());recipe=load_recipe(doc)
                    result.append({'id':path.stem,'label':'★ '+recipe['archetype'].replace('_',' '),
                         'recipe':recipe,'thumbnail':f'/billboard-favorites/{path.stem}.webp'})
                except (ValueError,KeyError):continue
        return result

    def favorite(self,data):
        recipe=factory.normalize(data);payload=self.preview(recipe);key=payload['key'][:20]
        with self.lock:
            self.favorites.mkdir(parents=True,exist_ok=True)
            doc={**recipe,'generator_fingerprint':factory.fingerprint()}
            (self.favorites/f'{key}.json').write_text(json.dumps(doc,indent=2),encoding='utf-8')
            (self.favorites/f'{key}.webp').write_bytes((self.cache/payload['key']/'preview.webp').read_bytes())
        return {'id':key,'library':self.library()}

    def export(self,data):
        name=data.get('name','');resolution=data.get('resolution',512)
        if not isinstance(name,str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,63}',name):raise ValueError('Use 1–64 ASCII letters, numbers, underscores or hyphens')
        if name.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:raise ValueError('Reserved Windows name')
        if resolution not in (512,1024):raise ValueError('Export resolution must be 512 or 1024')
        with self.lock:
            chosen=name;i=1
            while (self.exports/chosen).exists():i+=1;chosen=f'{name}_r{i:02}'
            return factory.export(data.get('recipe',{}),self.exports/chosen,resolution)

    def asset_path(self,route):
        match=re.fullmatch('/billboard-cache/([a-f0-9]{64})/(albedo.png|emission.png|orm.png|preview.webp)',route)
        if match:return self.cache/match[1]/match[2]
        match=re.fullmatch('/billboard-library/([a-z_]+)/preview.webp',route)
        if match and match[1].upper() in factory.ARCHETYPES:return self.exports/match[1]/'preview.webp'
        match=re.fullmatch('/billboard-favorites/([a-f0-9]{20})\.webp',route)
        if match:return self.favorites/(match[1]+'.webp')
        return None
