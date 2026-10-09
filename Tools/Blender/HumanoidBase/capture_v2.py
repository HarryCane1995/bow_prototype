"""Capture explicit full Actions; preserve keys and the current live authoring pose.

Idle/Slide keep frame-1, one-second static semantics. Extras use Action range,
scene FPS and use_cyclic. V2_EXTRA_ACTIONS selects extras explicitly.
V2_SAMPLE_FPS defaults to 60. V2_CAPTURE_DIR optionally isolates test output.
"""
import bpy, json, math
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(globals().get('V2_CAPTURE_DIR',ROOT/'.godot/humanoid-base'))
OUT.mkdir(parents=True,exist_ok=True)
rig=bpy.data.objects['Male_Rig']; body=bpy.data.objects['Male_Body']; sc=bpy.context.scene
SOCKET='FP_CAMERA_SOCKET'
assert SOCKET in rig.data.bones and not rig.data.bones[SOCKET].use_deform
assert Path(bpy.data.filepath).name=='Humanoid_Male_PoseLab.blend'
active=rig.animation_data.action; active_slot=rig.animation_data.action_slot
frame,subframe=sc.frame_current,sc.frame_subframe
use_nla=rig.animation_data.use_nla
action_names=list(dict.fromkeys(['BH01_IDLE','BH01_SLIDE']+list(globals().get('V2_EXTRA_ACTIONS',[]))))
assert all(n.startswith('BH01_') and n in bpy.data.actions for n in action_names)
fps=sc.render.fps/sc.render.fps_base
sample_fps=max(fps,float(globals().get('V2_SAMPLE_FPS',60)))
channels=['location','rotation_quaternion','rotation_euler','rotation_axis_angle','scale']
live={p.name:{k:list(getattr(p,k)) for k in channels} for p in rig.pose.bones}
props={p.name:{k:v for k,v in p.items() if isinstance(v,(str,int,float))} for p in rig.pose.bones}

def key_metadata(action):
    return [{'path':f.data_path,'index':f.array_index,'extrapolation':f.extrapolation,
        'keys':[{'co':list(k.co),'interpolation':k.interpolation,'left':list(k.handle_left),'right':list(k.handle_right)} for k in f.keyframe_points]}
        for layer in action.layers for strip in layer.strips for bag in strip.channelbags for f in bag.fcurves]

def sample(surface=False,projections=False):
    deps=bpy.context.evaluated_depsgraph_get(); er=rig.evaluated_get(deps)
    socket_position=er.pose.bones[SOCKET].matrix.translation
    cameras={}
    for name in ['CAM_FP_WORLD','CAM_FP_VIEWMODEL']:
        cam=bpy.data.objects[name].evaluated_get(deps); lens=cam.data
        assert lens.type=='PERSP'
        frustum=lens.view_frame(scene=sc)
        tx=[v.x/-v.z for v in frustum]; ty=[v.y/-v.z for v in frustum]
        aspect=sc.render.resolution_x*sc.render.pixel_aspect_x/(sc.render.resolution_y*sc.render.pixel_aspect_y)
        fit=lens.sensor_fit
        if fit=='AUTO':fit='HORIZONTAL' if aspect>=1 else 'VERTICAL'
        relative=er.matrix_world.inverted()@cam.matrix_world
        relative.translation-=socket_position
        cameras[name]={'socket_offset_matrix_blender':[list(row) for row in relative],
            'fov_x_degrees':math.degrees(2*math.atan((max(tx)-min(tx))/2)),
            'fov_y_degrees':math.degrees(2*math.atan((max(ty)-min(ty))/2)),
            'sensor_fit':fit,'source_aspect':aspect,'shift':[lens.shift_x,lens.shift_y],
            'near':lens.clip_start,'far':lens.clip_end}
        if projections:
            cameras[name]['bone_uv']={p.name:list(world_to_camera_view(sc,cam,er.matrix_world@p.head)) for p in er.pose.bones if p.bone.use_deform}
    result={'bones':{p.name:[list(row) for row in p.matrix] for p in er.pose.bones if p.bone.use_deform or p.name==SOCKET},
        'bow_matrix':[list(row) for row in bpy.data.objects['POSE_CyberBow'].matrix_world],'cameras':cameras}
    if surface:
        ev=body.evaluated_get(deps); mesh=ev.to_mesh()
        result['surface']=[list(ev.matrix_world@v.co) for v in mesh.vertices]
        ev.to_mesh_clear()
    return result

original=sample(True,True)
backup=OUT/('PoseLab_V2_source_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
poses={}; clips={}
try:
    rig.animation_data.use_nla=False
    for name in action_names:
        action=bpy.data.actions[name]
        rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
        static=name in {'BH01_IDLE','BH01_SLIDE'}
        start,end=(1.0,1.0) if static else tuple(action.frame_range)
        assert end>=start
        duration=(end-start)/fps if end>start else 1.0
        loop=bool(action.use_cyclic) and not static
        keys=key_metadata(action)
        times={0.0}
        if end>start:
            times.update(i/sample_fps for i in range(math.ceil(duration*sample_fps)) if i/sample_fps<duration)
            times.add(duration)
            for f in keys:
                for i,k in enumerate(f['keys']):
                    t=(k['co'][0]-start)/fps
                    if 0<=t<=duration:
                        times.add(t)
                        # Hold constant segments until immediately before their jump.
                        if i and f['keys'][i-1]['interpolation']=='CONSTANT' and t>0:
                            # Blender deduplicates very close F-curve frames.
                            # A 1 ms boundary survives export and keeps a crisp step.
                            times.add(max(0,t-0.001))
        times=sorted(times); samples=[]
        for i,t in enumerate(times):
            source_frame=start+t*fps if end>start else start
            sc.frame_set(math.floor(source_frame),subframe=source_frame-math.floor(source_frame))
            bpy.context.view_layer.update()
            # Preserve the previous live, unkeyed frame-1 Idle/Slide capture rule.
            if end==start and action==active and abs(source_frame-frame-subframe)<1e-7: result=original
            else: result=sample(i in {0,len(times)//2,len(times)-1},i==0)
            samples.append(dict(result,time=t,frame=source_frame))
        poses[name]=samples[0]
        clips[name]={'action':name,'kind':'static_pose' if end==start else 'clip',
            'start_frame':start,'end_frame':end,'fps':fps,'sample_fps':sample_fps,
            'duration_seconds':duration,'loop':loop,'source_keys':keys,'samples':samples}
finally:
    rig.animation_data.action=active; rig.animation_data.action_slot=active_slot
    rig.animation_data.use_nla=use_nla; sc.frame_set(frame,subframe=subframe)
    for name,values in live.items():
        for k,value in values.items():setattr(rig.pose.bones[name],k,value)
        for k,value in props[name].items():rig.pose.bones[name][k]=value
    rig.update_tag(); bpy.context.view_layer.update()
result={'version':3,'source_snapshot':str(backup),'canonical_source':bpy.data.filepath,'active':active.name,'actions':action_names,
    'camera_reference':'FP_CAMERA_SOCKET animated origin + offset in Male_Rig axes; position only',
    'camera_socket':SOCKET,'poses':poses,'clips':clips,
    'audit':[{'action':n,'classification':'explicit_selection'} for n in action_names]}
(OUT/'v2_source_capture.json').write_text(json.dumps(result))
print('V2_CAPTURED',json.dumps({'backup':str(backup),'actions':{n:{k:v for k,v in c.items() if k not in ['samples','source_keys']} for n,c in clips.items()}}))
