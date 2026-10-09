"""True second angles, common-scale elevations and an atmospheric composition.
All imagery is rendered from the saved procedural meshes. No generated-image textures.
"""
import bpy,json,math,sys
from pathlib import Path
from types import SimpleNamespace
from mathutils import Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(HERE));from build_library import render,aim
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100.blend'))
data=json.loads((OUT/'manifest.json').read_text());records=data['buildings'];byid={r['id']:r for r in records}
best=['HR007','HR012','HR026','HR037','HR047','HR055','HR060','HR064','HR070','HR073','HR089','HR099']
preview=bpy.data.scenes['Neutral_Preview'];cam=preview.camera;inst=bpy.data.objects['PREVIEW_INSTANCE']
for r in records:r['previews']=[f"Previews/{r['id']}.png"]
second=sorted(set(best+[f'HR{i:03}' for i in range(3,101,5)]+['HR056','HR059']))
for id in second:
    r=byid[id];t=SimpleNamespace(col=bpy.data.collections[r['collection']]);render(preview,cam,inst,t,r,145,'_rear')
    r['previews'].append(f'Previews/{id}_rear.png')
# Fixed camera scale for all 100; temp tiles are explicitly disposable and later composited.
temp=OUT/'QA/CommonScaleTiles';temp.mkdir(exist_ok=True)
preview.render.resolution_x=200;preview.render.resolution_y=260;cam.data.ortho_scale=600
cam.location=(0,-1600,300);aim(cam,(0,0,300))
for r in records:
    inst.instance_collection=bpy.data.collections[r['collection']];preview.render.filepath=str(temp/(r['id']+'.png'))
    bpy.context.window.scene=preview;bpy.ops.render.render(write_still=True)
# A separate world makes mood frames reproducible without changing neutral lighting.
mood=bpy.data.scenes.new('Atmosphere_Review');mood.render.engine='BLENDER_EEVEE';mood.eevee.taa_render_samples=32
mood.render.resolution_x=640;mood.render.resolution_y=800;mood.render.resolution_percentage=100;mood.render.image_settings.file_format='PNG'
mood.view_settings.view_transform='AgX';mood.view_settings.look='AgX - Medium High Contrast';mood.view_settings.exposure=.6
world=bpy.data.worlds.new('BOW_Dusk_Clouds');world.use_nodes=True;mood.world=world;n=world.node_tree.nodes;l=world.node_tree.links
bg=n['Background'];bg.inputs['Strength'].default_value=.35
tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5;noise.inputs['Detail'].default_value=4
l.new(tex.outputs['Normal'],noise.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.28;ramp.color_ramp.elements[0].color=(.018,.03,.047,1);ramp.color_ramp.elements[1].position=.72;ramp.color_ramp.elements[1].color=(.36,.29,.19,1)
l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bg.inputs['Color'])
vol=n.new('ShaderNodeVolumePrincipled');vol.inputs['Density'].default_value=.00025;vol.inputs['Color'].default_value=(.38,.47,.52,1);vol.inputs['Anisotropy'].default_value=.25
l.new(vol.outputs['Volume'],n['World Output'].inputs['Volume'])
for name,energy,color,rotation in [('DuskSun',2.8,(1,.52,.18),(78,-10,-115)),('DuskFill',.65,(.25,.53,1),(40,0,40))]:
    ld=bpy.data.lights.new(name,'SUN');ld.energy=energy;ld.color=color;ld.angle=.15
    o=bpy.data.objects.new(name,ld);mood.collection.objects.link(o);o.rotation_euler=[math.radians(a) for a in rotation]
mc=bpy.data.objects.new('Mood_Camera',bpy.data.cameras.new('Mood_Camera'));mc.data.type='ORTHO';mc.data.clip_end=6000;mood.collection.objects.link(mc);mood.camera=mc
mi=bpy.data.objects.new('MOOD_INSTANCE',None);mi.instance_type='COLLECTION';mood.collection.objects.link(mi)
mood.collection.objects.link(bpy.data.objects['Ground'])
for id in best:
    r=byid[id];t=SimpleNamespace(col=bpy.data.collections[r['collection']]);render(mood,mc,mi,t,r,15,'_mood');r['previews'].append(f'Previews/{id}_mood.png')
# Actual 3D skyline: 12 selected foreground masses and restrained lower-cost background.
mi.instance_collection=None
for j,id in enumerate(best):
    r=byid[id];o=bpy.data.objects.new('Skyline_'+id,None);o.instance_type='COLLECTION';o.instance_collection=bpy.data.collections[r['collection']]
    o.location=((j%6-2.5)*150,(j//6)*260,0);mood.collection.objects.link(o)
background=[r for r in records if r['role']=='background']
for j,r in enumerate(background):
    o=bpy.data.objects.new('Skyline_BG_'+r['id'],None);o.instance_type='COLLECTION';o.instance_collection=bpy.data.collections[r['collection']]
    o.location=((j%10-4.5)*135,580+(j//10)*200,0);mood.collection.objects.link(o)
mc.data.type='PERSP';mc.data.lens=46;mc.location=(1120,-1370,720);aim(mc,(0,350,190))
mood.render.resolution_x=1920;mood.render.resolution_y=1080
(OUT/'Mood').mkdir(exist_ok=True);mood.render.filepath=str(OUT/'Mood/Skyline.png');bpy.context.window.scene=mood;bpy.ops.render.render(write_still=True)
data['curated_best']=best;data['preview_notes']=dict(neutral='Fit-to-frame, individual scale',common_scale='100 front elevations; fixed orthographic vertical extent 600m',mood='Procedural world clouds and volume, rendered from the same source geometry; presentation only')
(OUT/'manifest.json').write_text(json.dumps(data,indent=2))
for r in records:bpy.data.objects[r['id']]['record_json']=json.dumps(r)
bpy.context.window.scene=bpy.data.scenes['Library_100'];bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highrise100.blend'),compress=True)
print('ADDITIONAL_PREVIEWS',len(second),len(best),'COMMON_SCALE',100)
