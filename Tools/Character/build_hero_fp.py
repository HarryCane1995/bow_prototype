"""Shared hero design adapted to the established FP rig and fixed Sojourn slide pose.
Keeps the old blocking sources intact. No runtime motion or physics edits.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from hero_geometry import Builder,arm_parts,bv,gv
OUT=ROOT/'Assets/Models/Characters/Hero'
if (OUT/'Hero_FP_Arms.blend').exists() and '--rebuild' not in sys.argv:raise RuntimeError('Use -- --rebuild for deliberate source regeneration.')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/Models/Player/FP_Hands_Blocking.blend'))
rig=bpy.data.objects['HandsRig']
for o in list(bpy.data.objects):
 if o!=rig:bpy.data.objects.remove(o,do_unlink=True)
B=Builder()
for side in ['L','R']:
 bones=rig.data.bones
 p={'shoulder':gv(bones['Upper.'+side].head_local),'elbow':gv(bones['Forearm.'+side].head_local),'wrist':gv(bones['Hand.'+side].head_local),'hand':gv(bones['Fingers.'+side].head_local),'finger':gv(bones['Fingers.'+side].tail_local),'thumb':gv(bones['Thumb.'+side].tail_local)}
 arm_parts(B,side,p,True)
obs=B.emit(rig)
bpy.ops.object.select_all(action='DESELECT')
for o in obs:o.select_set(True)
bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();mesh=obs[0];mesh.name='Hands_Blocking'
mesh.shape_key_add(name='Basis');mesh.shape_key_add(name='Heavy')
rig['geometry_source']='Shared arm_parts design in hero_geometry.py; same hero palette, left cyber/right human. Original FP rest bones preserved exactly.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Hero_FP_Arms.blend'))
fp={'arms_vertices':len(mesh.data.vertices),'arms_faces':len(mesh.data.polygons),'arms_triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),'bones':len(rig.data.bones)}

# Reuse the actual authored full-body leg surfaces, warped into the established
# slide representation. This is a static FP pose, not an extra runtime skeleton.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Hero_Kaze.blend'))
rig=bpy.data.objects['HeroRig'];maps={}
for side,h,k,a in [('L',(-.22,-.12,.58),(-.35,-.025,.035),(-.48,-.08,-.62)),('R',(.16,-.07,.63),(.85,.20,0),(.78,-.04,.43))]:
 for role,start,end in [('Thigh',h,k),('Shin',k,a)]:
  bone=rig.data.bones[role+'.'+side];v1=(bone.tail_local-bone.head_local);v2=bv(end)-bv(start)
  rot=v1.normalized().rotation_difference(v2.normalized()).to_matrix().to_4x4()
  axis=v1.normalized();stretch=Matrix.Identity(3)+(v2.length/v1.length-1)*Matrix([axis*x for x in axis]).transposed()
  m=rot@stretch.to_4x4();m.translation=bv(start)-m.to_3x3()@bone.head_local;maps[role+'.'+side]=m
 bone=rig.data.bones['Foot.'+side]
 # Match the earlier feet's raised leading toe and tucked outward foot.
 rotg=Matrix.Rotation(math.radians(50 if side=='R' else -6),3,'Y')@Matrix.Rotation(math.radians(10 if side=='R' else 48),3,'X')
 conversion=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
 r=conversion@rotg@conversion.inverted();m=r.to_4x4();m.translation=bv(a)-r@bone.head_local
 maps['Foot.'+side]=m;maps['Toe.'+side]=m
pelvis=Matrix.Identity(4);pelvis.translation=bv((-.03,-.095,.605))-rig.data.bones['Pelvis'].head_local;maps['Pelvis']=pelvis
keep=[]
for obj in list(bpy.context.scene.objects):
 if obj.type!='MESH' or not obj.name.startswith(('Pants_','PantsPelvis','LegHardware_','Boots_','Belt')):
  if obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
  continue
 names={g.index:g.name for g in obj.vertex_groups}
 for v in obj.data.vertices:
  original=v.co.copy();result=Vector();total=0
  for weight in v.groups:
   name=names[weight.group]
   if name in maps:result+=(maps[name]@original)*weight.weight;total+=weight.weight
  if total>0:v.co=result/total
 obj.parent=None
 for mod in list(obj.modifiers):obj.modifiers.remove(mod)
 obj.vertex_groups.clear();keep.append(obj)
bpy.data.objects.remove(rig,do_unlink=True)
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
root=bpy.data.objects.new('SeatedPoseRoot',None);bpy.context.scene.collection.objects.link(root)
for o in keep:o.parent=root
root['source']='Actual Hero_Kaze leg surfaces mapped to the preserved left-straight/right-tucked FP pose. Runtime world-lock/yaw-only logic is unchanged.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Hero_FP_SlideLegs.blend'))
fp.update({'slide_meshes':len(keep),'slide_vertices':sum(len(o.data.vertices) for o in keep),'slide_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in keep)})
(ROOT/'.godot/hero-pass/fp-stats.json').write_text(json.dumps(fp,indent=2));print('HERO_FP_SAVED',json.dumps(fp))
