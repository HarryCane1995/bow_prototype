"""One-time recipe. Refuses to overwrite an existing authored .blend."""
import bpy
import math
import runpy
from mathutils import Quaternion
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Assets/Levels/Level_Freestyle_01'
SOURCE = BASE / 'Source/Level_Freestyle_01.blend'
if SOURCE.exists():
    raise RuntimeError('Source already exists. Use export_level.py; never regenerate manual geometry.')
SOURCE.parent.mkdir(parents=True, exist_ok=True)
(SOURCE.parent / '.gdignore').write_text('')
# This script runs only in a new background process, never in the dirty PoseLab session.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'Level_Freestyle_01'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = 'METERS'
names = ('LEVEL_GEO','COLLISION_GUIDES','DEV_METRICS','GAMEPLAY_MARKERS',
         'GRAPPLE_GUIDES','LIGHTING_GUIDES','NOTES_HELPERS','DEV_MECHANICS_REFERENCE')
cols = {}
for name in names:
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    cols[name] = col
cols['LEVEL_GEO'].color_tag = 'COLOR_04'
cols['DEV_METRICS'].color_tag = 'COLOR_05'
cols['DEV_MECHANICS_REFERENCE'].color_tag = 'COLOR_02'

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color,1)
    bsdf.inputs['Roughness'].default_value = .85
    return mat
floor_mat = material('M_Freestyle_Neutral',(.32,.36,.39))
dev_mat = material('M_Freestyle_Dev',(.55,.35,.16))
metric_mat = material('M_Freestyle_Metric',(.12,.75,.8))
human_mat = material('M_Freestyle_Human',(.92,.64,.12))

def relocate(obj, name, collection, mat=None):
    obj.name = name
    for col in list(obj.users_collection): col.objects.unlink(obj)
    cols[collection].objects.link(obj)
    if mat: obj.data.materials.append(mat)
    return obj

def box(name, xyz, size, col='LEVEL_GEO', mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = relocate(bpy.context.object,name,col,mat or floor_mat)
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def empty(name, xyz, col, size=1):
    obj = bpy.data.objects.new(name,None)
    cols[col].objects.link(obj)
    obj.location = xyz
    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = size
    return obj

def label(text, xyz, col='DEV_METRICS', size=.55):
    data = bpy.data.curves.new(text,'FONT')
    data.body = text
    data.size = size
    obj = bpy.data.objects.new(text+'-noimp',data)
    cols[col].objects.link(obj)
    obj.location = xyz
    data.materials.append(metric_mat)
    return obj

box('BuildFloor-col',(0,0,-.25),(200,200,.5))
empty('WorldOrigin-noimp',(0,0,0),'NOTES_HELPERS',2)
# Blender +Y is Godot -Z (camera forward); no manual axis compensation.
empty('PlayerSpawn',(0,0,.05),'GAMEPLAY_MARKERS')
box('PlayerCapsule_0.9x1.8m-noimp',(2,0,.9),(.9,.9,1.8),'DEV_METRICS',human_mat).display_type = 'WIRE'
# Neutral human silhouette, exact 1.80m total height, without a copied character asset.
box('HumanTorso-noimp',(3.5,0,1.16),(.46,.24,.52),'DEV_METRICS',human_mat)
for side in (-1,1):
    box('HumanLeg'+str(side)+'-noimp',(3.5+side*.13,0,.45),(.19,.22,.9),'DEV_METRICS',human_mat)
    box('HumanArm'+str(side)+'-noimp',(3.5+side*.34,0,1.06),(.16,.2,.65),'DEV_METRICS',human_mat)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.17, location=(3.5,0,1.63))
relocate(bpy.context.object,'HumanHead_1.80m-noimp','DEV_METRICS',human_mat)
label('HUMAN 1.80m | capsule diameter 0.90m',(1,-2,.05),size=.4)
for i,length in enumerate((1,2,5,10,20,50)):
    x,y = -38,-12-i*3
    box(f'Ruler_{length}m-noimp',(x+length/2,y,.04),(length,.07,.07),'DEV_METRICS',metric_mat)
    for tick in range(length+1):
        box(f'Tick_{length}_{tick}-noimp',(x+tick,y,.1),(.05,.4 if tick%5 else .8,.08),'DEV_METRICS',metric_mat)
    label(f'{length} m',(x-4,y,.08),size=.7)
label('EMPTY BUILD AREA | author freely',(-17,-6,.03),'NOTES_HELPERS',1)
label('DEV KIT > | F3 in game',(35,-5,.03),'NOTES_HELPERS',.8)

# DEV primitives are off to the east. They are not a route or an authored level layout.
col='DEV_MECHANICS_REFERENCE'
box('DevWall-col',(65,25,9),(1,60,18),col,dev_mat)
box('GapTakeoff-col',(85,-17,1.5),(10,10,3),col,dev_mat)
box('GapLanding-col',(85,-1,1.5),(10,10,3),col,dev_mat)
box('LowObstacle-col',(70,-28,.4),(4,1,.8),col,dev_mat)
# 1.25m clear opening; crouched capsule is 1.10m, standing is 1.80m.
box('SlideLintel-col',(82,-28,1.55),(6,1,.6),col,dev_mat)
for x in (78.75,85.25): box('SlidePost'+str(x)+'-col',(x,-28,1.4),(.5,1,2.8),col,dev_mat)
box('WindowSill-col',(94,-28,.35),(5,.6,.7),col,dev_mat)
box('WindowLintel-col',(94,-28,2.75),(5,.6,.5),col,dev_mat)
for x in (91.25,96.75): box('WindowPost'+str(x)+'-col',(x,-28,1.5),(.5,.6,3),col,dev_mat)
# Wedge 10m long, 2m rise; inspect normal floor/slide behaviour without a new slope mechanic.
verts=[(-3,-5,0),(3,-5,0),(-3,5,0),(3,5,0),(-3,5,2),(3,5,2)]
faces=[(0,2,3,1),(0,1,5,4),(0,4,2),(1,3,5),(2,4,5,3)]
mesh=bpy.data.meshes.new('SlopeMesh'); mesh.from_pydata(verts,[],faces); mesh.update()
obj=bpy.data.objects.new('Slope_1in5-col',mesh); cols[col].objects.link(obj); obj.location=(80,-48,0); mesh.materials.append(dev_mat)
for x,dist in ((45,15),(80,30),(95,45)):
    empty(f'GrappleAnchor_{dist}',(x,45,10),col)
    empty(f'AcquisitionStation_{dist}-noimp',(x,45-dist,0),'GRAPPLE_GUIDES')
    label(f'{dist}m horizontal / anchor +10m',(x-3,45-dist,.05),'GRAPPLE_GUIDES',.4)
    # Hollow wire volume gives Blender-visible anchor position without exporting a fake anchor mesh.
    guide=box(f'Anchor_{dist}_reference-noimp',(x,45,10),(.8,.8,.8),'GRAPPLE_GUIDES',metric_mat)
    guide.display_type='WIRE'
label('DEV wall: both sides / Shift + jump',(60,-8,.08),size=.55)
label('DEV gap 6m / platforms +3m',(78,-10,.05),size=.45)
label('Slide clearance 1.25m',(77,-31,.05),size=.5)
label('Window sill .70 / opening 1.80',(90,-31,.05),size=.4)
label('Slope 1:5 / 11.31 degrees',(76,-56,.05),size=.45)
for colname in ('COLLISION_GUIDES','LIGHTING_GUIDES'):
    cols[colname].hide_render=True
for colname in ('DEV_METRICS','GRAPPLE_GUIDES','NOTES_HELPERS'):
    cols[colname].hide_render=True

scene.tool_settings.snap_elements={'INCREMENT'}
scene.tool_settings.use_snap_grid_absolute=True
scene.tool_settings.use_snap=False
workspace=bpy.data.workspaces.get('Layout') or bpy.context.workspace
workspace.name='LEVEL_BLOCKOUT'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.clip_end=2000
            space.show_region_ui=True
            space.overlay.grid_scale=.5
            space.shading.type='SOLID'
            space.shading.color_type='MATERIAL'
            space.region_3d.view_distance=125
            space.region_3d.view_location=(15,10,0)
            space.region_3d.view_rotation=Quaternion((.880,.279,.116,.365)).normalized()
        elif area.type=='OUTLINER':
            area.spaces.active.show_restrict_column_viewport=True
            area.spaces.active.show_restrict_column_hide=True
            area.spaces.active.show_restrict_column_render=True
bpy.ops.object.select_all(action='DESELECT')
cols['LEVEL_GEO'].objects[0].select_set(True)
bpy.context.view_layer.objects.active=cols['LEVEL_GEO'].objects[0]
text=bpy.data.texts.new('FREESTYLE_TOOLS.py')
text.write((ROOT/'Tools/Levels/Freestyle01/session_tools.py').read_text())
helptext=bpy.data.texts.new('READ_ME')
helptext.write('LEVEL_FREESTYLE_01\n1 unit = 1 metre. Empty canvas, no designed route.\n'
 'Put new collidable meshes in LEVEL_GEO with -col suffix. Collision-only: *_COL-colonly.\n'
 'DEV_METRICS / GRAPPLE_GUIDES / NOTES_HELPERS never export.\n'
 'Run FREESTYLE_TOOLS.py in Text Editor (Alt+P) to restore the N > Freestyle panel.\n'
 'Save + Export. Godot: focus editor for import, open Level_Freestyle_01.tscn, F6.\n'
 'Snap: Shift+Tab; Ctrl while moving; G X .25 for exact 0.25m.\n'
 'F1 reset; F3 DEV kit including collision/anchors; F5 readout; Shift parkour.\n'
 'See Docs/LEVEL_FREESTYLE_01_METRICS.md for dated measured limits, not guarantees.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
runpy.run_path(str(ROOT/'Tools/Levels/Freestyle01/export_level.py'),run_name='__main__')
print('FREESTYLE_CREATED',SOURCE)
