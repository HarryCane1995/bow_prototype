import bpy, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'Docs/Reviews/FlowCourseV03'
before=json.loads((REPORT/'before.json').read_text())
def fingerprint(o):
    d={'type':o.type,'matrix':[list(r) for r in o.matrix_world],'collections':sorted(c.name for c in o.users_collection)}
    if o.type=='MESH':d.update(v=[list(v.co) for v in o.data.vertices],f=[list(p.vertices) for p in o.data.polygons])
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
objects={name:name in bpy.data.objects and fingerprint(bpy.data.objects[name])==expected for name,expected in before['objects'].items()}
groups={name:name in bpy.data.node_groups and {'nodes':len(bpy.data.node_groups[name].nodes),'links':len(bpy.data.node_groups[name].links)}==expected for name,expected in before['groups'].items()}
files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected for name,expected in before['files'].items()}
result={'objects':objects,'groups':groups,'files':files,'all_preserved':all(objects.values()) and all(groups.values()) and all(files.values())}
(REPORT/'preservation.json').write_text(json.dumps(result,indent=2))
print('PRESERVATION',result['all_preserved'],len(objects),'objects',len(groups),'groups',len(files),'protected files')
print('changed',[(label,name) for label,items in [('object',objects),('group',groups),('file',files)] for name,ok in items.items() if not ok])
