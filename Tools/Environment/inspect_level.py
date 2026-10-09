"""Read-only baseline of the canonical map before additive skyline authoring."""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.godot/skyscraper-pass'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Level_01_Blockout.blend'))

def signature(o):
    data = {'name':o.name,'type':o.type,'matrix':[list(r) for r in o.matrix_world],
            'parent':o.parent.name if o.parent else None,
            'collections':sorted(c.name for c in o.users_collection)}
    if o.type == 'MESH':
        data.update(vertices=[list(v.co) for v in o.data.vertices],
                    faces=[list(p.vertices) for p in o.data.polygons],
                    materials=[m.name if m else None for m in o.data.materials])
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()

records=[]
for o in bpy.context.scene.objects:
    points=[o.matrix_world@Vector(c) for c in o.bound_box] if o.type=='MESH' else [o.matrix_world.translation]
    # Godot axes, useful for scene composition; importer owns the actual conversion.
    points=[(p.x,p.z,-p.y) for p in points]
    records.append({'name':o.name,'type':o.type,'collections':[c.name for c in o.users_collection],
                    'min':[min(p[i] for p in points) for i in range(3)],
                    'max':[max(p[i] for p in points) for i in range(3)],'signature':signature(o),
                    'materials':[m.name if m else None for m in o.data.materials] if o.type=='MESH' else []})
out={'file':bpy.data.filepath,'objects':records,'collections':[c.name for c in bpy.data.collections],
     'images':[{'name':im.name,'path':im.filepath} for im in bpy.data.images]}
(OUT/'source_baseline.json').write_text(json.dumps(out,indent=2))
print('INSPECTED',len(records),'objects')
print(json.dumps(out['collections']))
