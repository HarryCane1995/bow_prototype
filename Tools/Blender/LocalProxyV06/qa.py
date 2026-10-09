"""Independent primitive-level overlap and local authoring QA on disposable meshes."""
import bpy,bmesh,importlib.util,json,math,time,statistics,hashlib
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV06'
sp=importlib.util.spec_from_file_location('v06_qa_base',HERE.parent/'LocalProxyV05/qa.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
q=base.q;q.GROUP='GN_LevelProxyGenerator_v06';q.PREFIX='TEST_LPV06_';q.REPORT=REPORT
records=base.records
def save(name,data):(REPORT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
def dots(a,b):return sum(x*y for x,y in zip(a,b))
def overlap(a,b,clearance=0,tolerance=.0004):
    aa=[Vector(a['occ_'+k]) for k in ['x','y','z']];bb=[Vector(b['occ_'+k]) for k in ['x','y','z']]
    ha=[x/2 for x in a['occ_size']];hb=[x/2 for x in b['occ_size']];delta=Vector(b['position'])-Vector(a['position'])
    axes=aa+bb+[x.cross(y) for x in aa for y in bb]
    for v in axes:
        if v.length<1e-5:continue
        v.normalize();ra=sum(abs(dots(v,x))*h for x,h in zip(aa,ha));rb=sum(abs(dots(v,x))*h for x,h in zip(bb,hb))
        if abs(dots(delta,v))>=ra+rb+clearance-tolerance:return False
    return True
def touching_exempt(a,b):
    floor={0,1,6};ground={2,4};ra=a['primitive_role'];rb=b['primitive_role']
    return (ra in floor and rb in floor) or (a['patch_id']==b['patch_id'] and ((ra in floor and rb in ground) or (rb in floor and ra in ground)))
def check_records(rows):
    rows=[r for r in rows if r['primitive_role']<90];overlaps=[];clearance=[];contacts=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            pair=[a['placement_id'],b['placement_id']]
            if overlap(a,b):overlaps.append(pair)
            elif not touching_exempt(a,b) and overlap(a,b,.3):clearance.append(pair)
            elif touching_exempt(a,b) and overlap(a,b,.001,tolerance=.0001):contacts.append(pair)
    groups={}
    for r in rows:groups.setdefault(r['section_id'],[]).append(r)
    budgets=[{'section':sid,'count':len(rs),'budget':rs[0]['primitive_budget']} for sid,rs in groups.items()]
    return {'primitive_count':len(rows),'unintended_overlaps':len(overlaps),'first_overlaps':overlaps[:10],'clearance_violations':len(clearance),'first_clearance_violations':clearance[:10],'intentional_boundary_contacts':len(contacts),'budgets':budgets,'budget_pass':all(r['count']<=r['budget'] for r in budgets),'pass':not overlaps and not clearance}
def helper_check(rows,spans):
    result=[]
    for s in spans:
        if s['span_class']!=4:continue
        group=[r for r in rows if r['section_id']==s['section_id']];helpers=[r for r in group if r['primitive_role']==9]
        roles={r['primitive_role'] for r in group};distance=[r['anchor_distance_from_approach'] for r in helpers]
        result.append({'span':s['section_id'],'gap':s['span_distance'],'catch':s['catch_length'],'helpers':len(helpers),'approach_and_catch_present':{0,1}.issubset(roles),'acquisition_distance':distance,'pass':len(helpers)==1 and {0,1}.issubset(roles) and s['span_distance']>23.035 and all(d<50 for d in distance)})
    return result
def representative(kind):
    q.cleanup();dims={'wide':(70,90,24),'narrow':(16,240,14),'spans':(20,480,12),'vertical':(14,18,72)}[kind]
    w,l,h=dims;s=q.box(width=w,length=l,height=h);o=q.host(s);p=q.host(s,6);d=q.host(s,2);reject=q.host(s,8)
    report={'fixture':kind,'width_length_height_m':dims,'seeds':{}}
    for seed in [17,42,73,109]:
        for obj in [o,p,d,reject]:q.setcontrol(obj,'Seed',seed)
        rows=records(p);spans=records(d);check=check_records(rows)
        arena=[r for r in rows if r['primitive_role']==6]
        report['seeds'][str(seed)]={'overlap':check,'patterns':sorted(set(r['pattern_id'] for r in rows)),'roles':{str(role):sum(r['primitive_role']==role for r in rows) for role in set(r['primitive_role'] for r in rows)},'rejected_count':len(records(reject)),'arena_score_max':max((r.get('arena_score',0) for r in spans),default=0),'arena_floors':[{'area':r['occ_size'][0]*r['occ_size'][1],'size':r['occ_size'],'scale_class':r['primitive_scale_class']} for r in arena],'required':helper_check(rows,spans),'warnings':q.snapshot(o)['warnings'],'records':rows,'spans':spans}
    report['containment']=q.containment(o,s)
    report['all_overlap_pass']=all(v['overlap']['pass'] and v['overlap']['budget_pass'] for v in report['seeds'].values())
    report['all_required_pass']=all(r['pass'] for v in report['seeds'].values() for r in v['required'])
    save(kind,report);q.cleanup()
    return {k:v for k,v in report.items() if k!='seeds'}|{'seeds':{s:{k:v for k,v in r.items() if k not in ['records','spans']} for s,r in report['seeds'].items()}}
def stability(case):
    q.cleanup();s=q.box(length=90,width=16,height=12);o=q.host(s);p=q.host(s,6)
    before=q.snapshot(o,lambda x:x[1]<75);br=[r for r in records(p) if r['position'][1]<75]
    q.extrude(s,(0,1,0),(0,20,0))
    if case=='vertical':q.extrude(s,(0,0,1),(0,0,28),lambda p:p.y>90)
    elif case=='angled':q.extrude(s,(0,1,0),(16,24,0),angle=-33)
    elif case=='wide':q.extrude(s,(0,1,0),(0,26,0),scale=(2,1,1))
    after=q.snapshot(o,lambda x:x[1]<75);ar=[r for r in records(p) if r['position'][1]<75]
    keys=['placement_id','pattern_id','primitive_id','position','occ_size','occ_x','occ_z']
    strip=lambda rows:sorted([repr({k:r[k] for k in keys}) for r in rows])
    report={'case':case,'old_geometry_hash_stable':before['hash']==after['hash'],'old_bounds_stable':before['bounds']==after['bounds'],'old_placements_stable':strip(br)==strip(ar),'overlap':check_records(records(p)),'containment':q.containment(o,s),'old_before':before,'old_after':after}
    save('stability_'+case,report);q.cleanup();return report
def authored():
    q.cleanup();src=bpy.data.objects['LEVEL_PROXY'];s=bpy.data.objects.new(q.PREFIX+'AuthoredCopy',src.data.copy());q.collection().objects.link(s)
    o=q.host(s);h=q.host(s,1);p=q.host(s,6);d=q.host(s,2);result={'source':q.source_summary(s)}
    rows=records(p);spans=records(d);result.update(overlap=check_records(rows),required=helper_check(rows,spans),records=rows,spans=spans,output=q.snapshot(o),helpers=q.snapshot(h),surface_containment=q.containment(o,s),helper_containment=q.containment(h,s))
    # Remove diagnostic hosts before performance measurements.
    for obj in [p,d]:m=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(m)
    timing={}
    for quality in [0,1]:
        q.setcontrol(o,'Preview Quality',quality);q.setcontrol(h,'Preview Quality',quality);runs=[]
        for i in range(5):
            s.data.vertices[0].co.z+=.0005*(1 if i%2==0 else -1);s.data.update();s.update_tag();t=time.perf_counter();bpy.context.view_layer.update()
            for obj in [o,h]:e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();nv=len(m.vertices);e.to_mesh_clear()
            runs.append((time.perf_counter()-t)*1000)
        timing[str(quality)]={'median_ms':statistics.median(runs),'max_ms':max(runs),'runs_ms':runs}
    result['timing']=timing;save('authored_performance',result);q.cleanup();return {k:v for k,v in result.items() if k not in ['records','spans']}

def mesh_matches_records(raw,rows):
    """Verify actual pre-Boolean mesh vertices against each independent OBB."""
    byid={r['placement_id']:r for r in rows if r['primitive_role']<9}
    e=raw.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();a=m.attributes.get('placement_id');errors=[];bounds={}
    assert a and a.domain=='POINT'
    for v in m.vertices:
        ident=a.data[v.index].value;r=byid.get(ident)
        if r is None:errors.append(['unknown_id',ident]);continue
        relative=v.co-Vector(r['position']);coords=[relative.dot(Vector(r['occ_'+k])) for k in ['x','y','z']]
        bounds.setdefault(ident,[]).append(coords)
        if any(abs(c)>size/2+.001 for c,size in zip(coords,r['occ_size'])):errors.append(['outside_obb',ident,list(v.co)])
    for ident,coords in bounds.items():
        sizes=[max(p[k] for p in coords)-min(p[k] for p in coords) for k in range(3)]
        if any(abs(a-b)>.002 for a,b in zip(sizes,byid[ident]['occ_size'])):errors.append(['wrong_size',ident,sizes,byid[ident]['occ_size']])
    e.to_mesh_clear();return {'checked_primitives':len(bounds),'duplicate_placement_ids':len([r for r in rows if r['primitive_role']<9])-len(byid),'errors':errors[:10],'pass':not errors and len(byid)==len(bounds)}

def controls_and_meshes():
    q.cleanup();result={'mesh_fixtures':[]}
    for width,length,height in [(20,480,16),(70,90,24),(14,18,72)]:
        s=q.box(width=width,length=length,height=height);p=q.host(s,6);raw=q.host(s,4)
        for o in [p,raw]:
            for name,val in [('Density',1.),('Verticality',1.),('Wallrun Bias',1.),('Ramp Presence',1.),('Orientation Randomness',25.)]:q.setcontrol(o,name,val)
        for seed in [17,42,73]:
            for o in [p,raw]:q.setcontrol(o,'Seed',seed)
            rows=records(p);result['mesh_fixtures'].append({'dimensions':[width,length,height],'seed':seed,'bounds':mesh_matches_records(raw,rows),'overlap':check_records(rows),'ramp_count':sum(r['primitive_role']==4 for r in rows)})
        q.cleanup()
    s=q.box(width=20,length=480,height=12);out=q.host(s);p=q.host(s,6);d=q.host(s,2);helper=q.host(s,1)
    spans=records(d);result['mesh_gaps']=base.gap_measurements(out,spans)
    for o in [p,helper]:q.setcontrol(o,'Grapple Bias',0.)
    rows=records(p);result['bias_zero']={'required':helper_check(rows,spans),'optional_count':sum(r['primitive_role']==10 for r in rows)}
    marker=next(r for r in rows if r['primitive_role']==9);x,y,z=marker['position'];cut=q.box('MarkerCutter',4,4,4,(x,y-2,z-2))
    for o in [out,p,d,helper]:q.setcontrol(o,'Cutter',cut);q.setcontrol(o,'Use Cutter',True)
    after=next(r for r in records(d) if r['section_id']==marker['section_id']);result['cutter_required_fallback']={'span_class':after['span_class'],'gap':after['span_distance'],'pass':after['span_class']!=4}
    for o in [out,p,d,helper]:q.setcontrol(o,'Use Cutter',False)
    result['length_variation']={}
    for v in [0,.82,1]:
        q.setcontrol(d,'Length Variation',v);lengths=[r['section_length'] for r in records(d) if r['span_class']];result['length_variation'][str(v)]={'min':min(lengths),'max':max(lengths),'std':statistics.pstdev(lengths)}
    before=q.snapshot(out);q.setcontrol(out,'Seed',42);changed=q.snapshot(out);q.setcontrol(out,'Seed',17);again=q.snapshot(out);result['seed']={'changes':before['hash']!=changed['hash'],'returns':before['hash']==again['hash']}
    # Disconnected island append, not a replacement of the authored shape.
    island=q.box('Island',width=16,length=24,height=12,origin=(50,0,-.7));bm=bmesh.new();bm.from_mesh(s.data);bm.from_mesh(island.data);bm.to_mesh(s.data);bm.free();s.data.update();s.update_tag();bpy.context.view_layer.update()
    old=q.snapshot(out,lambda p:p[0]<20);result['island_old_stable']=again['hash']==old['hash']
    modals=[o.bl_idname for o in getattr(bpy.context.window,'modal_operators',[])]
    if modals:
        result['api_edit_mode']={'deferred_user_modal':modals,'human_test':False}
        save('controls_and_meshes',result);q.cleanup();return result
    for x in bpy.context.selected_objects:x.select_set(False)
    s.select_set(True);bpy.context.view_layer.objects.active=s;before=q.snapshot(out);beforetop=q.source_summary(s);bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(s.data);f=max(bm.faces,key=lambda f:f.calc_center_median().y)
    ret=bmesh.ops.extrude_face_region(bm,geom=[f]);verts=[v for v in ret['geom'] if isinstance(v,bmesh.types.BMVert)];bmesh.ops.delete(bm,geom=[f],context='FACES_ONLY');bmesh.ops.translate(bm,verts=verts,vec=(0,30,0));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.update_edit_mesh(s.data,loop_triangles=True,destructive=True);s.update_tag();bpy.context.view_layer.update();after=q.snapshot(out)
    result['api_edit_mode']={'mode':bpy.context.mode,'output_changed':before['hash']!=after['hash'],'live_vertex_count':len(bm.verts),'before_vertex_count':beforetop['vertices'],'human_test':False};bpy.ops.object.mode_set(mode='OBJECT')
    save('controls_and_meshes',result);q.cleanup();return result
