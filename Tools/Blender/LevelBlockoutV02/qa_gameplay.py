"""Check actual reviewed meshes for the requested grammar correction."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/'Docs/Reviews/V02GameplayCorrection'
checks=[];details=[]
def expect(ok,label):checks.append({'check':label,'passed':bool(ok)})
for seed in (17,41,109):
    before=json.loads((REPORT/f'before_{seed}.json').read_text())
    after=json.loads((REPORT/f'after_{seed}.json').read_text())
    boxes={tuple(map(int,k.split(','))):v for k,v in after['boxes'].items()}
    expect(after['support_count']==0 and after['support_surface_area_m2']==0,f'{seed}: no generated supports or bearing piers')
    expect(after['plate_count']==before['plate_count'],f'{seed}: existing band population retained')
    expect(after['access_flight_count']<=2 and after['access_flight_count']<after['plate_count']*.25,f'{seed}: access flights are sparse optional routes')
    expect(after['bridge_count']==before['bridge_count'],f'{seed}: inter-zone bridge grammar retained')
    expect(after['wall_surface_area_m2']<before['wall_surface_area_m2']*.5,f'{seed}: tall facade fill reduced')
    expect(after['plate_top_area_m2']<before['plate_top_area_m2']*.85,f'{seed}: larger vertical openings between plate footprints')
    expect(all(v['clearance_below_m'] is None or v['clearance_below_m']>3 for v in after['under_plate_samples']),f'{seed}: sampled plate undersides have at least 3m of air')
    walls=[v for k,v in boxes.items() if k[2] in (31,32)]
    expect(walls and all(v[2][0]>=.7 for v in walls),f'{seed}: isolated walls do not receive ground-to-platform bases')
    expect(all(max(v[0][1]-v[0][0],v[1][1]-v[1][0])<=44.319893*.9+.03 for v in walls),f'{seed}: isolated wall lengths stay inside measured wallrun budget')
    rises=[];opportunities=[];pair_rises=[]
    for (zone,band,part),v in boxes.items():
        if part==10 and (zone,band-1,10) in boxes:
            lower=boxes[(zone,band-1,10)]
            rise=v[2][1]-lower[2][1];rises.append(rise)
            gap=[max(0,lower[i][0]-v[i][1],v[i][0]-lower[i][1]) for i in (0,1)]
            opportunities.append(math.sqrt(sum(x*x for x in gap)+(rise-1.6)**2))
        if part==44 and (zone,0,43) in boxes:
            pair_rises.append(v[2][1]-boxes[(zone,0,43)][2][1])
    expect(rises and all(0<d<=10.506917*.9 for d in rises),f'{seed}: adjacent vertical bands remain below conservative wall-jump rise')
    expect(opportunities and max(opportunities)<50*.82,f'{seed}: adjacent surfaces within reserved 3D grapple acquisition envelope')
    expect(pair_rises and all(0<d<=10.506917*.9 for d in pair_rises),f'{seed}: local wall-jump landings measured from their actual lower floor')
    details.append({'seed':seed,'adjacent_band_rise_m':rises,'nearest_edge_camera_to_upper_m':opportunities,'wall_jump_landing_rise_m':pair_rises,
                    'note':'Geometric opportunity envelopes only; trajectory timing, line of sight and runtime grapple anchors are not certified.'})
result={'passed':all(c['passed'] for c in checks),'checks':checks,'details':details}
(REPORT/'grammar_qa.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[c for c in checks if not c['passed']]}))
