"""Reopen the saved source; compare original geometry and non-target surface data."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.godot/level01-art'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Level_01_Blockout.blend'))
before=json.loads((OUT/'source_before.json').read_text())
manifest=json.loads((ROOT/'Assets/Materials/Environment/Level01Art/placement_manifest.json').read_text())
changed=set(manifest['material_assignments'])
for old in before['objects']:
    obj=bpy.data.objects[old['name']]
    assert [list(row) for row in obj.matrix_world]==old['matrix'],obj.name
    assert [c.name for c in obj.users_collection]==old['collections'],obj.name
    if obj.type=='MESH':
        geometry=hashlib.sha256(json.dumps({'v':[list(v.co) for v in obj.data.vertices],
            'p':[list(p.vertices) for p in obj.data.polygons]},sort_keys=True).encode()).hexdigest()
        assert geometry==old['geometry_hash'],'Geometry drift: '+obj.name
        if obj.name not in changed:
            assert [m.name if m else None for m in obj.data.materials]==old['materials'],obj.name
            assert [p.material_index for p in obj.data.polygons]==old['indices'],obj.name
            uvs=hashlib.sha256(json.dumps([[list(v.uv) for v in uv.data] for uv in obj.data.uv_layers]).encode()).hexdigest()
            assert uvs==old['uv_hash'],'Unrelated UV drift: '+obj.name
images=[]
for im in bpy.data.images:
    if im.name.startswith('T_Level01_Art_'):
        assert im.filepath.replace('\\','/').startswith('//Assets/Textures/Levels/Level_01/ArtPass/'),repr(im.filepath)
        assert Path(bpy.path.abspath(im.filepath)).is_file() and im.packed_file is None
        images.append(im.filepath)

# Every new solid in the combat half stays outside the original five route pads.
layout=json.loads((ROOT/'Scenes/Levels/Level_01/combat_layout.json').read_text())
pads=[r for r in layout['boxes'] if r['name'].startswith('CB_RoutePad')]
new_colliders=0
for obj in bpy.data.objects:
    if obj.get('art_owner')!=manifest['owner'] or not obj.name.endswith('-colonly'):
        continue
    new_colliders+=1
    points=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    xmin,xmax=min(p.x for p in points),max(p.x for p in points)
    zmin,zmax=min(-p.y for p in points),max(-p.y for p in points)
    if xmax<70:
        continue
    for pad in pads:
        x,_,z=pad['position']; w,_,d=pad['size']
        overlaps=xmax>x-w/2 and xmin<x+w/2 and zmax>z-d/2 and zmin<z+d/2
        assert not overlaps,'New solid encroaches on route: '+obj.name+' / '+pad['name']
protected=json.loads((OUT/'protected_before.json').read_text())
drift=[name for name,h in protected.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h]
assert not drift,'Protected file drift: '+str(drift)
report=dict(original_objects_preserved=len(before['objects']),material_assignments=len(changed),
            relative_images=len(images),new_colliders=new_colliders,route_pad_intrusions=0,
            protected_files=len(protected),protected_drift=drift,
            source_bytes=(ROOT/'Level_01_Blockout.blend').stat().st_size,
            materials=len(manifest['materials']),signs=sum(p['kind']=='sign' for p in manifest['placements']))
(OUT/'source_validation.json').write_text(json.dumps(report,indent=2))
print('LEVEL01_ART_SOURCE_PASS '+json.dumps(report))
