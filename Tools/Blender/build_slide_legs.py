"""Small editable slide-only FPS blocking. Run in a separate background Blender.

Creates FP_Slide_Legs.blend only. Godot owns visibility and intent yaw; no rig,
physics, cameras or gameplay collision are exported from this source.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Assets/Models/Player/FP_Slide_Legs.blend'
if OUT.exists() and '--rebuild' not in sys.argv:
    raise RuntimeError('Source exists; edit it in Blender or explicitly use -- --rebuild.')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.name = 'FP_Slide_Legs'

def bv(p): return Vector((p[0], -p[2], p[1]))
def material(name, color, metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Roughness'].default_value=.82;b.inputs['Metallic'].default_value=metal
    return m
cloth=material('Legs_Cloth',(.065,.084,.092))
plate=material('Legs_Plates',(.23,.28,.30),.2)
panel=material('Legs_DarkPanels',(.10,.135,.15),.2)
rubber=material('Legs_Joints',(.035,.045,.050))
trim=material('Legs_RedTrim',(.24,.065,.04),.15)
cyan=material('Legs_Cyan',(.06,.42,.46),.15)

def mesh(name, verts, faces, mat):
    data=bpy.data.meshes.new(name);data.from_pydata([bv(p) for p in verts],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj);data.materials.append(mat)
    return obj

def segment(name,a,b,ra,rb,mat,depth=.85):
    a=Vector(a);b=Vector(b);axis=(b-a).normalized()
    ref=Vector((0,1,0)) if abs(axis.y)<.9 else Vector((1,0,0))
    u=axis.cross(ref).normalized();v=axis.cross(u).normalized();verts=[];faces=[]
    for t,r in [(0,ra*.85),(.12,ra),(.83,rb),(1,rb*.82)]:
        for i in range(8):
            theta=(i+.5)*math.tau/8
            verts.append(a.lerp(b,t)+u*math.cos(theta)*r+v*math.sin(theta)*r*depth)
    faces.append(tuple(reversed(range(8))))
    for j in range(3):
        for i in range(8):faces.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
    faces.append(tuple(range(24,32)))
    return mesh(name,verts,faces,mat)

def box(name,center,size,mat,bevel=.015,rotation=None):
    c=Vector(center);s=Vector(size)*.5
    rotation=rotation if rotation is not None else Matrix.Identity(3)
    verts=[c+rotation@Vector((x*s.x,y*s.y,z*s.z)) for z in [-1,1] for y in [-1,1] for x in [-1,1]]
    faces=[(2,3,1,0),(5,7,6,4),(1,5,4,0),(6,7,3,2),(4,6,2,0),(3,7,5,1)]
    obj=mesh(name,verts,faces,mat)
    # Only this newly-created blocking mesh is modified.
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    mod=obj.modifiers.new('Blocking chamfer','BEVEL');mod.width=bevel;mod.segments=1
    bpy.ops.object.modifier_apply(modifier=mod.name);obj.select_set(False)
    return obj

# Fixed Sojourn-inspired seated silhouette: a long leading left leg and a
# folded right leg. These proportions are composed for the CyberBow camera.
# All parts keep this relationship while Godot rotates the whole pose.
poses=[
    ('L',(-.22,-.12,.58),(-.35,-.025,.035),(-.48,-.08,-.62)),
    ('R',(.16,-.07,.63),(.85,.20,.00),(.78,-.04,.43)),
]
hips=[]
for side,h,k,a in poses:
    hip,knee,ankle=Vector(h),Vector(k),Vector(a);hips.append(hip)
    segment('Thigh_'+side,hip,knee,.15,.115,cloth)
    segment('ThighPlate_'+side,hip.lerp(knee,.18)+Vector((0,.045,0)),hip.lerp(knee,.74)+Vector((0,.045,0)),.123,.10,panel,.45)
    box('KneeJoint_'+side,knee,(.22,.16,.19),rubber)
    box('KneePlate_'+side,knee+Vector((0,.065,-.035)),(.22,.09,.21),plate,
        rotation=Matrix.Rotation(math.radians(30 if side=='R' else 0),3,'X'))
    segment('Shin_'+side,knee,ankle,.10,.072,cloth)
    segment('ShinPlate_'+side,knee.lerp(ankle,.19)+Vector((0,.045,0)),knee.lerp(ankle,.83)+Vector((0,.045,0)),.089,.071,panel,.5)
    segment('AnkleCuff_'+side,knee.lerp(ankle,.82),ankle,.085,.087,trim)
    foot=(Matrix.Rotation(math.radians(50 if side=='R' else -6),3,'Y')
          @Matrix.Rotation(math.radians(10 if side=='R' else 48),3,'X'))
    box('Boot_'+side,ankle+foot@Vector((0,-.055,-.09)),(.225,.18,.34),cloth,.025,foot)
    box('BootToe_'+side,ankle+foot@Vector((0,-.015,-.19)),(.22,.10,.16),plate,.018,foot)
    box('BootSole_'+side,ankle+foot@Vector((0,-.15,-.09)),(.235,.04,.35),rubber,.009,foot)
    box('ShinMark_'+side,knee.lerp(ankle,.4)+Vector((0,.088,0)),(.11,.014,.025),cyan,.003)

segment('Pelvis_Block',hips[0],hips[1],.15,.145,cloth)
pose_root=bpy.data.objects.new('SeatedPoseRoot',None)
bpy.context.scene.collection.objects.link(pose_root)
pose_root.empty_display_type='PLAIN_AXES';pose_root.empty_display_size=.15
pose_root.location=bv((-.03,-.095,.605))
bpy.context.view_layer.update()
for obj in list(bpy.context.scene.objects):
    if obj.type=='MESH':
        obj.parent=pose_root;obj.matrix_parent_inverse=pose_root.matrix_world.inverted()

for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    uv=obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
        for li in poly.loop_indices:
            co=obj.data.vertices[obj.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]],co[axes[1]])

readme=bpy.data.texts.new('README_SLIDE_LEGS')
readme.write('Sojourn-inspired slide-only FPS blocking. Metres; Godot forward is -Z after import.\nLEFT leg extended, toe raised; RIGHT leg folded, knee high/outward, foot near pelvis.\nSeatedPoseRoot and a small pelvis block connect the fixed pose; no torso, rig or collision.\nThe imported scene origin is a camera-composition pivot. Godot rotates the entire pose from WASD; it never reposes individual legs.\nReference: Markus Hammarstedt Sojourn/Ramattra reel https://vimeo.com/826349362 (sliding around 0:48-0:53). Visual interpretation, not a claim about Blizzard rig implementation.\nMaterials match FP_Hands_Blocking.\n')
OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('SLIDE_LEGS_SAVED',len(bpy.data.objects),'objects',sum(len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'),'faces')
