"""Add only missing Idle-derived RMB authoring Actions; never export placeholders.

Run on Humanoid_Male_PoseLab.blend in Blender, or pass the source file before
--python on the Blender command line. Existing Action curves are preserved.
"""
import bpy, json, hashlib, math
from pathlib import Path
from datetime import datetime
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend'
OUT = ROOT / '.godot/rmb-foundation'
OUT.mkdir(parents=True, exist_ok=True)
assert Path(bpy.data.filepath).resolve() == SOURCE.resolve(), 'Open canonical PoseLab first'
rig = bpy.data.objects['Male_Rig']

def action_signature(action):
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for f in bag.fcurves:
                    curves.append([f.data_path, f.array_index, f.extrapolation,
                        [[list(k.co), list(k.handle_left), list(k.handle_right), k.interpolation, k.handle_left_type, k.handle_right_type] for k in f.keyframe_points]])
    return hashlib.sha256(json.dumps(curves).encode()).hexdigest()

before = {a.name:action_signature(a) for a in bpy.data.actions}
rest = {b.name:(b.parent.name if b.parent else None, [list(row) for row in b.matrix_local], b.use_deform) for b in rig.data.bones}
backup = OUT / ('PoseLab_before_RMB_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
names = ['BH01_RMB_ANTICIPATION', 'BH01_MELEE', 'BH01_PARRY', 'BH01_MELEE_RECOVERY']
created = []
for name in names:
    if name in bpy.data.actions:
        continue
    action = bpy.data.actions['BH01_IDLE'].copy()
    action.name = name
    action.use_fake_user = True
    action['authoring_status'] = 'Idle-derived starting pose; author manually before runtime export'
    created.append(name)

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
rig.animation_data.action = bpy.data.actions[names[0]]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
bpy.context.scene.frame_set(1)
rig.show_in_front = True
for collection in rig.data.collections_all:
    if collection.name in {'DEF','MCH'}: collection.is_visible = False
    elif collection.name.startswith('CTRL_'): collection.is_visible = True
for obj in bpy.context.scene.objects:
    if obj.name.startswith('Female_') and obj.name in bpy.context.view_layer.objects:
        obj.hide_set(True)
bpy.data.objects['POSE_CyberBow'].hide_set(False)
bpy.ops.object.mode_set(mode='POSE')

# Keep one useful full-body viewport plus an available first-person camera view.
for window in bpy.context.window_manager.windows:
    window.workspace = bpy.data.workspaces['BH01 PoseLab']
    views = sorted([a for a in window.screen.areas if a.type == 'VIEW_3D'], key=lambda a:a.width*a.height, reverse=True)
    for i, area in enumerate(views):
        space = area.spaces.active
        space.overlay.show_overlays = True
        space.shading.type = 'MATERIAL'
        if i == 0:
            space.region_3d.view_perspective = 'PERSP'
            space.region_3d.view_location = rig.matrix_world @ Vector((0,0,0.95))
            space.region_3d.view_distance = 3.3
            space.region_3d.view_rotation = Euler((math.radians(78),0,math.radians(20))).to_quaternion()
        else:
            space.use_local_camera = True
            space.camera = bpy.data.objects['CAM_FP_WORLD']
            space.region_3d.view_perspective = 'CAMERA'
    for area in window.screen.areas:
        if area.type == 'DOPESHEET_EDITOR' and area.ui_type != 'TIMELINE':
            area.ui_type = 'DOPESHEET'
            area.spaces.active.mode = 'ACTION'
            area.spaces.active.show_region_channels = True

assert before == {a.name:action_signature(a) for a in bpy.data.actions if a.name in before}, 'Existing Action changed'
assert rest == {b.name:(b.parent.name if b.parent else None,[list(row) for row in b.matrix_local],b.use_deform) for b in rig.data.bones}, 'Rig structure changed'
for name in created:
    assert action_signature(bpy.data.actions[name]) == before['BH01_IDLE']
    assert bpy.data.actions[name].use_fake_user
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
result = {'created':created,'preserved_existing_actions':len(before),'preserved_bones':len(rest),'backup':str(backup),'active_action':rig.animation_data.action.name,'frame':bpy.context.scene.frame_current,'mode':bpy.context.mode,'action_hashes_before':before}
(OUT/'blender_slots.json').write_text(json.dumps(result,indent=2))
print('RMB_SLOTS_READY',json.dumps({k:v for k,v in result.items() if k!='action_hashes_before'}))
