"""Read-only source inventory for the Level_01 art dressing pass."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.godot/level01-art'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Level_01_Blockout.blend'))
records = []
for obj in bpy.context.scene.objects:
    points = [obj.matrix_world @ Vector(c) for c in obj.bound_box] if obj.type == 'MESH' else [obj.matrix_world.translation]
    points = [(p.x, p.z, -p.y) for p in points]
    record = dict(name=obj.name, type=obj.type, collections=[c.name for c in obj.users_collection],
                  min=[round(min(p[i] for p in points), 3) for i in range(3)],
                  max=[round(max(p[i] for p in points), 3) for i in range(3)],
                  matrix=[list(row) for row in obj.matrix_world])
    if obj.type == 'MESH':
        record.update(materials=[m.name if m else None for m in obj.data.materials],
                      vertices=len(obj.data.vertices), faces=len(obj.data.polygons),
                      indices=[p.material_index for p in obj.data.polygons],
                      geometry_hash=hashlib.sha256(json.dumps({'v':[list(v.co) for v in obj.data.vertices],
                          'p':[list(p.vertices) for p in obj.data.polygons]}, sort_keys=True).encode()).hexdigest(),
                      uv_hash=hashlib.sha256(json.dumps([[list(v.uv) for v in uv.data] for uv in obj.data.uv_layers]).encode()).hexdigest())
    records.append(record)
result = dict(file=bpy.data.filepath, objects=records,
              images=[dict(name=im.name, path=im.filepath) for im in bpy.data.images])
(OUT / 'source_before.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
for r in records:
    print(json.dumps({k:r[k] for k in ('name','type','min','max','collections')} | {'materials':r.get('materials',[])}, ensure_ascii=False))
