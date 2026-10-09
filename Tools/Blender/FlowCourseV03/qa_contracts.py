"""Additional geometry contracts and real saved-chunk roundtrip; disposable data only."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from common import *
obj,mod,ids=context();saved={k:mod[v] for k,v in ids.items()};checks={};fixtures=[]
try:
    set_controls(**{'Seed':17,'Layout Mode':0,'Use Cutter':False,'Section Preview':0})
    m=evaluated();base=summary()
    def bvh(mesh):
        return BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons if value(mesh,'flow_role',p.index)!=99])
    tree=bvh(m);loc,normal,face,dist=tree.ray_cast(Vector((0,0,100)),Vector((0,0,-1)),200)
    checks['spawn_clear_sky_floor_zero']=loc is not None and abs(loc.z)<.001
    checks['default_bbox_within_manual_volume']=all(a>=lo and b<=hi for (a,b),(lo,hi) in zip(base['bounds'],[[-110,110],[-88,88],[-8,42]]))
    # Confirm geometric surface normals rather than trusting the angle attribute.
    slopes=[]
    for angle in [35,45,70]:
        set_controls(**{'Steep Angle':angle});m2=evaluated()
        found=[math.degrees(math.acos(max(-1,min(1,p.normal.z)))) for p in m2.polygons if value(m2,'flow_section',p.index)==7 and value(m2,'flow_role',p.index)==2 and .01<p.normal.z<.999]
        slopes.append({'requested':angle,'measured':found});checks['actual_slope_%d'%angle]=bool(found) and all(abs(v-angle)<.05 for v in found)
        bpy.data.meshes.remove(m2)
    set_controls(**{'Steep Angle':45})
    temp=bpy.data.objects.new('TEST_V03_SPAWN_CUT',bpy.data.meshes.new('TEST_V03_SPAWN_CUT'));bpy.context.scene.collection.objects.link(temp);fixtures.append(temp)
    import bmesh
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=24);bm.to_mesh(temp.data);bm.free();temp.hide_set(True)
    set_controls(**{'Cutter Object':temp,'Use Cutter':True})
    cut=summary();m2=evaluated();hit=bvh(m2).ray_cast(Vector((0,0,100)),Vector((0,0,-1)),200)[0]
    checks['spawn_survives_covering_cutter']=hit is not None and abs(hit.z)<.001
    checks['covering_cutter_changes_route']=cut['hash']!=base['hash'];bpy.data.meshes.remove(m2)
    set_controls(**{'Preview Quality':1});exact=summary();checks['exact_cutter_nonempty']=exact['polygons']>0
    bpy.data.meshes.remove(m)
    # Load actual saved scenes, inspect entry/exit and mesh, then remove only new data-blocks.
    roundtrips=[]
    for path in json.loads((REPORT/'saved_chunks.json').read_text()):
        prior={name:set(getattr(bpy.data,name)) for name in ['scenes','objects','meshes','materials']}
        with bpy.data.libraries.load(path,link=False) as (source,target):target.scenes=list(source.scenes)
        scene=target.scenes[0];piece=next(o for o in scene.objects if o.type=='MESH')
        names=[o.name.split('.')[0] for o in scene.objects]
        item={'file':path,'vertices':len(piece.data.vertices),'faces':len(piece.data.polygons),'section':piece['flow_section'],'entry_marker':any(n=='ENTRY' for n in names),'exit_marker':any(n=='EXIT' for n in names)}
        roundtrips.append(item)
        for collection in ['objects','scenes','meshes','materials']:
            data=getattr(bpy.data,collection)
            for item_data in list(set(data)-prior[collection]):data.remove(item_data,do_unlink=True)
    checks['two_saved_chunks_reloaded']=len(roundtrips)==2 and all(r['vertices']>0 and r['faces']>0 and r['entry_marker'] and r['exit_marker'] for r in roundtrips)
    result={'checks':checks,'slopes':slopes,'chunk_roundtrips':roundtrips}
finally:
    set_controls(**saved)
    for o in fixtures:
        mesh=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(mesh)
(REPORT/'geometry_contracts.json').write_text(json.dumps(result,indent=2))
print('V03_CONTRACTS',checks)
