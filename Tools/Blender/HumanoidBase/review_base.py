"""Read-only source QA and static renders. Never saves posed bodies into source."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'Assets/Characters/BaseHumanoid';OUT=BASE/'Review'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Source/Humanoid_Base.blend'))
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'
sc.render.resolution_x=720;sc.render.resolution_y=960;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
sc.world.color=(.055,.065,.078)
sh=sc.display.shading;sh.light='STUDIO';sh.studiolight_rotate_z=.3
sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True
sh.cavity_type='BOTH';sh.curvature_ridge_factor=1.25;sh.curvature_valley_factor=1.0
sh.show_specular_highlight=True;sh.background_type='WORLD';sh.show_object_outline=False
sc.view_settings.view_transform='Standard'
data=bpy.data.cameras.new('QA_Camera');cam=bpy.data.objects.new('QA_Camera',data);sc.collection.objects.link(cam);sc.camera=cam
data.type='ORTHO';data.ortho_scale=2.10
def view(angle,target=(0,0,.92),scale=2.10):
    a=math.radians(angle);target=Vector(target)
    cam.location=target+Vector((math.sin(a)*5,-math.cos(a)*5,0.10 if angle%90 else 0))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
def render(name):
    sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
def reset(rig):
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def turn(rig,name,axis,degrees):
    # Rotation axes are specified in Blender model coordinates, then mapped to bone rest axes.
    pb=rig.pose.bones[name];local=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    pb.rotation_quaternion=Quaternion(local,math.radians(degrees))
def pose(rig,name):
    reset(rig)
    if name=='arms_forward':
        for s,sign in [('L',1),('R',-1)]:
            pb=rig.pose.bones['upper_arm.'+s]
            direction=pb.bone.tail_local-pb.bone.head_local
            q=direction.rotation_difference(Vector((sign*.06,-1,.02)))
            pb.rotation_quaternion=pb.bone.matrix_local.to_quaternion().inverted()@q@pb.bone.matrix_local.to_quaternion()
    elif name=='elbow_90':
        for s in ['L','R']:turn(rig,'forearm.'+s,(1,0,0),-90)
    elif name=='overhead':
        for s,sign in [('L',1),('R',-1)]:
            turn(rig,'clavicle.'+s,(0,1,0),-sign*12)
            turn(rig,'upper_arm.'+s,(0,1,0),-sign*128)
    elif name=='deep_crouch':
        turn(rig,'pelvis',(1,0,0),18)
        for s in ['L','R']:
            turn(rig,'thigh.'+s,(1,0,0),-112)
            turn(rig,'calf.'+s,(1,0,0),128)
            turn(rig,'foot.'+s,(1,0,0),-34)
        turn(rig,'spine_01',(1,0,0),12)
        for s in ['L','R']:turn(rig,'upper_arm.'+s,(1,0,0),-55)
    elif name=='knee_115':turn(rig,'calf.L',(1,0,0),115)
    elif name=='wide_step':
        turn(rig,'thigh.L',(1,0,0),-65);turn(rig,'thigh.R',(1,0,0),40)
        turn(rig,'calf.L',(1,0,0),40);turn(rig,'calf.R',(1,0,0),28)
        turn(rig,'foot.L',(1,0,0),-15);turn(rig,'foot.R',(1,0,0),-20)
    elif name=='neck_wrist_flex':
        turn(rig,'neck',(1,0,0),25)
        for s,sign in [('L',1),('R',-1)]:
            axis=(.77*sign,0,.64)
            turn(rig,'hand.'+s,axis,-35*sign)
            for finger in ['thumb','index','middle','ring','pinky']:
                for i,angle in [(1,20),(2,35),(3,25)]:
                    turn(rig,finger+'_'+str(i).zfill(2)+'.'+s,axis,-angle*sign)
    bpy.context.view_layer.update()
def mesh_stats(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    unseen=set(bm.verts);parts=[]
    while unseen:
        seed=unseen.pop();stack=[seed];num=0
        while stack:
            v=stack.pop();num+=1
            for e in v.link_edges:
                vv=e.other_vert(v)
                if vv in unseen:unseen.remove(vv);stack.append(vv)
        parts.append(num)
    st={'cage_vertices':len(bm.verts),'cage_faces':len(bm.faces),'cage_quads':sum(len(f.verts)==4 for f in bm.faces),
        'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'components':parts,
        'weight_sum_max_error':max(abs(sum(g.weight for g in v.groups)-1) for v in o.data.vertices),
        'unweighted_vertices':sum(not v.groups for v in o.data.vertices),'max_influences_cage':max(len(v.groups) for v in o.data.vertices)}
    bm.free();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
    st.update({'surface_vertices':len(m.vertices),'surface_faces':len(m.polygons),'triangles':len(m.loop_triangles),
        'height_m':max(v.co.z for v in m.vertices)-min(v.co.z for v in m.vertices),'ground_min_z':min(v.co.z for v in m.vertices)})
    ev.to_mesh_clear();return st

report={'standard':'BH_01','poses':{},'bodies':{}}
for kind in ['Male','Female']:
    rig=bpy.data.objects[kind+'_Rig'];obj=bpy.data.objects[kind+'_Body'];rig.location.x=0
    for other in ['Male','Female']:bpy.data.objects[other+'_Body'].hide_render=other!=kind
    reset(rig);report['bodies'][kind]=mesh_stats(obj)
    report['bodies'][kind]['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None} for b in rig.data.bones]
    if '--quick' in sys.argv:
        view(0);render(kind+'_quick');continue
    if '--supplement' in sys.argv:
        pose(rig,'neck_wrist_flex');view(-30);render(kind+'_test_neck_wrist_flex')
        points=[p for b in rig.pose.bones if b.name.endswith('.L') and b.name.startswith(('hand','thumb','index','middle','ring','pinky')) for p in [b.head,b.tail]]
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        view(-25,(low+high)/2,.30);render(kind+'_test_fingers_detail')
        reset(rig);continue
    for name,angle in [('front',0),('side',90),('back',180),('quarter',-35)]:view(angle);render(kind+'_'+name)
    hand_points=[p for b in rig.data.bones if b.name.endswith('.L') and (b.name.startswith(('hand','thumb','index','middle','ring','pinky'))) for p in [b.head_local,b.tail_local]]
    hand_min=Vector(tuple(min(p[i] for p in hand_points) for i in range(3)))
    hand_max=Vector(tuple(max(p[i] for p in hand_points) for i in range(3)))
    view(0,target=(hand_min+hand_max)/2,scale=.30);render(kind+'_hand_detail')
    for name in ['arms_forward','elbow_90','overhead','deep_crouch','knee_115','wide_step']:
        pose(rig,name)
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
        pts=[v.co.copy() for v in m.vertices];ev.to_mesh_clear()
        lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        report['poses'][kind+'_'+name]={'finite':all(math.isfinite(x) for p in pts for x in p),'bounds_min':list(lo),'bounds_max':list(hi)}
        angle=70 if name in ['elbow_90','deep_crouch','knee_115','wide_step'] else -25
        view(angle,(lo+hi)/2,max(hi.z-lo.z,hi.y-lo.y,hi.x-lo.x)*1.22)
        render(kind+'_test_'+name)
    reset(rig)
(OUT/('supplemental_qa.json' if '--supplement' in sys.argv else 'blender_qa.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HUMANOID_REVIEW_DONE',json.dumps({k:{n:v for n,v in st.items() if n!='bones'} for k,st in report['bodies'].items()}))
