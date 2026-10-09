import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/'Docs/Reviews/ProxyChunksV04'
NAME='GN_ProxyChunk_Generator_v04'
TYPES=['PAD','WALLRUN','SLIDE','ARENA','DESCENT','VERTICAL','MIXED','GRAPPLE']

def context(obj):
    mod=next(m for m in obj.modifiers if m.type=='NODES' and m.node_group and m.node_group.name==NAME)
    ids={s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry'}
    return mod,ids
def set_controls(obj,**values):
    mod,ids=context(obj)
    for key,value in values.items():mod[ids[key]]=value
    obj.update_tag();bpy.context.view_layer.update()
def evaluated(obj):
    deps=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(deps)
    warnings=[w.message for mod in ev.modifiers if mod.type=='NODES' for w in mod.node_warnings]
    if warnings:raise RuntimeError(str(warnings))
    return bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
def attr(mesh,name,index=0):
    d=mesh.attributes[name].data[index];return list(d.vector) if hasattr(d,'vector') else d.value
def summary(obj):
    mesh=evaluated(obj)
    real=[p for p in mesh.polygons if attr(mesh,'flow_role',p.index)!=99]
    used=sorted({i for p in real for i in p.vertices});geometry={'v':[[round(c,5) for c in mesh.vertices[i].co] for i in used],'f':[list(p.vertices) for p in real]}
    result={'name':obj.name,'vertices':len(used),'faces':len(real),'hash':hashlib.sha256(json.dumps(geometry,sort_keys=True).encode()).hexdigest(),'bounds':[[min(mesh.vertices[v].co[i] for v in used),max(mesh.vertices[v].co[i] for v in used)] for i in range(3)],'type':TYPES[attr(mesh,'chunk_type')],**{n.removeprefix('chunk_'):attr(mesh,n) for n in ['chunk_entry','chunk_exit','chunk_anchor','chunk_length','chunk_width','chunk_wall_yaw','chunk_wall_pair_gap','chunk_steepness','chunk_valid']}}
    bpy.data.meshes.remove(mesh);return result
def extracted(obj,world=False):
    source=evaluated(obj);faces=[p for p in source.polygons if attr(source,'flow_role',p.index)!=99];used=sorted({v for p in faces for v in p.vertices});mapping={v:i for i,v in enumerate(used)}
    mesh=bpy.data.meshes.new(obj.name+'_SNAPSHOT');mesh.from_pydata([list(source.vertices[v].co) for v in used],[],[[mapping[v] for v in p.vertices] for p in faces])
    for mat in source.materials:mesh.materials.append(mat)
    for p,q in zip(mesh.polygons,faces):p.material_index=q.material_index
    if world:mesh.transform(obj.matrix_world)
    mesh.update();bpy.data.meshes.remove(source);return mesh
