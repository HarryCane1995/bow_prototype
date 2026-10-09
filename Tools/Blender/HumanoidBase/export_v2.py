"""Export captured evaluated authoring poses, never save or rebuild PoseLab.

Run Blender --background --python this_file -- capture.json.
The capture contains exact evaluated deform matrices and the untouched source snapshot.
"""
import bpy,bmesh,json,sys,struct,hashlib,argparse,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('capture')
parser.add_argument('--output',default=str(ROOT/'Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.glb'))
parser.add_argument('--idle-action',default='BH01_IDLE')
parser.add_argument('--parts',nargs='+',default=['HEAD','TORSO','ARMS','LEGS'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
capture=Path(args.capture)
path=Path(args.output).resolve(); path.parent.mkdir(parents=True,exist_ok=True)
pending=capture.resolve().parent/'V2_export_pending.glb'
EXPORT_FPS=60
data=json.loads(capture.read_text())
action_names=data['actions']
assert args.idle_action in action_names
if args.idle_action=='BH01_IDLE':assert 'BH01_SLIDE' in action_names
assert len(action_names)==len(set(action_names)) and all(n.startswith('BH01_') for n in action_names)
# Camera local axes already match Godot cameras (-Z forward, +Y up).
# Convert only the reference space, not the camera's local axes.
C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
SOCKET=data['camera_socket']
clips=data.get('clips') or {n:{'samples':[dict(p,time=0.0,frame=1)],'kind':'static_pose','start_frame':1,'end_frame':1,'fps':24,'sample_fps':24,'duration_seconds':1,'loop':False} for n,p in data['poses'].items()}
camera_calibration={'version':2,'reference':data['camera_reference'],'socket':SOCKET,
    'offset_space':'skeleton_axes_position_only','cameras':{}}
for pose in [sample for clip in clips.values() for sample in clip['samples']]:
    for camera,src in pose['cameras'].items():
        assert max(abs(v) for v in src['shift'])<1e-7,'Camera lens shift is not supported by this centered-perspective calibration'
        m=C@Matrix(src['socket_offset_matrix_blender'])
        entry={k:v for k,v in src.items() if k not in ['socket_offset_matrix_blender','bone_uv']}
        entry['socket_offset_transform']=[list(row) for row in m]
        if camera in camera_calibration['cameras']:
            previous=camera_calibration['cameras'][camera]
            assert max(abs(m[i][j]-previous['socket_offset_transform'][i][j]) for i in range(4) for j in range(4))<1e-5, 'Pose-specific camera offset detected; use the shared socket anchor'
            assert abs(entry['fov_y_degrees']-previous['fov_y_degrees'])<1e-5
        else:camera_calibration['cameras'][camera]=entry
bpy.ops.wm.open_mainfile(filepath=data['source_snapshot'])
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
if data.get('scene'):bpy.context.window.scene=bpy.data.scenes[data['scene']]
rig=bpy.data.objects[data.get('rig','Male_Rig')];body=bpy.data.objects[data.get('body','Male_Body')];sc=bpy.context.scene
rest={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones if b.use_deform or b.name==SOCKET}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones if b.use_deform or b.name==SOCKET}
assert SOCKET not in body.vertex_groups and not rig.data.bones[SOCKET].use_deform
for o in list(bpy.data.objects):
    if o not in [rig,body]:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();body.animation_data_clear()
for p in rig.pose.bones:
    for c in list(p.constraints):p.constraints.remove(c)
    p.custom_shape=None
    for k in list(p.keys()):del p[k]
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for b in list(rig.data.edit_bones):
    if b.name not in rest:rig.data.edit_bones.remove(b)
bpy.ops.object.mode_set(mode='OBJECT')
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
assert len(rig.data.bones)==54
assert {b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}==rest
assert {b.name:b.parent.name if b.parent else None for b in rig.data.bones}==parents
rig.hide_set(False);body.hide_set(False)
bpy.context.view_layer.objects.active=body;body.select_set(True)
for mod in list(body.modifiers):
    if mod.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
pose_errors={}
sc.render.fps=EXPORT_FPS; sc.render.fps_base=1
for name in action_names:
    clip=clips[name]; samples=clip['samples']
    action=bpy.data.actions.new(name); action.use_fake_user=True
    action.use_frame_range=True; action.frame_start=0
    action.frame_end=clip['duration_seconds']*EXPORT_FPS
    action.use_cyclic=clip['loop']
    rig.animation_data_create(); rig.animation_data.action=action
    previous_quaternions={}
    baked={}
    for sample_index,pose in enumerate(samples):
        time=pose['time']
        for p in rig.pose.bones:
            desired=Matrix(pose['bones'][p.name])
            kw={}
            if p.parent:
                kw={'parent_matrix':Matrix(pose['bones'][p.parent.name]),'parent_matrix_local':p.parent.bone.matrix_local}
            p.rotation_mode='QUATERNION'
            local=p.bone.convert_local_to_pose(desired,p.bone.matrix_local,invert=True,**kw)
            position,rotation,scale=local.decompose()
            if p.name in previous_quaternions and rotation.dot(previous_quaternions[p.name])<0: rotation.negate()
            previous_quaternions[p.name]=rotation.copy()
            p.location=position; p.rotation_quaternion=rotation; p.scale=scale
            # The socket is baked too. It stays non-deforming, under chest.
            times=[0,clip['duration_seconds']] if len(samples)==1 else [time]
            for t in times:
                for channel in ['location','rotation_quaternion','scale']:
                    if sample_index==0 and t==0:
                        p.keyframe_insert(data_path=channel,frame=0,group=p.name)
                    for index,value in enumerate(getattr(p,channel)):
                        baked.setdefault((p.path_from_id(channel),index),[]).extend([t*EXPORT_FPS,value])
    # Authored interpolation was evaluated in Blender; these are baked samples,
    # not another Bezier fit (which would overshoot constraints and contacts).
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    values=baked[(curve.data_path,curve.array_index)]
                    # Bulk insertion preserves sub-frame step boundaries. Ordinary
                    # keyframe_insert merges keys separated by <0.01 frames.
                    curve.keyframe_points.clear()
                    curve.keyframe_points.add(len(values)//2)
                    curve.keyframe_points.foreach_set('co',values)
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
                    curve.update()
    for pose in samples:
        if 'surface' not in pose:continue
        time=pose['time']; frame=time*EXPORT_FPS
        sc.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
        bpy.context.view_layer.update()
        ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh()
        assert len(mesh.vertices)==len(pose['surface'])
        error=max((ev.matrix_world@v.co-Vector(co)).length for v,co in zip(mesh.vertices,pose['surface']))
        ev.to_mesh_clear(); assert error<.0001,(name,time,error)
        pose_errors[name]=max(pose_errors.get(name,0),error)

# Split only the disposable export surface. All four pieces share the same armature.
def category(bone):
    if bone=='head':return 'HEAD'
    if any(bone.startswith(n) for n in ['thigh','calf','foot','toes']):return 'LEGS'
    if any(bone.startswith(n) for n in ['clavicle','upper_arm','forearm','hand','thumb','index','middle','ring','pinky']):return 'ARMS'
    return 'TORSO'
groups={g.index:category(g.name) for g in body.vertex_groups}
face_categories=[]
for face in body.data.polygons:
    sums={n:0. for n in ['HEAD','TORSO','ARMS','LEGS']}
    for vi in face.vertices:
        for g in body.data.vertices[vi].groups:sums[groups[g.group]]+=g.weight
    face_categories.append(max(sums,key=sums.get))
pieces=[]
for part in args.parts:
    obj=body.copy();obj.data=body.data.copy();obj.name=part;sc.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(obj.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if face_categories[f.index]!=part],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(obj.data);bm.free();obj.hide_viewport=False;obj.hide_render=False;obj.hide_select=False;obj.hide_set(False);pieces.append(obj)
bpy.data.objects.remove(body,do_unlink=True)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for obj in pieces:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
rig.animation_data.action=bpy.data.actions[args.idle_action];sc.frame_start=0;sc.frame_end=math.ceil(max(c['duration_seconds'] for c in clips.values())*EXPORT_FPS);sc.frame_set(0)
print('EXPORT_SELECTION',[(o.name,o.type,o.select_get(),o.visible_get()) for o in bpy.context.view_layer.objects])
bpy.ops.export_scene.gltf(filepath=str(pending),check_existing=False,export_format='GLB',use_selection=True,
    export_yup=True,export_apply=True,export_skins=True,export_influence_nb=8,export_all_influences=False,
    export_armature_object_remove=True,export_rest_position_armature=True,export_def_bones=False,
    export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,
    export_force_sampling=False,export_frame_range=False,export_optimize_animation_size=False,export_anim_slide_to_zero=True,
    export_materials='EXPORT',export_cameras=False,export_lights=False,export_extras=False)
raw=pending.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length])
# Loop/range-only edits must also invalidate Godot's GLB import hash. Keep their
# metadata in the generated animation extras as well as the readable sidecar.
for animation in doc['animations']:
    animation.setdefault('extras',{})['v2_clip']={k:v for k,v in clips[animation['name']].items() if k not in ['samples','source_keys']}
json_chunk=json.dumps(doc,separators=(',',':')).encode('utf-8')
json_chunk+=b' '*((-len(json_chunk))%4)
tail=raw[20+length:]
raw=raw[:8]+struct.pack('<I',20+len(json_chunk)+len(tail))+struct.pack('<I',len(json_chunk))+b'JSON'+json_chunk+tail
assert len(doc['skins'])==1 and len(doc['skins'][0]['joints'])==54
assert any(n.get('name')==SOCKET for n in doc['nodes'])
assert len(doc.get('meshes',[]))==len(args.parts),'Requested body regions must be present'
assert {a['name'] for a in doc['animations']}==set(action_names)
assert not any(n.get('name','').startswith(('CTRL_','MCH_')) for n in doc['nodes'])
assert not doc.get('cameras')
calibration_path=path.with_suffix('.camera.json')
calibration_path.write_text(json.dumps(camera_calibration,indent=2))
result={'source':'Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend','source_snapshot':data['source_snapshot'],
 'actions':action_names,'audit':data['audit'],'bones':54,'deform_bones':53,
 'non_deform_sockets':[SOCKET],'parents':parents,'rest':rest,
 'parts':{o.name:len(o.data.vertices) for o in pieces},'bake_surface_error_m':pose_errors,
 'export_sha256':hashlib.sha256(raw).hexdigest(),'static_hold_seconds':1,'clips':{n:{k:v for k,v in c.items() if k not in ['samples','source_keys']} for n,c in clips.items()},'axes':'Blender (x,y,z) -> Godot (x,z,-y); model faces +Z',
 'camera_calibration':str(calibration_path.relative_to(ROOT)).replace('\\','/'),'camera_reference':data['camera_reference']}
metadata={'version':1,'clips':{n:{k:v for k,v in c.items() if k not in ['samples','source_keys']} for n,c in clips.items()}}
path.with_suffix('.animations.json').write_text(json.dumps(metadata,indent=2))
# Publish only after both sidecars are ready for the editor's import hook.
path.write_bytes(raw)
review=ROOT/'Assets/Characters/BaseHumanoid/Review' if path.name=='BH01_Male_V2.glb' else path.parent
review.mkdir(parents=True,exist_ok=True)
(review/('v2_export_manifest.json' if path.name=='BH01_Male_V2.glb' else path.stem+'.manifest.json')).write_text(json.dumps(result,indent=2))
print('V2_EXPORT_PASS',json.dumps({k:v for k,v in result.items() if k not in ['rest','parents','audit']}))
