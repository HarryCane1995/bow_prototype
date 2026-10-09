"""Render reference cameras in a disposable PoseLab copy; never save the source."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
data=json.loads((ROOT/'.godot/humanoid-base/v2_source_capture.json').read_text())
bpy.ops.wm.open_mainfile(filepath=data['source_snapshot'])
s=bpy.context.scene;rig=bpy.data.objects['Male_Rig'];body=bpy.data.objects['Male_Body']
out=ROOT/'.godot/humanoid-base/v2-camera';out.mkdir(exist_ok=True)
# Workbench is a composition check with the actual source mesh and reference bow.
s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
s.display.shading.light='STUDIO';s.display.shading.color_type='SINGLE'
s.display.shading.single_color=(0.8,0.8,0.8)
s.display.shading.background_type='WORLD';s.world.color=(0.04,0.04,0.04)
s.display.shading.show_shadows=False;s.display.shading.show_cavity=True
allowed={'Male_Body','POSE_CyberBow','POSE_String','POSE_Arrow'}
print('REFERENCE_MESHES',[(o.name,o.hide_render) for o in s.objects if o.type=='MESH' and ('Bow' in o.name or 'Arrow' in o.name or 'String' in o.name)])
for o in s.objects:
    if o.type in {'MESH','CURVE','FONT'} and o.name not in allowed:o.hide_render=True
body.hide_render=False
for pose in ['BH01_IDLE','BH01_SLIDE']:
    rig.animation_data.action=bpy.data.actions[pose];s.frame_set(1);bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    error=max((ev.matrix_world@v.co-Vector(co)).length for v,co in zip(mesh.vertices,data['poses'][pose]['surface']))
    ev.to_mesh_clear();assert error<0.0001,(pose,error)
    for name in ['CAM_FP_WORLD','CAM_FP_VIEWMODEL']:
        s.camera=bpy.data.objects[name]
        s.render.filepath=str(out/f'blender_{pose}_{name}.png')
        bpy.ops.render.render(write_still=True)
print('V2_BLENDER_CAMERA_REFERENCES_PASS')
