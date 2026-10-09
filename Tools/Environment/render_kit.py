"""Blender-only silhouette review of all ten archetypes; source is never saved."""
import bpy,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'Art/Environment/Skyscrapers'
bpy.ops.wm.open_mainfile(filepath=str(ART/'Skyscraper_Kit.blend'))
sc=bpy.context.scene;sc.render.engine='BLENDER_EEVEE';sc.eevee.taa_render_samples=24
sc.render.resolution_x=500;sc.render.resolution_y=640;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.20,.23,1)
sc.world.node_tree.nodes['Background'].inputs[1].default_value=.5
sc.view_settings.view_transform='AgX'
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,energy,size in [((-140,-150,320),1400000,250),((170,50,270),1700000,170)]:
    d=bpy.data.lights.new('Review area','AREA');d.energy=energy;d.size=size
    o=bpy.data.objects.new('Review area',d);sc.collection.objects.link(o);o.location=loc;aim(o,(0,0,110))
camera_data=bpy.data.cameras.new('Kit review');camera=bpy.data.objects.new('Kit review',camera_data);sc.collection.objects.link(camera)
camera.location=(260,-520,340);aim(camera,(0,0,205));camera_data.type='ORTHO';camera_data.ortho_scale=452;camera_data.clip_end=2000;sc.camera=camera
roots=sorted([o for o in sc.objects if o.type=='EMPTY'],key=lambda o:o.name)
for root in roots:
    root.location=(0,0,0);root.rotation_euler=(0,0,0)
    for other in roots:
        for child in other.children:child.hide_render=(other!=root or child.name.endswith('-colonly'))
    sc.render.filepath=str(ART/'Review'/('kit_'+root.name+'.png'))
    bpy.ops.render.render(write_still=True)
print('KIT_REVIEW_COMPLETE',len(roots))
