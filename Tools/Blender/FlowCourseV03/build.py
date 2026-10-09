"""Additive V03 setup. Old generators and all user-authored mesh topology remain intact."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Euler
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent/'LevelBlockout'))
from grammar import FlowGraph,segment_group,KINDS,COLORS
from metrics import load_metrics
SOURCE=ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
REPORT=ROOT/'Docs/Reviews/FlowCourseV03'
assert Path(bpy.data.filepath)==SOURCE and bpy.context.mode=='OBJECT'
assert 'GN_LevelBlockout_Generator_v03' not in bpy.data.node_groups
assert (REPORT/'before.json').exists()
movement=load_metrics();M=movement['values'];(REPORT/'movement_metrics.json').write_text(json.dumps(movement,indent=2))
volume=bpy.data.objects['LEVEL_VOLUME'];cutter=bpy.data.objects['LEVEL_CUTTER'];wedge=bpy.data.objects['V02_INTERNAL_UNIT_RAMP']
collection=bpy.data.collections.new('V03_FLOW_COURSE');bpy.context.scene.collection.children.link(collection)
out=bpy.data.objects.new('LEVEL_FLOW_OUTPUT',bpy.data.meshes.new('V03_EmptyModifierHost'));collection.objects.link(out)
out.hide_select=True;out.lock_location=out.lock_rotation=out.lock_scale=(True,True,True)
bpy.data.collections['V02_OUTPUT'].hide_viewport=True
for name in ('GN_LevelAuthoring_POC','GN_LevelBlockout_Generator_v01','GN_LevelBlockout_Generator_v02'):bpy.data.node_groups[name].use_fake_user=True
segment=segment_group(M,wedge)
g=FlowGraph('GN_LevelBlockout_Generator_v03')
seed=g.input('Seed','NodeSocketInt',17,0,1000000,'Changes route handedness, bend spacing, wall angles and section details.')
style=g.input('Layout Mode','NodeSocketInt',0,0,3,'0 BALANCED; 1 VERTICAL; 2 SPEED; 3 ARENA MIX')
vertical=g.input('Verticality',value=.78,low=0,high=1)
density=g.input('Density',value=.7,low=0,high=1)
openness=g.input('Openness',value=.4,low=0,high=1)
complexity=g.input('Route Complexity',value=.7,low=0,high=1)
difficulty=g.input('Traversal Difficulty',value=.4,low=0,high=1)
grapple=g.input('Grapple Presence',value=.7,low=0,high=1)
jitter=g.input('Wall Angle Jitter',value=14,low=0,high=30,description='Maximum local wall yaw in degrees; route heading stays coherent.')
angle=g.input('Steep Angle',value=45,low=35,high=70,description='35-45: tested grounded descent. 55-70: airborne drop chute with recovery, not continuous grounded slide.')
safe=g.input('Spawn Safe Radius',value=8,low=3,high=12)
use=g.input('Use Cutter','NodeSocketBool',False,description='Enable intentional subtraction. Off initially because the shared V02 cutter can sever this new route.')
quality=g.input('Preview Quality','NodeSocketInt',0,0,1)
preview=g.input('Section Preview','NodeSocketInt',0,0,15,'0 full route; 1-15 isolate that section. Stored flow_section IDs are 0-14.')
colors=g.input('Section Colors','NodeSocketBool',True)
guide=g.input('Flow Guide','NodeSocketBool',True,description='Thin cyan progression guide; omitted from game and chunk exports.')
volsocket=g.input('Volume Object','NodeSocketObject',volume);cutsocket=g.input('Cutter Object','NodeSocketObject',cutter)
read=g.object(None);g.set(read,'Object',volsocket)
bb=g.node('GeometryNodeBoundBox','Live XYZ envelope');g.set(bb,'Geometry',read.outputs['Geometry'])
lo=g.separate(bb.outputs['Min']);hi=g.separate(bb.outputs['Max'])
W=g.mul(2,g.low(g.neg(lo[0]),hi[0]));H=g.mul(2,g.low(g.neg(lo[1]),hi[1]))
floor_min=g.add(lo[2],.85);floor_max=g.sub(hi[2],8)
mirror=g.switch(g.gt(g.random(seed,0,701),.5),1,-1,'FLOAT')
rnd=lambda stream,a,b:g.random(seed,0,stream,a,b)
# A non-crossing folded lane from the origin; seed moves broad bends, not isolated pieces.
left=g.mul(g.mul(W,rnd(702,-.35,-.31)),mirror);right=g.mul(g.mul(W,rnd(703,.30,.34)),mirror)
inner=g.mul(g.mul(W,rnd(704,.115,.145)),mirror)
north=g.mul(H,rnd(705,.225,.255));south=g.mul(H,rnd(706,-.35,-.31));outer_north=g.mul(H,rnd(707,.34,.37))
points=[(0,0),(0,north),(left,g.add(north,g.mul(H,rnd(708,-.025,.025)))),(left,south),(right,south),(right,outer_north),(inner,g.add(outer_north,g.mul(H,rnd(709,-.025,.025)))),(inner,g.mul(H,-.10))]
fractions=[[0,.48,1],[0,.50,1],[0,.48,1],[0,.56,1],[0,.34,.68,1],[0,1],[0,.5,1]]
legs=[]
for i,ts in enumerate(fractions):
    a,b=points[i],points[i+1]
    for t0,t1 in zip(ts,ts[1:]):
        interp=lambda t:(g.add(a[0],g.mul(g.sub(b[0],a[0]),t)),g.add(a[1],g.mul(g.sub(b[1],a[1]),t)))
        legs.append((interp(t0),interp(t1)))
legs.append((points[-1],(inner,g.sub(points[-1][1],14))))
base_kinds=[0,1,2,8,3,7,6,5,4,2,8,3,5,9,10]
types=[];parts=[];z=0
lane=g.add(7,g.mul(openness,5))
cut=g.object(None);g.set(cut,'Object',cutsocket)
cutsize=g.node('GeometryNodeAttributeDomainSize','Empty cutter bypass',component='MESH');g.set(cutsize,'Geometry',cut.outputs['Geometry'])
cut_enabled=g.boolean('AND',use,g.gt(cutsize.outputs['Face Count'],0))
neutral=bpy.data.materials.new('M_V03_Gray');neutral.diffuse_color=(.45,.48,.50,1)
materials=[]
for name,color in zip(KINDS,COLORS):
    mat=bpy.data.materials.new('M_V03_'+name);mat.diffuse_color=(*color,1);materials.append(mat)
cyan=bpy.data.materials.new('M_V03_FLOW_GUIDE');cyan.diffuse_color=(.12,.78,.83,1)
def setmaterial(geo,material,selection=True):
    n=g.node('GeometryNodeSetMaterial');g.set(n,'Geometry',geo);g.set(n,'Material',material);g.set(n,'Selection',selection);return n.outputs[0]
for sid,((ax,ay),(bx,by)) in enumerate(legs):
    dx=g.sub(bx,ax);dy=g.sub(by,ay);L=g.vector('LENGTH',g.vec(dx,dy,0));heading=g.math('ARCTAN2',dy,dx)
    kind=base_kinds[sid]
    if sid in (4,11):kind=g.switch(g.eq(style,2),kind,11,'INT')
    if sid==5:kind=g.choose(style,[7,3,11,8],'INT')
    if sid==9:kind=g.switch(g.eq(style,3),kind,8,'INT')
    if sid==6:kind=g.switch(g.gt(grapple,.1),1,6,'INT')
    types.append(kind)
    climb=g.mul(M['wall_jump_rise'],g.add(.38,g.mul(vertical,g.choose(style,[.28,.40,.28,.24],'FLOAT'))))
    up=g.choose(kind,[0,0,0,climb,0,0,g.mul(10,g.add(.4,g.mul(vertical,.7))),g.mul(M['air_rise'],g.add(.3,g.mul(vertical,.4))),0,0,0,g.low(12,g.mul(g.sub(L,12),.35))],'FLOAT')
    # Even when slope contact is lost, an initial 40m/s carry lands inside the recovery length.
    drop_budget=g.mul(M['gravity']*.5,g.math('POWER',g.div(g.high(0,g.sub(L,18)),40),2))
    wanted_drop=g.choose(style,[14,10,20,12],'FLOAT')
    drop=g.low(wanted_drop,g.low(drop_budget,g.high(0,g.sub(z,floor_min))))
    dz=g.switch(g.eq(kind,5),up,g.neg(drop),'FLOAT')
    end_z=g.high(floor_min,g.low(floor_max,g.add(z,dz)));dz=g.sub(end_z,z)
    n=g.node('GeometryNodeGroup',f'{sid:02d} Flow section');n.node_tree=segment
    for key,value in [('Kind',kind),('Section',sid),('Seed',seed),('Length',L),('Lane Width',lane),('Height Change',dz),('Difficulty',difficulty),('Wall Jitter',jitter),('Steep Angle',angle),('Spawn Radius',safe),('Density',density),('Complexity',complexity)]:g.set(n,key,value)
    geo=g.transform(n.outputs['Geometry'],g.vec(ax,ay,z),rotation=g.vec(0,0,heading))
    if sid in (1,3,5,7,10,11):
        # A turn has a real catch surface around the junction, not just two lane tips.
        geo=g.join([geo,g.slab(g.add(lane,3),g.add(lane,3),end_z,bx,by)])
    geo=g.mesh_boolean('INTERSECT',geo,bb.outputs['Bounding Box'])
    fast=g.mesh_boolean('DIFFERENCE',geo,cut.outputs['Geometry']);exact=g.mesh_boolean('DIFFERENCE',geo,cut.outputs['Geometry'],'EXACT')
    geo=g.switch(cut_enabled,geo,g.switch(g.gt(quality,.5),fast,exact))
    if sid==0:
        pad=g.slab(g.mul(safe,2),g.mul(safe,2),0,0)
        pad=g.mesh_boolean('INTERSECT',pad,bb.outputs['Bounding Box']);geo=g.join([geo,pad])
    geo=setmaterial(geo,neutral)
    for k,mat in enumerate(materials):geo=setmaterial(geo,mat,g.boolean('AND',colors,g.eq(kind,k)))
    entry=g.vec(ax,ay,z);exit=g.vec(bx,by,end_z)
    # Native guide geometry follows the actual sequential entry/exit fields.
    line=g.node('GeometryNodeCurvePrimitiveLine','Progression guide')
    g.set(line,'Start',g.vec(ax,ay,g.add(z,.18)));g.set(line,'End',g.vec(bx,by,g.add(end_z,.18)))
    circle=g.node('GeometryNodeCurvePrimitiveCircle');g.set(circle,'Resolution',4);g.set(circle,'Radius',.09)
    tube=g.node('GeometryNodeCurveToMesh');g.set(tube,'Curve',line.outputs['Curve']);g.set(tube,'Profile Curve',circle.outputs['Curve']);g.set(tube,'Fill Caps',True)
    guide_geo=setmaterial(g.store(tube.outputs['Mesh'],'flow_role',99),cyan)
    geo=g.join([geo,g.keep(guide_geo,guide)])
    anchor=g.vec(g.add(ax,g.mul(dx,.38)),g.add(ay,g.mul(dy,.38)),g.add(z,10))
    for name,value,datatype in [('flow_section',sid,'INT'),('flow_kind',kind,'INT'),('flow_entry',entry,'FLOAT_VECTOR'),('flow_exit',exit,'FLOAT_VECTOR'),('flow_anchor',anchor,'FLOAT_VECTOR'),('flow_length',L,'FLOAT'),('flow_height_change',dz,'FLOAT'),('flow_steep_angle',angle,'FLOAT')]:geo=g.store(geo,name,value,datatype)
    selected=g.boolean('OR',g.eq(preview,0),g.eq(preview,sid+1));parts.append(g.keep(geo,selected))
    z=end_z
g.output('Geometry',g.join(parts));g.arrange();g.tree['section_types']=json.dumps(KINDS);g.tree['section_count']=15
g.tree['contract']='Sequential entry/exit flow chain, native GN, editable bounds/cutter, float geometry, guide excluded from export'
mod=out.modifiers.new(g.tree.name,'NODES');mod.node_group=g.tree
for s in g.tree.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT':mod[s.identifier]=s.default_value
for obj in bpy.context.selected_objects:obj.select_set(False)
volume.select_set(True);bpy.context.view_layer.objects.active=volume
for area in bpy.context.screen.areas:
    s=area.spaces.active
    if area.type=='VIEW_3D':
        s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.show_cavity=True;s.shading.cavity_type='BOTH'
        s.lens=50;s.region_3d.view_distance=295;s.region_3d.view_location=(0,0,9);s.region_3d.view_rotation=Euler((math.radians(48),0,math.radians(-28))).to_quaternion();s.region_3d.update()
    elif area.type=='PROPERTIES':s.pin_id=out;s.use_pin_id=True;s.context='MODIFIER'
    elif area.type=='OUTLINER':s.filter_text='';s.show_restrict_column_select=True
    elif area.type=='TEXT_EDITOR':
        t=bpy.data.texts.new('V03_FLOW_QUICKSTART');t.write('V03 FLOW COURSE | Seed + Layout Mode: 0 Balanced / 1 Vertical / 2 Speed / 3 Arena Mix\nLEVEL_VOLUME / LEVEL_CUTTER: ordinary editable meshes. Section Preview: 0 all, 1-15 isolate.\nFlow Guide is preview-only. Steep Angle 35-45 grounded descent; 55-70 airborne drop + recovery.\n');s.text=t;t.cursor_set(0);s.top=0
    area.tag_redraw()
bpy.context.workspace.name='FLOW_COURSE_V03';bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),check_existing=False)
print('V03_BUILT','main nodes',len(g.tree.nodes),'segment nodes',len(segment.nodes),'sections',len(legs))
