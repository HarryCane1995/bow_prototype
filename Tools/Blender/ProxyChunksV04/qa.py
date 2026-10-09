"""Disposable source-mesh, transform, duplication and per-object control QA."""
import bpy,bmesh,sys,json,time,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from proxy_api import *
checks={};details={};fixtures=[];original=bpy.data.objects['PROXY_01_WALLRUN'];active=bpy.context.active_object
def check(name,ok,detail=None):checks[name]=bool(ok);details[name]=detail
def clone(obj):
    copy=obj.copy();copy.data=obj.data.copy();copy.name='TEST_V04_'+obj.name;bpy.context.scene.collection.objects.link(copy);fixtures.append(copy);return copy
def sample(obj,**changes):
    t=time.perf_counter();set_controls(obj,**changes);r=summary(obj);r['update_read_ms']=round((time.perf_counter()-t)*1000,2);return r
try:
    baseline={o.name:summary(o) for o in bpy.data.collections['V04_PROXY_CHUNKS'].objects}
    check('eight_independent_proxy_objects',len(baseline)==8)
    for name,r in baseline.items():check(name+'_nonempty',r['faces']>0)
    copy=clone(original);set_controls(copy,**{'Show Direction':False})
    a=summary(copy);b=sample(copy,Seed=22)
    check('per_proxy_seed_changes_output',a['hash']!=b['hash'])
    check('source_proxy_unaffected_by_duplicate_seed',summary(original)['hash']==baseline[original.name]['hash'])
    check('duplicate_mesh_is_single_user',copy.data!=original.data and copy.data.users==1)
    repeat=sample(copy,Seed=17);check('repeat_seed_deterministic',a['hash']==repeat['hash'])
    before=summary(copy);copy.location+=(Vector((11,-8,3)));copy.rotation_euler.z+=.7;copy.update_tag();bpy.context.view_layer.update();after=summary(copy)
    check('G_R_keep_local_generated_geometry',before['hash']==after['hash'])
    check('no_global_volume_dependency',not any(n.bl_idname=='GeometryNodeObjectInfo' and n.inputs['Object'].default_value in [bpy.data.objects.get('LEVEL_VOLUME'),bpy.data.objects.get('LEVEL_CUTTER')] for n in bpy.data.node_groups[NAME].nodes))
    before=summary(copy);bm=bmesh.new();bm.from_mesh(copy.data);bm.normal_update();face=max(bm.faces,key=lambda f:f.calc_center_median().y)
    added=bmesh.ops.extrude_face_region(bm,geom=[face]);newv=[v for v in added['geom'] if isinstance(v,bmesh.types.BMVert)];bmesh.ops.translate(bm,verts=newv,vec=(0,9,0));bm.to_mesh(copy.data);bm.free();copy.data.update();copy.update_tag();bpy.context.view_layer.update();after=summary(copy)
    check('source_extrude_changes_topology',len(copy.data.vertices)>8)
    check('source_extrude_updates_own_result',before['hash']!=after['hash'] and after['length']>before['length']+8)
    check('source_extrude_leaves_original_mesh',len(original.data.vertices)==8 and summary(original)['hash']==baseline[original.name]['hash'])
    copy.scale=(1.5,1.3,1.2);copy.update_tag();bpy.context.view_layer.update();scaled=summary(copy)
    check('object_scale_updates_metric_dimensions',abs(scaled['length']-51*1.3)<.001)
    check('wall_pair_metric_spacing_scale_compensated',abs(scaled['wall_pair_gap']-after['wall_pair_gap'])<.001)
    arena=clone(bpy.data.objects['PROXY_02_ARENA']);set_controls(arena,**{'Show Direction':False})
    def changes(obj,name,low,high):
        mod,ids=context(obj);saved=mod[ids[name]];a=sample(obj,**{name:low});b=sample(obj,**{name:high});check(name+'_effective',a['hash']!=b['hash'],{'a':a['faces'],'b':b['faces']});set_controls(obj,**{name:saved})
    for name,lo,hi in [('Density',0,1),('Verticality',.1,.95),('Obstacle Spacing',6,24),('Orientation Randomness',0,28),('Complexity',0,1)]:changes(arena,name,lo,hi)
    changes(copy,'Openness',.1,.9)
    descent=clone(bpy.data.objects['PROXY_05_DESCENT']);changes(descent,'Ramp Steepness',35,70)
    # With only one non-zero auto bias (and mixed baseline disabled by explicit comparison),
    # a sweep over seeds must alter archetype distribution for each requested bias.
    big=clone(bpy.data.objects['PROXY_07_GRAPPLE']);set_controls(big,**{'Chunk Type':0,'Verticality':0,'Complexity':0,'Show Direction':False})
    biases=['Wallrun Bias','Slide Bias','Arena Bias','Grapple Bias']
    for bias in biases:
        set_controls(big,**{b:0 for b in biases})
        low=[sample(big,Seed=s)['type'] for s in range(1,9)]
        set_controls(big,**{bias:1})
        high=[sample(big,Seed=s)['type'] for s in range(1,9)]
        check(bias+'_changes_auto_selection',low!=high,{'zero':low,'one':high})
    set_controls(big,**{'Chunk Type':7})
    seed_hashes=[sample(big,Seed=s)['hash'] for s in [17,18,19]]
    check('grapple_seed_varies_optional_geometry',len(set(seed_hashes))>1)
    # Independent exclusion mesh; closed box shifts locally on a test copy only.
    cutter=bpy.data.objects.new('TEST_V04_EXCLUSION',bpy.data.objects['LEVEL_CUTTER'].data.copy());bpy.context.scene.collection.objects.link(cutter);fixtures.append(cutter);cutter.location=arena.matrix_world@Vector((0,15,0))
    set_controls(arena,**{'Exclusion Object':cutter,'Use Exclusion':False});a=summary(arena);b=sample(arena,**{'Use Exclusion':True});check('per_chunk_exclusion_changes_output',a['hash']!=b['hash'])
    check('other_chunks_unchanged_after_QA',all(summary(bpy.data.objects[n])['hash']==r['hash'] for n,r in baseline.items()))
    details['baseline']=baseline
finally:
    for o in fixtures:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if not data.users:bpy.data.meshes.remove(data)
    bpy.context.view_layer.objects.active=active
(REPORT/'technical_qa.json').write_text(json.dumps({'checks':checks,'details':details},indent=2))
print('V04_QA',len(checks),'checks; failures',[k for k,v in checks.items() if not v])
