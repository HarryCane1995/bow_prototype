"""Live PoseLab: preserve existing Actions; add only missing Run container.
LOCO_HANDOFF=True selects Wallrun Left at the end of the pass.
"""
import bpy,json,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'.godot/locomotion-authoring'; OUT.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).name=='Humanoid_Male_PoseLab.blend'
rig=bpy.data.objects['Male_Rig']
def signature(a):
    curves=[(f.data_path,f.array_index,f.extrapolation,[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in f.keyframe_points]) for l in a.layers for s in l.strips for bag in s.channelbags for f in bag.fcurves]
    return hashlib.sha256(json.dumps([curves,list(a.frame_range),a.use_frame_range,a.use_cyclic,a.use_fake_user]).encode()).hexdigest()
before={a.name:signature(a) for a in bpy.data.actions}
backup=OUT/('PoseLab_authoring_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
required=['BH01_WALLRUN_LEFT','BH01_WALLRUN_RIGHT','BH01_RUN_CONTACT','BH01_RUN_FLIGHT']
assert all(n in bpy.data.actions for n in required)
created=[]
if 'BH01_RUN' not in bpy.data.actions:
    action=bpy.data.actions['BH01_RUN_CONTACT'].copy()
    action.name='BH01_RUN'; action.use_fake_user=True
    action.use_frame_range=True; action.frame_start=1; action.frame_end=25; action.use_cyclic=True
    action['authoring_status']='Run container: Contact-derived frame 1 only; user authors the cycle'
    created.append(action.name)
if globals().get('LOCO_HANDOFF',False):
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT'); rig.hide_set(False); rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    rig.animation_data.action=bpy.data.actions['BH01_WALLRUN_LEFT']
    rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    bpy.context.scene.frame_set(1)
    bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=25
    rig.show_in_front=True
    for c in rig.data.collections_all:
        if c.name in {'DEF','MCH'}: c.is_visible=False
        elif c.name.startswith('CTRL_'): c.is_visible=True
    bpy.data.objects['POSE_CyberBow'].hide_set(False)
    bpy.ops.object.mode_set(mode='POSE')
    for window in bpy.context.window_manager.windows:
        window.workspace=bpy.data.workspaces['BH01 PoseLab']
        editors=[a for a in window.screen.areas if a.type in {'DOPESHEET_EDITOR','GRAPH_EDITOR'}]
        action_editor=max(editors,key=lambda a:a.height)
        for area in editors:
            area.type='DOPESHEET_EDITOR'
            if area==action_editor:
                area.ui_type='DOPESHEET'; area.spaces.active.mode='ACTION'
            else:area.ui_type='TIMELINE'
assert before=={a.name:signature(a) for a in bpy.data.actions if a.name in before},'Existing Action changed'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
result={'backup':str(backup),'created':created,'preserved_actions':len(before),'hashes':before,'active':rig.animation_data.action.name,'handoff':bool(globals().get('LOCO_HANDOFF',False))}
(OUT/('handoff.json' if result['handoff'] else 'source_validation.json')).write_text(json.dumps(result,indent=2))
print('LOCOMOTION_AUTHORING_READY',json.dumps({k:v for k,v in result.items() if k!='hashes'}))
