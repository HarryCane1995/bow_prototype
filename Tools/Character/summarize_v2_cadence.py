"""Compact telemetry tables from the actual render-frame probes (no resampling)."""
import csv,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.godot/humanoid-base/v2-cadence'
summary={}
for label in ['baseline','fixed']:
    data=json.loads((OUT/f'{label}.json').read_text())
    fields=['frame','physics','fps_cap','pattern','camera_yaw','bow_solved_yaw','solved_error_deg','interpolated_error_deg','attachment_error_m']
    with (OUT/f'{label}_yaw.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in data['frames']:
            # Derive the heading from the captured basis. The initial probe's
            # camera-yaw display used the back vector with a 180-degree offset.
            x,y,z=map(float,row['camera_basis'][2].strip('()').split(','))
            row['camera_yaw']=math.degrees(math.atan2(x,z))
            writer.writerow({k:row[k] for k in fields})
    summary[label]={}
    for fps in [60,240]:
        rows=[r for r in data['frames'] if r['fps_cap']==fps]
        summary[label][fps]={"frames":len(rows),"max_solved_error_deg":max(r['solved_error_deg'] for r in rows),
            "max_interpolated_error_deg":max(r['interpolated_error_deg'] for r in rows),
            "max_attachment_error_m":max(r['attachment_error_m'] for r in rows)}
turn=json.loads((OUT/'slide360.json').read_text())
summary['slide360']={'status':turn['status'],'frames':len(turn['frames']),
    'max_spine_step_deg':max(r['spine_step_deg'] for r in turn['frames']),
    'max_aim_error_deg':max(r['aim_error_deg'] for r in turn['frames']),
    'max_reach_error_m':max(r['left_reach_error_m'] for r in turn['frames'])}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
