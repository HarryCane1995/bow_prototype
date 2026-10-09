"""Clay comparison renders for selecting proportions. No export or integration."""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from hero_geometry import bv
OUT=ROOT/'Art/Characters/Hero_Silhouette'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Hero_Silhouette_ABC.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=700;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.1,.115,.13,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.35
sc.view_settings.view_transform='AgX'
def aim(o,target):o.rotation_euler=(bv(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,color,size in [('Key',(-3,4,-4),450,(.93,.95,1),4),('Fill',(3,2,-1),190,(1,1,1),3),('Rim',(0,3,3),420,(.88,.92,1),3)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=bv(loc);aim(o,(0,1,0))
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object
m=bpy.data.materials.new('ReviewFloor');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.024,.029,.036,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9;floor.data.materials.append(m)
d=bpy.data.cameras.new('StudyCamera');cam=bpy.data.objects.new('StudyCamera',d);sc.collection.objects.link(cam);sc.camera=cam;d.type='ORTHO';d.ortho_scale=2.35
views=[('front',0),('quarter',-35),('side',-90),('back',180)]
variants=['A_Concept','B_Powerful','C_AnimeLean']
if '--quick' in sys.argv:views=[('front',0),('quarter',-35)];variants=['A_Concept']
for variant in variants:
 for o in sc.objects:
  if o.type=='MESH' and o.data.shape_keys:
   for key in o.data.shape_keys.key_blocks:
    if key.name!='Basis':key.value=1 if key.name==variant else 0
 for view,angle in views:
  a=math.radians(angle);cam.location=bv((math.sin(a)*4,1.07,-math.cos(a)*4));aim(cam,(0,1.07,0))
  sc.render.filepath=str(OUT/'Review'/(variant+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('SILHOUETTE_REVIEW_DONE')
