"""Bounded structural QA on disposable Field/Cutter/Output. Does not edit authoring meshes."""
import bpy,bmesh,json,time,hashlib,math,sys,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from metrics import load_metrics
from vocabulary import CATEGORIES
R=ROOT/'Docs/Reviews/GNLevelBlockout';M=load_metrics()['values']
assert bpy.context.mode=='OBJECT'
assert 'TEST_BLOCKOUT_QA' not in bpy.data.collections
originals=[bpy.data.objects[n] for n in ('LEVEL_FIELD','LEVEL_CUTTER')]
real=bpy.data.objects['LEVEL_GENERATED_OUTPUT'];group=real.modifiers[0].node_group

def digest(mesh):
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in mesh.vertices],
                                    'f':[list(p.vertices) for p in mesh.polygons]},sort_keys=True).encode()).hexdigest()
before={o.name:digest(o.data) for o in originals}
col=bpy.data.collections.new('TEST_BLOCKOUT_QA');bpy.context.scene.collection.children.link(col)
copies=[]
for original in originals:
    o=bpy.data.objects.new('TEST_'+original.name,original.data.copy());o.matrix_world=original.matrix_world.copy();col.objects.link(o);copies.append(o)
field,cutter=copies
out=bpy.data.objects.new('TEST_BLOCKOUT_OUTPUT',bpy.data.meshes.new('TEST_BLOCKOUT_EMPTY'));col.objects.link(out);copies.append(out)
mod=out.modifiers.new('QA','NODES');mod.node_group=group
for k in real.modifiers[0].keys():mod[k]=real.modifiers[0][k]
ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
mod[ids['Field Object']]=field;mod[ids['Cutter Object']]=cutter
checks=[];samples={};seed_rows=[];updates=[];dimension_rows=[]
def expect(ok,name,detail=None):
    checks.append({'check':name,'passed':bool(ok),'detail':detail})
    if not ok:print('QA_FAIL',name,detail)
def set_input(name,val):mod[ids[name]]=val;out.update_tag()
def observed(scene,dg):updates.extend(u.id.name for u in dg.updates if u.is_updated_geometry and u.id.name.startswith('TEST_'))
bpy.app.handlers.depsgraph_update_post.append(observed)
def edit(obj):
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.mode_set(mode='EDIT')
    return bmesh.from_edit_mesh(obj.data)
def changed(obj):bmesh.update_edit_mesh(obj.data,loop_triangles=True,destructive=True)
def reset(obj,source):
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    mesh=obj.data;obj.data=source.data.copy();bpy.data.meshes.remove(mesh);obj.matrix_world=source.matrix_world.copy()

def capture(label,analyze=False):
    start=time.perf_counter();ev=out.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    elapsed=(time.perf_counter()-start)*1000
    verts=[v.co.copy() for v in mesh.vertices]
    polygons=[list(p.vertices) for p in mesh.polygons]
    bm=bmesh.new();bm.from_mesh(mesh);volume=bm.calc_volume(signed=True);bm.free()
    record={'vertices':len(verts),'faces':len(polygons),'hash':digest(mesh),'volume':volume,
            'bounds':[[min(v[i] for v in verts),max(v[i] for v in verts)] for i in range(3)] if verts else [],
            'wall_ms':elapsed,'modifier_ms':ev.modifiers[0].execution_time*1000,
            'warnings':[w.message for w in ev.modifiers[0].node_warnings],
            'field_mode':field.mode,'cutter_mode':cutter.mode}
    if analyze and verts:
        regions={};parts={};category_mismatches=[]
        cats=mesh.attributes.get('category_id');part=mesh.attributes.get('part_id');rids=mesh.attributes.get('region_id');angles=mesh.attributes.get('region_angle')
        if cats and part and rids:
            for p in mesh.polygons:
                category=cats.data[p.index].value;partid=part.data[p.index].value
                if category<0 or partid==100:continue
                vi=p.vertices[0]
                rid=rids.data[vi if rids.domain=='POINT' else p.index].value
                angle=angles.data[vi if angles.domain=='POINT' else p.index].value if angles else 0
                if rid<0:continue
                actual_module=mesh.attributes['module_id'].data[vi].value
                if actual_module!=category:category_mismatches.append([rid,actual_module,category])
                regions[rid]=category
                key=(rid,category,partid)
                item=parts.setdefault(key,{'coords':[],'world':[]})
                for vi in p.vertices:
                    v=verts[vi];item['coords'].append((math.cos(angle)*v.x+math.sin(angle)*v.y,-math.sin(angle)*v.x+math.cos(angle)*v.y,v.z));item['world'].append(v)
        for item in parts.values():item['bounds']=[[min(v[i] for v in item['coords']),max(v[i] for v in item['coords'])] for i in range(3)]
        record['category_counts']=dict(collections.Counter(CATEGORIES[c] for c in regions.values()))
        record['region_count']=len(regions)
        distances=[];violations=[]
        def value(rid,cat,partid):return parts.get((rid,cat,partid))
        def note(kind,val,limit,rid):
            distances.append({'kind':kind,'value_m':val,'reference_m':limit,'region':rid})
            if val<=0 or val>limit+.03:violations.append(distances[-1])
        bvh=BVHTree.FromPolygons(verts,polygons,all_triangles=False)
        for rid,cat in regions.items():
            if cat in (1,2,3):
                a=value(rid,cat,10);b=value(rid,cat,11)
                if a and b:
                    span=b['bounds'][0][0]-a['bounds'][0][1]
                    note(CATEGORIES[cat],span,M[{1:'running_jump',2:'air_jump',3:'slide_jump'}[cat]]*.9,rid)
                    if abs(a['bounds'][2][1]-b['bounds'][2][1])>.03:violations.append({'unequal_landing_height':rid})
                    midpoint=(sum(a['world'],Vector())/len(a['world'])+sum(b['world'],Vector())/len(b['world']))/2
                    hit=bvh.ray_cast(Vector((midpoint.x,midpoint.y,.1)),Vector((0,0,-1)),30)[0]
                    if hit is None or hit.z>-.2:violations.append({'gap_not_cut_from_floor':rid,'hit_z':hit.z if hit else None})
            if cat==5:
                wall=value(rid,cat,20)
                if wall:note('WALLRUN_LENGTH',wall['bounds'][0][1]-wall['bounds'][0][0],M['wallrun']*.9,rid)
            if cat==6:
                a=value(rid,cat,21);b=value(rid,cat,22)
                if a and b:note('WALL_JUMP_CHANNEL',b['bounds'][1][0]-a['bounds'][1][1],M['wall_jump_lateral']*.9,rid)
            if cat in (4,14):
                roof=value(rid,cat,30)
                if roof:
                    clear=roof['bounds'][2][0]
                    distances.append({'kind':'SLIDE_CLEARANCE' if cat==4 else 'STAND_CLEARANCE','value_m':clear,'region':rid})
                    if clear<(M['slide_height']+.1 if cat==4 else M['standing_height']+.15):violations.append({'low_clearance':clear,'region':rid})
            if cat==13:
                a=value(rid,cat,40);b=value(rid,cat,41)
                if a and b:
                    launch=sum(a['world'],Vector())/len(a['world']);launch.z=a['bounds'][2][1]+M['standing_height']-.15
                    anchor=sum(b['world'],Vector())/len(b['world'])
                    note('GRAPPLE_ACQUISITION_3D',(anchor-launch).length,M['grapple_range']*.9,rid)
            if cat==9:
                stairs=[value(rid,cat,i) for i in range(60,67)]
                if all(stairs):
                    for a,b in zip(stairs,stairs[1:]):note('STEP_RISE',b['bounds'][2][1]-a['bounds'][2][1],M['jump_rise']*.8,rid)
        record['dimensions']=distances;record['dimension_violations']=violations
        record['category_mismatches']=category_mismatches
        record['spawn_hits']=[]
        for radius in (0,mod[ids['Spawn Safe Radius']]*.95):
            for i in range(12 if radius else 1):
                angle=i*math.tau/12
                hit=bvh.ray_cast(Vector((radius*math.cos(angle),radius*math.sin(angle),30)),Vector((0,0,-1)),60)[0]
                record['spawn_hits'].append(list(hit) if hit else None)
    ev.to_mesh_clear();samples[label]=record
    return record

try:
    set_input('Use Cutter',False)
    for seed in (17,41,73,109,211):
        set_input('Seed',seed)
        row=capture('seed_'+str(seed),True);row['seed']=seed;seed_rows.append(row)
        expect(not row['warnings'],f'Seed {seed}: no modifier warnings',row['warnings'])
        expect(not row['category_mismatches'],f'Seed {seed}: macro grammar selects intended category',row['category_mismatches'][:5])
        expect(not row['dimension_violations'],f'Seed {seed}: evaluated traversal dimensions fit observed envelopes',row['dimension_violations'])
        expect(all(h and abs(h[2])<.01 for h in row['spawn_hits']),f'Seed {seed}: protected spawn has floor and no blocking overhead')
        expect(row['bounds'][0]==[-110.0,110.0] and row['bounds'][1]==[-88.0,88.0],f'Seed {seed}: clean full field bounds')
    expect(len({r['hash'] for r in seed_rows})==5,'Five seeds generate distinct layouts')
    set_input('Seed',17);repeat=capture('seed_17_repeat')
    expect(repeat['hash']==seed_rows[0]['hash'],'Same field + seed + parameters reproduces identical mesh')

    for name,values in [('Density',(0,1)),('Verticality',(0,1)),('Openness',(0,1)),('Route Complexity',(0,1)),('Traversal Difficulty',(0,1)),('Grapple Presence',(0,1)),('Height Range',(2,12))]:
        original=mod[ids[name]];states=[]
        for v in values:set_input(name,v);states.append(capture(name+'_'+str(v),name in ('Verticality','Traversal Difficulty','Grapple Presence')))
        expect(states[0]['hash']!=states[1]['hash'],name+' changes evaluated geometry')
        expect(not states[0]['warnings'] and not states[1]['warnings'],name+' endpoints produce no node warnings')
        if name=='Grapple Presence':expect(states[0].get('category_counts',{}).get('GRAPPLE_CROSSING',0)==0,'Grapple Presence zero removes target courts')
        if name=='Traversal Difficulty':expect(all(not s['dimension_violations'] for s in states),'Difficulty endpoints remain within observed metric envelopes')
        set_input(name,original)

    base=capture('field_before')
    bm=edit(field)
    for v in bm.verts:v.co.x*=1.2
    changed(field);scaled=capture('field_edit_scale')
    expect(scaled['field_mode']=='EDIT' and scaled['bounds'][0][1]>131.9 and scaled['hash']!=base['hash'],'Field Edit Mode scaling expands the evaluated extent live')
    corner=max(bm.verts,key=lambda v:v.co.x+v.co.y);corner.co.x-=70
    changed(field);skew=capture('field_corner_skew')
    expect(skew['hash']!=scaled['hash'],'Moving a Field corner changes footprint and whole-region admission')
    reset(field,originals[0])
    field.scale.y=.8;field.update_tag();scaled=capture('field_object_scale')
    expect(abs(scaled['bounds'][1][1]-70.4)<.02,'Field Object Mode scale changes actual dimensions')
    reset(field,originals[0])

    set_input('Use Cutter',False);uncut=capture('cutter_disabled')
    set_input('Use Cutter',True);cut=capture('cutter_enabled',True)
    expect(cut['hash']!=uncut['hash'] and cut['volume']<uncut['volume'],'Cutter subtracts real volume')
    bm=edit(cutter)
    for v in bm.verts:v.co.x-=20
    changed(cutter);moved=capture('cutter_edit_move')
    expect(moved['cutter_mode']=='EDIT' and moved['hash']!=cut['hash'],'Cutter Edit Mode move changes evaluated result live')
    face=max(bm.faces,key=lambda f:f.calc_center_median().y)
    result=bmesh.ops.extrude_face_region(bm,geom=[face]);newverts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,verts=newverts,vec=(0,12,0));bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    changed(cutter);extruded=capture('cutter_edit_extrude')
    expect(extruded['hash']!=moved['hash'] and all(e.is_manifold for e in bm.edges),'Cutter topology extrusion updates a closed exclusion volume')
    reset(cutter,originals[1])
    # Concave L-shaped prism rather than only rectangular cutters.
    poly=[(-9,-9),(9,-9),(9,-1),(-1,-1),(-1,9),(-9,9)];n=len(poly)
    verts=[(x,y,z) for z in (-10,20) for x,y in poly]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cutter.data.clear_geometry();cutter.data.from_pydata(verts,[],faces);cutter.data.update();cutter.update_tag()
    irregular=capture('cutter_concave_L')
    expect(irregular['volume']<uncut['volume'] and not irregular['warnings'],'Concave L-shaped cutter subtracts geometry without warnings')
    cutter.data.clear_geometry();cutter.data.update();cutter.update_tag();empty=capture('cutter_empty')
    expect(abs(empty['volume']-uncut['volume'])<.05 and not empty['warnings'],'Empty Cutter behaves as no exclusion')
    reset(cutter,originals[1]);cutter.location=(0,0,0);cutter.scale=(3,3,3);cutter.update_tag()
    spawn_cut=capture('cutter_over_spawn',True)
    expect(all(h and abs(h[2])<.01 for h in spawn_cut['spawn_hits']),'Cutter across origin cannot remove spawn floor')
    reset(cutter,originals[1])
    for quality in (0,1):
        set_input('Preview Quality',quality)
        timing=[]
        for i in range(3):set_input('Seed',17+i);timing.append(capture(f'perf_q{quality}_{i}'))
        samples['performance_q'+str(quality)]={'min_ms':min(s['wall_ms'] for s in timing),'max_ms':max(s['wall_ms'] for s in timing),'mean_ms':sum(s['wall_ms'] for s in timing)/3}
        expect(all(not s['warnings'] for s in timing),f'Preview quality {quality}: valid cutter evaluation')
    expect(bool(updates),'Depsgraph reports Field/Cutter/Output geometry updates')
    expect(all(digest(o.data)==before[o.name] for o in originals),'Real Field and Cutter geometry unchanged by technical QA')
finally:
    if observed in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(observed)
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for obj in copies:
        data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if data.users==0:bpy.data.meshes.remove(data)
    bpy.data.collections.remove(col)
    for obj in bpy.context.selected_objects:obj.select_set(False)
    originals[0].select_set(True);bpy.context.view_layer.objects.active=originals[0]
    report={'passed':bool(checks) and all(c['passed'] for c in checks),'checks':checks,'seeds':seed_rows,'samples':samples,'depsgraph_ids':sorted(set(updates))}
    (R/'technical_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('BLOCKOUT_QA',json.dumps({'passed':report['passed'],'checks':len(checks),'failed':[c for c in checks if not c['passed']],
        'seeds':[{k:s[k] for k in ('seed','vertices','faces','bounds','category_counts')} for s in seed_rows],
        'performance':{k:v for k,v in samples.items() if k.startswith('performance_')}}))
