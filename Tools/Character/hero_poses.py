"""Authored readiness poses; no gameplay controller or third-person locomotion."""
import bpy,math
from mathutils import Vector,Matrix
from hero_geometry import bv,gv
V=Vector
POSE_NAMES=['Neutral','ArmsForward','BowReady','FullDraw','Crouch','Slide','Wallrun']

def global_bone(rig,name,head,tail):
 rest=rig.data.bones[name];q=(rest.tail_local-rest.head_local).normalized().rotation_difference(bv(tail)-bv(head))
 m=q.to_matrix().to_4x4()@rest.matrix_local;m.translation=bv(head);rig.pose.bones[name].matrix=m
 bpy.context.view_layer.update()

def two_bone(rig,upper,lower,end,target,pole):
 rest1,rest2=rig.data.bones[upper],rig.data.bones[lower]
 shoulder=gv(rig.pose.bones[upper].head);target=V(target);direction=(target-shoulder).normalized()
 a,b=rest1.length,rest2.length;d=min(max((target-shoulder).length,abs(a-b)+.001),a+b-.001)
 pole=V(pole)-shoulder;pole=(pole-direction*pole.dot(direction)).normalized()
 along=(a*a-b*b+d*d)/(2*d);elbow=shoulder+direction*along+pole*math.sqrt(max(0,a*a-along*along))
 wrist=shoulder+direction*d
 global_bone(rig,upper,shoulder,elbow);global_bone(rig,lower,elbow,wrist)
 if end:
  # Keep the target joint, with its original orientation until pose-specific aim below.
  bone=rig.data.bones[end];global_bone(rig,end,wrist,wrist+gv(bone.tail_local-bone.head_local))
 return wrist

def pose(rig,name):
 for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 if name=='Neutral':return
 pelvis=rig.pose.bones['Pelvis']
 if name=='Crouch':
  m=pelvis.matrix.copy();m.translation+=bv((0,-.34,.12));pelvis.matrix=m
  rig.pose.bones['Spine'].rotation_mode='XYZ';rig.pose.bones['Spine'].rotation_euler.x=math.radians(16)
 elif name=='Slide':
  m=pelvis.matrix.copy();m.translation+=bv((0,-.69,.05));pelvis.matrix=m
  rig.pose.bones['Spine'].rotation_mode='XYZ';rig.pose.bones['Spine'].rotation_euler.x=math.radians(-18)
 elif name=='Wallrun':
  rig.pose.bones['Root'].rotation_mode='XYZ';rig.pose.bones['Root'].rotation_euler.y=math.radians(-13)
 bpy.context.view_layer.update()
 if name in ['Crouch','Slide','Wallrun']:
  targets={'Crouch':[(-.22,.14,-.01),(.24,.14,.07)],'Slide':[(-.15,.14,-.75),(.33,.16,.10)],'Wallrun':[(-.19,.47,.37),(.20,.14,-.15)]}[name]
  for side,target in zip(['L','R'],targets):
   wrist=two_bone(rig,'Thigh.'+side,'Shin.'+side,'Foot.'+side,target,(target[0]*1.7,.60,-.55))
   ft=wrist+V((0,-.025,-.16))
   if name=='Slide' and side=='L':ft=wrist+V((0,.12,-.09))
   global_bone(rig,'Foot.'+side,wrist,ft)
 if name=='ArmsForward':targets=[(-.18,1.39,-.52),(.18,1.39,-.52)]
 elif name in ['BowReady','FullDraw']:targets=[(-.34,1.41,-.46),(.20,1.40,-.16 if name=='FullDraw' else -.37)]
 elif name=='Crouch':targets=[(-.27,.93,-.34),(.28,.93,-.32)]
 elif name=='Slide':targets=[(-.27,.65,-.26),(.28,.62,-.13)]
 else:targets=[(-.58,1.57,-.12),(.19,1.51,-.40)]
 for side,target in zip(['L','R'],targets):
  wrist=two_bone(rig,'Upper.'+side,'Forearm.'+side,'Hand.'+side,target,(-.6 if side=='L' else .6,target[1]-.25,.09))
  global_bone(rig,'Hand.'+side,wrist,wrist+V((0,.10,-.02)))
  # Gross glove curl; the group stays intentionally small and editable.
  p=rig.pose.bones['Fingers.'+side];p.rotation_mode='XYZ';p.rotation_euler.x=math.radians(60)
 bpy.context.view_layer.update()

def add_library(rig):
 rig.animation_data_create()
 for name in POSE_NAMES:
  action=bpy.data.actions.new(name);rig.animation_data.action=action;pose(rig,name)
  for pb in rig.pose.bones:
   # Bake the resulting local pose, independent of Blender constraints / IK solvers.
   pb.rotation_mode='QUATERNION'
   for frame in [1,30]:
    pb.keyframe_insert('location',frame=frame);pb.keyframe_insert('rotation_quaternion',frame=frame);pb.keyframe_insert('scale',frame=frame)
  action.use_fake_user=True
 rig.animation_data.action=None;pose(rig,'Neutral')
