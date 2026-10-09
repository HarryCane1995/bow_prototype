"""Edit-mode technical QA on disposable copies only. Never touches real source topology."""
import bpy
import bmesh
import hashlib
import json
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/'Docs/Reviews/GNAuthoringLab'
REPORT.mkdir(parents=True,exist_ok=True)
(REPORT/'.gdignore').write_text('')
real_source=bpy.data.objects['LEVEL_AUTHORING_SOURCE']
real_envelope=bpy.data.objects['LEVEL_ENVELOPE']
group=bpy.data.node_groups['GN_LevelAuthoring_POC']
assert bpy.context.mode=='OBJECT'
assert not bpy.data.collections.get('TEST_GN_DISABLED'), 'Previous QA fixture exists; inspect before reusing'
def mesh_hash(mesh):
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in mesh.vertices],
                                     'f':[list(p.vertices) for p in mesh.polygons]},sort_keys=True).encode()).hexdigest()
original_hashes={o.name:mesh_hash(o.data) for o in (real_source,real_envelope)}
col=bpy.data.collections.new('TEST_GN_DISABLED');bpy.context.scene.collection.children.link(col)
src=bpy.data.objects.new('TEST_GN_AUTHORING_SOURCE',real_source.data.copy());col.objects.link(src)
env=bpy.data.objects.new('TEST_GN_ENVELOPE',real_envelope.data.copy());col.objects.link(env)
out=bpy.data.objects.new('TEST_GN_OUTPUT',bpy.data.meshes.new('TEST_GN_OutputMesh'));col.objects.link(out)
mod=out.modifiers.new('TEST_GN','NODES');mod.node_group=group
ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
for s in group.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT':mod[s.identifier]=s.default_value
mod[ids['Source Object']]=src;mod[ids['Envelope Object']]=env
checks=[];samples={};perf=[];updates=[]
def depsgraph_handler(scene,depsgraph):
    updates.extend(u.id.name for u in depsgraph.updates if u.is_updated_geometry and u.id.name.startswith('TEST_GN'))
bpy.app.handlers.depsgraph_update_post.append(depsgraph_handler)
def expect(condition,name):
    checks.append({'check':name,'passed':bool(condition)})
    if not condition:print('GN_QA_FAIL',name)
def sample(name):
    t=time.perf_counter()
    evaluated=out.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    elapsed=(time.perf_counter()-t)*1000
    result={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'hash':mesh_hash(mesh),
            'bounds':[[min(v.co[i] for v in mesh.vertices),max(v.co[i] for v in mesh.vertices)] for i in range(3)] if mesh.vertices else [],
            'evaluate_and_materialize_ms':elapsed,'source_mode':src.mode,'envelope_mode':env.mode}
    em=evaluated.modifiers[0]
    result['modifier_execution_ms']=em.execution_time*1000
    warnings=getattr(em,'node_warnings',None)
    result['node_warnings']=[str(w.message) for w in warnings] if warnings is not None else []
    evaluated.to_mesh_clear()
    samples[name]=result
    return result
def select_edit(obj):
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT')
    return bmesh.from_edit_mesh(obj.data)
def changed(obj):
    bmesh.update_edit_mesh(obj.data,loop_triangles=True,destructive=True)
def set_input(name,value):
    mod[ids[name]]=value;out.update_tag()
def topology(bm):return [len(bm.verts),len(bm.edges),len(bm.faces)]

try:
    clipped=sample('baseline_clipped')
    set_input('Use Envelope',False);full=sample('baseline_unclipped')
    expect(abs(full['bounds'][0][1]-3.8)<.001,'Unconstrained source panels end at X=3.8')
    expect(abs(clipped['bounds'][0][1]-2.8)<.001,'Envelope clips at X=2.8')
    expect(full['vertices']==32 and full['faces']==24,'Four source quads generate four closed six-face panels')

    # Reproduce the zero-displacement intermediate state of native UI E.
    set_input('Use Envelope',True)
    bm=select_edit(src)
    face=list(bm.faces)[0]
    result=bmesh.ops.extrude_face_region(bm,geom=[face])
    newverts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY')
    changed(src);zero_extrude=sample('edit_extrude_zero_displacement')
    expect(len(bm.faces)>4 and zero_extrude['faces']==24 and not zero_extrude['node_warnings'],
           'Native Extrude zero-displacement intermediate state keeps valid clipped preview')
    bmesh.ops.translate(bm,verts=newverts,vec=(0,0,1))
    changed(src);moved_extrude=sample('edit_region_extrude_clipped')
    expect(moved_extrude['faces']>zero_extrude['faces'] and not moved_extrude['node_warnings'],
           'Region Extrude with envelope enabled changes clipped output without warnings')
    bpy.ops.object.mode_set(mode='OBJECT')
    old=src.data;src.data=real_source.data.copy();bpy.data.meshes.remove(old)
    set_input('Use Envelope',False)

    bm=select_edit(src);before=topology(bm)
    vertex=min(bm.verts,key=lambda v:v.co.x+v.co.y);vertex.co.x-=1
    changed(src);moved=sample('edit_vertex_move')
    expect(moved['bounds'][0][0]<full['bounds'][0][0]-.5 and src.mode=='EDIT','Vertex move changes evaluated bounds while source stays in Edit Mode')
    face=min(bm.faces,key=lambda f:f.calc_center_median().x)
    bmesh.ops.subdivide_edges(bm,edges=list(face.edges),cuts=1,use_grid_fill=True)
    changed(src);subdivided=sample('edit_subdivide')
    expect(topology(bm)!=before and subdivided['faces']>moved['faces'],'Subdivide changes source topology and output face count')

    face=max(bm.faces,key=lambda f:f.calc_area())
    result=bmesh.ops.extrude_discrete_faces(bm,faces=[face])
    newfaces=result['faces'];newverts={v for f in newfaces for v in f.verts}
    bmesh.ops.translate(bm,verts=list(newverts),vec=(0,0,1.0))
    changed(src);extruded=sample('edit_extrude')
    expect(extruded['hash']!=subdivided['hash'] and extruded['bounds'][2][1]>1.5,'Extrude changes evaluated topology and height in Edit Mode')
    before=topology(bm)
    bmesh.ops.delete(bm,geom=[max(bm.faces,key=lambda f:f.calc_center_median().z)],context='FACES')
    changed(src);deleted=sample('edit_delete_face')
    expect(topology(bm)[2]<before[2] and deleted['faces']<extruded['faces'],'Deleting a source face removes its generated panel')

    candidates=[e for e in bm.edges if len(e.link_faces)==2]
    edge=candidates[0] if candidates else list(bm.edges)[0]
    before=topology(bm)
    bmesh.ops.bevel(bm,geom=[edge],offset=.08,segments=2,affect='EDGES',clamp_overlap=True)
    changed(src);beveled=sample('edit_bevel')
    expect(topology(bm)!=before and beveled['hash']!=deleted['hash'],'Bevel changes source and generated topology')

    # Replace ONLY disposable data for an independent envelope case.
    bpy.ops.object.mode_set(mode='OBJECT')
    old=src.data;src.data=real_source.data.copy();bpy.data.meshes.remove(old)
    set_input('Use Envelope',True)
    sample('envelope_before')
    bm=select_edit(env)
    for vertex in bm.verts:
        if vertex.co.x>0:vertex.co.x=-.5
    changed(env);contracted=sample('edit_envelope_contract')
    expect(contracted['faces']<clipped['faces'] and abs(contracted['bounds'][0][1]+.5)<.001,'Editing envelope clips away panels; source untouched')
    face=max(bm.faces,key=lambda f:f.calc_center_median().x)
    before=topology(bm)
    result=bmesh.ops.extrude_face_region(bm,geom=[face])
    newverts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,verts=newverts,vec=(4,0,0))
    bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    changed(env);expanded=sample('edit_envelope_extrude')
    expect(topology(bm)!=before and expanded['faces']>contracted['faces'] and expanded['bounds'][0][1]>3.4,
           'Envelope face extrusion restores generation space live in Edit Mode')
    expect(all(e.is_manifold for e in bm.edges),'Extruded envelope remains a closed manifold volume')
    bpy.ops.object.mode_set(mode='OBJECT')
    set_input('Envelope Margin',.3);margin_plus=sample('margin_positive')
    set_input('Envelope Margin',-.3);margin_minus=sample('margin_negative')
    expect(margin_plus['bounds'][0][1]>margin_minus['bounds'][0][1],'Positive and negative envelope margins expand and contract result')
    set_input('Envelope Margin',0)
    set_input('Use Envelope',False)
    set_input('Preview Quality',1);q1=sample('quality_1')
    expect(q1['faces']>full['faces'],'Preview Quality adds procedural subdivisions only')

    flag=src.data.attributes.new('proc_enabled','BOOLEAN','FACE')
    for i,item in enumerate(flag.data):item.value=(i==0)
    src.data.update();src.update_tag()
    set_input('Preview Quality',0);flagged=sample('face_attribute')
    expect(flagged['faces']==6,'Optional proc_enabled selects one source face = one closed panel')
    src.data.attributes.remove(flag)

    # Modest scale-up probe. Values are local warm update times, not FPS promises.
    old=src.data;src.data=bpy.data.meshes.new('TEST_GN_PerformanceGrid');bpy.data.meshes.remove(old)
    grid=bmesh.new();bmesh.ops.create_grid(grid,x_segments=16,y_segments=16,size=8);grid.to_mesh(src.data);grid.free()
    src.data.update();src.update_tag()
    for quality in (0,1,2):
        set_input('Preview Quality',quality);set_input('Use Envelope',True)
        times=[];executions=[]
        for iteration in range(4):
            set_input('Envelope Margin',.01 if iteration%2 else -.01)
            record=sample(f'performance_q{quality}_{iteration}')
            times.append(record['evaluate_and_materialize_ms']);executions.append(record['modifier_execution_ms'])
        perf.append({'source_faces':len(src.data.polygons),'preview_quality':quality,
                     'min_ms':min(times),'max_ms':max(times),'mean_ms':sum(times)/len(times),
                     'modifier_execution_ms':executions,'clipped_output_faces':record['faces']})
    expect(bool(updates),'Depsgraph reports geometry updates on disposable dependencies')
    expect(all(not v['node_warnings'] for v in samples.values()),'No evaluated Geometry Nodes warnings')
    expect(all(mesh_hash(bpy.data.objects[name].data)==digest for name,digest in original_hashes.items()),'Real source and envelope topology unchanged by QA')
    expect(len(real_source.modifiers)==0 and len(real_envelope.modifiers)==0,'Real source/envelope remain plain meshes without modifiers')
finally:
    if depsgraph_handler in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(depsgraph_handler)
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for obj in (src,env,out):
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(col)
    for obj in bpy.context.selected_objects:obj.select_set(False)
    real_source.select_set(True);bpy.context.view_layer.objects.active=real_source
    report={'blender':bpy.app.version_string,'checks':checks,'samples':samples,'performance':perf,
            'depsgraph_updated_ids':sorted(set(updates)),'real_mesh_hashes':original_hashes,
            'passed':bool(checks) and all(c['passed'] for c in checks)}
    (REPORT/'technical_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('GN_TECHNICAL_QA',json.dumps({'passed':report['passed'],'checks':len(checks),'failed':[c['check'] for c in checks if not c['passed']],'performance':perf}))
