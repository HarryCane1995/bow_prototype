"""Read evaluated native GN geometry and its stable section metadata."""
import bpy, json, hashlib, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/'Docs/Reviews/FlowCourseV03'
KINDS=['ENTRY','GAP_JUMP','WALLRUN','WALL_JUMP_SHAFT','SLIDE_CHUTE','STEEP_DESCENT','GRAPPLE_CATCH','MIXED_PLATFORMS','ARENA_POCKET','MULTI_ROUTE','RECOVERY','RAMP_ASCENT']

def context():
    obj=bpy.data.objects['LEVEL_FLOW_OUTPUT'];mod=obj.modifiers['GN_LevelBlockout_Generator_v03']
    ids={s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    return obj,mod,ids

def set_controls(**values):
    obj,mod,ids=context()
    for key,value in values.items():mod[ids[key]]=value
    obj.update_tag();bpy.context.view_layer.update()

def evaluated():
    obj,mod,ids=context();deps=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(deps)
    warnings=[w.message for w in ev.modifiers[0].node_warnings]
    if warnings:raise RuntimeError(str(warnings))
    return bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)

def value(mesh,name,index):
    d=mesh.attributes[name].data[index]
    return list(d.vector) if hasattr(d,'vector') else d.value

def sections(mesh):
    result=[]
    ids=sorted({value(mesh,'flow_section',p.index) for p in mesh.polygons})
    for sid in ids:
        faces=[p for p in mesh.polygons if value(mesh,'flow_section',p.index)==sid and value(mesh,'flow_role',p.index)!=99]
        if not faces:continue
        # Corner catch pads are added outside the shared grammar and carry zero
        # defaults for its metadata. Read from a grammar face instead of the pad.
        i=max(faces,key=lambda p:abs(value(mesh,'flow_wall_yaw',p.index))).index
        result.append({'id':sid,'kind':KINDS[value(mesh,'flow_kind',i)],'faces':len(faces),**{name.removeprefix('flow_'):value(mesh,name,i) for name in ['flow_entry','flow_exit','flow_anchor','flow_length','flow_height_change','flow_steep_angle','flow_gap','flow_wall_pair_gap','flow_wall_yaw']}})
    return result

def summary():
    mesh=evaluated();mesh.calc_loop_triangles()
    data={'v':[[round(c,5) for c in v.co] for v in mesh.vertices],'f':[list(p.vertices) for p in mesh.polygons]}
    result={'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'triangles':len(mesh.loop_triangles),
        'hash':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),
        'bounds':[[min(v.co[i] for v in mesh.vertices),max(v.co[i] for v in mesh.vertices)] for i in range(3)],'sections':sections(mesh)}
    bpy.data.meshes.remove(mesh);return result

def section_mesh(source,sid,relative=False):
    faces=[p for p in source.polygons if value(source,'flow_section',p.index)==sid and value(source,'flow_role',p.index)!=99]
    used=sorted({v for p in faces for v in p.vertices});remap={v:i for i,v in enumerate(used)}
    origin=value(source,'flow_entry',faces[0].index) if relative else (0,0,0)
    mesh=bpy.data.meshes.new('V03_SECTION_%02d'%sid)
    mesh.from_pydata([tuple(source.vertices[v].co[i]-origin[i] for i in range(3)) for v in used],[],[[remap[v] for v in p.vertices] for p in faces])
    for mat in source.materials:mesh.materials.append(mat)
    for target,original in zip(mesh.polygons,faces):target.material_index=original.material_index
    mesh.update();return mesh
