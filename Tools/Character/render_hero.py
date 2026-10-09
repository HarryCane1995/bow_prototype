"""Studio review only. Creates no persistent scene objects in the source asset."""
import bpy,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from hero_geometry import bv
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/Models/Characters/Hero/Hero_Kaze.blend'))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=850;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.080,.10,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.45
sc.view_settings.view_transform='AgX'
def aim(o,target):o.rotation_euler=(bv(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,color,size in [('Key',(-3,4,-4),650,(1,.82,.65),4),('Fill',(3,2,-1),420,(.57,.72,1),3),('Rim',(0,3,3),850,(1,.55,.25),2.5)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=bv(loc);aim(o,(0,1,0))
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='ReviewFloor'
m=bpy.data.materials.new('ReviewFloor');m.diffuse_color=(.027,.033,.04,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.027,.033,.04,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.88;floor.data.materials.append(m)
d=bpy.data.cameras.new('ReviewCamera');o=bpy.data.objects.new('ReviewCamera',d);sc.collection.objects.link(o);sc.camera=o;d.type='ORTHO';d.ortho_scale=2.35
out=ROOT/'.godot/hero-pass';out.mkdir(exist_ok=True)
views=[('front',0),('quarter',-38),('side',-90),('back',180)]
if '--quick' in sys.argv:views=[('milestone-a',-30)]
if '--turntable' in sys.argv:
 views=[('turn_%03d'%i,i*360/48) for i in range(48)];sc.render.resolution_x=640;sc.render.resolution_y=800;sc.cycles.samples=12
for name,angle in views:
 a=math.radians(angle);o.location=bv((math.sin(a)*4,1.38,-math.cos(a)*4));aim(o,(0,1.02,0));sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
print('HERO_RENDER_DONE')
