"""Disposable input topology QA, chain contracts, native update and preservation."""
import bpy, bmesh, sys, json, time, hashlib, math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from common import *
obj,mod,ids=context();saved={k:mod[v] for k,v in ids.items()};tests={};presets={}
fixtures=[]
def check(name,condition,detail=None):
    tests[name]={'pass':bool(condition),'detail':detail}
def sample(**changes):
    t=time.perf_counter();set_controls(**changes);r=summary();r['update_and_read_ms']=round((time.perf_counter()-t)*1000,2);return r
try:
    for title,seed,style in [('balanced',17,0),('vertical',41,1),('speed',109,2)]:
        r=sample(**{'Seed':seed,'Layout Mode':style,'Section Preview':0,'Use Cutter':False,'Steep Angle':45})
        presets[title]=r
        check(title+'_15_nonempty_sections',len(r['sections'])==15)
        deltas=[(Vector(a['exit'])-Vector(b['entry'])).length for a,b in zip(r['sections'],r['sections'][1:])]
        check(title+'_continuous_section_chain',max(deltas)<.001,{'max_error_m':max(deltas),'length_m':sum(s['length'] for s in r['sections'])})
        check(title+'_origin_entry',r['sections'][0]['entry']==[0,0,0])
        running_jump=json.loads((REPORT/'movement_metrics.json').read_text())['values']['running_jump']
        check(title+'_comfortable_jump_gaps',all(0<=s['gap']<=running_jump*.65 for s in r['sections']),[s['gap'] for s in r['sections'] if s['kind']=='GAP_JUMP'])
        check(title+'_rotated_walls',any(abs(s['wall_yaw'])>.03 for s in r['sections'] if s['kind']=='WALLRUN'))
        check(title+'_steep_class',sum(s['kind']=='STEEP_DESCENT' for s in r['sections'])==2)
        check(title+'_grapple_in_range',all((Vector(s['anchor'])-Vector(s['entry'])).length<50 for s in r['sections'] if s['kind']=='GRAPPLE_CATCH'))
    base=sample(**{'Seed':17,'Layout Mode':0});repeat=sample(**{'Seed':18});repeat=sample(**{'Seed':17})
    check('seed_repeat_deterministic',base['hash']==repeat['hash'])
    check('three_distinct_examples',len({r['hash'] for r in presets.values()})==3)
    isolated=sample(**{'Section Preview':4});check('section_isolation',[s['id'] for s in isolated['sections']]==[3])
    sample(**{'Section Preview':0})
    for kind in ('Volume','Cutter'):
        real=saved[kind+' Object'];temp=bpy.data.objects.new('TEST_V03_'+kind,real.data.copy());bpy.context.scene.collection.objects.link(temp);fixtures.append(temp);temp.matrix_world=real.matrix_world.copy();temp.hide_set(True)
        set_controls(**{kind+' Object':temp,'Use Cutter':kind=='Cutter'})
        a=summary();bm=bmesh.new();bm.from_mesh(temp.data)
        bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
        for v in bm.verts:
            if kind=='Volume':v.co.x*=.82;v.co.y*=.85;v.co.z*=.9
            else:v.co.x*=2;v.co.y*=2;v.co.z*=2
        bm.to_mesh(temp.data);bm.free();temp.data.update();temp.update_tag();bpy.context.view_layer.update();b=summary()
        check(kind+'_disposable_topology_changed',len(temp.data.vertices)>len(real.data.vertices),{'before_v':len(real.data.vertices),'after_v':len(temp.data.vertices)})
        check(kind+'_depsgraph_output_changed',a['hash']!=b['hash'],{'before_faces':a['polygons'],'after_faces':b['polygons'],'before_bounds':a['bounds'],'after_bounds':b['bounds']})
        set_controls(**{kind+' Object':real,'Use Cutter':False})
    # Empty cutter bypass and spawn protection are independent of authored cutter placement.
    empty=bpy.data.objects.new('TEST_V03_EMPTY',bpy.data.meshes.new('TEST_V03_EMPTY'));bpy.context.scene.collection.objects.link(empty);fixtures.append(empty)
    e=sample(**{'Cutter Object':empty,'Use Cutter':True});n=sample(**{'Use Cutter':False})
    check('empty_cutter_bypass',e['hash']==n['hash'])
    set_controls(**{'Cutter Object':saved['Cutter Object']})
    low=sample(**{'Density':0});high=sample(**{'Density':1});check('density_changes_optional_walls',low['hash']!=high['hash'])
    set_controls(**{'Density':saved['Density']})
    steep=sample(**{'Steep Angle':70});check('steep_angle_changes_geometry',steep['hash']!=base['hash']);set_controls(**{'Steep Angle':45})
    before=json.loads((REPORT/'before.json').read_text())
    (REPORT/'qa_structure_before_keys.json').write_text(json.dumps(list(before)))
finally:
    set_controls(**saved)
    for fixture in fixtures:
        mesh=fixture.data;bpy.data.objects.remove(fixture,do_unlink=True);bpy.data.meshes.remove(mesh)
(REPORT/'technical_qa.json').write_text(json.dumps({'tests':tests,'presets':presets},indent=2))
print('V03_QA',len(tests),'checks; failures:',[k for k,v in tests.items() if not v['pass']])
print('presets',[(k,v['vertices'],v['polygons'],v['bounds'],v['update_and_read_ms']) for k,v in presets.items()])
