"""One-time additive GN POC setup. Never rebuild an existing authoring mesh."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Euler

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILE = ROOT / 'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
assert Path(bpy.data.filepath).resolve() == SOURCE_FILE.resolve(), 'Wrong Blender source'
assert bpy.context.mode == 'OBJECT', 'Finish the current edit operation first'
for name in ('LEVEL_AUTHORING_SOURCE', 'LEVEL_ENVELOPE', 'LEVEL_GENERATED_OUTPUT'):
    assert name not in bpy.data.objects, f'{name} already exists; do not overwrite manual work'
assert 'GN_LevelAuthoring_POC' not in bpy.data.node_groups

for name, color in (('LEVEL_AUTHORING','COLOR_04'),('LEVEL_ENVELOPE','COLOR_03'),
                    ('LEVEL_GENERATED','COLOR_05'),('LEVEL_GUIDES','COLOR_06')):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    col.hide_viewport = False
    col.color_tag = color
    col['purpose'] = 'Blender authoring lab only; excluded from Freestyle export whitelist'

def mesh_object(name, verts, faces, collection):
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.data.collections[collection].objects.link(obj)
    return obj

# Initial neutral patch only. No handler or generator ever writes this mesh again.
verts = [(x,y,0) for y in (-2,0,2) for x in (-4,0,4)]
faces = [(j*3+i,j*3+i+1,(j+1)*3+i+1,(j+1)*3+i) for j in range(2) for i in range(2)]
source = mesh_object('LEVEL_AUTHORING_SOURCE', verts, faces, 'LEVEL_AUTHORING')
source.display_type = 'WIRE'
source.show_in_front = True
source.color = (.10,.48,1,1)
source['role'] = 'EDIT THIS normal mesh. No modifiers, baking, Python updates, or gameplay semantics.'

verts = [(x,y,z) for z in (-.5,2.5) for y in (-2.6,2.6) for x in (-4.6,2.8)]
faces = [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
envelope = mesh_object('LEVEL_ENVELOPE', verts, faces, 'LEVEL_ENVELOPE')
envelope.display_type = 'WIRE'
envelope.show_in_front = True
envelope.color = (1,.5,.10,1)
envelope.hide_render = True
envelope['role'] = 'Allowed procedural volume only. Keep closed for predictable Boolean intersection. No gameplay boundary.'
output = mesh_object('LEVEL_GENERATED_OUTPUT', [], [], 'LEVEL_GENERATED')
output.hide_select = True
output['role'] = 'Evaluated preview only. Edit Source/Envelope; never Apply or edit generated topology.'

mat = bpy.data.materials.new('M_GN_Lab_Generated')
mat.diffuse_color = (.12,.62,.54,1)
mat.use_nodes = True
mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = mat.diffuse_color
mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .72
output.data.materials.append(mat)

group = bpy.data.node_groups.new('GN_LevelAuthoring_POC', 'GeometryNodeTree')
group.is_modifier = True
group.description = 'Manual source faces -> independent closed panels -> optional spatial envelope intersection. Blender only.'
def interface(name, kind, default=None, minimum=None, maximum=None, description=''):
    socket = group.interface.new_socket(name=name, in_out='INPUT', socket_type=kind)
    if default is not None: socket.default_value = default
    if minimum is not None: socket.min_value = minimum
    if maximum is not None: socket.max_value = maximum
    socket.description = description
    return socket
interface('Source Object','NodeSocketObject',source,description='Normal editable mesh; read-only input to this graph.')
interface('Envelope Object','NodeSocketObject',envelope,description='Closed editable mesh defining allowed generation volume; never gameplay collision.')
interface('Use Envelope','NodeSocketBool',True,description='Intersect generated panels with the envelope; OFF shows the unconstrained result.')
interface('Robust Clipping','NodeSocketBool',False,description='OFF: fast Manifold solver for closed volumes. ON: slower Exact fallback for difficult coplanar intersections.')
interface('Envelope Margin','NodeSocketFloat',0,-2,2,'Approximate normal offset in metres. Positive expands, negative contracts. Not a precise distance field.')
interface('Structural Scale','NodeSocketFloat',.90,.1,.99,'Individual face-panel width factor; gap prevents adjacent panels sharing topology.')
interface('Extrusion Depth','NodeSocketFloat',.6,.02,3,'Panel depth along source face normal in metres.')
interface('Preview Quality','NodeSocketInt',0,0,2,'Extra subdivision levels BEFORE panel generation: 0=current topology; 1=4x faces; 2=16x.')
group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
nodes=group.nodes; links=group.links
def node(typ,name,xy):
    n=nodes.new(typ);n.name=name;n.label=name;n.location=xy;n.width=190
    return n
def link(a,out,b,inp): links.new(a.outputs[out],b.inputs[inp])
inp=node('NodeGroupInput','High-level controls',(-1200,250))
out=node('NodeGroupOutput','GENERATED only',(1680,250))
src=node('GeometryNodeObjectInfo','Read SOURCE - never write',(-1200,650));src.transform_space='RELATIVE'
env=node('GeometryNodeObjectInfo','Read ENVELOPE volume',(-1200,-500));env.transform_space='RELATIVE'
link(inp,'Source Object',src,'Object');link(inp,'Envelope Object',env,'Object')
src.inputs['As Instance'].default_value=False;env.inputs['As Instance'].default_value=False

# Optional face flag: missing attribute means all faces enabled, no custom UI.
attr=node('GeometryNodeInputNamedAttribute','Optional proc_enabled',(-1190,20));attr.data_type='BOOLEAN';attr.inputs['Name'].default_value='proc_enabled'
enabled=node('GeometryNodeSwitch','Missing attribute = all faces',(-950,20));enabled.input_type='BOOLEAN';enabled.inputs['False'].default_value=True
link(attr,'Exists',enabled,'Switch');link(attr,'Attribute',enabled,'True')
select=node('GeometryNodeSeparateGeometry','Source faces enabled',(-720,650));select.domain='FACE'
# A native E operation first creates zero-area side faces at zero displacement.
# Ignore those procedurally so the fast Boolean remains valid during the gesture.
area=node('GeometryNodeInputMeshFaceArea','Ignore transient zero-area faces',(-1190,-220))
valid=node('ShaderNodeMath','Nondegenerate face area',(-950,-220));valid.operation='GREATER_THAN';valid.inputs[1].default_value=1e-8
usable=node('FunctionNodeBooleanMath','Enabled AND nondegenerate',(-720,220));usable.operation='AND'
link(area,'Area',valid,0);link(enabled,'Output',usable,0);link(valid,0,usable,1)
link(src,'Geometry',select,'Geometry');link(usable,'Boolean',select,'Selection')
sub=node('GeometryNodeSubdivideMesh','Preview subdivision',(-490,650));link(select,'Selection',sub,'Mesh');link(inp,'Preview Quality',sub,'Level')
split=node('GeometryNodeSplitEdges','Independent face panels',(-260,650));link(sub,'Mesh',split,'Mesh')
scale=node('GeometryNodeScaleElements','Panel gap / structural scale',(-20,650));scale.domain='FACE'
link(split,'Mesh',scale,'Geometry');link(inp,'Structural Scale',scale,'Scale')
extrude=node('GeometryNodeExtrudeMesh','Panel depth',(230,650));extrude.mode='FACES';extrude.inputs['Individual'].default_value=True
link(scale,'Geometry',extrude,'Mesh');link(inp,'Extrusion Depth',extrude,'Offset Scale')
bottom=node('GeometryNodeFlipFaces','Close panel bottoms',(230,300));link(scale,'Geometry',bottom,'Mesh')
join=node('GeometryNodeJoinGeometry','Top sides + bottom',(490,650));link(extrude,'Mesh',join,'Geometry');link(bottom,'Mesh',join,'Geometry')
weld=node('GeometryNodeMergeByDistance','Weld each closed panel',(720,650));weld.inputs['Distance'].default_value=.00001
link(join,'Geometry',weld,'Geometry')

normal=node('GeometryNodeInputNormal','Envelope vertex normal',(-950,-750))
margin=node('ShaderNodeVectorMath','Approximate margin',(-700,-650));margin.operation='SCALE'
link(normal,'Normal',margin,0);link(inp,'Envelope Margin',margin,'Scale')
offset=node('GeometryNodeSetPosition','Effective envelope',(-440,-500))
link(env,'Geometry',offset,'Geometry');link(margin,'Vector',offset,'Offset')
boolean=node('GeometryNodeMeshBoolean','INTERSECT allowed volume',(970,50));boolean.operation='INTERSECT';boolean.solver='EXACT'
boolean.inputs['Self Intersection'].default_value=True
boolean.inputs['Hole Tolerant'].default_value=True
# INTERSECT uses one multi-input Mesh socket (Mesh 1 is disabled in this mode).
link(weld,'Geometry',boolean,'Mesh');link(offset,'Geometry',boolean,'Mesh')
fast=node('GeometryNodeMeshBoolean','Fast closed-volume intersection',(970,-350));fast.operation='INTERSECT';fast.solver='MANIFOLD'
link(weld,'Geometry',fast,'Mesh');link(offset,'Geometry',fast,'Mesh')
solver=node('GeometryNodeSwitch','Robust Clipping',(1210,50));solver.input_type='GEOMETRY'
link(inp,'Robust Clipping',solver,'Switch');link(fast,'Mesh',solver,'False');link(boolean,'Mesh',solver,'True')
switch=node('GeometryNodeSwitch','Use Envelope',(1210,450));switch.input_type='GEOMETRY'
link(inp,'Use Envelope',switch,'Switch');link(weld,'Geometry',switch,'False');link(solver,'Output',switch,'True')
material=node('GeometryNodeSetMaterial','Solid preview',(1450,450));material.inputs['Material'].default_value=mat
link(switch,'Output',material,'Geometry');link(material,'Geometry',out,'Geometry')

modifier=output.modifiers.new('GN_LevelAuthoring_POC','NODES');modifier.node_group=group
modifier.show_in_editmode=True
for s in group.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT':modifier[s.identifier]=s.default_value

# Pin the output's simple modifier controls while the user edits the SOURCE.
for obj in bpy.context.selected_objects:obj.select_set(False)
source.select_set(True);bpy.context.view_layer.objects.active=source
bpy.context.view_layer.active_layer_collection=bpy.context.view_layer.layer_collection.children['LEVEL_AUTHORING']
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        s=area.spaces.active;s.show_region_ui=False;s.shading.type='SOLID';s.shading.color_type='MATERIAL'
        s.region_3d.view_distance=15;s.region_3d.view_location=(0,0,.6)
        s.region_3d.view_rotation=Euler((math.radians(55),0,math.radians(18))).to_quaternion()
        s.overlay.show_stats=True
    if area.type=='PROPERTIES':
        area.spaces.active.pin_id=output;area.spaces.active.use_pin_id=True;area.spaces.active.context='MODIFIER'
    if area.type=='DOPESHEET_EDITOR':
        area.type='TEXT_EDITOR'
        text=bpy.data.texts.new('GN_LAB_QUICKSTART')
        text.write('EDIT SOURCE: select LEVEL_AUTHORING_SOURCE, Tab, normal mesh modelling.\n'
                   'ENVELOPE: editable closed wire volume; procedural limit only, no gameplay boundary.\n'
                   'OUTPUT: locked preview. Controls pinned on the right; Use Envelope compares clipping.\n'
                   'No handlers, baking, conversion, export or source-rebuilding Python.\n'
                   'Optional Boolean face attribute proc_enabled: missing = all faces enabled.\n'
                   'Keep envelope closed; large offsets / self-intersections can invalidate Boolean volume.\n')
        area.spaces.active.text=text
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_FILE))
print('GN_LAB_BUILT',len(group.nodes),'nodes; source',len(source.data.polygons),'faces')
