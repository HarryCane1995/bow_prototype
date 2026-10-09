"""Disposable background-only multi-frame proof; never saves canonical PoseLab."""
import bpy,runpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.godot/locomotion-authoring/multiframe'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend'))
rig=bpy.data.objects['Male_Rig']; sc=bpy.context.scene
action=bpy.data.actions['BH01_RUN_CONTACT'].copy(); action.name='BH01_TEST_MULTIFRAME'
action.use_frame_range=True; action.frame_start=5; action.frame_end=35; action.use_cyclic=True
rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
sc.render.fps=30; sc.render.fps_base=1
sc.frame_set(1)
base_cog=rig.pose.bones['CTRL_COG'].location.copy()
base_root=rig.pose.bones['CTRL_ROOT'].location.copy()
for frame,height,side in [(5,0,0),(20,.06,.02),(35,0,0)]:
    rig.pose.bones['CTRL_COG'].location=base_cog
    rig.pose.bones['CTRL_COG'].location.z+=height
    rig.pose.bones['CTRL_COG'].keyframe_insert(data_path='location',frame=frame)
    rig.pose.bones['CTRL_ROOT'].location=base_root
    rig.pose.bones['CTRL_ROOT'].location.x+=side
    rig.pose.bones['CTRL_ROOT'].keyframe_insert(data_path='location',frame=frame)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if 'CTRL_COG' in curve.data_path:
                    for key in curve.keyframe_points:
                        key.interpolation='BEZIER'; key.handle_left_type=key.handle_right_type='AUTO_CLAMPED'
                if 'CTRL_ROOT' in curve.data_path:
                    for key in curve.keyframe_points:key.interpolation='CONSTANT'
sc.frame_set(5)
runpy.run_path(str(ROOT/'Tools/Blender/HumanoidBase/capture_v2.py'),init_globals={'V2_EXTRA_ACTIONS':[action.name],'V2_CAPTURE_DIR':str(OUT)})
capture=json.loads((OUT/'v2_source_capture.json').read_text())
clip=capture['clips'][action.name]
assert clip['start_frame']==5 and clip['end_frame']==35 and clip['fps']==30 and clip['loop']
heights=[s['bones']['FP_CAMERA_SOCKET'][1][3] for s in clip['samples']]
assert max(heights)-min(heights)>.04, 'Test must really animate the socket'
assert len(clip['samples'])>60
print('MULTIFRAME_CAPTURE_PASS',len(clip['samples']),'samples, socket range',max(heights)-min(heights))
