"""Determinism, independent overlays, emission and recipe replay contracts."""
import copy
import json
import numpy as np
from billboard_factory import *

def run():
    checks=[];hashes=set()
    for key in ARCHETYPES:
        r=preset(key);a,m=render(r);b,n=render(json.loads(json.dumps(a)))
        assert all(np.array_equal(m[k],n[k]) for k in m),key+' replay'
        different=copy.deepcopy(r);different['seed']=12345;_,v=render(different)
        assert not np.array_equal(m['albedo'],v['albedo']),key+' seed'
        digest=hashlib.sha256(m['albedo'].tobytes()).hexdigest();assert digest not in hashes;hashes.add(digest)
        checks.append({'archetype':key,'replay':True,'seed_variation':True,'size':m['albedo'].size})
    r=preset('HORIZONTAL_BILLBOARD');_,m=render(r)
    altered=copy.deepcopy(r);altered['colors']['neon']='#ff2233';_,n=render(altered)
    assert np.array_equal(m['orm'],n['orm']) and not np.array_equal(m['emission'],n['emission'])
    altered=copy.deepcopy(r);altered['parameters']['wear']=0;altered['parameters']['grime']=0;_,clean=render(altered)
    assert not np.array_equal(m['albedo'],clean['albedo'])
    for bad in ({'seed':-1},{'parameters':{'aspect':float('nan')}},{'colors':{'neon':'bad'}},{'support_frame':'false'}):
        try:normalize(bad)
        except ValueError:pass
        else:raise AssertionError('Invalid recipe accepted')
    out=ROOT/'Tools/Art/ArtPass/review/billboard_qa.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'passed':True,'checks':checks,'independent_color_orm':True,'clean_overlay_control':True},indent=2))
    print('BILLBOARD_QA PASS: 12 archetypes, deterministic replay, seed variation, isolated color/ORM, clean layers')

if __name__=='__main__':run()
