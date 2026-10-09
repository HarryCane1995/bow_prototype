"""Rebuild only selected assets in disposable memory; never save any .blend."""
import bpy,json,hashlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[2]/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA';sys.path.insert(0,str(HERE))
import build_library as build
data=json.loads((QA/'candidate_manifest.json').read_text())['buildings']
selected={'HR003','HR007','HR013','HR018','HR025','HR027','HR036','HR057','HR064','HR070','HR083','HR100'}
def signature(col):
    result={}
    for o in col.objects:
        if o.type!='MESH':continue
        me=o.data;uv=me.uv_layers.active
        faces=[dict(vertices=list(p.vertices),material=me.materials[p.material_index].name,uv=[[round(x,5) for x in uv.data[li].uv] for li in p.loop_indices]) for p in me.polygons]
        result[o['part']]=dict(vertices=[[round(x,5) for x in v.co] for v in me.vertices],faces=faces)
    return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100_UV_Candidate.blend'))
expected={r['id']:signature(bpy.data.collections[r['collection']]) for r in data if r['id'] in selected}
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
# Start with fresh material registry: generator and migration must converge.
for m in list(bpy.data.materials):bpy.data.materials.remove(m)
actual={}
for r in data:
    if r['id'] not in selected:continue
    i=int(r['id'][2:]);p=r['parameters'];t=build.Tower(i,r['category'],r['subtype'],p['width'],p['depth'],p['height'])
    (build.A if r['category'] in build.A.NAMES else build.B).build(t,r['category'],r['subtype'],p['width'],p['depth'],p['height'])
    generated=t.finish();assert generated['geometry_only_sha256']==r['geometry_only_sha256']
    actual[r['id']]=signature(t.col)
report=dict(passed=actual==expected,selected=sorted(selected),expected=expected,actual=actual,comparison='vertices/face indices/material keys/loop UV rounded 5 decimals',saved_source=False)
(QA/'reproducibility.json').write_text(json.dumps(report,indent=2));print('UV_REPRODUCIBILITY',report['passed']);assert report['passed']
