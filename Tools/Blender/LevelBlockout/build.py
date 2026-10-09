"""Additive one-time seeded blockout generator. Run in the connected Freestyle Blender."""
import bpy
import bmesh
import json
import math
import sys
from pathlib import Path
from mathutils import Euler

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from nodes import Graph
from metrics import load_metrics
from vocabulary import build_category, build_connections, CATEGORIES

REPORT=ROOT/'Docs/Reviews/GNLevelBlockout'
EXPECTED=ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
assert Path(bpy.data.filepath).resolve()==EXPECTED.resolve()
assert bpy.context.mode=='OBJECT'
assert 'LEVEL_FIELD' not in bpy.data.objects, 'Existing editable field must never be overwritten'
assert 'GN_LevelBlockout_Generator_v01' not in bpy.data.node_groups
assert (REPORT/'before.json').exists(), 'Create pre-change backup first'
movement=load_metrics();M=movement['values']
(REPORT/'movement_metrics.json').write_text(json.dumps(movement,indent=2),encoding='utf-8')

def collection(name,color):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);c.color_tag=color
    c['role']='Blender-only blockout experiment; outside all export whitelists'
    return c

cols={name:collection('BLOCKOUT_'+name,color) for name,color in [('FIELD','COLOR_04'),('CUTTER','COLOR_03'),('OUTPUT','COLOR_05'),('GUIDES','COLOR_06'),('INTERNAL','COLOR_01')]}
def mesh(name,verts,faces,col):
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);col.objects.link(obj);return obj
field=mesh('LEVEL_FIELD',[(-110,-88,0),(110,-88,0),(110,88,0),(-110,88,0)],[(0,1,2,3)],cols['FIELD'])
field.display_type='WIRE';field.show_in_front=True;field.color=(.12,.45,1,1);field.hide_render=True
field['role']='2D footprint. Edit or scale this quad; Seed generates the internal layout. Keep convex and near origin.'
cube_verts=[(x,y,z) for z in (-7,15) for y in (-9,9) for x in (-9,9)]
cube_faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
cutter=mesh('LEVEL_CUTTER',cube_verts,cube_faces,cols['CUTTER']);cutter.location=(66,22,0)
cutter.display_type='WIRE';cutter.show_in_front=True;cutter.color=(1,.35,.05,1);cutter.hide_render=True
cutter['role']='Closed exclusion volume. Move / extrude / scale manually. Spawn floor is reserved even inside cutter.'
spawn=bpy.data.objects.new('PLAYER_SPAWN',None);cols['GUIDES'].objects.link(spawn)
spawn.location=(0,0,.05);spawn.empty_display_type='ARROWS';spawn.empty_display_size=2;spawn.show_name=True
spawn['role']='Fixed world-origin spawn; floor top Z=0. This is a Blender helper only.'
# Primitive library mesh, never generated from user input. Correct outward normals.
wedge=mesh('BLK_INTERNAL_UNIT_RAMP',[(-.5,-.5,0),(-.5,.5,0),(.5,-.5,0),(.5,.5,0),(.5,-.5,1),(.5,.5,1)],
           [(0,1,3,2),(2,3,5,4),(0,2,4),(1,5,3),(0,4,5,1)],cols['INTERNAL'])
bm=bmesh.new();bm.from_mesh(wedge.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wedge.data);bm.free()
wedge.hide_render=True;cols['INTERNAL'].hide_viewport=True

# Preserve the old POC and its dependencies in their original collections.
old=bpy.data.objects.get('LEVEL_GENERATED_OUTPUT')
if old:old.name='POC_GENERATED_OUTPUT'
for name in ('LEVEL_AUTHORING','LEVEL_ENVELOPE','LEVEL_GENERATED','LEVEL_GUIDES'):
    if name in bpy.data.collections:bpy.data.collections[name].hide_viewport=True
bpy.data.node_groups['GN_LevelAuthoring_POC'].use_fake_user=True
output=mesh('LEVEL_GENERATED_OUTPUT',[],[],cols['OUTPUT']);output.hide_select=True
output['role']='Native seeded result. Field / Cutter and the pinned modifier are the authoring interface.'

palette=[build_category(i,M,wedge) for i in range(len(CATEGORIES))]
g=Graph('GN_LevelBlockout_Generator_v01')
seed=g.input('Seed','NodeSocketInt',17,0,1000000,'One seed controls macro zones, category placement, rotation and regional variation.')
density=g.input('Density',value=.72,low=0,high=1,description='Region occupancy, not decorative scatter.')
vertical=g.input('Verticality',value=.68,low=0,high=1,description='Platform rises, pit depths and high points; clearance heights remain valid.')
openness=g.input('Openness',value=.3,low=0,high=1,description='Bias toward large quiet floor regions and fewer occupied zones.')
routes=g.input('Route Complexity',value=.65,low=0,high=1,description='Enable secondary ledges, narrow bridges and upper bypasses inside regions.')
difficulty=g.input('Traversal Difficulty',value=.45,low=0,high=1,description='Comfortable to near-observed-limit spans; never uses theoretical chain length as wall-to-wall gap.')
grapple=g.input('Grapple Presence',value=.55,low=0,high=1,description='Frequency of high grapple target structures and crossing courts.')
height=g.input('Height Range',value=12,low=1,high=12,description='Cap structural ascent heights in metres; fixed human clearance is preserved.')
safe=g.input('Spawn Safe Radius',value=8,low=3,high=20,description='Protected clear area at world origin. Cutter cannot remove its floor.')
use_cutter=g.input('Use Cutter','NodeSocketBool',True)
quality=g.input('Preview Quality','NodeSocketInt',0,0,1,'0: fast Manifold cutter. 1: slower Exact cutter for difficult intersections.')
debug=g.input('Debug Traversal Colors','NodeSocketBool',False)
field_input=g.input('Field Object','NodeSocketObject',field)
cutter_input=g.input('Cutter Object','NodeSocketObject',cutter)

add=lambda a,b:g.math('ADD',a,b)
sub=lambda a,b:g.math('SUBTRACT',a,b)
mul=lambda a,b:g.math('MULTIPLY',a,b)
minimum=lambda a,b:g.math('MINIMUM',a,b)
maximum=lambda a,b:g.math('MAXIMUM',a,b)
factor=add(.52,mul(difficulty,.38))
pos=g.node('GeometryNodeInputPosition').outputs['Position']
px,py,pz=g.separate(pos)
read=g.object(None);read.label='Read editable FIELD';g.set(read,'Object',field_input)
flat=g.node('GeometryNodeSetPosition','Field footprint projected to world XY')
g.set(flat,'Geometry',read.outputs['Geometry']);g.set(flat,'Position',g.vec(px,py,0))
field_geo=flat.outputs['Geometry']
bounds=g.node('GeometryNodeBoundBox','Field bounds');g.set(bounds,'Geometry',field_geo)
lo=g.separate(bounds.outputs['Min']);hi=g.separate(bounds.outputs['Max'])
sizes=[sub(hi[i],lo[i]) for i in range(2)]
counts=[minimum(12,maximum(1,g.math('FLOOR',g.math('DIVIDE',s,44)))) for s in sizes]
# Grid has a minimum of 2 vertices; singleton dimensions are deduplicated before instances.
grid=g.node('GeometryNodeMeshGrid','Macro candidate regions / 44m pitch')
for i,axis in enumerate(('X','Y')):
    g.set(grid,'Size '+axis,mul(sub(counts[i],1),44))
    g.set(grid,'Vertices '+axis,maximum(2,counts[i]))
grid_geo=g.transform(grid.outputs['Mesh'],g.vec(mul(add(lo[0],hi[0]),.5),mul(add(lo[1],hi[1]),.5),0))
weld=g.node('GeometryNodeMergeByDistance','Deduplicate small-field candidates');g.set(weld,'Geometry',grid_geo);g.set(weld,'Distance',.001)
points=weld.outputs['Geometry']

# Whole-region footprint containment gives clean edges without chopped obstacles.
fit=True
for x,y in [(-21,-21),(-21,21),(21,-21),(21,21),(0,0)]:
    ray=g.node('GeometryNodeRaycast',f'Field containment {x},{y}')
    g.set(ray,'Target Geometry',field_geo);g.set(ray,'Source Position',g.vector('ADD',pos,(x,y,100)))
    g.set(ray,'Ray Direction',(0,0,-1));g.set(ray,'Ray Length',200)
    fit=g.boolean('AND',fit,ray.outputs['Is Hit'])
outside_spawn=g.math('GREATER_THAN',g.vector('LENGTH',pos),add(safe,29.7))
fit=g.boolean('AND',fit,outside_spawn)

ix=g.math('FLOOR',g.math('DIVIDE',add(px,22),44));iy=g.math('FLOOR',g.math('DIVIDE',add(py,22),44))
identifier=add(add(ix,mul(iy,101)),20000)
macro_id=add(g.math('FLOOR',g.math('DIVIDE',px,88)),mul(31,g.math('FLOOR',g.math('DIVIDE',py,88))))
macro=g.random(seed,macro_id,7,0,5,'INT')
variant=g.random(seed,identifier,19,0,2,'INT')
# Meaningful grammar per macro type: open, dense, raised, lowered, vertical, corridor.
choices=[(0,1,0),(4,7,10),(8,9,2),(1,3,11),(6,12,13),(5,14,4)]
category=0
for macro_index,options in enumerate(choices):
    chosen=options[0]
    for vi,ci in enumerate(options[1:],1):
        chosen=g.switch(g.math('COMPARE',variant,vi,.1),chosen,ci,'INT')
    category=g.switch(g.math('COMPARE',macro,macro_index,.1),category,chosen,'INT')
category=g.switch(g.math('LESS_THAN',g.random(seed,identifier,23),mul(openness,.45)),category,0,'INT')
category=g.switch(g.math('LESS_THAN',g.random(seed,identifier,29),mul(grapple,.24)),category,13,'INT')
disable_grapple=g.boolean('AND',g.math('COMPARE',category,13,.1),g.math('LESS_THAN',grapple,.001))
category=g.switch(disable_grapple,category,12,'INT')
occupancy=minimum(1,maximum(.05,sub(add(.15,mul(density,1.0)),mul(openness,.3))))
occupied=g.math('LESS_THAN',g.random(seed,identifier,31),occupancy)
category=g.switch(occupied,0,category,'INT')
angle=mul(g.random(seed,identifier,37,0,3,'INT'),math.pi/2)
xscale=g.random(seed,identifier,41,.86,1)
zscale=g.random(seed,identifier,43,.68,1)
# Never scale human headroom or slide openings. Other regional heights vary by seed.
clearance_category=g.boolean('OR',g.math('COMPARE',category,4,.1),g.math('COMPARE',category,7,.1))
clearance_category=g.boolean('OR',clearance_category,g.math('COMPARE',category,14,.1))
zscale=g.switch(clearance_category,zscale,1,'FLOAT')
for name,value,kind in [('region_id',identifier,'INT'),('macro_region',macro,'INT'),('module_id',category,'INT'),('region_angle',angle,'FLOAT')]:
    points=g.store(points,name,value,kind,'POINT')
selection=g.node('GeometryNodeSeparateGeometry','Whole regions outside protected spawn',domain='POINT')
g.set(selection,'Geometry',points);g.set(selection,'Selection',fit);points=selection.outputs['Selection']
solids=[];voids=[]
for tree in palette:
    n=g.node('GeometryNodeGroup',tree.name);n.node_tree=tree
    for name,value in [('Difficulty factor',factor),('Verticality',vertical),('Height Range',height),('Route Complexity',routes)]:g.set(n,name,value)
    solids.append(n.outputs['Solid']);voids.append(n.outputs['Voids'])

def region_instances(geometries,label):
    instances=g.node('GeometryNodeGeometryToInstance',label+' palette')
    # Blender's multi-input links evaluate newest first. Insert in reverse to keep
    # semantic category ids equal to the instance indices for both parallel palettes.
    for geometry in reversed(geometries):g.set(instances,'Geometry',geometry)
    n=g.node('GeometryNodeInstanceOnPoints',label+' / seeded regions')
    g.set(n,'Points',points);g.set(n,'Instance',instances.outputs['Instances']);g.set(n,'Pick Instance',True)
    g.set(n,'Instance Index',g.attr('module_id'));g.set(n,'Rotation',g.vec(0,0,angle));g.set(n,'Scale',g.vec(xscale,1,zscale))
    real=g.node('GeometryNodeRealizeInstances',label+' / realize only for volume operations')
    g.set(real,'Geometry',n.outputs['Instances'])
    return real.outputs['Geometry']
structures=region_instances(solids,'Traversal solids')
structures=g.join([structures,build_connections(g,points,seed,routes,vertical,height,wedge)])
holes=region_instances(voids,'Pits and gaps')

# An ordinary quad footprint is made into a closed floor slab.
extrude=g.node('GeometryNodeExtrudeMesh','Field floor thickness',mode='FACES')
g.set(extrude,'Mesh',field_geo);g.set(extrude,'Individual',False);g.set(extrude,'Offset',g.vec(0,0,-.5));g.set(extrude,'Offset Scale',1)
flip=g.node('GeometryNodeFlipFaces');g.set(flip,'Mesh',extrude.outputs['Mesh'])
floorjoin=g.join([flip.outputs['Mesh'],field_geo])
floorweld=g.node('GeometryNodeMergeByDistance','Close floor slab');g.set(floorweld,'Geometry',floorjoin)
floor=floorweld.outputs['Geometry']

def cylinder(radius,depth,center,label):
    n=g.node('GeometryNodeMeshCylinder',label);g.set(n,'Vertices',48);g.set(n,'Radius',radius);g.set(n,'Depth',depth)
    return g.transform(n.outputs['Mesh'],center)
pad=cylinder(safe,.5,(0,0,-.25),'Guaranteed spawn floor')
floor=g.mesh_boolean('UNION',floor,pad)
floor=g.mesh_boolean('DIFFERENCE',floor,holes)
floor=g.store(g.store(floor,'category_id',-1),'region_id',-1)
level=g.join([floor,structures])
cutread=g.object(None);cutread.label='Read editable CUTTER';g.set(cutread,'Object',cutter_input)
reserve=cylinder(add(safe,.1),200,(0,0,0),'Uncuttable spawn reserve')
effective=g.mesh_boolean('DIFFERENCE',cutread.outputs['Geometry'],reserve)
fast=g.mesh_boolean('DIFFERENCE',level,effective)
exact=g.mesh_boolean('DIFFERENCE',level,effective,'EXACT')
cutresult=g.switch(g.math('GREATER_THAN',quality,.5),fast,exact)
level=g.switch(use_cutter,level,cutresult)

mat=bpy.data.materials.new('M_Blockout_Neutral');mat.diffuse_color=(.42,.5,.55,1)
mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=mat.diffuse_color
paint=g.node('GeometryNodeSetMaterial','Neutral blockout');g.set(paint,'Geometry',level);g.set(paint,'Material',mat)
level=paint.outputs['Geometry']
colors=[(.5,.56,.6),(.23,.57,.8),(.28,.4,.85),(.8,.65,.18),(.8,.38,.14),(.25,.7,.67),(.65,.35,.75),(.68,.62,.36),(.4,.7,.36),(.55,.72,.32),(.57,.5,.38),(.35,.43,.5),(.33,.63,.72),(.9,.65,.12),(.65,.55,.5)]
category_attr=g.attr('category_id')
for i,color in enumerate(colors):
    material=bpy.data.materials.new('M_Blockout_'+CATEGORIES[i]);material.diffuse_color=(*color,1)
    n=g.node('GeometryNodeSetMaterial',CATEGORIES[i]);g.set(n,'Geometry',level);g.set(n,'Material',material)
    g.set(n,'Selection',g.boolean('AND',debug,g.math('COMPARE',category_attr,i,.1)))
    level=n.outputs['Geometry']
g.output('Geometry',level);g.arrange()
g.tree['metrics_snapshot']=movement['snapshot'];g.tree['categories']=json.dumps(CATEGORIES)
g.tree['spawn_contract']='Fixed origin; radius protected from region placement and Cutter. Spawn pad persists for undersized/moved fields.'
mod=output.modifiers.new(g.tree.name,'NODES');mod.node_group=g.tree
for s in g.tree.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT':mod[s.identifier]=s.default_value
for o in bpy.context.selected_objects:o.select_set(False)
field.select_set(True);bpy.context.view_layer.objects.active=field
bpy.context.view_layer.active_layer_collection=bpy.context.view_layer.layer_collection.children[cols['FIELD'].name]
for area in bpy.context.screen.areas:
    s=area.spaces.active
    if area.type=='VIEW_3D':
        s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.overlay.show_stats=True
        s.region_3d.view_distance=255;s.region_3d.view_location=(0,0,0)
        s.region_3d.view_rotation=Euler((math.radians(30),0,math.radians(-25))).to_quaternion()
    elif area.type=='PROPERTIES':s.pin_id=output;s.use_pin_id=True;s.context='MODIFIER'
    elif area.type=='OUTLINER':s.filter_text='BLOCKOUT';s.show_restrict_column_select=True
    elif area.type=='TEXT_EDITOR':
        t=bpy.data.texts.get('BLOCKOUT_QUICKSTART') or bpy.data.texts.new('BLOCKOUT_QUICKSTART')
        t.clear();t.write('FIELD: scale the wire quad. SEED: pinned controls on the right. CUTTER: edit the orange wire volume.\n'
                          'Origin = protected spawn. Closed Cutter subtracts geometry; Use Cutter compares.\n'
                          'Default 220 x 176 m. Native GN; no bake, Python handlers, export or gameplay edits.\n')
        s.text=t;t.cursor_set(0);s.top=0
bpy.context.scene['blockout_generator_version']='v01'
bpy.ops.wm.save_as_mainfile(filepath=str(EXPECTED))
print('BUILT',g.tree.name,'main nodes',len(g.tree.nodes),'categories',len(palette),'objects',len(bpy.data.objects))
