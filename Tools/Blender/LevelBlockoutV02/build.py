"""One-time additive V02 authoring setup. Does not rewrite editable Volume/Cutter meshes."""
import bpy,bmesh,sys,json,math
from pathlib import Path
from mathutils import Euler
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent/'LevelBlockout'))
from geometry import SpatialGraph,ROLES
from region import build_region
from metrics import load_metrics
EXPECTED=ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
REPORT=ROOT/'Docs/Reviews/GNLevelBlockoutV02'
assert Path(bpy.data.filepath)==EXPECTED
assert (REPORT/'before.json').exists()
assert bpy.context.mode=='OBJECT'
assert 'LEVEL_VOLUME' not in bpy.data.objects,'Do not replace manual V02 authoring'
assert 'GN_LevelBlockout_Generator_v02' not in bpy.data.node_groups
movement=load_metrics();M=movement['values']

def collection(name,color):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);c.color_tag=color;return c
def mesh(name,verts,faces,col):
    m=bpy.data.meshes.new(name+'_Mesh');m.from_pydata(verts,[],faces);m.update()
    o=bpy.data.objects.new(name,m);col.objects.link(o);return o
cols={n:collection('V02_'+n,c) for n,c in [('VOLUME','COLOR_04'),('CUTTER','COLOR_03'),('OUTPUT','COLOR_05'),('GUIDES','COLOR_06'),('INTERNAL','COLOR_01')]}
for name,new in [('LEVEL_GENERATED_OUTPUT','V01_GENERATED_OUTPUT'),('LEVEL_CUTTER','V01_LEVEL_CUTTER'),('PLAYER_SPAWN','V01_PLAYER_SPAWN')]:bpy.data.objects[name].name=new
for c in bpy.data.collections:
    if c.name.startswith('BLOCKOUT_'):c.hide_viewport=True
for name in ('GN_LevelAuthoring_POC','GN_LevelBlockout_Generator_v01'):bpy.data.node_groups[name].use_fake_user=True
faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
volume=mesh('LEVEL_VOLUME',[(x,y,z) for z in (-8,42) for y in (-88,88) for x in (-110,110)],faces,cols['VOLUME'])
volume.display_type='WIRE';volume.show_in_front=True;volume.hide_render=True;volume.color=(.12,.4,1,1)
volume['role']='Rectangular authoring domain: native evaluated XYZ bounds, not gameplay boundary. Keep origin inside.'
old=bpy.data.objects['V01_LEVEL_CUTTER'];cutter=old.copy();cutter.data=old.data.copy();cutter.name='LEVEL_CUTTER';cols['CUTTER'].objects.link(cutter)
cutter.hide_viewport=False;cutter.hide_set(False);cutter.hide_select=False
cutter['role']='Closed 3D exclusion. One mesh may contain disconnected solid islands. Spawn floor is reserved.'
spawn=bpy.data.objects.new('PLAYER_SPAWN',None);cols['GUIDES'].objects.link(spawn)
spawn.empty_display_type='ARROWS';spawn.empty_display_size=2.5;spawn.show_name=True;spawn.location=(0,0,.05)
spawn.lock_location=spawn.lock_rotation=spawn.lock_scale=(True,True,True)
wedge=bpy.data.objects['BLK_INTERNAL_UNIT_RAMP'].copy();wedge.data=wedge.data.copy();wedge.name='V02_INTERNAL_UNIT_RAMP';cols['INTERNAL'].objects.link(wedge)
cols['INTERNAL'].hide_viewport=True
out=mesh('LEVEL_GENERATED_OUTPUT',[],[],cols['OUTPUT']);out.hide_select=True
out.lock_location=out.lock_rotation=out.lock_scale=(True,True,True)
region=build_region(M,wedge)
g=SpatialGraph('GN_LevelBlockout_Generator_v02')
seed=g.input('Seed','NodeSocketInt',41,0,1000000,'Changes BSP partitions, merged zones, vertical masses and route graph.')
density=g.input('Density',value=.76,low=0,high=1,description='Gameplay surface occupancy and population of elevated bands.')
vertical=g.input('Verticality',value=.84,low=0,high=1,description='Changes populated floor count and lower voids, not merely object Z offsets.')
openness=g.input('Openness',value=.34,low=0,high=1,description='Width of open channels between major spatial masses.')
routes=g.input('Route Complexity',value=.68,low=0,high=1,description='More elevated inter-zone links and secondary vertical opportunities.')
difficulty=g.input('Traversal Difficulty',value=.45,low=0,high=1,description='Metric bands affect gaps, wall spacing/length, rise and landing runways.')
grapple=g.input('Grapple Presence',value=.65,low=0,high=1,description='Frequency of usable high landing surfaces marked as grapple candidates.')
safe=g.input('Spawn Safe Radius',value=8,low=3,high=20,description='Open starting clearing; floor at Z=0 protected from all exclusions.')
use=g.input('Use Cutter','NodeSocketBool',True)
quality=g.input('Preview Quality','NodeSocketInt',0,0,1,'0 Manifold interactive; 1 Exact fallback.')
debug=g.input('Debug Spatial Roles','NodeSocketBool',False)
volume_socket=g.input('Volume Object','NodeSocketObject',volume)
cutter_socket=g.input('Cutter Object','NodeSocketObject',cutter)
read=g.object(None);g.set(read,'Object',volume_socket);read.label='Manual rectangular VOLUME'
bound=g.node('GeometryNodeBoundBox','Actual evaluated XYZ domain bounds');g.set(bound,'Geometry',read.outputs['Geometry'])
lo=g.separate(bound.outputs['Min']);hi=g.separate(bound.outputs['Max'])
size=[g.sub(hi[i],lo[i]) for i in range(3)]
center=[g.mul(g.add(lo[i],hi[i]),.5) for i in range(2)]
rotate=g.gt(g.random(seed,0,301),.5)
width=g.switch(rotate,size[0],size[1],'FLOAT');length=g.switch(rotate,size[1],size[0],'FLOAT')
xmin=g.mul(width,-.5);xmax=g.mul(width,.5);ymin=g.mul(length,-.5);ymax=g.mul(length,.5)
split=g.add(xmin,g.mul(width,g.random(seed,0,302,.35,.65)))
gutter=g.add(5,g.mul(openness,M['air_jump']*.65))
rise=g.mul(g.mul(M['wall_jump_rise'],g.add(.56,g.mul(difficulty,.2))),g.random(seed,0,307,.90,1.08))
trees=[];rectangles=[]
for col in range(2):
    a=xmin if col==0 else split;b=split if col==0 else xmax
    cut1=g.add(ymin,g.mul(length,g.random(seed,col,303,.24,.42)))
    cut2=g.add(ymin,g.mul(length,g.random(seed,col,304,.61,.78)))
    merged=g.lt(g.random(seed,col,305),.38)
    cuts=[ymin,cut1,g.switch(merged,cut2,ymax,'FLOAT'),ymax]
    for row in range(3):
        zone=col*3+row;active=True if row<2 else g.boolean('NOT',merged,False)
        cy=g.mul(g.add(cuts[row],cuts[row+1]),.5);cx=g.mul(g.add(a,b),.5)
        w=g.high(8,g.sub(g.sub(b,a),gutter));l=g.high(16,g.sub(g.sub(cuts[row+1],cuts[row]),gutter))
        n=g.node('GeometryNodeGroup','Spatial volume '+str(zone));n.node_tree=region
        for key,val in [('Seed',seed),('Zone',zone),('Width',w),('Length',l),('Center X',cx),('Center Y',cy),('Bottom',lo[2]),('Top',hi[2]),('Verticality',vertical),('Density',density),('Openness',openness),('Route Complexity',routes),('Traversal Difficulty',difficulty),('Grapple Presence',grapple),('Band Rise',rise),('Outer Side',-1 if col==0 else 1),('Major',g.eq(col,g.random(seed,0,306,0,1,'INT')) if row==0 else False)]:g.set(n,key,val)
        trees.append(n);rectangles.append((cx,cy,w,l,active))
parts=[g.keep(n.outputs['Geometry'],r[4]) for n,r in zip(trees,rectangles)]

def connection(a,b,width,role,part):
    ax,ay,az=g.separate(a);bx,by,bz=g.separate(b)
    dx=g.sub(bx,ax);dy=g.sub(by,ay);dz=g.sub(bz,az)
    distance=g.vector('LENGTH',g.vec(dx,dy,0));angle=g.math('ARCTAN2',dy,dx)
    middle=[g.mul(g.add(ax,bx),.5),g.mul(g.add(ay,by),.5),g.sub(g.low(az,bz),.4)]
    plate=g.cube((distance,width,.8),(0,0,0),role,-1,0,part,'Broad spatial connection')
    plate=g.transform(plate,g.vec(middle[0],middle[1],g.sub(az,.4)),rotation=g.vec(0,0,angle))
    slope=g.object(wedge)
    slope=g.transform(slope.outputs['Geometry'],g.vec(middle[0],middle[1],g.low(az,bz)),g.vec(distance,width,g.high(.02,g.math('ABSOLUTE',dz))),g.vec(0,0,g.add(angle,g.switch(g.gt(dz,0),math.pi,0,'FLOAT'))))
    slope=g.tag(slope,3,-1,0,part)
    return g.switch(g.lt(g.math('ABSOLUTE',dz),.01),slope,plate)

# Main floor access radiates from the protected clearing, not from a tiled ground plane.
for i in (0,1,3,4):
    cx,cy,w,l,active=rectangles[i];endpoint=g.vec(cx,cy,trees[i].outputs['Ground'])
    distance=g.vector('LENGTH',g.vec(cx,cy,0));unit=g.vector('NORMALIZE',g.vec(cx,cy,0))
    start=g.vector('SCALE',unit,g.mul(safe,.8))
    parts.append(g.keep(connection(start,endpoint,8,0,70+i),active))

# Elevated connections change adjacency and selected elevation with Seed.
edges=[(0,1),(1,2),(3,4),(4,5),(0,3),(1,4),(2,5),(0,4),(1,3)]
for i,(a,b) in enumerate(edges):
    common=g.low(trees[a].outputs['Layers'],trees[b].outputs['Layers'])
    chosen=g.high(1,g.math('FLOOR',g.mul(common,g.random(seed,i,330,.55,1.01))))
    condition=g.boolean('AND',rectangles[a][4],rectangles[b][4])
    condition=g.boolean('AND',condition,g.gt(common,.5))
    condition=g.boolean('AND',condition,g.lt(g.random(seed,i,331),g.add(.15,g.mul(routes,.72))))
    def selected_anchor(n):
        v=n.outputs['Anchor 1']
        for k in range(2,7):v=g.switch(g.eq(chosen,k),v,n.outputs['Anchor '+str(k)],'VECTOR')
        return v
    bridge=connection(selected_anchor(trees[a]),selected_anchor(trees[b]),g.add(4,g.mul(g.sub(1,difficulty),3)),3,100+i)
    bridge=g.store(bridge,'v02_band',chosen)
    parts.append(g.keep(bridge,condition))
level=g.join(parts)
level=g.transform(level,g.vec(center[0],center[1],0),rotation=g.vec(0,0,g.switch(rotate,0,math.pi/2,'FLOAT')))
# Clip to the volume BOUNDS. This clips only existing solids and creates no global roof.
level=g.mesh_boolean('INTERSECT',level,bound.outputs['Bounding Box'])
# Carve a clear spawn column through every elevated band; then add the protected floor.
reserve=g.cylinder(g.add(safe,.1),g.add(g.math('ABSOLUTE',size[2]),200),(0,0,g.mul(g.add(lo[2],hi[2]),.5)))
level=g.mesh_boolean('DIFFERENCE',level,reserve)
pad=g.tag(g.cylinder(g.add(safe,.3),.65,(0,0,-.325)),0,-1,0,90)
pad=g.mesh_boolean('INTERSECT',pad,bound.outputs['Bounding Box'])
cut=g.object(None);g.set(cut,'Object',cutter_socket);cut.label='One editable CUTTER / multiple closed islands'
fast=g.mesh_boolean('DIFFERENCE',level,cut.outputs['Geometry'])
exact=g.mesh_boolean('DIFFERENCE',level,cut.outputs['Geometry'],'EXACT')
cut_size=g.node('GeometryNodeAttributeDomainSize','Empty cutter bypass',component='MESH');g.set(cut_size,'Geometry',cut.outputs['Geometry'])
cut_enabled=g.boolean('AND',use,g.gt(cut_size.outputs['Face Count'],0))
level=g.switch(cut_enabled,level,g.switch(g.gt(quality,.5),fast,exact))
level=g.join([level,pad])
neutral=bpy.data.materials.new('M_V02_Graybox');neutral.diffuse_color=(.48,.50,.52,1)
n=g.node('GeometryNodeSetMaterial','Neutral graybox');g.set(n,'Geometry',level);g.set(n,'Material',neutral);level=n.outputs[0]
colors=[(.38,.42,.45),(.48,.40,.31),(.48,.57,.62),(.35,.55,.44),(.68,.58,.27),(.45,.38,.49)]
role=g.attr('v02_role')
for i,(name,color) in enumerate(zip(ROLES,colors)):
    m=bpy.data.materials.new('M_V02_'+name);m.diffuse_color=(*color,1)
    n=g.node('GeometryNodeSetMaterial',name);g.set(n,'Geometry',level);g.set(n,'Material',m);g.set(n,'Selection',g.boolean('AND',debug,g.eq(role,i)));level=n.outputs[0]
g.output('Geometry',level);g.arrange()
g.tree['contract']='Open-top XYZ bounds / floating gameplay surfaces, optional access and open voids / native GN only'
g.tree['metrics_snapshot']=movement['snapshot'];g.tree['roles']=json.dumps(ROLES)
mod=out.modifiers.new(g.tree.name,'NODES');mod.node_group=g.tree
for s in g.tree.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT':mod[s.identifier]=s.default_value
for o in bpy.context.selected_objects:o.select_set(False)
volume.select_set(True);bpy.context.view_layer.objects.active=volume
bpy.context.view_layer.active_layer_collection=bpy.context.view_layer.layer_collection.children[cols['VOLUME'].name]
for area in bpy.context.screen.areas:
    s=area.spaces.active
    if area.type=='VIEW_3D':
        s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.light='STUDIO';s.shading.show_cavity=True;s.shading.cavity_type='BOTH';s.overlay.show_stats=True
        s.region_3d.view_distance=415;s.region_3d.view_location=(0,0,10);s.region_3d.view_rotation=Euler((math.radians(66),0,math.radians(-33))).to_quaternion()
    elif area.type=='PROPERTIES':s.pin_id=out;s.use_pin_id=True;s.context='MODIFIER'
    elif area.type=='OUTLINER':s.filter_text='V02';s.show_restrict_column_select=True
    elif area.type=='TEXT_EDITOR':
        t=bpy.data.texts.get('V02_QUICKSTART') or bpy.data.texts.new('V02_QUICKSTART')
        t.clear();t.write('VOLUME: ordinary XYZ box bounds. Tab / S X / S Y / S Z. Keep origin inside.\nSEED + VERTICALITY: pinned modifier. CUTTER: closed islands subtract any geometry live.\nOpen top. Protected origin floor. Native GN; no Bake, export or gameplay changes.\n');s.text=t;t.cursor_set(0);s.top=0
bpy.context.workspace.name='LEVEL_VOLUME_V02';bpy.context.scene['blockout_generator_version']='v02'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(EXPECTED))
print('V02_BUILT',len(g.tree.nodes),'main nodes;',len(region.nodes),'region nodes')
