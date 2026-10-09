"""Apply rules to saved source/test subset; assert exact geometry invariance."""
import bpy,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
sys.path.insert(0,str(Path(__file__).resolve().parent))
import uv_material_rules as rules
data=json.loads((QA/'Before/manifest.json').read_text())
subset='--subset' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100.blend'))
def geometry():
    result={}
    for r in data['buildings']:
        rows=[]
        for o in sorted(bpy.data.collections[r['collection']].objects,key=lambda x:x.name):
            row=[o.name,o.type,list(map(list,o.matrix_local)),o.parent.name if o.parent else None]
            if o.type=='MESH':row.extend([[list(v.co) for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]])
            rows.append(row)
        result[r['id']]=hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    return result
before=geometry();changes=[]
ids=['HR003','HR007','HR013','HR018','HR027','HR036','HR039','HR057','HR064','HR083','HR098','HR100']
for r in data['buildings']:
    if subset and r['id'] not in ids:continue
    changes.extend(rules.apply_collection(bpy.data.collections[r['collection']],r))
after=geometry();assert before==after,'GEOMETRY CHANGED'
phase='subset' if subset else 'candidate'
(QA/(phase+'_geometry.json')).write_text(json.dumps(dict(all100_exactly_unchanged=before==after,before=before,after=after),indent=2))
(QA/(phase+'_assignment_changes.json')).write_text(json.dumps(changes,indent=2))
(QA/(phase+'_manifest.json')).write_text(json.dumps(data,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('Highrise100_UV_Subset.blend' if subset else 'Highrise100_UV_Candidate.blend')),compress=True)
print('UV_RULE_PASS',phase,'collections',len(data['buildings']),'assignments',len(changes),'EXACT_GEOMETRY_UNCHANGED')
