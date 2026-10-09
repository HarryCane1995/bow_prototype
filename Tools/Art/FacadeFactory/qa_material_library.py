"""Focused tests for additive palette knobs and shipped canonical replay."""
import copy
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'WebLab'))
from lab_backend import Lab,load_recipe,normalized_request,render_recipe
from material_library import authored_request


def main():
    report={'controls':{},'production_replay':[]}
    with tempfile.TemporaryDirectory(prefix='bow-library-qa-') as temp:
        temp=Path(temp);lab=Lab(temp/'cache',temp/'favorites',temp/'exports',temp/'materials')
        controls=(('accent_usage','ACCENT_HAZARD_SKIN','albedo'),
                  ('colored_balance','WALL_PAINTED_UTILITY','albedo'),
                  ('structural_separation','WALL_MEGABLOCK','albedo'),
                  ('orm_influence','FLOOR_DAMP_CONCRETE','orm'))
        for key,name,changed in controls:
            request=authored_request(name)
            outputs=[]
            for amount in (0.,1.):
                r=copy.deepcopy(request);r['palette_mix'][key]=amount
                outputs.append(lab.preview(r))
            a,b=outputs
            assert a['sha256'][changed]!=b['sha256'][changed],(key,'no response')
            for c in ('height','normal','detail_normal','weather_mask','emission'):
                assert a['sha256'][c]==b['sha256'][c],(key,c,'cross-channel contamination')
            if key=='orm_influence':assert a['sha256']['albedo']==b['sha256']['albedo']
            else:assert a['sha256']['orm']==b['sha256']['orm']
            report['controls'][key]=dict(response=True,geometry_and_masks_fixed=True)
        for key in ('wall_dark_concrete','floor_hex_armor','floor_damp_concrete','wrap_reactor_core','accent_control_console'):
            doc=json.loads((ROOT/'Tools/Art/Library/materials'/f'{key}.facade.json').read_text(encoding='utf-8'))
            preset,recipe=normalized_request(load_recipe(doc));result=render_recipe(preset,recipe,temp/'replay')
            assert all(result['sha256'][c]==doc['sha256'][c] for c in doc['sha256']),key
            report['production_replay'].append(key)
        files=list((HERE/'WebLab/favorites').glob('*.facade.json'))
        for path in files:load_recipe(json.loads(path.read_text(encoding='utf-8')))
        report['existing_favorites_load']=len(files)
    report['passed']=True
    target=ROOT/'Tools/Art/ArtPass/review/materials_controls_qa.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
