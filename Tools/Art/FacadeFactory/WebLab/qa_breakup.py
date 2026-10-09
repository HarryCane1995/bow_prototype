"""Regression, layer isolation, seam, old recipe and production replay checks."""
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from lab_backend import Lab, HERE, ROOT, load_recipe, normalized_request, render_recipe, make_recipe
from surface_breakup import BREAKUP_CONTROLS, DETAIL_CHANNELS


def main():
    review=HERE/'review/breakup'
    baseline=json.loads((review/'baseline.json').read_text(encoding='utf-8'))
    report={'presets':[], 'layers':{}, 'old_recipes':[], 'exports':[]}
    with tempfile.TemporaryDirectory(prefix='breakup_qa_',dir=review) as temporary:
        work=Path(temporary); lab=Lab(work/'cache',work/'favorites',work/'exports',work/'materials')
        for name,old in baseline['presets'].items():
            baked=lab.preview({**old['recipe'],'breakup':{'mode':'LEGACY_BAKED'}})
            assert baked['sha256']==old['sha256'],(name,'legacy changed')
            layered=lab.preview({**old['recipe'],'breakup':{'mode':'LAYERED'},'palette_mix':{'enabled':False}})
            assert layered['structure_hash']==old['structure_hash'],name
            for channel in ('normal','height','emission'):
                assert layered['sha256'][channel]==old['sha256'][channel],(name,channel)
            if layered['seam_qa']: assert layered['seam_qa']['passed'],name
            report['presets'].append(dict(preset=name,old_baked_byte_exact=True,layout_normal_height_emission_unchanged=True,seams=layered['seam_qa']))
        request=dict(surface_mode='TILEABLE_SURFACE',preset='INDUSTRIAL_FLOOR',seed=99,palette_mix={'enabled':False},
                     breakup=dict(mode='LAYERED',export_mode='SEPARATE',**{k:0 for k in BREAKUP_CONTROLS}))
        clean=lab.preview(request)
        for c in ('albedo','orm','normal'):
            assert clean['sha256'][c]==clean['sha256']['preview_'+c],c
        for key in BREAKUP_CONTROLS:
            changed=lab.preview({**request,'breakup':{**request['breakup'],key:1}})
            for c in ('albedo','normal','orm','height','emission',*DETAIL_CHANNELS):
                assert changed['sha256'][c]==clean['sha256'][c],(key,c)
            assert changed['sha256']['preview_albedo']!=clean['sha256']['preview_albedo'],key
            assert (changed['sha256']['preview_normal']!=clean['sha256']['normal'])==(key=='micro_grain'),key
            assert changed['seam_qa']['passed'],key
            report['layers'][key]={'base_immutable':True,'preview_effective':True,'main_normal_immutable':True}
        macro=np.asarray(Image.open(lab.cache/clean['key']/'weather_mask.png'))[:-1,:-1,0].astype(float)
        spectrum=np.abs(np.fft.fft2(macro-macro.mean()))**2
        low=spectrum[:2,:2].sum()+spectrum[-1:,:2].sum()+spectrum[:2,-1:].sum()+spectrum[-1:,-1:].sum()
        assert low/spectrum.sum()>.99,low/spectrum.sum()
        report['macro_low_frequency_energy']=float(low/spectrum.sum())
        for mode,name in [('TILEABLE_SURFACE','INDUSTRIAL_FLOOR'),('CYLINDER_WRAP','REACTOR_CORE_WRAP'),('UNIQUE_FACADE','INDUSTRIAL_TOWER')]:
            size=[1024,1024] if mode=='TILEABLE_SURFACE' else [512,1024]
            for strategy in ('BAKED','SEPARATE'):
                payload=dict(surface_mode=mode,preset=name,seed=99,resolution=size,breakup=dict(mode='LAYERED',export_mode=strategy,micro_grain=.65,grime=.7))
                a=lab.export(dict(payload,name='qa_breakup'))
                b=lab.export(dict(load_recipe(a['recipe']),name='qa_breakup'))
                assert a['recipe']['sha256']==b['recipe']['sha256'] and b['revisioned']
                assert set(DETAIL_CHANNELS).issubset(a['recipe']['outputs'])
                for c in a['recipe']['sha256']:
                    file=lab.exports/a['recipe']['outputs'][c]
                    assert hashlib.sha256(file.read_bytes()).hexdigest()==a['recipe']['sha256'][c]
                    assert list(Image.open(file).size)==size
                report['exports'].append(dict(mode=mode,strategy=strategy,resolution=size,replay=True,no_overwrite=True))
        for filename in ('industrial_99_weblab.facade.json','surface_industrial_floor_99.facade.json','surface_reactor_core_99.facade.json'):
            old=json.loads((ROOT/'Assets/Textures/Levels/Level_01/FacadeFactory'/filename).read_text(encoding='utf-8'))
            p,recipe=normalized_request(load_recipe(old)); result=render_recipe(p,recipe,work/'old')
            assert result['sha256']==old['sha256'],filename
            report['old_recipes'].append(filename)
        favorite=lab.favorite(request)
        assert lab.preview(load_recipe(favorite['recipe']))['sha256']==clean['sha256']
        restore=dict(request,breakup={**request['breakup'],'grime':.25,'micro_grain':.12})
        assert lab.preview(restore)['key']==lab.preview(restore)['key']
        for invalid in ({'micro_grain':True},{'grime':float('nan')},{'mode':'wrong'},{'export_mode':'wrong'},{'unknown':1}):
            try: lab.preview({**request,'breakup':invalid})
            except ValueError: pass
            else: raise AssertionError(invalid)
        report['validation']=True
        # Either vertical mode remains seamless in the relevant axes.
        for tile_mode in ('FULL_2D_TILE','HORIZONTAL_WRAP_ONLY'):
            result=lab.preview(dict(surface_mode='CYLINDER_WRAP',preset='PIPE_HEAVY',seed=123,tile_mode=tile_mode))
            assert result['seam_qa']['passed']
        report['favorite_roundtrip']=True
    report['passed']=True
    (review/'qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='presets'},indent=2))


if __name__=='__main__': main()
