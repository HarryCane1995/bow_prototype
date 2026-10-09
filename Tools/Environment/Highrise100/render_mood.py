"""Bounded atmospheric volume: an infinite World volume extinguishes the sun."""
import bpy,sys,json,math
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(Path(__file__).parent));from build_library import render,aim
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100.blend'))
data=json.loads((OUT/'manifest.json').read_text());byid={r['id']:r for r in data['buildings']}
scene=bpy.data.scenes['Atmosphere_Review'];cam=scene.camera;inst=bpy.data.objects['MOOD_INSTANCE']
world=scene.world
for link in list(world.node_tree.links):
    if link.to_node.type=='OUTPUT_WORLD' and link.to_socket.name=='Volume':world.node_tree.links.remove(link)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
scene.view_settings.exposure=.30
fog=bpy.data.objects.get('BoundedAtmosphere')
if fog is None:
    verts=[(x,y,z) for z in (-5,820) for y in (-1700,1600) for x in (-1500,1500)]
    mesh=bpy.data.meshes.new('AtmosphereVolume');mesh.from_pydata(verts,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
    fog=bpy.data.objects.new('BoundedAtmosphere',mesh);scene.collection.objects.link(fog)
    mat=bpy.data.materials.new('Atmospheric_Haze');mat.use_nodes=True;mat.node_tree.nodes.clear()
    volume=mat.node_tree.nodes.new('ShaderNodeVolumePrincipled');volume.inputs['Density'].default_value=.00038;volume.inputs['Color'].default_value=(.52,.61,.69,1);volume.inputs['Anisotropy'].default_value=.25
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(volume.outputs['Volume'],output.inputs['Volume']);mesh.materials.append(mat)
for name in ('DuskSun','DuskFill'):
    bpy.data.objects[name].data.energy=2.2 if name=='DuskSun' else .9
bpy.data.objects['DuskSun'].data.color=(1,.69,.4)
bpy.data.objects['DuskSun'].rotation_euler=[math.radians(v) for v in (65,-20,-35)]
fog.data.materials[0].node_tree.nodes.get('Principled Volume').inputs['Density'].default_value=.000075
city=[o for o in scene.objects if o.name.startswith('Skyline_')]
for o in city:o.hide_render=True
scene.render.resolution_x=640;scene.render.resolution_y=800;cam.data.type='ORTHO'
for id in data['curated_best']:
    r=byid[id];render(scene,cam,inst,SimpleNamespace(col=bpy.data.collections[r['collection']]),r,15,'_mood')
inst.instance_collection=None
for o in city:o.hide_render=False
cam.data.type='PERSP';cam.data.lens=46;cam.location=(1120,-1370,720);aim(cam,(0,350,190))
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.filepath=str(OUT/'Mood/Skyline.png');bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
bpy.context.window.scene=bpy.data.scenes['Library_100'];bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highrise100.blend'),compress=True)
print('BOUNDED_MOOD_COMPLETE')
