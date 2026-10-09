"""Editable FPS blocking rig; metre units in the existing 65-degree viewmodel camera.

Run Blender --background --factory-startup --python Tools/Blender/build_player_hands.py.
Creates only Assets/Models/Player/FP_Hands_Blocking.blend. Existing bow sources stay
untouched. Godot adds string/arrow response and poses these simple weighted bones.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

REPO=Path(__file__).resolve().parents[2]
OUT=REPO/'Assets/Models/Player/FP_Hands_Blocking.blend'
OUT.parent.mkdir(parents=True,exist_ok=True)
if OUT.exists() and '--rebuild' not in sys.argv:
    raise RuntimeError('Source already exists. Edit it in Blender, or explicitly pass -- --rebuild to replace the generated blocking.')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.name='FP_Hands_Blocking'
scene.unit_settings.system='METRIC'

def bv(p): return Vector((p[0],-p[2],p[1]))
def mat(name,color,metal=0.0,emission=False):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=.78;bs.inputs['Metallic'].default_value=metal
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=.35
    return m
mats=[mat('Hands_Glove',(.065,.084,.092)),mat('Hands_Plates',(.29,.34,.36),.25),mat('Hands_Joints',(.035,.045,.05)),mat('Hands_Cyan',(.06,.55,.61),.1,True),mat('Hands_RedTrim',(.24,.065,.04),.25)]

points={
 'Upper.L':((-.42,-.68,-.10),(-.42,-.56,-.40)),
 'Forearm.L':((-.42,-.56,-.40),(-.085,-.395,-.82)),
 'Hand.L':((-.085,-.395,-.82),(.018,-.295,-.84)),
 'Fingers.L':((.018,-.295,-.84),(.048,-.355,-.885)),
 'Thumb.L':((-.028,-.365,-.88),(.022,-.31,-.925)),
 'Upper.R':((.43,-.66,-.10),(.45,-.45,-.25)),
 'Forearm.R':((.45,-.45,-.25),(.14,-.285,-.50)),
 'Hand.R':((.14,-.285,-.50),(.063,-.23,-.555)),
 'Fingers.R':((.063,-.23,-.555),(.013,-.247,-.605)),
 'Thumb.R':((.095,-.272,-.55),(.029,-.26,-.59)),
}
armdata=bpy.data.armatures.new('FP_Hands_Rig')
rig=bpy.data.objects.new('HandsRig',armdata);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root=armdata.edit_bones.new('Root');root.head=(0,0,-.8);root.tail=(0,0,-.7)
for name,(a,b) in points.items():
    bone=armdata.edit_bones.new(name);bone.head=bv(a);bone.tail=bv(b)
    role,side=name.split('.')
    parent={'Upper':'Root','Forearm':'Upper.'+side,'Hand':'Forearm.'+side,'Fingers':'Hand.'+side,'Thumb':'Hand.'+side}[role]
    bone.parent=armdata.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front=True

vertices=[];faces=[];indices=[];weights=[];heavy=[]
def segment(a,b,ra,rb,material,bone,depth=1):
    a=Vector(a);b=Vector(b);axis=(b-a).normalized()
    ref=Vector((0,1,0)) if abs(axis.y)<.9 else Vector((1,0,0))
    u=axis.cross(ref).normalized();v=axis.cross(u).normalized();start=len(vertices)
    rings=[(0,ra*.82),(.1,ra),(.83,rb),(1,rb*.83)]
    for t,r in rings:
        center=a.lerp(b,t)
        for i in range(8):
            angle=(i+.5)*math.tau/8
            offset=u*(math.cos(angle)*r)+v*(math.sin(angle)*r*depth)
            vertices.append(bv(center+offset));heavy.append(bv(center+offset*1.22));weights.append(bone)
    faces.append(tuple(start+i for i in reversed(range(8))));indices.append(material)
    for ring in range(3):
        for i in range(8):
            j=(i+1)%8;faces.append((start+ring*8+i,start+ring*8+j,start+(ring+1)*8+j,start+(ring+1)*8+i));indices.append(material)
    faces.append(tuple(start+24+i for i in range(8)));indices.append(material)

for side in ['L','R']:
    upper=points['Upper.'+side];fore=points['Forearm.'+side];hand=points['Hand.'+side]
    segment(*upper,.075,.060,0,'Upper.'+side)
    segment(Vector(upper[1]).lerp(Vector(fore[1]),.015),Vector(upper[1]).lerp(Vector(fore[1]),.14),.068,.071,2,'Forearm.'+side)
    segment(Vector(fore[0]).lerp(Vector(fore[1]),.10),Vector(fore[0]).lerp(Vector(fore[1]),.81),.072,.049,1,'Forearm.'+side,.78)
    segment(Vector(fore[0]).lerp(Vector(fore[1]),.79),Vector(fore[0]).lerp(Vector(fore[1]),.90),.051,.047,4,'Forearm.'+side,.85)
    segment(Vector(fore[0]).lerp(Vector(fore[1]),.90),Vector(fore[1]),.043,.041,2,'Forearm.'+side)
    # Small single stripe, not a luminous sleeve.
    segment(Vector(fore[0]).lerp(Vector(fore[1]),.72),Vector(fore[0]).lerp(Vector(fore[1]),.745),.054,.053,3,'Forearm.'+side,.79)
    segment(*hand,.047,.050,0,'Hand.'+side,.60)
    segment(Vector(hand[0]).lerp(Vector(hand[1]),.25)+Vector((0,.012,.012)),Vector(hand[0]).lerp(Vector(hand[1]),.78)+Vector((0,.012,.012)),.039,.042,1,'Hand.'+side,.40)
    f0,f1=map(Vector,points['Fingers.'+side]);middle=f0.lerp(f1,.5)+Vector((.012,.005,.012))
    segment(f0,middle,.034,.032,0,'Fingers.'+side,.55)
    segment(middle,f1,.032,.028,0,'Fingers.'+side,.55)
    segment(*points['Thumb.'+side],.019,.017,0,'Thumb.'+side)

mesh=bpy.data.meshes.new('Hands_Blocking_Mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for polygon in mesh.polygons:
    axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(polygon.normal[i]))]
    for li in polygon.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co
        uv.data[li].uv=(co[axes[0]],co[axes[1]])
obj=bpy.data.objects.new('Hands_Blocking',mesh);scene.collection.objects.link(obj)
for m in mats:mesh.materials.append(m)
for p,mi in zip(mesh.polygons,indices):p.material_index=mi
for name in points:
    group=obj.vertex_groups.new(name=name);group.add([i for i,w in enumerate(weights) if w==name],1,'REPLACE')
obj.parent=rig
mod=obj.modifiers.new('Armature','ARMATURE');mod.object=rig
obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Heavy')
for v,co in zip(key.data,heavy):v.co=co
key.value=0
obj['blocking_variants']='A: slim functional (Heavy=0); B: heavy mechanical (Heavy=1)'
rig['runtime_pose_owner']='FirstPersonHands.cs: visual-only two-bone solve and wrist targets; no player physics.'

# Authoring guides are empties, so they add no rendered/collision geometry.
for name,p in [('BowGrip_Guide',(-.005,-.326,-.847)),('NockIdle_Guide',(.025,-.22,-.58)),('NockDraw_Guide',(.115,-.10,-.38))]:
    guide=bpy.data.objects.new(name,None);scene.collection.objects.link(guide);guide.location=bv(p);guide.empty_display_type='PLAIN_AXES';guide.empty_display_size=.05
readme=bpy.data.texts.new('README_HANDS')
readme.write('FPS HANDS / BLOCKING PASS\nMetres, Blender Z-up. Godot viewmodel camera is origin, looking -Z after import.\n11 bones: Root + upper/forearm/hand/fingers/thumb for each arm. Rigid skin weights are intentional mechanical blocking.\nHeavy shape key compares two thicknesses. Slim is the selected first pass.\nExisting CyberBow source is BlenderAssets/Bow_Assembly.blend; it is not rewritten here. Runtime string and pose targets live in Scenes/ViewModel/FirstPersonHands.tscn.\nUse the three guide empties to adjust grip/nock. No torso and no finger anatomy polish.\n')
for o in bpy.context.selected_objects:o.select_set(False)
rig.select_set(True);obj.select_set(True);bpy.context.view_layer.objects.active=rig
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=1.6
            area.spaces.active.region_3d.view_location=(0,.5,-.35)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('HANDS_SOURCE_SAVED',len(vertices),'vertices',len(faces),'faces',len(points)+1,'bones')
