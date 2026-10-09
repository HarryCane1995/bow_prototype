"""Material/loop-UV only correction. Never edits vertices, faces or transforms.

Shared by the normal generator and the non-destructive saved-library migration.
Facades use gravity-aligned floor pitch; service surfaces use isometric face UV.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[3]/'Art/Environment/Highrise100'
RECS={r['key']:r for r in json.loads((OUT/'materials.json').read_text())}
Z=Vector((0,0,1));X=Vector((1,0,0))
TILES={'floor_rooftop':5.,'floor_metal_deck':3.,'wall_dark_concrete':12.,'wall_maintenance':4.,'wall_service_rack':3.,'wall_vent_bank':4.,'wrap_tank_shell':4.,'wrap_heavy_pipe':3.}

def is_facade(key):return key.startswith('f') and key[1:2].isdigit()
def basekey(key):return key[:-3] if key.endswith('_uv') else key

def get_material(key):
    name='H100_'+key;m=bpy.data.materials.get(name)
    if m is None:
        old=bpy.data.materials.get('H100_'+basekey(key))
        if old is None:
            # Inactive original recipe, e.g. tank shell: reuse the PBR node contract.
            old=bpy.data.materials.get('H100_floor_metal_deck')
        m=old.copy();m.name=name
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image:
                channel=Path(n.image.filepath).stem
                img=bpy.data.images.load(str(OUT/'Textures'/key/(channel+'.png')),check_existing=True)
                img.filepath=f'//Textures/{key}/{channel}.png'
                if channel in ('normal','orm'):img.colorspace_settings.name='Non-Color'
                n.image=img;n.extension='EXTEND' if key.startswith('sign_') else 'REPEAT'
    if key in RECS:
        m['recipe']=RECS[key]['recipe'];m['seed']=RECS[key]['seed']
    m['uv_qa_version']=1;m['uv_qa_source_key']=basekey(key)
    if is_facade(key):
        m['uv_qa_facade_crop_height_px']=956;m['uv_qa_tile_width_m']=42.
        m['uv_qa_floor_height_px']=RECS[key]['parameters']['floor_height']
    elif not key.startswith('sign_'):
        size=TILES.get(key,4.);m['uv_qa_tile_width_m']=size;m['uv_qa_tile_height_m']=size
    return m

def desired(key,part,n,area):
    k=basekey(key);p=part.lower()
    if k.startswith('sign_'):
        return k+'_uv' if n.y < -.99 and abs(n.z)<.1 and area>1 else 'floor_metal_deck'
    if k in ('signal','warm'):return k
    if n.z < -.55:return 'wall_dark_concrete'
    if n.z > .55:
        return 'floor_rooftop' if is_facade(k) or k in ('glass','wall_dark_concrete','floor_rooftop') else 'floor_metal_deck'
    if 'hvacfan' in p or 'antenna' in p:return 'floor_metal_deck'
    if 'hvac' in p:return 'wall_vent_bank'
    if 'watertank' in p:return 'wrap_tank_shell'
    if 'exhaust' in p:return 'wrap_heavy_pipe'
    if 'roofaccess' in p or 'replacementpanel' in p:return 'wall_maintenance'
    if 'commscabinet' in p:return 'wall_service_rack'
    if is_facade(k):return k+'_uv'
    if k=='floor_rooftop':return 'floor_metal_deck'
    return k

def apply_collection(col,record):
    changes=[];pitch=record['parameters']['floor_pitch']
    for o in col.objects:
        if o.type!='MESH':continue
        mesh=o.data;uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
        o['uv_qa_floor_pitch_m']=pitch;o['uv_qa_version']=1
        part=o.get('part',o.name);normalmat=o.matrix_world.to_3x3().inverted().transposed()
        for p in mesh.polygons:
            old=mesh.materials[p.material_index];oldkey=old.name.removeprefix('H100_')
            coords=[o.matrix_world@mesh.vertices[i].co for i in p.vertices]
            n=(normalmat@p.normal).normalized();key=desired(oldkey,part,n,p.area)
            mat=get_material(key)
            if mat.name not in mesh.materials:mesh.materials.append(mat)
            p.material_index=mesh.materials.find(mat.name)
            u=Z.cross(n).normalized() if abs(n.z)<.999 else X
            v=n.cross(u).normalized()
            if is_facade(key):
                width=42.;height=956/RECS[key]['parameters']['floor_height']*pitch
                points=[(q.dot(u)/width,q.z/height) for q in coords]
            elif key.startswith('sign_'):
                # Outward U and gravity V: text is never mirrored, entire sheet fits.
                width=max(q.dot(u) for q in coords)-min(q.dot(u) for q in coords)
                height=max(q.z for q in coords)-min(q.z for q in coords)
                iw,ih=RECS[key]['image_size'];scale=min(width/iw,height/ih)
                cx=(max(q.dot(u) for q in coords)+min(q.dot(u) for q in coords))/2
                cz=(max(q.z for q in coords)+min(q.z for q in coords))/2
                points=[((q.dot(u)-cx)/(iw*scale)+.5,(q.z-cz)/(ih*scale)+.5) for q in coords]
            else:
                size=TILES.get(key,4.);points=[(q.dot(u)/size,q.dot(v)/size) for q in coords]
            for li,xy in zip(p.loop_indices,points):uv.data[li].uv=xy
            if oldkey!=key:changes.append(dict(mesh=o.name,face=p.index,before=oldkey,after=key))
        # Keep only used slots, remapping indices without touching mesh topology.
        used=sorted(set(p.material_index for p in mesh.polygons));mats=[mesh.materials[i] for i in used];indices=[used.index(p.material_index) for p in mesh.polygons]
        mesh.materials.clear()
        for m in mats:mesh.materials.append(m)
        for p,i in zip(mesh.polygons,indices):p.material_index=i
        o['recipe']=json.dumps([m.name.removeprefix('H100_') for m in mats])
    slots={o.get('part',o.name):[m.name.removeprefix('H100_') for m in o.data.materials] for o in col.objects if o.type=='MESH'}
    counts={}
    for o in col.objects:
        if o.type=='MESH':
            for p in o.data.polygons:
                key=o.data.materials[p.material_index].name.removeprefix('H100_');counts[key]=counts.get(key,0)+1
    record.update(material_slots=slots,material_face_counts=counts,material_assignment_schema='per-mesh list; per-face indices in source',uv_material_qa_version=1,
        recipes=[RECS[k]['recipe'] for k in sorted(counts) if k in RECS],material_seeds={k:RECS[k]['seed'] for k in sorted(counts) if k in RECS})
    record['previews']=[f'Previews/{record["id"]}.png',f'UV_Material_QA/Views/{record["id"]}_back.png',f'UV_Material_QA/Views/{record["id"]}_roof.png']
    bpy.data.objects[record['id']]['record_json']=json.dumps(record)
    return changes
