"""Read-only source snapshot for the Level_01 floor material pass."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.godot/level01-floor'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Level_01_Blockout.blend'))

records = []
for obj in bpy.context.scene.objects:
    record = {'name': obj.name, 'type': obj.type, 'collections': [c.name for c in obj.users_collection],
              'matrix': [list(row) for row in obj.matrix_world]}
    if obj.type == 'MESH':
        mesh = obj.data
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        normals = obj.matrix_world.to_3x3().inverted().transposed()
        up_faces = [p.index for p in mesh.polygons if (normals @ p.normal).normalized().z > 0.7]
        record.update(materials=[m.name if m else None for m in mesh.materials],
            material_faces={str(i): sum(p.material_index == i for p in mesh.polygons) for i in range(len(mesh.materials))},
            min=[min(v[i] for v in coords) for i in range(3)],
            max=[max(v[i] for v in coords) for i in range(3)],
            vertices=len(mesh.vertices), faces=len(mesh.polygons),
            uv_layers=[uv.name for uv in mesh.uv_layers], up_faces=up_faces,
            geometry_hash=hashlib.sha256(json.dumps({'v': [list(v.co) for v in mesh.vertices],
               'p': [list(p.vertices) for p in mesh.polygons]}, sort_keys=True).encode()).hexdigest(),
            uv_hash=hashlib.sha256(json.dumps([[list(x.uv) for x in uv.data] for uv in mesh.uv_layers]).encode()).hexdigest(),
            indices=[p.material_index for p in mesh.polygons])
    records.append(record)
result = {'file': bpy.data.filepath, 'objects': records,
          'images': [{'name': im.name, 'path': im.filepath} for im in bpy.data.images]}
(OUT / 'source_inspection.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('FLOOR_SOURCE_INSPECTION=' + str(len(records)))
