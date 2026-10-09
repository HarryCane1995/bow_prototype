"""Bounded regression/seam QA for global art and additive surface modes."""
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
from PIL import Image
import numpy as np
from lab_backend import (HERE,ROOT,FACTORY,Lab,normalized_request,load_recipe,render_recipe,
                         TILE_PRESETS,CYLINDER_PRESETS,make_recipe)
from facade_factory import Facade,generate
from facade_presets import PRESETS,get_preset
from facade_art_profiles import normalized_art,effective_stylizer


def main():
    report={'legacy':[],'surfaces':[],'exports':[],'checks':{}}
    review=HERE/'review/art_direction';review.mkdir(exist_ok=True)
    baseline=json.loads((review/'legacy_baseline.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='surface_qa_',dir=review) as temporary:
        work=Path(temporary);lab=Lab(work/'cache',work/'favorites',work/'exports',work/'materials')
        for name,p in PRESETS.items():
            structural=Facade(p,99).generate();old=baseline['presets'][name]
            for key in ('albedo','height','orm','emission'):
                assert hashlib.sha256(getattr(structural,key).tobytes()).hexdigest()==old[key],(name,key)
            assert structural.groups==old['groups'] and dict(structural.window_states)==old['windows']
            a=lab.preview(dict(preset=name,seed=99))
            assert a['sha256']==old['maps']
            b=lab.preview(dict(preset=name,seed=99,art={'profile':'BOW_BASE'}))
            assert a['structure_hash']==b['structure_hash']
            assert a['sha256']['height']==b['sha256']['height'] and a['sha256']['emission']==b['sha256']['emission']
            assert a['sha256']['albedo']!=b['sha256']['albedo'] and a['sha256']['orm']!=b['sha256']['orm']
            report['legacy'].append(dict(preset=name,exact_legacy=True,structure_unchanged=True,bow_ms=b['generation_ms']))
        industrial=lab.preview(dict(preset='INDUSTRIAL_TOWER',seed=99,art={'profile':'BOW_BASE'}))
        stats=industrial['art_statistics']
        assert all(v>0 for v in stats['seam_classes'].values()),stats
        assert all(v>0 for v in stats['material_classes'].values()),stats
        light=normalized_art(dict(profile='BOW_BASE',material_mix=0,weathering=0))
        heavy=normalized_art(dict(profile='BOW_BASE',material_mix=1,weathering=1))
        assert heavy['controls']['material_variation']>light['controls']['material_variation']
        assert heavy['controls']['saturation']<light['controls']['saturation']
        assert effective_stylizer(get_preset('industrial'),heavy).style.posterization==256
        report['art_statistics']=stats
        for mode,family in [('TILEABLE_SURFACE',TILE_PRESETS),('CYLINDER_WRAP',CYLINDER_PRESETS)]:
            for name in family:
                payload=dict(surface_mode=mode,preset=name,seed=99)
                a=lab.preview(payload);b=lab.preview(payload)
                assert b['cached'] and a['sha256']==b['sha256']
                assert a['seam_qa']['passed']
                assert a['seam_qa']['axes']==(['X','Y'] if mode=='TILEABLE_SURFACE' else ['X'])
                report['surfaces'].append(dict(preset=name,mode=mode,milliseconds=a['generation_ms'],seam_qa=a['seam_qa']))
            chosen=next(iter(family));request=dict(surface_mode=mode,preset=chosen,seed=99)
            favorite=lab.favorite(request);assert lab.preview(load_recipe(favorite['recipe']))['sha256']==lab.preview(request)['sha256']
            resolution=[1024,1024] if mode=='TILEABLE_SURFACE' else [1024,2048]
            first=lab.export(dict(request,name='surface_qa',resolution=resolution))
            restored=load_recipe(first['recipe'])
            second=lab.export(dict(restored,name='surface_qa'))
            assert second['revisioned'] and first['recipe']['sha256']==second['recipe']['sha256']
            for channel in ('albedo','emission','normal','orm','height'):
                path=lab.exports/first['recipe']['outputs'][channel]
                assert hashlib.sha256(path.read_bytes()).hexdigest()==first['recipe']['sha256'][channel]
                with Image.open(path) as image: assert list(image.size)==resolution
            assert set(('preview','tiled_preview','seam_debug')).issubset(first['recipe']['outputs'])
            assert 'texture_repeat = true' in (lab.materials/f'{first["name"]}.tres').read_text()
            report['exports'].append(dict(mode=mode,resolution=resolution,replay_exact=True,no_overwrite=True))
        full=lab.preview(dict(surface_mode='CYLINDER_WRAP',preset='PIPE_HEAVY',seed=99,tile_mode='FULL_2D_TILE'))
        assert full['seam_qa']['passed'] and full['seam_qa']['axes']==['X','Y']
        old=json.loads((ROOT/'Assets/Textures/Levels/Level_01/FacadeFactory/industrial_99_weblab.facade.json').read_text())
        p,recipe=normalized_request(load_recipe(old));replay=render_recipe(p,recipe,work/'v1')
        assert replay['sha256']==old['sha256']
        report['checks']=dict(all_6_legacy_byte_exact=True,all_6_structures_unchanged=True,three_seam_classes=True,
            six_material_classes=True,meta_control_direction=True,all_12_new_presets=True,seam_all_five_maps=True,
            cylinder_optional_2d_tile=True,v1_recipe_exact_replay=True,favorites_roundtrip=True,
            production_export_replay=True,no_silent_overwrite=True)
    report['average_surface_preview_ms']=round(statistics.mean(r['milliseconds'] for r in report['surfaces']),1)
    report['passed']=True
    (review/'surface_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
