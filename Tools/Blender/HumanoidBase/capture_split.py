"""Capture the explicitly selected split branch, preserving live Actions/poses.

MCP: exec(..., {'__file__':path, 'SPLIT_BRANCH':'1POV'}) (then 3POV).
Full Action range/FPS for every indexed slot; no legacy frame-1 override.
"""
import bpy, json, math
from pathlib import Path
from datetime import datetime
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[3]
branch=globals().get('SPLIT_BRANCH','1POV')
assert branch in ['1POV','3POV']
out=ROOT/'.godot/split-presentation'/branch;out.mkdir(parents=True,exist_ok=True)
window=bpy.context.window;previous=window.scene
sc=bpy.data.scenes['BH01_'+branch];rig=bpy.data.objects[sc['split_rig']];body=bpy.data.objects[sc['split_body']]
active=rig.animation_data.action;slot=rig.animation_data.action_slot
frame=sc.frame_current;subframe=sc.frame_subframe;use_nla=rig.animation_data.use_nla
channels=['location','rotation_quaternion','rotation_euler','rotation_axis_angle','scale']
live={p.name:{k:list(getattr(p,k)) for k in channels} for p in rig.pose.bones}
props={p.name:{k:v for k,v in p.items() if isinstance(v,(str,int,float))} for p in rig.pose.bones}
snapshot=out/('source_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(snapshot),copy=True)
fps=sc.render.fps/sc.render.fps_base;sample_fps=max(fps,60)
actions=sorted(a.name for a in bpy.data.actions if a.name.startswith('BH01_'+branch+'_'))
clips={}
try:
    window.scene=sc;rig.animation_data.use_nla=False
    for name in actions:
        action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
        start,end=action.frame_range;duration=(end-start)/fps if end>start else 1.0
        times={0.0}
        if end>start:
            times.update(i/sample_fps for i in range(math.ceil(duration*sample_fps)));times.add(duration)
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for i,k in enumerate(curve.keyframe_points):
                                t=(k.co.x-start)/fps
                                if 0<=t<=duration:
                                    times.add(t)
                                    if i and curve.keyframe_points[i-1].interpolation=='CONSTANT' and t>0:times.add(max(0,t-.001))
        samples=[];times=sorted(times)
        for i,t in enumerate(times):
            f=start+t*fps if end>start else start
            sc.frame_set(math.floor(f),subframe=f-math.floor(f));bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get();er=rig.evaluated_get(deps)
            sample={'time':t,'frame':f,'bones':{p.name:[list(r) for r in p.matrix] for p in er.pose.bones if p.bone.use_deform or p.name=='FP_CAMERA_SOCKET'},'cameras':{}}
            if i in {0,len(times)//2,len(times)-1}:
                ev=body.evaluated_get(deps);mesh=ev.to_mesh();sample['surface']=[list(ev.matrix_world@v.co) for v in mesh.vertices];ev.to_mesh_clear()
            samples.append(sample)
        clips[name]={'action':name,'kind':'clip' if end>start else 'static_pose','start_frame':start,'end_frame':end,'fps':fps,'sample_fps':sample_fps,'duration_seconds':duration,'loop':bool(action.use_cyclic) and end>start,'samples':samples}
    C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
    # Fixed authoring camera -> camera-local model transform; animation can never
    # move this camera. Editing CTRL_CAM_1POV explicitly updates framing on export.
    camera=sc.camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
    framing=(C@camera.matrix_world).inverted()@(C@rig.matrix_world@C.inverted())
    calibration={'branch':branch,'fp_model_rows':[list(r) for r in framing],'fov':math.degrees(camera.data.angle),'near':camera.data.clip_start}
finally:
    rig.animation_data.action=active;rig.animation_data.action_slot=slot;rig.animation_data.use_nla=use_nla
    sc.frame_set(frame,subframe=subframe)
    for n,values in live.items():
        for k,v in values.items():setattr(rig.pose.bones[n],k,v)
        for k,v in props[n].items():rig.pose.bones[n][k]=v
    rig.update_tag();window.scene=previous;bpy.context.view_layer.update()
data={'version':4,'source_snapshot':str(snapshot),'canonical_source':bpy.data.filepath,'scene':sc.name,'rig':rig.name,'body':body.name,
      'actions':actions,'camera_socket':'FP_CAMERA_SOCKET','camera_reference':'Split camera independent of animated skeleton',
      'clips':clips,'audit':[{'action':n,'classification':'explicit_split_'+branch} for n in actions]}
(out/'capture.json').write_text(json.dumps(data))
(out/'presentation.json').write_text(json.dumps(calibration,indent=2))
print('SPLIT_CAPTURED',branch,len(actions),str(out/'capture.json'))
