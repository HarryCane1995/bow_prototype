"""Bounded V02 QA on disposable copies. Never edits production authoring meshes."""
import bpy,bmesh,json,time,hashlib,math,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
REPORT=Path(globals().get('REPORT_OVERRIDE',ROOT/'Docs/Reviews/GNLevelBlockoutV02'))
assert bpy.context.mode=='OBJECT'
real=bpy.data.objects['LEVEL_GENERATED_OUTPUT']
col=bpy.data.collections.new('TEST_V02_QA');bpy.context.scene.collection.children.link(col)
originals=[bpy.data.objects[n] for n in ('LEVEL_VOLUME','LEVEL_CUTTER')]
def digest(me):return hashlib.sha256(json.dumps({'v':[list(v.co) for v in me.vertices],'f':[list(p.vertices) for p in me.polygons]},sort_keys=True).encode()).hexdigest()
before={o.name:digest(o.data) for o in originals}
copies=[]
for o in originals:
    cp=o.copy();cp.data=o.data.copy();cp.name='TEST_'+o.name;col.objects.link(cp);copies.append(cp)
volume,cutter=copies
out=bpy.data.objects.new('TEST_V02_OUTPUT',bpy.data.meshes.new('TEST_V02_EMPTY'));col.objects.link(out);copies.append(out)
mod=out.modifiers.new('QA','NODES');mod.node_group=real.modifiers[0].node_group
for k in real.modifiers[0].keys():mod[k]=real.modifiers[0][k]
ids={s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
mod[ids['Volume Object']]=volume;mod[ids['Cutter Object']]=cutter
checks=[];samples={};updates=[]
def expect(ok,name,detail=None):checks.append({'check':name,'passed':bool(ok),'detail':detail})
def parameter(n,v):mod[ids[n]]=v;out.update_tag()
def observer(scene,dg):updates.extend(u.id.name for u in dg.updates if u.is_updated_geometry and u.id.name.startswith('TEST_'))
bpy.app.handlers.depsgraph_update_post.append(observer)
def capture(label,analyze=False):
    start=time.perf_counter();ev=out.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    vertices=[v.co.copy() for v in me.vertices];polys=[list(p.vertices) for p in me.polygons]
    bounds=[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)] if vertices else []
    bm=bmesh.new();bm.from_mesh(me);vol=bm.calc_volume();bm.free()
    r={'hash':digest(me),'vertices':len(vertices),'faces':len(polys),'bounds':bounds,'volume':vol,'evaluation_ms':(time.perf_counter()-start)*1000,'warnings':[w.message for w in ev.modifiers[0].node_warnings]}
    if analyze:
        attrs={n:me.attributes[n] for n in ('v02_role','v02_zone','v02_band','v02_part')}
        groups={};zlevels=set();zones=set();roles=collections.Counter();roofarea=0;max_horizontal_area=0
        vworld=[volume.matrix_world@v.co for v in volume.data.vertices];domain=[[min(v[i] for v in vworld),max(v[i] for v in vworld)] for i in range(3)]
        for p in me.polygons:
            role,zone,band,part=[attrs[n].data[p.index].value for n in attrs];roles[role]+=1
            coords=[vertices[i] for i in p.vertices];groups.setdefault((zone,band,part),[]).extend(coords)
            if role==2 and part==10 and abs(p.normal.z)>.99 and p.normal.z>0:zlevels.add(round(max(v.z for v in coords),3));zones.add(zone)
            if p.normal.z>.99:
                max_horizontal_area=max(max_horizontal_area,p.area)
                if all(abs(v.z-domain[2][1])<.01 for v in coords):roofarea+=p.area
        r.update(roles=dict(roles),platform_levels=sorted(zlevels),platform_zone_count=len(zones),domain=domain,top_boundary_cap_area=roofarea,max_horizontal_face_area=max_horizontal_area)
        r['inside_bounds']=all(bounds[i][0]>=domain[i][0]-.01 and bounds[i][1]<=domain[i][1]+.01 for i in range(3))
        bvh=BVHTree.FromPolygons(vertices,polys)
        radius=float(mod[ids['Spawn Safe Radius']]);rays=[]
        for x,y in [(0,0)]+[(radius*.93*math.cos(i*math.tau/12),radius*.93*math.sin(i*math.tau/12)) for i in range(12)]:
            hit=bvh.ray_cast(Vector((x,y,domain[2][1]+5)),Vector((0,0,-1)),domain[2][1]-domain[2][0]+20)[0]
            rays.append(None if hit is None else hit.z)
        r['spawn_z']=rays;r['spawn_safe']=all(z is not None and abs(z)<.02 for z in rays)
        dims=[];bad=[]
        def box(coords):return [[min(v[i] for v in coords),max(v[i] for v in coords)] for i in range(3)]
        boxes={k:box(c) for k,c in groups.items()}
        for (zone,band,part),b in boxes.items():
            extent=[v[1]-v[0] for v in b]
            if part==40:
                d=max(extent[:2]);dims.append({'kind':'wallrun_surface','m':d,'zone':zone});
                if d>44.319893*.9+.03:bad.append(['wallrun',d])
            if part==41 and (zone,band,42) in boxes:
                b2=boxes[(zone,band,42)];axis=min(range(2),key=lambda i:extent[i]);a,c=sorted([b,b2],key=lambda q:q[axis][0]);d=c[axis][0]-a[axis][1];dims.append({'kind':'wall_jump_spacing','m':d,'zone':zone})
                if not 0<d<=9.53*.9+.03:bad.append(['wall_jump_spacing',d])
            if part==10:
                d=min(extent[:2]);dims.append({'kind':'platform_short_side','m':d,'zone':zone,'band':band})
                if d<5.4:bad.append(['landing_width',d])
            if part==20:
                slope=extent[2]/max(max(extent[:2]),.01);dims.append({'kind':'ramp_slope','ratio':slope,'zone':zone,'band':band})
                if slope>.65:bad.append(['ramp_slope',slope])
            if part==60:
                center=Vector([(a+b)/2 for a,b in b]);center.z=b[2][1]
                lower=[(key,value) for key,value in groups.items() if key[0]==zone and key[2]==10 and max(v.z for v in value)<center.z-.5]
                if lower:
                    points=[v+Vector((0,0,1.6)) for key,value in lower for v in value if abs(v.z-max(p.z for p in value))<.01]
                    d=min((center-v).length for v in points);dims.append({'kind':'grapple_candidate_3D','m':d,'zone':zone})
                    if d>45:bad.append(['grapple_candidate_3D',d])
        r['dimensions']=dims;r['dimension_violations']=bad
    ev.to_mesh_clear();samples[label]=r;return r
def reset(obj,original):
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    m=obj.data;obj.data=original.data.copy();bpy.data.meshes.remove(m);obj.matrix_world=original.matrix_world.copy()
def edit(obj):
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.mode_set(mode='EDIT');return bmesh.from_edit_mesh(obj.data)
try:
    parameter('Use Cutter',False);seeds=[]
    for seed in (17,41,109):
        parameter('Seed',seed);r=capture('seed_'+str(seed),True);r['seed']=seed;seeds.append(r)
        expect(r['inside_bounds'],'seed_'+str(seed)+'_inside_XYZ')
        expect(r['spawn_safe'],'seed_'+str(seed)+'_spawn')
        expect(r['top_boundary_cap_area']<1 and r['max_horizontal_face_area']<220*176*.4,'seed_'+str(seed)+'_no_global_ceiling')
        expect(len(r['platform_levels'])>=2 and r['roles'].get(1,0)>0 and r['roles'].get(2,0)>0,'seed_'+str(seed)+'_walls_and_multiple_bands',r['platform_levels'])
        expect(not r['warnings'] and not r['dimension_violations'],'seed_'+str(seed)+'_metrics_and_modifier',r['dimension_violations'])
    expect(len({r['hash'] for r in seeds})==3,'different_seed_layouts')
    parameter('Seed',17);repeat=capture('seed_17_repeat');expect(repeat['hash']==seeds[0]['hash'],'deterministic_repeat')
    for axis in range(3):
        bm=edit(volume)
        for v in bm.verts:v.co[axis]*=(.75 if axis!=2 else 1.25)
        bmesh.update_edit_mesh(volume.data);r=capture('volume_edit_'+str(axis));expect(r['hash']!=repeat['hash'],'edit_volume_'+str(axis)+'_updates_output')
        reset(volume,originals[0])
    volume.scale.x=.85;volume.update_tag();r=capture('volume_object_scale');expect(r['hash']!=repeat['hash'],'object_volume_scale_updates');reset(volume,originals[0])
    for value in (.05,.5,.95):
        parameter('Verticality',value);r=capture('verticality_'+str(value),True)
    expect(len(samples['verticality_0.05']['platform_levels'])<len(samples['verticality_0.5']['platform_levels'])<=len(samples['verticality_0.95']['platform_levels']),'verticality_changes_number_of_levels')
    parameter('Verticality',.84)
    for val in (0,1):
        parameter('Traversal Difficulty',val);r=capture('difficulty_'+str(val),True);expect(not r['dimension_violations'],'difficulty_'+str(val)+'_metric_dimensions',r['dimension_violations'])
    parameter('Traversal Difficulty',.45)
    uncut=capture('uncut');parameter('Use Cutter',True);cut=capture('cut')
    expect(cut['hash']!=uncut['hash'] and abs(cut['volume']-uncut['volume'])>.1,'cutter_removes_geometry')
    bm=edit(cutter)
    for v in bm.verts:v.co.x*=2
    bmesh.update_edit_mesh(cutter.data);r=capture('cutter_edit_scale');expect(r['hash']!=cut['hash'],'cutter_edit_live');reset(cutter,originals[1])
    bm=edit(cutter);face=max(bm.faces,key=lambda f:f.normal.x);before_count=len(bm.verts)
    result=bmesh.ops.extrude_face_region(bm,geom=[face]);new=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,verts=new,vec=Vector((12,0,0)));bmesh.ops.delete(bm,geom=[face],context='FACES_ONLY');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.update_edit_mesh(cutter.data)
    r=capture('cutter_edit_extrude');expect(len(bm.verts)>before_count and r['hash']!=cut['hash'],'cutter_topology_live');reset(cutter,originals[1])
    # Two disconnected closed components in ONE cutter object, one at an upper band.
    bm=bmesh.new();bm.from_mesh(cutter.data)
    for center,scale in [((-110,-40,16),(18,22,12)),((-40,25,0),(24,20,12))]:
        verts=bmesh.ops.create_cube(bm,size=1)['verts'];bmesh.ops.scale(bm,verts=verts,vec=Vector(scale));bmesh.ops.translate(bm,verts=verts,vec=Vector(center))
    bm.to_mesh(cutter.data);bm.free();cutter.data.update();r=capture('cutter_disconnected_islands');expect(r['hash']!=cut['hash'],'multiple_cutter_islands');reset(cutter,originals[1])
    # Large origin-covering box must still leave the protected floor and clear sky.
    bm=bmesh.new();verts=bmesh.ops.create_cube(bm,size=1)['verts'];bmesh.ops.scale(bm,verts=verts,vec=Vector((100,100,100)));bm.to_mesh(cutter.data);bm.free();cutter.location=(0,0,0);cutter.data.update();r=capture('cutter_over_spawn',True);expect(r['spawn_safe'],'cutter_cannot_remove_spawn');reset(cutter,originals[1])
    cutter.data.clear_geometry();cutter.data.update();r=capture('cutter_empty');expect(r['hash']==uncut['hash'],'empty_cutter_harmless');reset(cutter,originals[1])
    parameter('Use Cutter',True)
    times=[]
    for seed in (18,42,110):parameter('Seed',seed);times.append(capture('timing_'+str(seed))['evaluation_ms'])
    expect(all(digest(o.data)==before[o.name] for o in originals),'manual_authoring_meshes_unchanged')
    expect(any('VOLUME' in n for n in updates) and any('CUTTER' in n for n in updates) and 'TEST_V02_OUTPUT' in updates,'depsgraph_updates_inputs_and_output')
    result={'passed':all(c['passed'] for c in checks),'checks':checks,'seeds':seeds,'samples':samples,'performance_ms':{'min':min(times),'max':max(times),'mean':sum(times)/len(times)},'depsgraph_ids':sorted(set(updates))}
    (REPORT/'technical_qa.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'failures':[c for c in checks if not c['passed']],'performance_ms':result['performance_ms'],'seed_summary':[{'seed':r['seed'],'v':r['vertices'],'f':r['faces'],'levels':r['platform_levels'],'bounds':r['bounds']} for r in seeds]}))
finally:
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.app.handlers.depsgraph_update_post.remove(observer)
    for o in copies:
        me=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
    bpy.data.collections.remove(col)
    for o in bpy.context.selected_objects:o.select_set(False)
    originals[0].select_set(True);bpy.context.view_layer.objects.active=originals[0]
