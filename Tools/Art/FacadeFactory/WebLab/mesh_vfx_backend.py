"""Mesh-driven extension of the local VFX service; sprite exports are preserved."""
from datetime import datetime, timezone
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import time

from vfx_backend import ROOT, HERE, VFX
from mesh_schema import config as schema_config, normalize, VERSION
from mesh_archetypes import EFFECTS
from mesh_geometry import generate
from mesh_export import export as write_mesh_effect
from mesh_thumbnail import thumbnail
sys.path.insert(0,str(VFX.parent/'ArtPass'))
from storage import guard


def config():
    result=schema_config()
    library=ROOT/'Assets/ProceduralArt/VFX'
    for effect,meta in result['effects'].items():
        path=library/meta['slug']/'preview.png'
        if path.is_file():
            meta['thumbnail']='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')
        meta['scene']='res://Assets/ProceduralArt/VFX/'+meta['slug']+'/review.tscn'
    return result


def generator_hash():
    files=[VFX/name for name in ('mesh_schema.py','mesh_geometry.py','mesh_families.py','mesh_archetypes.py','mesh_export.py','godot_export.py')]
    files+=sorted((VFX/'mesh_godot').glob('*.gd'))
    return hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()


def load_recipe(data):
    recipe=normalize(data)
    # 0.1 explosion geometry is retained exactly; its legacy recipes migrate to
    # the expanded schema instead of being stranded by unrelated archetype edits.
    if data.get('generator_version',VERSION) != '0.1.0' and data.get('generator_fingerprint',generator_hash())!=generator_hash():
        raise ValueError('Mesh generator version changed; use the recipe with its original generator')
    return recipe


class MeshVFXLab:
    def __init__(self,cache=None,exports=None):
        self.cache=Path(cache or HERE/'.cache/mesh-vfx')
        self.exports=Path(exports or ROOT/'Assets/ProceduralArt/VFX')
        self.cache.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock()

    def preview(self,data):
        disk=guard(4*1024*1024)
        start=time.perf_counter();recipe=normalize(data)
        key=hashlib.sha256(json.dumps([generator_hash(),recipe],sort_keys=True).encode()).hexdigest()
        path=self.cache/f'{key}.json'
        with self.lock:
            cached=path.is_file()
            if not cached:
                payload=dict(key=key,**generate(recipe))
                path.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
                # Geometry previews have no textures; retain only the latest 24.
                history=[p for p in self.cache.glob('*.json') if re.fullmatch(r'[a-f0-9]{64}\.json',p.name) and not p.is_symlink()]
                retain=8 if disk['mode']=='CONSERVE' else 24
                for stale in sorted(history,key=lambda p:p.stat().st_mtime,reverse=True)[retain:]:
                    stale.unlink(missing_ok=True)
            payload=json.loads(path.read_text())
        return dict(**payload,cached=cached,elapsed_ms=round((time.perf_counter()-start)*1000))

    def export(self,data):
        guard(16*1024*1024)
        name=data.get('name','')
        if not isinstance(name,str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,63}',name):
            raise ValueError('Asset name: 1–64 ASCII letters, digits, _ or -')
        if name.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
            raise ValueError('Reserved Windows name')
        recipe=normalize(data.get('recipe',{}))
        payload=generate(recipe)
        with self.lock:
            self.exports.mkdir(parents=True,exist_ok=True)
            chosen,revision=name,1
            while (self.exports/chosen).exists():
                revision+=1;chosen=f'{name}_r{revision:02}'
            target=self.exports/chosen;resource='res://'+target.relative_to(ROOT).as_posix()
            with tempfile.TemporaryDirectory(prefix='mesh_export_',dir=self.cache) as tmp:
                stage=Path(tmp);write_mesh_effect(payload,stage,resource)
                hashes={p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((stage/'meshes').glob('*.obj'))}
                doc=dict(**recipe,name=chosen,generator_fingerprint=generator_hash(),
                         created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),mesh_sha256=hashes)
                (stage/f'{chosen}.meshvfx.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
                thumbnail(payload,EFFECTS[recipe['effect']]['sample_time']).save(stage/'preview.png',optimize=True)
                stage.rename(target)
        return dict(name=chosen,directory=target.relative_to(ROOT).as_posix(),scene=resource+'/review.tscn',
                    effect_scene=resource+'/effect.tscn',recipe=doc,stats=payload['stats'],
                    files=sorted(p.relative_to(ROOT).as_posix() for p in target.rglob('*') if p.is_file()))
