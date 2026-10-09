"""Disposable bmesh regressions; never writes to LEVEL_PROXY or its source mesh."""
import bpy
import bmesh
import hashlib
import importlib.util
import json
import math
import statistics
import time
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV04'
GROUP='GN_LevelProxyGenerator_v04';PREFIX='TEST_LPV04_'


def collection():
    c=bpy.data.collections.get(PREFIX+'QA')
    if not c:c=bpy.data.collections.new(PREFIX+'QA');bpy.context.scene.collection.children.link(c)
    c.hide_viewport=False;c.hide_render=True
    return c


def box(name='Source',width=12,length=24,height=12,origin=(0,0,-.7)):
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:v.co=Vector((v.co.x*width,(v.co.y+.5)*length,(v.co.z+.5)*height))+Vector(origin)
    mesh=bpy.data.meshes.new(PREFIX+name+'_Mesh');bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(PREFIX+name,mesh);collection().objects.link(obj);obj.display_type='WIRE';obj.hide_render=True
    return obj


def host(source,mode=0):
    obj=bpy.data.objects.new(PREFIX+'Output',bpy.data.meshes.new(PREFIX+'Host'));collection().objects.link(obj)
    obj.parent=source;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
    m=obj.modifiers.new('QA live dependency','NODES');m.node_group=bpy.data.node_groups[GROUP]
    ids={s.name:s.identifier for s in m.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    for s in m.node_group.interface.items_tree:
        if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type not in ['NodeSocketObject','NodeSocketGeometry']:m[s.identifier]=s.default_value
    m[ids['Proxy']]=source;m[ids['Output Mode']]=mode
    return obj


def setcontrol(obj,name,value):
    m=obj.modifiers[0];ids={s.name:s.identifier for s in m.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    m[ids[name]]=value;obj.update_tag();bpy.context.view_layer.update()


def source_summary(source):
    bm=bmesh.new();bm.from_mesh(source.data)
    result={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'volume':bm.calc_volume(signed=True)};bm.free()
    result['hash']=hashlib.sha256(repr(([tuple(v.co) for v in source.data.vertices],[tuple(p.vertices) for p in source.data.polygons])).encode()).hexdigest()
    return result


def extrude(source,normal,delta,face_filter=None,scale=(1,1,1),angle=0):
    bm=bmesh.new();bm.from_mesh(source.data);bm.normal_update()
    faces=[f for f in bm.faces if f.normal.dot(Vector(normal))>.8 and (not face_filter or face_filter(f.calc_center_median()))]
    assert faces,'No QA cap matched'
    face=max(faces,key=lambda f:f.calc_center_median().dot(Vector(normal)))
    result=bmesh.ops.extrude_face_region(bm,geom=[face],use_keep_orig=False)
    newverts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY')
    center=sum((v.co for v in newverts),Vector())/len(newverts)
    rot=Matrix.Rotation(math.radians(angle),4,'Z')
    for v in newverts:
        p=v.co-center;p=Vector((p.x*scale[0],p.y*scale[1],p.z*scale[2]));v.co=center+rot@p+Vector(delta)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag()
    bpy.context.view_layer.update()
    assert source_summary(source)['nonmanifold']==0


def snapshot(obj,region=None):
    bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    coords=[tuple(round(c,5) for c in v.co) for v in mesh.vertices]
    take=[i for i,c in enumerate(coords) if region is None or region(c)]
    selected=set(take)
    faces=[tuple(sorted(coords[i] for i in p.vertices)) for p in mesh.polygons if all(i in selected for i in p.vertices)]
    roles=mesh.attributes.get('surface_role');rolecounts={}
    if roles:
        for p in mesh.polygons:
            if all(i in selected for i in p.vertices):
                key=str(roles.data[p.index].value);rolecounts[key]=rolecounts.get(key,0)+1
    dims={}
    for name in ['lp_width','lp_length','lp_beat','lp_height']:
        attr=mesh.attributes.get(name)
        if attr and attr.domain=='POINT':dims[name]=sorted(set(round(attr.data[i].value,4) for i in take))
    result={'vertices':len(take),'faces':len(faces),'hash':hashlib.sha256(repr(sorted(faces)).encode()).hexdigest(),'vertex_hash':hashlib.sha256(repr(sorted(coords[i] for i in take)).encode()).hexdigest(),
            'bounds':[[min((coords[j][i] for j in take),default=0),max((coords[j][i] for j in take),default=0)] for i in range(3)],'dimensions':dims,'roles':rolecounts}
    result['warnings']=[str(w) for w in obj.modifiers[0].node_warnings] if hasattr(obj.modifiers[0],'node_warnings') else []
    ev.to_mesh_clear();return result


def containment(obj,source):
    # Check actual closed volume, not its AABB. Sample every vertex and triangle
    # interior, and independently compute Exact(output minus cleaned proxy).
    cleanhost=host(source,3);bpy.context.view_layer.update()
    ce=cleanhost.evaluated_get(bpy.context.evaluated_depsgraph_get());cm=ce.to_mesh();bm=bmesh.new();bm.from_mesh(cm);bm.normal_update();bvh=BVHTree.FromBMesh(bm,epsilon=1e-7)
    cm.calc_loop_triangles()
    triangles=[[tuple(cm.vertices[i].co) for i in t.vertices] for t in cm.loop_triangles]
    cleanmesh=bpy.data.meshes.new_from_object(ce);ce.to_mesh_clear()
    envelope=bpy.data.objects.new(PREFIX+'Envelope',cleanmesh);collection().objects.link(envelope)
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    samples=[v.co.copy() for v in mesh.vertices]
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        samples += [(a+b+c)/3,a*.6+b*.2+c*.2,a*.2+b*.6+c*.2,a*.2+b*.2+c*.6]
    def inside(p):
        hit=bvh.find_nearest(p)
        if hit[0] is not None and hit[3]<.0003:return True
        # Double-precision generalized winding number. BVH ray parity is
        # unsuitable here: float ray hits can re-hit the same polygon.
        angle=0.
        for tri in triangles:
            a,b,c=[[v[i]-float(p[i]) for i in range(3)] for v in tri]
            la,lb,lc=[math.sqrt(sum(t*t for t in v)) for v in [a,b,c]]
            dot=lambda u,v:sum(u[i]*v[i] for i in range(3))
            det=a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
            den=la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb
            angle+=2*math.atan2(det,den)
        return abs(angle)>2*math.pi
    outside=[list(p) for p in samples if not inside(p)]
    tempmesh=bpy.data.meshes.new_from_object(ev);ev.to_mesh_clear()
    temp=bpy.data.objects.new(PREFIX+'Difference',tempmesh);collection().objects.link(temp)
    mod=temp.modifiers.new('Independent Exact containment check','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=envelope;mod.use_self=True;mod.use_hole_tolerant=True
    bpy.context.view_layer.update();ee=temp.evaluated_get(bpy.context.evaluated_depsgraph_get());mm=ee.to_mesh();diff=bmesh.new();diff.from_mesh(mm)
    volume=abs(diff.calc_volume(signed=True));area=sum(f.calc_area() for f in diff.faces)
    residual_outside=sum(not inside(v.co) for v in mm.vertices)
    result={'method':'double precision winding + Exact Difference','tolerance_m':.0003,'samples':len(samples),'outside_samples':len(outside),'first_outside':outside[:3],'exact_difference_vertices':len(mm.vertices),'exact_difference_faces':len(mm.polygons),'exact_difference_volume':volume,'exact_difference_area':area,'difference_exterior_vertices':residual_outside,'pass':not outside and volume<1e-5 and residual_outside==0}
    diff.free();ee.to_mesh_clear();bm.free()
    for o in [cleanhost,envelope,temp]:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if data.users==0:bpy.data.meshes.remove(data)
    return result


def cleanup():
    c=bpy.data.collections.get(PREFIX+'QA')
    if c:
        for o in list(c.objects):
            data=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if data and data.users==0:bpy.data.meshes.remove(data)
        bpy.data.collections.remove(c)


def regression(kind):
    cleanup();source=box();out=host(source);helpers=host(source,1)
    before_topology=source_summary(source);before=snapshot(out);old=snapshot(out,lambda p:p[1]<20)
    extrude(source,(0,1,0),(0,16,0))
    horizontal=snapshot(out);horizontal_old=snapshot(out,lambda p:p[1]<20)
    middle=snapshot(out)
    if kind=='vertical':extrude(source,(0,0,1),(0,0,26),lambda p:p.y>24)
    elif kind=='angled':extrude(source,(0,1,0),(12,20,0),angle=-32)
    elif kind=='wide':extrude(source,(0,1,0),(0,18,0),scale=(2.5,1,1))
    else:raise ValueError(kind)
    after=snapshot(out);old_after=snapshot(out,lambda p:p[1]<20)
    new=snapshot(out,lambda p:p[2]>12) if kind=='vertical' else snapshot(out,lambda p:p[1]>40.01)
    result={'case':kind,'before_topology':before_topology,'after_topology':source_summary(source),'before':before,'after_horizontal':horizontal,'before_last_extension':middle,'after':after,'old_before':old,'old_after_horizontal':horizontal_old,'old_after':old_after,'new_region':new,
            'horizontal_added_geometry':horizontal['hash']!=before['hash'],'old_faces_stable':old['hash']==old_after['hash'],'old_vertices_stable':old['vertex_hash']==old_after['vertex_hash'],'old_bounds_stable':old['bounds']==old_after['bounds'],'old_dims_stable':old['dimensions']==old_after['dimensions'],'new_region_nonempty':new['faces']>0,
            'surface_containment':containment(out,source),'helper_containment':containment(helpers,source)}
    (REPORT/('regression_'+kind+'.json')).write_text(json.dumps(result,indent=2))
    cleanup();return {k:v for k,v in result.items() if k in ['case','horizontal_added_geometry','old_faces_stable','old_vertices_stable','old_bounds_stable','old_dims_stable','new_region_nonempty','surface_containment','helper_containment']}


def standard_operations():
    cleanup();results={};source=box();out=host(source);helpers=host(source,1)
    base=snapshot(out);source_before=source_summary(source)
    setcontrol(out,'Seed',42);changed=snapshot(out);setcontrol(out,'Seed',17);again=snapshot(out)
    results['seed']={'changes':base['hash']!=changed['hash'],'deterministic_return':base['hash']==again['hash'],'source_unchanged':source_before==source_summary(source)}
    setcontrol(helpers,'Grapple Bias',0);none=snapshot(helpers);setcontrol(helpers,'Grapple Bias',1);many=snapshot(helpers)
    results['grapple_bias']={'zero_faces':none['faces'],'full_faces':many['faces'],'pass':none['faces']==0 and many['faces']>0}
    setcontrol(out,'Ramp Presence',1);setcontrol(out,'Density',1)
    ramp_results={}
    for angle in [45,55,70]:
        setcontrol(out,'Ramp Steepness',angle);s=snapshot(out)
        ev=out.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();roles=mesh.attributes.get('surface_role');slopes=[]
        for p in mesh.polygons:
            if roles and roles.data[p.index].value==3 and .05<p.normal.z<.99:slopes.append(round(math.degrees(math.acos(p.normal.z)),3))
        ev.to_mesh_clear();ramp_results[str(angle)]={'faces':s['roles'].get('3',0),'measured_slopes_deg':sorted(set(slopes)),'matches':any(abs(a-angle)<.02 for a in slopes)}
    results['ramp_angles']=ramp_results
    # Cutter entirely local to the QA source, never the production cutter.
    cutter=box('Cutter',width=30,length=10,height=35,origin=(0,5,-5));setcontrol(out,'Cutter',cutter)
    before_cut=snapshot(out);setcontrol(out,'Use Cutter',True);after_cut=snapshot(out)
    results['cutter']={'changes':before_cut['hash']!=after_cut['hash'],'before':before_cut['faces'],'after':after_cut['faces'],'containment':containment(out,source)}
    setcontrol(out,'Use Cutter',False)
    # Mesh-domain rotation + scale, not object bounding-box scaling.
    before=snapshot(out);bm=bmesh.new();bm.from_mesh(source.data)
    transform=Matrix.Rotation(math.radians(31),4,'Z')@Matrix.Diagonal((1.2,1.1,1.,1.))
    for v in bm.verts:v.co=transform@v.co
    bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag();bpy.context.view_layer.update();after=snapshot(out)
    results['mesh_scale_rotation']={'changes':before['hash']!=after['hash'],'containment':containment(out,source)}
    # Ordinary object transforms keep local fill identical and carry both hosts.
    before=snapshot(out);source.location=(7,13,2);source.rotation_euler.z=math.radians(27);source.scale=(1.1,.9,1.2);source.update_tag();bpy.context.view_layer.update();after=snapshot(out)
    results['object_transforms']={'local_hash_unchanged':before['hash']==after['hash'],'output_matrix_matches':all(abs(out.matrix_world[i][j]-source.matrix_world[i][j])<1e-5 for i in range(4) for j in range(4))}
    cleanup();source=box();out=host(source)
    before=snapshot(out);island=box('Island',width=16,length=18,height=22,origin=(35,5,-.7))
    bm=bmesh.new();bm.from_mesh(source.data);bm.from_mesh(island.data);bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag();bpy.context.view_layer.update()
    islands=snapshot(out);old=snapshot(out,lambda p:p[0]<10);new=snapshot(out,lambda p:p[0]>20)
    results['islands']={'added_faces':new['faces'],'old_hash_unchanged':before['hash']==old['hash'],'containment':containment(out,source)}
    bm=bmesh.new();bm.from_mesh(source.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.x>20],context='VERTS');bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag();bpy.context.view_layer.update()
    removed=snapshot(out);results['delete_island']={'returns_to_original':before['hash']==removed['hash'],'source_faces':len(source.data.polygons)}
    # Face deletion leaves an open volume: fail closed rather than emit leakage.
    saved=source.data.copy();bm=bmesh.new();bm.from_mesh(source.data);bmesh.ops.delete(bm,geom=[max(bm.faces,key=lambda f:f.calc_center_median().z)],context='FACES_ONLY');bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag();bpy.context.view_layer.update()
    opened=snapshot(out);results['open_volume_guard']={'output_faces':opened['faces'],'pass':opened['faces']==0}
    olddata=source.data;source.data=saved
    if olddata.users==0:bpy.data.meshes.remove(olddata)
    # Standard topology operators on disposable meshes.
    for op in ['subdivide','inset','bevel','vertex_move']:
        backup=source.data.copy();before=snapshot(out);topobefore=source_summary(source);bm=bmesh.new();bm.from_mesh(source.data)
        if op=='subdivide':bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
        elif op=='inset':
            face=min(bm.faces,key=lambda f:f.calc_center_median().z);bmesh.ops.inset_region(bm,faces=[face],thickness=1,depth=0,use_boundary=True,use_even_offset=True)
        elif op=='bevel':bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.35,segments=1,affect='EDGES')
        elif op=='vertex_move':
            for v in bm.verts:
                if v.co.y>23:v.co.x+=2
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(source.data);bm.free();source.data.update();source.update_tag();bpy.context.view_layer.update();after=snapshot(out)
        results[op]={'input_changed':topobefore['hash']!=source_summary(source)['hash'],'output_changed':before['hash']!=after['hash'],'nonempty':after['faces']>0,'warnings':after['warnings'],'containment':containment(out,source)}
        olddata=source.data;source.data=backup
        if olddata.users==0:bpy.data.meshes.remove(olddata)
        bpy.context.view_layer.update()
    # API Edit Mode depsgraph evidence; this is NOT a human/UI smoke test.
    for o in bpy.context.selected_objects:o.select_set(False)
    source.select_set(True);bpy.context.view_layer.objects.active=source
    before=snapshot(out);bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(source.data)
    face=max(bm.faces,key=lambda f:f.calc_center_median().y)
    res=bmesh.ops.extrude_face_region(bm,geom=[face]);verts=[v for v in res['geom'] if isinstance(v,bmesh.types.BMVert)];bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY');bmesh.ops.translate(bm,verts=verts,vec=(0,14,0));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.update_edit_mesh(source.data,loop_triangles=True,destructive=True);source.update_tag();bpy.context.view_layer.update()
    after=snapshot(out);results['api_edit_mode']={'mode_when_measured':bpy.context.mode,'bmesh_faces':len(bm.faces),'output_changed_while_editing':before['hash']!=after['hash'],'before_faces':before['faces'],'after_faces':after['faces'],'human_test':False}
    bpy.ops.object.mode_set(mode='OBJECT');cleanup()
    (REPORT/'standard_operations.json').write_text(json.dumps(results,indent=2));return results


def vertical_and_performance():
    cleanup();s=box(height=48,length=12);out=host(s);helpers=host(s,1);results={}
    low=snapshot(out)
    for param in ['Verticality','Platform Density']:
        setcontrol(out,param,0);a=snapshot(out);setcontrol(out,param,1);b=snapshot(out)
        results[param]={'changes':a['hash']!=b['hash'],'low_faces':a['faces'],'high_faces':b['faces'],'low_platform_faces':a['roles'].get('2',0),'high_platform_faces':b['roles'].get('2',0)}
        setcontrol(out,param,.65 if param=='Platform Density' else .72)
    before=snapshot(out,lambda p:p[2]<42);extrude(s,(0,0,1),(0,0,22));after=snapshot(out,lambda p:p[2]<42)
    results['shaft_extension']={'old_hash_stable':before['hash']==after['hash'],'new_top':snapshot(out,lambda p:p[2]>48),'containment':containment(out,s),'helper_containment':containment(helpers,s)}
    cleanup()
    # Copy authored mesh for timings. Include a real dependency dirty/update in
    # each timing; cached evaluated_get is not an evaluation measurement.
    s=bpy.data.objects.new(PREFIX+'TimingSource',bpy.data.objects['LEVEL_PROXY'].data.copy());collection().objects.link(s)
    out=host(s);helpers=host(s,1)
    times={}
    for quality in [0,1]:
        setcontrol(out,'Preview Quality',quality);setcontrol(helpers,'Preview Quality',quality)
        runs=[]
        for i in range(8):
            z=s.data.vertices[0].co.z;s.data.vertices[0].co.z=z+.0005*(1 if i%2==0 else -1);s.data.update();s.update_tag()
            t=time.perf_counter();bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
            for o in [out,helpers]:
                e=o.evaluated_get(dg);m=e.to_mesh();count=len(m.vertices);e.to_mesh_clear()
            runs.append((time.perf_counter()-t)*1000)
        times['manifold' if quality==0 else 'exact']={'runs_ms':[round(t,3) for t in runs],'median_ms':round(statistics.median(runs),3),'max_ms':round(max(runs),3),'includes':'one dirty proxy edit + two outputs, main-thread depsgraph update'}
    results['performance']=times;results['warnings']=snapshot(out)['warnings']
    cleanup();(REPORT/'vertical_performance.json').write_text(json.dumps(results,indent=2));return results


def local_frames_and_controls():
    cleanup();results={};s=box();o=host(s)
    extrude(s,(0,1,0),(0,16,0));extrude(s,(0,1,0),(12,20,0),angle=-32)
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();directions=[]
    for v in m.vertices:
        if v.co.y>42 and m.attributes['lp_kind'].data[v.index].value<.5:directions.append(m.attributes['lp_forward'].data[v.index].vector.copy())
    expected=Vector((12,20,0)).normalized();valid_dirs=[v for v in directions if v.length>.5];dots=[abs(v.normalized().dot(expected)) for v in valid_dirs]
    results['angled_local_axis']={'expected':list(expected),'directions':sorted(set(tuple(round(c,5) for c in v) for v in valid_dirs)),'boolean_cap_vertices_without_frame':len(directions)-len(valid_dirs),'min_alignment_dot':min(dots,default=0),'pass':bool(dots) and min(dots)>.99};ev.to_mesh_clear();cleanup()
    s=box();o=host(s);extrude(s,(0,1,0),(0,18,-10))
    results['inclined_descent']={'geometry':snapshot(o,lambda p:p[1]>25),'containment':containment(o,s)};cleanup()
    # Merge and dissolve alter only disposable topology. A closed prism stays
    # valid; face-based local interpretation is allowed to change in this patch.
    s=box();o=host(s)
    bm=bmesh.new();bm.from_mesh(s.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True);bm.to_mesh(s.data);bm.free();s.data.update();bpy.context.view_layer.update();before=snapshot(o);tb=source_summary(s)
    bm=bmesh.new();bm.from_mesh(s.data);bm.normal_update();bmesh.ops.dissolve_limit(bm,angle_limit=.001,verts=list(bm.verts),edges=list(bm.edges),delimit=set());bm.to_mesh(s.data);bm.free();s.data.update();s.update_tag();bpy.context.view_layer.update()
    results['dissolve']={'input_changed':tb['hash']!=source_summary(s)['hash'],'output_changed':before['hash']!=snapshot(o)['hash'],'closed':source_summary(s)['nonmanifold']==0,'containment':containment(o,s)}
    extrude(s,(0,1,0),(0,0,0));merge_before=source_summary(s)
    bm=bmesh.new();bm.from_mesh(s.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.to_mesh(s.data);bm.free();s.data.update();s.update_tag();bpy.context.view_layer.update();merge_after=source_summary(s)
    results['merge_by_distance']={'closed':merge_after['nonmanifold']==0,'vertices_before':merge_before['vertices'],'vertices_after':merge_after['vertices'],'topology_changed':merge_before['hash']!=merge_after['hash'],'nonempty':snapshot(o)['faces']>0}
    # Source custom-property -> native SUM driver -> GN dependency.
    spec=importlib.util.spec_from_file_location('lpbuild',HERE/'build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
    o.modifiers.clear()
    for name,kind,value,low,high,desc in build.module.CONTROLS:s[name]=value
    build.bind(o,s,bpy.data.node_groups[GROUP],0,drivers=True);s.update_tag();bpy.context.view_layer.update();a=snapshot(o)
    s['Seed']=94;s.update_tag();bpy.context.view_layer.update();b=snapshot(o)
    s['Seed']=17;s.update_tag();bpy.context.view_layer.update();c=snapshot(o)
    results['source_controls_driver']={'changes':a['hash']!=b['hash'],'deterministic_return':a['hash']==c['hash'],'driver_count':len(o.animation_data.drivers),'all_drivers_valid':all(fc.driver.is_valid for fc in o.animation_data.drivers)}
    cleanup();(REPORT/'local_frames_controls.json').write_text(json.dumps(results,indent=2));return results


if __name__=='__main__':print(json.dumps(regression('vertical')))
