"""Read persisted transforms from the pre-V05 backup; never save Blender data."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def transform(o):
    return {'basis':[list(r) for r in o.matrix_basis],
            'parent':o.parent.name if o.parent else None,
            'parent_inverse':[list(r) for r in o.matrix_parent_inverse]}
data={o.name:transform(o) for o in bpy.data.objects}
(ROOT/'Docs/Reviews/LocalProxyV05/baseline_transforms.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('BASELINE_TRANSFORMS',len(data))
