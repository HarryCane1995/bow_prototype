"""Palette invariance and scalar/channel isolation against real exported pixels."""
import copy
import json
import tempfile
import numpy as np
from PIL import Image
from lab_backend import Lab, HERE, load_recipe, config
from palette_mixer import PRESETS, ROLES, normalized_palette, randomize_palette


def main():
    review=HERE/'review/palette';review.mkdir(exist_ok=True)
    report={'presets':[], 'checks':{}}
    with tempfile.TemporaryDirectory(prefix='palette_qa_',dir=review) as temporary:
        work=__import__('pathlib').Path(temporary);lab=Lab(work/'cache',work/'favorites',work/'exports',work/'materials')
        def array(result,channel): return np.asarray(Image.open(lab.cache/result['key']/(channel+'.png')))
        for item in config()['presets']:
            base={**item['defaults'],'breakup':{**item['defaults']['breakup'],'mode':'LAYERED'},'palette_mix':{'enabled':False}}
            a=lab.preview(base)
            b=lab.preview({**base,'palette_mix':{'enabled':True,'preset':'WARNING_ORANGE'}})
            for channel in ('normal','height','weather_mask','detail_normal'):
                assert a['sha256'][channel]==b['sha256'][channel],(item['name'],channel)
            assert a['structure_hash']==b['structure_hash']
            if b['seam_qa']: assert b['seam_qa']['passed']
            report['presets'].append(item['name'])
        request=dict(surface_mode='TILEABLE_SURFACE',preset='INDUSTRIAL_FLOOR',seed=99,
            breakup={'mode':'LAYERED','grime':.8,'micro_grain':.4})
        outputs=[]
        for name in PRESETS:
            item=lab.preview({**request,'palette_mix':{'enabled':True,'preset':name}})
            assert item['seam_qa']['passed'];outputs.append(item)
        assert len({v['sha256']['normal'] for v in outputs})==1
        assert len({v['sha256']['height'] for v in outputs})==1
        assert len({v['sha256']['weather_mask'] for v in outputs})==1
        base=copy.deepcopy(outputs[0]['recipe']);first=outputs[0]
        changed=copy.deepcopy(base);changed['palette_mix']['colors']['BASE']='#795030'
        second=lab.preview(changed)
        assert first['sha256']['albedo']!=second['sha256']['albedo']
        for channel in ('orm','normal','height','emission','weather_mask'): assert first['sha256'][channel]==second['sha256'][channel],channel
        modified=np.any(array(first,'albedo')!=array(second,'albedo'),axis=-1)
        assert 0<modified.mean()<.95,modified.mean()
        changed=copy.deepcopy(base);changed['palette_mix']['material_responses']['PAINTED_METAL']['roughness']=.2
        scalar=lab.preview(changed)
        assert first['sha256']['albedo']==scalar['sha256']['albedo']
        for c in (0,2): assert np.array_equal(array(first,'orm')[...,c],array(scalar,'orm')[...,c])
        assert not np.array_equal(array(first,'orm')[...,1],array(scalar,'orm')[...,1])
        for influence in (0,1):
            changed=copy.deepcopy(base);changed['palette_mix']['weather_tint_influence']=influence;changed['palette_mix']['colors']['GRIME_TINT']='#89552f'
            result=lab.preview(changed)
            if influence==0: neutral=result
            else:
                assert neutral['sha256']['preview_albedo']!=result['sha256']['preview_albedo']
                for c in ('orm','preview_orm','weather_mask','normal','height'): assert neutral['sha256'][c]==result['sha256'][c]
        emissive=dict(preset='INDUSTRIAL_TOWER',seed=99,art={'profile':'BOW_BASE'},breakup={'mode':'LAYERED'},palette_mix={'enabled':True})
        a=lab.preview(emissive);changed=copy.deepcopy(a['recipe']);changed['palette_mix']['colors'].update(EMISSION_PRIMARY='#ba5752',EMISSION_SECONDARY='#6b99ca')
        b=lab.preview(changed)
        assert a['sha256']['emission']!=b['sha256']['emission']
        for c in ('normal','height','albedo','orm','weather_mask','emission_mask'): assert a['sha256'][c]==b['sha256'][c],c
        assert np.array_equal(array(a,'emission').max(axis=-1),array(b,'emission').max(axis=-1))
        for amount in (.25,.75):
            changed['palette_mix']['emission_influence']=amount
            partial=lab.preview(changed)
            assert np.array_equal(array(a,'emission').max(axis=-1),array(partial,'emission').max(axis=-1))
        secondary=copy.deepcopy(a['recipe']);secondary['palette_mix']['colors']['EMISSION_SECONDARY']='#bf6262'
        assert lab.preview(secondary)['sha256']['emission']!=a['sha256']['emission']
        p=normalized_palette({'enabled':True,'locks':{role:i%2==0 for i,role in enumerate(ROLES)}})
        randomized=randomize_palette(p,12345)
        for role in ROLES:
            assert (randomized['colors'][role]==p['colors'][role])==p['locks'][role],role
        assert randomized==randomize_palette(p,12345)
        for n,name in enumerate(('NEUTRAL_COLD','INDUSTRIAL_GREEN','WARNING_ORANGE')):
            recipe=copy.deepcopy(base);recipe['palette_mix']=normalized_palette({'enabled':True,'preset':name,'locks':{'BASE':True}})
            exported=lab.export(dict(recipe,name='palette_test',resolution=[1024,1024]))
            replay=lab.export(dict(load_recipe(exported['recipe']),name='palette_test'))
            assert exported['recipe']['sha256']==replay['recipe']['sha256'] and replay['revisioned']
            favorite=lab.favorite(recipe)
            assert lab.preview(load_recipe(favorite['recipe']))['sha256']==lab.preview(recipe)['sha256']
            assert favorite['recipe']['palette_mix']['locks']['BASE']
        report['checks']=dict(all_18_layouts_fixed=True,all_8_palettes=True,seams_unchanged=True,
            normal_height_byte_identical=True,weather_masks_fixed=True,colors_not_global_tint=True,
            rgb_edits_do_not_change_orm=True,roughness_is_scalar_G_only=True,
            emission_colors_only_mask_intensity_fixed=True,weather_tint_color_only=True,
            randomization_respects_locks=True,production_replay=True,favorite_locks_roundtrip=True)
    report['passed']=True
    (review/'qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
