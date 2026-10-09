"""Functional API and billboard export/reload checks; temporary assets are scoped and removed."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from collections import namedtuple
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools/Art/FacadeFactory/WebLab'))
sys.path.insert(0,str(Path(__file__).parent))
import storage
from billboard_backend import BillboardLab,load_recipe
import billboard_factory as factory

def main():
    base='http://127.0.0.1:8765';report={}
    def get(path):return json.load(urlopen(base+path,timeout=30))
    token=get('/api/config')['token']
    def post(path,data,credential=token,origin=None):
        headers={'Content-Type':'application/json','X-Facade-Token':credential}
        if origin:headers['Origin']=origin
        return json.load(urlopen(Request(base+path,json.dumps(data).encode(),headers),timeout=45))
    config=get('/api/config');report['material_library_count']=len(config['material_library']);assert report['material_library_count']==50
    mesh=get('/api/mesh-vfx/config');assert len(mesh['effects'])==10
    sign=get('/api/billboard/config');assert len(sign['archetypes'])==12
    for route,recipe in [('/api/preview',{'preset':'WALL_TECH_SPINE','seed':99,'surface_mode':'TILEABLE_SURFACE'}),
                         ('/api/mesh-vfx/preview',mesh['defaults']),('/api/billboard/preview',sign['defaults'])]:
        result=post(route,recipe);assert 'recipe' in result;report[route]='PASS'
    for path in ['/material-library/wall_tech_spine.webp','/billboard-library/warning_panel/preview.webp']:
        response=urlopen(base+path);assert response.status==200 and len(response.read())>100
    for credential,origin in [('wrong',None),(token,'https://untrusted.example')]:
        try:post('/api/billboard/preview',sign['defaults'],credential,origin)
        except HTTPError as e:assert e.code==403
        else:raise AssertionError('Unexpected cross-origin write')
    report['same_origin_token_guard']='PASS'
    # Private test namespace, never a user's export or favorite.
    parent=ROOT/'Tools/Art/ArtPass/review';parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='integration_tmp_',dir=parent) as temporary:
        work=Path(temporary).resolve();assert work.is_relative_to(parent.resolve())
        lab=BillboardLab();lab.cache=work/'cache';lab.favorites=work/'favorites';lab.exports=work/'exports'
        recipe=factory.preset('WARNING_PANEL',7654)
        first=lab.export({'name':'test_sign','recipe':recipe,'resolution':512})
        second=lab.export({'name':'test_sign','recipe':recipe,'resolution':512})
        assert second['id']=='test_sign_r02'
        doc=json.loads((lab.exports/'test_sign/recipe.billboard.json').read_text())
        replay=lab.export({'name':'replay','recipe':load_recipe(doc),'resolution':doc['long_edge']})
        assert replay['recipe']['sha256']==doc['sha256']
        assert 'emission_operator = 1' in (lab.exports/'test_sign/sign.tres').read_text()
        for k,digest in doc['sha256'].items():assert hashlib.sha256((lab.exports/'test_sign'/f'{k}.png').read_bytes()).hexdigest()==digest
        favorite=lab.favorite(recipe);assert len(lab.library())==13
        favorite_doc=lab.favorites/(favorite['id']+'.json');stale=json.loads(favorite_doc.read_text());stale['generator_fingerprint']='old';favorite_doc.write_text(json.dumps(stale))
        assert len(lab.library())==12,'incompatible favorites must not silently load'
        for name in ('../outside','CON','a/b','a\\b'):
            try:lab.export({'name':name,'recipe':recipe})
            except ValueError:pass
            else:raise AssertionError('Unsafe name accepted')
    report['billboard_export_replay_no_overwrite_favorites']='PASS'
    Usage=namedtuple('Usage','total used free')
    with patch.object(storage.shutil,'disk_usage',return_value=Usage(100*storage.GIB,76*storage.GIB,24*storage.GIB)):
        assert storage.guard()['mode']=='CONSERVE'
    with patch.object(storage.shutil,'disk_usage',return_value=Usage(100*storage.GIB,86*storage.GIB,14*storage.GIB)):
        assert storage.status()['mode']=='STOP'
        try:storage.guard()
        except ValueError:pass
        else:raise AssertionError('Disk floor not enforced')
    report['disk_25_15_thresholds']='PASS';report['result']='PASS'
    (parent/'integration_qa.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
