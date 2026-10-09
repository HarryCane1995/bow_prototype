"""One-time additive demo setup, never a runtime layout builder."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Euler
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/ProxyChunksV04'
sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent/'LevelBlockout'))
from generator import build,NAME
from metrics import load_metrics
assert bpy.context.mode=='OBJECT' and Path(bpy.data.filepath)==ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
assert NAME not in bpy.data.node_groups and (REPORT/'before.json').exists()
metrics=load_metrics();M=metrics['values']
collection=bpy.data.collections.new('V04_PROXY_CHUNKS');bpy.context.scene.collection.children.link(collection)
internal=bpy.data.collections.new('V04_INTERNAL');bpy.context.scene.collection.children.link(internal);internal.hide_viewport=True;internal.hide_render=True
wedge=bpy.data.objects.new('V04_UNIT_WEDGE',bpy.data.objects['V02_INTERNAL_UNIT_RAMP'].data.copy());internal.objects.link(wedge);wedge.hide_render=True;wedge.hide_select=True
group=build(M,wedge)
def proxy(name,width,length,height,position,angle,kind,seed):
    verts=[(x,y,z) for z in [-.7,height-.7] for y in [0,length] for x in [-width/2,width/2]]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    mesh=bpy.data.meshes.new(name+'_SOURCE');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj.location=position;obj.rotation_euler.z=math.radians(angle)
    mod=obj.modifiers.new(NAME,'NODES');mod.node_group=group;mod.show_in_editmode=True;mod.show_on_cage=False
    for s in group.interface.items_tree:
        if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry':mod[s.identifier]=s.default_value
    ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    mod[ids['Chunk Type']]=kind;mod[ids['Seed']]=seed
    obj['authoring']='Manual mesh bounds; +Y entry to exit; Shift+D duplicates independent source and controls.'
    return obj
rise=M['wall_jump_rise']*(.4+.6*.35)
specs=[
 ('PROXY_00_START',16,16,2.8,(0,-8,0),0,0,1),
 ('PROXY_01_WALLRUN',12,42,12,(0,8,0),0,1,17),
 ('PROXY_02_ARENA',34,32,12,(0,50,0),0,3,41),
 ('PROXY_03_VERTICAL',12,44,16,(26,58,0),-90,5,23),
 ('PROXY_04_MIXED',18,44,12,(70,48,rise),180,6,109),
 ('PROXY_05_DESCENT',16,62,20,(-38,56,0),180,4,73),
 ('PROXY_06_SLIDE',12,42,8,(-38,-6,0),-90,2,29),
 ('PROXY_07_GRAPPLE',22,72,18,(24,-38,0),-70,7,37),
]
objects=[proxy(*s) for s in specs]
bpy.data.collections['V03_FLOW_COURSE'].hide_viewport=True
for name in ['LEVEL_VOLUME','LEVEL_CUTTER']:bpy.data.objects[name].hide_set(True)
for o in bpy.context.selected_objects:o.select_set(False)
objects[1].select_set(True);bpy.context.view_layer.objects.active=objects[1]
text=bpy.data.texts.new('V04_PROXY_QUICKSTART');text.write('V04 PROXY CHUNKS\n\nSelect a PROXY_* object: each has its own modifier and Seed.\nTab: edit its ordinary source mesh. Bounds in local axes drive this chunk.\nG / R / S: place and rotate the chunk; local +Y is entry -> exit.\nShift+D: independent source copy + independent modifier controls.\n\nNo LEVEL_VOLUME dependency. No whole-level layout generator.\nChunk Type: 0 Auto / 1 Wallrun / 2 Slide / 3 Arena / 4 Descent\n5 Vertical / 6 Mixed / 7 Grapple. Bias sliders select types in Auto.\n\nThis first pass uses an oriented prism, not concave mesh interior.\nSteepness 35-45 grounded; 55-70 airborne drop + recovery.\nDirection/anchor guides are excluded from export.\n\nDocs/PROXY_CHUNKS_V04.md\n')
for area in bpy.context.screen.areas:
    s=area.spaces.active
    if area.type=='PROPERTIES':s.use_pin_id=False;s.pin_id=None;s.context='MODIFIER'
    elif area.type=='TEXT_EDITOR':s.text=text;s.top=0;text.cursor_set(0)
    elif area.type=='VIEW_3D':
        s.overlay.show_overlays=True;s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.show_cavity=True;s.shading.cavity_type='BOTH'
        s.region_3d.view_distance=225;s.region_3d.view_location=(25,22,6);s.region_3d.view_rotation=Euler((math.radians(52),0,math.radians(-25))).to_quaternion();s.region_3d.update()
    area.tag_redraw()
bpy.context.workspace.name='PROXY_CHUNKS_V04';bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,check_existing=False)
print('V04_BUILT',len(group.nodes),'native nodes',len(objects),'independent proxies')
