"""One-time PoseLab migration: non-deforming chest socket and position-only camera anchor.
Run in the open authoring session. Saves a backup first and verifies existing poses/actions.
"""
import bpy,json,hashlib
from pathlib import Path
from datetime import datetime
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.godot/humanoid-base';OUT.mkdir(exist_ok=True)
s=bpy.context.scene;r=bpy.data.objects['Male_Rig'];anchor=bpy.data.objects['FP_Camera_Anchor']
SOCKET='FP_CAMERA_SOCKET'
assert Path(bpy.data.filepath).name=='Humanoid_Male_PoseLab.blend'
assert s.frame_current==1 and r.animation_data.action.name=='BH01_SLIDE','Calibrate against the approved current Slide'
assert SOCKET not in r.data.bones,'Socket migration already applied; do not rebuild it'
assert not anchor.constraints and anchor.parent is None,'Inspect changed anchor architecture first'
def action_hash():
    rows=[]
    for a in bpy.data.actions:
        for layer in a.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for f in bag.fcurves:
                        rows.append((a.name,f.data_path,f.array_index,[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation) for k in f.keyframe_points]))
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
def matrices():return {p.name:p.matrix.copy() for p in r.pose.bones if p.bone.use_deform}
def delta(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
action=r.animation_data.action;mode=r.mode;active_bone=r.data.bones.active.name
channels=['location','rotation_quaternion','rotation_euler','rotation_axis_angle','scale']
live={p.name:{k:list(getattr(p,k)) for k in channels} for p in r.pose.bones}
selected={p.name:p.select for p in r.pose.bones}
names=set(r.data.bones.keys());rest={b.name:b.matrix_local.copy() for b in r.data.bones}
fingerprint=action_hash();before={'BH01_SLIDE':matrices()}
cameras={n:bpy.data.objects[n].matrix_world.copy() for n in ['CAM_FP_WORLD','CAM_FP_VIEWMODEL']}
controls={n:bpy.data.objects[n].matrix_world.copy() for n in ['CTRL_CAM_WORLD','CTRL_CAM_VIEWMODEL']}
backup=OUT/('PoseLab_before_camera_socket_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
try:
    r.animation_data.action=bpy.data.actions['BH01_IDLE'];s.frame_set(1);bpy.context.view_layer.update()
    before['BH01_IDLE']=matrices()
finally:
    r.animation_data.action=action;s.frame_set(1)
    for n,values in live.items():
        for k,v in values.items():setattr(r.pose.bones[n],k,v)
    r.update_tag();bpy.context.view_layer.update()
bpy.context.view_layer.objects.active=r
bpy.ops.object.mode_set(mode='EDIT')
bone=r.data.edit_bones.new(SOCKET);bone.parent=r.data.edit_bones['chest']
bone.head=bone.parent.tail;bone.tail=bone.head+Vector((0,0,0.06))
bone.use_connect=False;bone.use_deform=False
bpy.ops.object.mode_set(mode='POSE')
for n,values in live.items():
    for k,v in values.items():setattr(r.pose.bones[n],k,v)
r.update_tag();bpy.context.view_layer.update()
collection=r.data.collections.get('Presentation') or r.data.collections.new('Presentation')
collection.assign(r.data.bones[SOCKET]);collection.is_visible=True
r.data.bones[SOCKET]['purpose']='Position-only FP camera socket; chest-driven, no mesh weights'
r.data.bones[SOCKET].color.palette='THEME04'
r.pose.bones[SOCKET].lock_location=(True,True,True)
r.pose.bones[SOCKET].lock_rotation=(True,True,True)
r.pose.bones[SOCKET].lock_scale=(True,True,True)
eye_in_rig=r.matrix_world.inverted()@cameras['CAM_FP_WORLD'].translation
socket_position=r.pose.bones[SOCKET].matrix.translation.copy()
# Position-only constraint in rig axes: torso rotation cannot become camera look.
anchor.parent=r;anchor.parent_type='OBJECT';anchor.matrix_parent_inverse=Matrix.Identity(4)
anchor.matrix_basis=Matrix.Translation(eye_in_rig-socket_position)
follow=anchor.constraints.new('COPY_LOCATION');follow.name='FP Socket Position Only'
follow.target=r;follow.subtarget=SOCKET;follow.head_tail=0
follow.target_space='POSE';follow.owner_space='LOCAL';follow.use_offset=True
bpy.context.view_layer.update()
# Rebase the existing controls while preserving both camera frames exactly in Slide.
for n,m in controls.items():bpy.data.objects[n].matrix_world=m
bpy.context.view_layer.update()
anchor['purpose']='Local composition offset from FP_CAMERA_SOCKET; no inherited chest rotation'
camera_error=max(delta(bpy.data.objects[n].matrix_world,m) for n,m in cameras.items())
assert camera_error<1e-5,('Slide camera drift',camera_error)
assert set(r.data.bones.keys())==names|{SOCKET}
assert max(delta(r.data.bones[n].matrix_local,m) for n,m in rest.items())<1e-6
report={'backup':str(backup),'parent':'chest','socket':SOCKET,'source_non_deform':not r.data.bones[SOCKET].use_deform,
    'slide_camera_matrix_drift':camera_error,'poses':{}}
try:
    for name in ['BH01_IDLE','BH01_SLIDE']:
        r.animation_data.action=bpy.data.actions[name];s.frame_set(1)
        if name=='BH01_SLIDE':
            for n,values in live.items():
                for k,v in values.items():setattr(r.pose.bones[n],k,v)
        r.update_tag();bpy.context.view_layer.update()
        error=max(delta(r.pose.bones[n].matrix,m) for n,m in before[name].items())
        assert error<1e-6,(name,error)
        report['poses'][name]={'body_pose_matrix_drift':error,'socket':list(r.pose.bones[SOCKET].matrix.translation),
            'world_camera':list(bpy.data.objects['CAM_FP_WORLD'].matrix_world.translation)}
finally:
    r.animation_data.action=action;s.frame_set(1)
    for n,values in live.items():
        for k,v in values.items():setattr(r.pose.bones[n],k,v)
    r.update_tag();bpy.context.view_layer.update()
for p in r.pose.bones:p.select=selected.get(p.name,False)
r.data.bones.active=r.data.bones[active_bone]
assert action_hash()==fingerprint,'Action keyframes changed'
report['actions_unchanged_sha256']=fingerprint
report['idle_camera_rise_m']=report['poses']['BH01_IDLE']['world_camera'][2]-report['poses']['BH01_SLIDE']['world_camera'][2]
assert report['idle_camera_rise_m']>0.2
(OUT/'v2_socket_migration.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('FP_SOCKET_MIGRATION_PASS',json.dumps(report))
