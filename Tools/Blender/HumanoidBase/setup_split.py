"""One-time, additive PoseLab split. Run in the open source through Blender MCP.

Never replaces existing indexed Actions/scenes. Legacy Actions/rig stay untouched.
"""
import bpy, bmesh, json, hashlib, math
from pathlib import Path
from datetime import datetime
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.godot/split-presentation'
STATES = ['IDLE','RUN','CROUCH','SLIDE','WALLRUN_LEFT','WALLRUN_RIGHT','WALL_JUMP',
          'JUMP_TAKEOFF','JUMP_AIR','FALL','LANDING','GRAPPLE_PULL','GRAPPLE_LAUNCH',
          'GRAPPLE_FLIGHT','BOW_READY','BOW_DRAW_START','BOW_FULL_DRAW','BOW_RELEASE',
          'BOW_FOLLOW_THROUGH','BOW_RECOVERY','RMB_ANTICIPATION','MELEE','PARRY','MELEE_RECOVERY']

def fingerprint(action):
    data = [(f.data_path,f.array_index,[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation) for k in f.keyframe_points])
            for layer in action.layers for strip in layer.strips for bag in strip.channelbags for f in bag.fcurves]
    return hashlib.sha256(repr(data).encode()).hexdigest()

assert Path(bpy.data.filepath).name == 'Humanoid_Male_PoseLab.blend'
assert not any('BH01_'+p in bpy.data.scenes for p in ['1POV','3POV']), 'Already set up; never overwrite authoring'
OUT.mkdir(parents=True,exist_ok=True)
backup = OUT / ('PoseLab_pre_authoring_split_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
original = bpy.context.scene
legacy = {a.name:fingerprint(a) for a in bpy.data.actions}
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
source_objects = {bpy.data.objects['Male_Rig'],bpy.data.objects['Male_Body']}
for name in ['POSELAB_BOW','POSELAB_STRING','POSELAB_RIG_SHAPES']:
    source_objects.update(bpy.data.collections[name].all_objects)
baseline = json.loads((OUT/'baseline.json').read_text())
C = Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
fp_camera_matrix = (Matrix(baseline['fp_model_rows']) @ C).inverted()
manifest = {'backup':str(backup),'legacy_fingerprints':legacy,'branches':{},'excluded_reference_actions':['BH01_RUN_CONTACT','BH01_RUN_FLIGHT']}

for branch in ['1POV','3POV']:
    sc = bpy.data.scenes.new('BH01_'+branch)
    sc.world = original.world
    sc.render.resolution_x=1280;sc.render.resolution_y=720;sc.render.resolution_percentage=100
    sc.render.fps=original.render.fps;sc.render.fps_base=original.render.fps_base
    collection = bpy.data.collections.new('POSELAB_'+branch);sc.collection.children.link(collection)
    copies = {}
    for src in source_objects:
        obj = src.copy();obj.name = branch+'_'+src.name
        if src.type in {'ARMATURE','MESH','CURVE'}: obj.data=src.data.copy()
        collection.objects.link(obj);copies[src]=obj
    for src,obj in copies.items():
        obj.parent = copies.get(src.parent,src.parent)
        # Reassigning parent resets parent inverse in Blender. Preserve it or the
        # bow/nock jumps, taking the right-hand IK with it despite identical keys.
        obj.matrix_parent_inverse = src.matrix_parent_inverse.copy()
        for modifier in obj.modifiers:
            if hasattr(modifier,'object'): modifier.object=copies.get(modifier.object,modifier.object)
        owners = [obj]+(list(obj.pose.bones) if obj.type=='ARMATURE' else [])
        for owner in owners:
            for constraint in owner.constraints:
                if hasattr(constraint,'target'): constraint.target=copies.get(constraint.target,constraint.target)
                if hasattr(constraint,'pole_target'): constraint.pole_target=copies.get(constraint.pole_target,constraint.pole_target)
            if hasattr(owner,'custom_shape'): owner.custom_shape=copies.get(owner.custom_shape,owner.custom_shape)
        for idblock in [obj,obj.data]:
            ad=getattr(idblock,'animation_data',None)
            if ad:
                for curve in ad.drivers:
                    for var in curve.driver.variables:
                        for target in var.targets:
                            if target.id in copies: target.id=copies[target.id]
    rig=copies[bpy.data.objects['Male_Rig']];body=copies[bpy.data.objects['Male_Body']]
    rig.hide_viewport=False;rig.hide_render=False;rig.show_in_front=True
    body.hide_viewport=False;body.hide_render=False
    # Keep only the same weight-defined ARMS region used by the runtime exporter.
    if branch=='1POV':
        def category(name):
            if name=='head':return 'HEAD'
            if name.startswith(('thigh','calf','foot','toes')):return 'LEGS'
            if name.startswith(('clavicle','upper_arm','forearm','hand','thumb','index','middle','ring','pinky')):return 'ARMS'
            return 'TORSO'
        cats={g.index:category(g.name) for g in body.vertex_groups}; keep=[]
        for face in body.data.polygons:
            sums={n:0. for n in ['HEAD','TORSO','ARMS','LEGS']}
            for vi in face.vertices:
                for g in body.data.vertices[vi].groups:sums[cats[g.group]]+=g.weight
            keep.append(max(sums,key=sums.get)=='ARMS')
        bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if not keep[f.index]],context='FACES')
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
        bm.to_mesh(body.data);bm.free()
    actions=[]
    for state in STATES:
        source=bpy.data.actions['BH01_'+(state if branch=='3POV' else 'IDLE')]
        name='BH01_'+branch+'_'+state
        assert name not in bpy.data.actions
        action=source.copy();action.name=name;action.use_fake_user=True
        action['split_source']=source.name;action['presentation_branch']=branch
        action['placeholder']=branch=='1POV' or fingerprint(source)==legacy['BH01_BOW_READY']
        actions.append({'name':name,'source':source.name,'placeholder':bool(action['placeholder'])})
    rig.animation_data_create();rig.animation_data.use_nla=False
    rig.animation_data.action=bpy.data.actions['BH01_'+branch+'_IDLE']
    rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    ctrl=bpy.data.objects.new('CTRL_CAM_'+branch,None);collection.objects.link(ctrl)
    cam=bpy.data.objects.new('CAM_'+branch,bpy.data.cameras.new('CAM_'+branch));collection.objects.link(cam)
    cam.parent=ctrl;cam.data.type='PERSP';cam.data.sensor_fit='VERTICAL';cam.data.angle=math.radians(65)
    cam.data.clip_start=.025;cam.data.clip_end=300
    if branch=='1POV':ctrl.matrix_world=fp_camera_matrix
    else:
        ctrl.location=(3,-4,2.5)
        ctrl.rotation_euler=(Vector((0,0,.9))-ctrl.location).to_track_quat('-Z','Y').to_euler()
    sc.camera=cam;sc.frame_set(1);sc.frame_start=1;sc.frame_end=25
    sc['split_rig']=rig.name;sc['split_body']=body.name;sc['split_branch']=branch
    sc['authoring_help']='Action Editor: select BH01_'+branch+'_*; export_split.py bakes this rig only. Switch Scene for the other POV.'
    manifest['branches'][branch]={'scene':sc.name,'rig':rig.name,'body':body.name,'camera':cam.name,'actions':actions}

assert legacy=={n:fingerprint(bpy.data.actions[n]) for n in legacy}, 'Legacy Action keys changed'
(OUT/'authoring_manifest.json').write_text(json.dumps(manifest,indent=2))
window=bpy.context.window;window.scene=bpy.data.scenes['BH01_1POV']
rig=bpy.data.objects[window.scene['split_rig']]
for obj in window.scene.objects:obj.select_set(False)
rig.hide_set(False);rig.select_set(True);window.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE')
# Scene selector is the persistent, safe branch switch; both scenes have their
# own rig, active Action, camera and visibility, without workspace handlers.
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.overlay.show_overlays=True
        area.spaces.active.shading.type='MATERIAL'
    elif area.type in {'DOPESHEET_EDITOR','TIMELINE'}:
        area.type='DOPESHEET_EDITOR';area.ui_type='DOPESHEET';area.spaces.active.mode='ACTION'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend'))
print('SPLIT_AUTHORING_READY',json.dumps(manifest['branches']))
