"""API-only technical contact sheet; all temporary render objects are removed."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'Docs/Reviews/LocalProxyV05'
manifest=json.loads((REPORT/'library_manifest.json').read_text())
families=['LANDING','PLATFORM','WALL','RAMP','BRIDGE','SPEED','VERTICAL']
colors=[(.49,.64,.73,1),(.37,.68,.60,1),(.35,.49,.70,1),(.77,.48,.25,1),(.58,.46,.72,1),(.72,.66,.34,1),(.57,.68,.50,1)]
scene=bpy.data.scenes.new('_V05_CONTACT_SHEET');created=[];data_to_remove=[]
try:
    for row in manifest:
        fi=families.index(row['family']);i=row['id']%6;x=i*29;y=(6-fi)*27
        obj=bpy.data.objects.new('_V05_RENDER_'+row['name'],bpy.data.objects[row['object']].data);scene.collection.objects.link(obj);obj.location=(x,y,0);obj.color=colors[fi];created.append(obj)
        text=bpy.data.curves.new('_V05_RENDER_LABEL','FONT');text.body=f"{row['id']:02d} {row['name']}";text.size=1.28;text.align_x='CENTER';text.extrude=0
        label=bpy.data.objects.new('_V05_RENDER_LABEL',text);scene.collection.objects.link(label);label.location=(x,y-10,.02);label.color=(.05,.07,.09,1);created.append(label);data_to_remove.append(text)
    camdata=bpy.data.cameras.new('_V05_RENDER_CAMERA');cam=bpy.data.objects.new('_V05_RENDER_CAMERA',camdata);scene.collection.objects.link(cam);created.append(cam);data_to_remove.append(camdata)
    target=Vector((72.5,78,0));cam.location=(72.5,-100,265);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=190;scene.camera=cam
    world=bpy.data.worlds.new('_V05_RENDER_WORLD');world.color=(.83,.86,.89);scene.world=world
    scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=2500;scene.render.resolution_y=2300;scene.render.resolution_percentage=100
    sh=scene.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';sh.show_specular_highlight=False
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(REPORT/'V05_LIBRARY_OVERVIEW.png');scene.render.film_transparent=False
    bpy.ops.render.render(scene=scene.name,write_still=True)
    print('LIBRARY_RENDER',scene.render.filepath)
finally:
    for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(scene)
    for data in data_to_remove:
        if not data.users:
            if isinstance(data,bpy.types.Camera):bpy.data.cameras.remove(data)
            else:bpy.data.curves.remove(data)
    if 'world' in locals() and not world.users:bpy.data.worlds.remove(world)
