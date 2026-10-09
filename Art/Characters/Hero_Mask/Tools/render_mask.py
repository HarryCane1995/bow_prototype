"""Reproducible studio photographs of the editable mask. Never saves studio into source."""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from mask_surfaces import material
OUT=HERE.parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Hero_Mask_Visual.blend'))
sc=bpy.context.scene;stage=sc['visual_pass_stage'];sc.render.engine='CYCLES';sc.cycles.samples=48;sc.cycles.use_denoising=True
sc.render.resolution_x=950;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.10,.12,.16,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.30
sc.view_settings.view_transform='AgX'
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,color,size in [('Large key',(-.40,-.45,.64),38,(.86,.92,1),.48),('Warm rim',(.43,.30,.38),45,(1,.64,.35),.34),('Front fill',(.32,-.48,.15),12,(.67,.78,1),.42),('Crown strip',(-.20,.28,.54),35,(1,1,1),.25)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=loc;aim(o,(0,0,.16))
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.location.z=-.038;floor.data.materials.append(material('Review backdrop','15191E',0,.86))
d=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',d);sc.collection.objects.link(cam);sc.camera=cam;d.type='ORTHO';d.ortho_scale=.41;d.lens=70
views=[('hero',(.48,-.72,.35),(0,-.005,.155),.405),('front',(0,-1,.153),(0,0,.153),.405),('side',(.8,0,.16),(0,-.005,.15),.405),('back',(0,.9,.21),(0,.015,.15),.405)]
if '--quick' in sys.argv:
 views=[views[0],views[1],views[2]];sc.render.resolution_x=760;sc.render.resolution_y=900;sc.cycles.samples=24
if '--details' in sys.argv:
 views=[('visor_close',(.34,-.72,.21),(.034,-.10,.14),.175),('vent_close',(.7,-.12,.255),(.078,.022,.176),.187),('underside',(.28,.65,-.17),(0,.018,.102),.245)]
if '--turntable' in sys.argv:
 views=[];sc.render.resolution_x=640;sc.render.resolution_y=720;sc.cycles.samples=16
 for i in range(60):
  a=math.tau*i/60;views.append(('turn_%03d'%i,(math.sin(a)*.9,-math.cos(a)*.9,.29),(0,0,.15),.43))
clay='--clay' in sys.argv
if clay:
 mat=material('Clay review','7A7C7E',0,.66);bpy.context.view_layer.material_override=mat
for name,loc,target,scale in views:
 cam.location=loc;aim(cam,target);d.ortho_scale=scale
 prefix='clay_' if clay else 'material_'
 if '--quick' in sys.argv:prefix='stage%d_'%stage+prefix
 if '--turntable' in sys.argv:prefix=''
 sc.render.filepath=str(OUT/'Review'/(prefix+name+'.png'));bpy.ops.render.render(write_still=True)
print('MASK_REVIEW_DONE',stage)
