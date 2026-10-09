"""Bounded API QA on disposable proxies. Human and Godot testing are excluded."""
import bpy,bmesh,importlib.util,json,math,statistics,time,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV05'
sp=importlib.util.spec_from_file_location('v05_fixture_base',HERE.parent/'LocalProxyV04/qa.py');q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
q.GROUP='GN_LevelProxyGenerator_v05';q.PREFIX='TEST_LPV05_';q.REPORT=REPORT
sp=importlib.util.spec_from_file_location('v05_containment',HERE/'containment.py');contain=importlib.util.module_from_spec(sp);sp.loader.exec_module(contain)
q.containment=lambda obj,source:contain.check(q,obj,source)


def records(obj):
    bpy.context.view_layer.update();e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();rows=[]
    attrs=[a for a in m.attributes if a.domain=='POINT' and not a.name.startswith('.') and a.name!='position']
    for v in m.vertices:
        row={'position':list(v.co)}
        for a in attrs:
            item=a.data[v.index]
            if a.data_type=='FLOAT_VECTOR':row[a.name]=list(item.vector)
            elif hasattr(item,'value'):row[a.name]=item.value
        rows.append(row)
    e.to_mesh_clear();return rows


def variants(obj,region=None):
    bpy.context.view_layer.update();e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
    out=[];va=m.attributes.get('variant_id');fa=m.attributes.get('variant_family');sa=m.attributes.get('section_id')
    if va and va.domain=='FACE':
        for p in m.polygons:
            if region and not all(region(m.vertices[i].co) for i in p.vertices):continue
            sid=sa.data[p.vertices[0]].value if sa and sa.domain=='POINT' else 0
            out.append((sid,va.data[p.index].value,fa.data[p.index].value))
    e.to_mesh_clear();return sorted(set(out))


def save(name,result):(REPORT/(name+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')


def gap_measurements(obj,spanrows):
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();bm=bmesh.new();bm.from_mesh(m);bv=BVHTree.FromBMesh(bm,epsilon=0);r=[]
    for row in spanrows:
        if not row['span_class']:continue
        forward=Vector(row['local_forward']).normalized();up=Vector(row['lp_up']);start=Vector(row['position'])
        p=start+forward*(row['section_length']+.005)+up*.25
        hit=bv.ray_cast(p,forward,row['span_distance']+1)
        measured=hit[3]+.005 if hit[0] is not None else None
        r.append({'class':row['span_class'],'section_id':row['section_id'],'declared':row['span_distance'],'mesh_measured':measured,'match':measured is not None and abs(measured-row['span_distance'])<.02})
    bm.free();e.to_mesh_clear();return r


def spans_and_rhythm():
    q.cleanup();s=q.box(length=480,width=20,height=12);d=q.host(s,2);h=q.host(s,5);out=q.host(s);report={};allclasses={};chosen=None
    for seed in [17,42,73,1,2,3,4,5,6,7,8,9,10,11]:
        q.setcontrol(d,'Seed',seed);rows=records(d)
        for row in rows:
            if row['span_class'] and str(row['span_class']) not in allclasses:allclasses[str(row['span_class'])]={'seed':seed,'row':row}
        if any(r['span_class']==4 for r in rows) and chosen is None:chosen=seed
        if len(allclasses)==4 and chosen is not None:break
    report['class_examples']=allclasses;report['all_four_classes_seen']=len(allclasses)==4
    rhythm={}
    for variation in [0,.82,1]:
        q.setcontrol(d,'Length Variation',variation);q.setcontrol(d,'Seed',17);rows=records(d)
        lengths=[r['section_length'] for r in rows if r['span_class']]
        starts=[r['sequence_start'] for r in rows]
        contiguous=all(abs(rows[i+1]['sequence_start']-(row['sequence_start']+row['section_length']+row['span_distance']+row['catch_length']))<.003 for i,row in enumerate(rows[:-1]))
        rhythm[str(variation)]={'lengths_m':lengths,'min':min(lengths),'max':max(lengths),'std':statistics.pstdev(lengths),'start_at_zero':abs(starts[0])<.001,'contiguous_sequence':contiguous}
    report['rhythm']=rhythm
    if chosen is not None:
        for o in [d,h,out]:q.setcontrol(o,'Seed',chosen);q.setcontrol(o,'Length Variation',.82)
        q.setcontrol(h,'Grapple Bias',0)
        rows=records(d);markers=records(h);required=[r for r in rows if r['span_class']==4]
        checks=[]
        for span in required:
            matches=[r for r in markers if r.get('grapple_required') and r.get('source_span')==span['section_id']]
            checks.append({'span':span['section_id'],'gap':span['span_distance'],'catch_length':span['catch_length'],'marker_count':len(matches),'distances':[r.get('anchor_distance_from_approach') for r in matches],'pass':bool(matches) and all(r['anchor_distance_from_approach']<=50 for r in matches)})
        report['required_seed']=chosen;report['required_helpers']=checks;report['helper_rows']=markers
        report['mesh_gap_measurements']=gap_measurements(out,rows)
        report['surface_containment']=q.containment(out,s)
        hh=q.host(s,1);q.setcontrol(hh,'Seed',chosen);q.setcontrol(hh,'Grapple Bias',0);report['helper_containment']=q.containment(hh,s)
        report['used_variant_ids']=sorted(set(x[1] for x in variants(out) if x[1]>=0));report['output']=q.snapshot(out)
        # A cutter surrounding the required candidate must downgrade the span,
        # not leave a mandatory marker that gets silently subtracted.
        span=required[0];mark=next(r for r in markers if r.get('source_span')==span['section_id'] and r.get('grapple_required'))
        px,py,pz=mark['position'];c=q.box('MarkerCutter',4,4,4,(px,py-2,pz-2))
        for ob in [d,h]:q.setcontrol(ob,'Cutter',c);q.setcontrol(ob,'Use Cutter',True)
        after=records(d);changed=next(r for r in after if r['section_id']==span['section_id'])
        report['cut_required_candidate']={'before_class':span['span_class'],'after_class':changed['span_class'],'after_gap':changed['span_distance'],'downgraded':changed['span_class']!=4}
    save('spans_rhythm',report);q.cleanup();return report


def stability(case):
    q.cleanup();s=q.box(length=90,width=16,height=12);out=q.host(s);d=q.host(s,2)
    before=q.snapshot(out,lambda p:p[1]<75);vb=variants(out,lambda p:p.y<75);rb=records(d)
    q.extrude(s,(0,1,0),(0,20,0))
    if case=='vertical':q.extrude(s,(0,0,1),(0,0,28),lambda p:p.y>90)
    elif case=='angled':q.extrude(s,(0,1,0),(16,24,0),angle=-33)
    elif case=='wide':q.extrude(s,(0,1,0),(0,26,0),scale=(2,1,1))
    after=q.snapshot(out,lambda p:p[1]<75);va=variants(out,lambda p:p.y<75);ra=[r for r in records(d) if r['position'][1]<89]
    result={'case':case,'old_geometry_hash_stable':before['hash']==after['hash'],'old_bounds_stable':before['bounds']==after['bounds'],'old_variant_choice_stable':vb==va,'old_sequence_stable':rb==ra,'old_before':before,'old_after':after,'variant_before':vb,'variant_after':va,'containment':q.containment(out,s)}
    save('stability_'+case,result);q.cleanup();return result


def authored_and_performance():
    q.cleanup();src=bpy.data.objects['LEVEL_PROXY'];mesh=src.data.copy()
    s=bpy.data.objects.new(q.PREFIX+'AuthoredCopy',mesh);q.collection().objects.link(s);out=q.host(s);h=q.host(s,1)
    result={'source':q.source_summary(s),'output':q.snapshot(out),'helpers':q.snapshot(h),'surface_containment':q.containment(out,s),'helper_containment':q.containment(h,s),'variants':variants(out)}
    timings={}
    for quality in [0,1]:
        q.setcontrol(out,'Preview Quality',quality);q.setcontrol(h,'Preview Quality',quality);runs=[]
        for i in range(6):
            s.data.vertices[0].co.z+=.0005*(1 if i%2==0 else -1);s.data.update();s.update_tag();t=time.perf_counter();bpy.context.view_layer.update()
            for o in [out,h]:e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();count=len(m.vertices);e.to_mesh_clear()
            runs.append((time.perf_counter()-t)*1000)
        timings[str(quality)]={'median_ms':statistics.median(runs),'max_ms':max(runs),'runs_ms':runs}
    result['timing']=timings;save('authored_performance',result);q.cleanup();return result


def vocabulary_and_controls():
    q.cleanup();manifest=json.loads((REPORT/'library_manifest.json').read_text());byid={r['id']:r for r in manifest};usage={f:set() for f in ['LANDING','PLATFORM','WALL','RAMP','BRIDGE','SPEED','VERTICAL']};scales=[];warnings=[]
    for length,width,height in [(360,24,16),(14,18,65)]:
        s=q.box(length=length,width=width,height=height);o=q.host(s,4)
        for name in ['Density','Ramp Presence','Slide Bias','Wallrun Bias','Route Complexity','Verticality']:q.setcontrol(o,name,1.)
        for seed in [17,42,73,5,8,23,109,2]:
            q.setcontrol(o,'Seed',seed)
            for _,variant,family in variants(o):
                if variant>=0:usage[byid[variant]['family']].add(variant)
            e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();a=m.attributes.get('variant_uniform_scale');ids=m.attributes.get('variant_id')
            if a and ids:
                for p in m.polygons:
                    if ids.data[p.index].value>=0:scales.extend(a.data[i].value for i in p.vertices)
            e.to_mesh_clear();warnings.extend(q.snapshot(o)['warnings'])
        q.cleanup()
    result={'library_count':len(manifest),'normalized_unique':len({r['normalized_geometry_hash'] for r in manifest}),'used_by_family':{k:sorted(v) for k,v in usage.items()},'used_variant_count':sum(len(v) for v in usage.values()),'scale_min':min(scales),'scale_max':max(scales),'scale_range_pass':min(scales)>=.649 and max(scales)<=1.351,'all_families_used':all(v for v in usage.values()),'warnings':warnings}
    # Numeric controls must have an effect; no decorative/dead controls.
    s=q.box(length=240,width=20,height=12);o=q.host(s);d=q.host(s,2)
    a=q.snapshot(o);q.setcontrol(o,'Seed',42);b=q.snapshot(o);q.setcontrol(o,'Seed',17);c=q.snapshot(o)
    result['seed_determinism']={'changes':a['hash']!=b['hash'],'returns':a['hash']==c['hash']}
    q.setcontrol(d,'Traversal Difficulty',0);low=records(d);q.setcontrol(d,'Traversal Difficulty',1);high=records(d)
    result['difficulty_changes_distances']=any(abs(a['span_distance']-b['span_distance'])>.1 for a,b in zip(low,high))
    q.setcontrol(o,'Density',0);low=q.snapshot(o);q.setcontrol(o,'Density',1);high=q.snapshot(o);result['density_changes_geometry']=low['hash']!=high['hash']
    # Native source controls and disconnected volume regression inherited from
    # V04; exercise the same public group object inputs, not a Python callback.
    before=q.snapshot(o);bm=bmesh.new();bm.from_mesh(s.data);q2=q.box('Island',length=20,width=14,height=18,origin=(40,0,-.7));bm.from_mesh(q2.data);bm.to_mesh(s.data);bm.free();s.data.update();s.update_tag();bpy.context.view_layer.update()
    old=q.snapshot(o,lambda p:p[0]<20);result['island_old_hash_stable']=before['hash']==old['hash'];result['island_containment']=q.containment(o,s)
    # Standard API Edit Mode extrusion remains live. No human hotkey test.
    for x in bpy.context.selected_objects:x.select_set(False)
    s.select_set(True);bpy.context.view_layer.objects.active=s;before=q.snapshot(o);bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(s.data);f=max(bm.faces,key=lambda f:f.calc_center_median().y)
    ret=bmesh.ops.extrude_face_region(bm,geom=[f]);v=[x for x in ret['geom'] if isinstance(x,bmesh.types.BMVert)];bmesh.ops.delete(bm,geom=[f],context='FACES_ONLY');bmesh.ops.translate(bm,verts=v,vec=(0,30,0));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.update_edit_mesh(s.data,loop_triangles=True,destructive=True);s.update_tag();bpy.context.view_layer.update();after=q.snapshot(o)
    result['api_edit_mode']={'mode':bpy.context.mode,'output_changed':before['hash']!=after['hash'],'human_test':False};bpy.ops.object.mode_set(mode='OBJECT')
    q.cleanup();save('vocabulary_controls',result);return result
