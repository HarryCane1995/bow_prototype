"""Additive Level_01 industrial dressing. Blender Python, Godot-axis placement data.

Run: blender --background --python Tools/Environment/Level01Art/dress_level.py
Re-running replaces ONLY objects tagged with this pass's owner. Existing map
geometry, transforms, collision, markers, skyline and authored floor are retained.
"""
import bpy
import hashlib
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Level_01_Blockout.blend'
OUT = ROOT / '.godot/level01-art'
OWNER = 'level01_industrial_dressing_v1'
PREFIX = 'M_Level01_Art_'
TEXTURES = ROOT / 'Assets/Textures/Levels/Level_01/ArtPass'
MATERIALS = ROOT / 'Assets/Materials/Environment/Level01Art'
assert shutil.disk_usage(ROOT).free > 16 * 1024**3, 'Disk reserve below 16 GiB'
OUT.mkdir(parents=True, exist_ok=True)
MATERIALS.mkdir(parents=True, exist_ok=True)
before_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = OUT / f'Level_01_before_art_{stamp}.blend'
shutil.copy2(SOURCE, backup)

# Protect every existing script/scene and sibling source outside this task's two
# integration points. Baseline is captured once, so later iterations cannot hide drift.
protected_file = OUT / 'protected_before.json'
if not protected_file.exists():
    paths = [p for folder in ('Scripts', 'Scenes', 'Resources') for p in (ROOT/folder).rglob('*') if p.is_file()]
    paths += list(ROOT.glob('*.blend')) + [ROOT/'project.godot']
    protected = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
                 if p != SOURCE and p.relative_to(ROOT).as_posix() not in (
                     'Scripts/Editor/Import/SimulationMaterialPostImport.gd',
                     'Scenes/Levels/Level_01/Level_01.tscn')}
    protected_file.write_text(json.dumps(protected, indent=2))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

def geometry(obj):
    result = dict(type=obj.type, matrix=[list(r) for r in obj.matrix_world],
                  parent=obj.parent.name if obj.parent else None,
                  collections=sorted(c.name for c in obj.users_collection))
    if obj.type == 'MESH':
        result.update(v=[list(v.co) for v in obj.data.vertices], p=[list(p.vertices) for p in obj.data.polygons])
    return result

original = {o.name:geometry(o) for o in bpy.data.objects if o.get('art_owner') != OWNER}
for obj in list(bpy.data.objects):
    if obj.get('art_owner') == OWNER:
        mesh = obj.data if obj.type == 'MESH' else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
collection = bpy.data.collections.get('70_LEVEL01_ART')
if collection is None:
    collection = bpy.data.collections.new('70_LEVEL01_ART')
    bpy.context.scene.collection.children.link(collection)

library = {r['id']:r for r in json.loads((ROOT/'Assets/ProceduralArt/Materials/manifest.json').read_text())['materials']}
signs = {r['id']:r for r in json.loads((ROOT/'Assets/ProceduralArt/Billboards/manifest.json').read_text())['items']}
used, placements, changed = {}, [], []
cache = {}

def material(asset, sign=False):
    key = ('sign_' if sign else '') + asset
    if key in cache:
        return cache[key]
    source_dir = ROOT / 'Assets/ProceduralArt' / ('Billboards' if sign else 'Materials') / asset
    target = TEXTURES / key
    target.mkdir(parents=True, exist_ok=True)
    channels = ('albedo', 'orm', 'emission') if sign else ('albedo', 'normal', 'orm', 'emission')
    for channel in channels:
        shutil.copy2(source_dir/f'{channel}.png', target/f'{channel}.png')
    runtime = (source_dir/('sign.tres' if sign else 'material.tres')).read_text()
    runtime = runtime.replace('res://' + source_dir.relative_to(ROOT).as_posix(), 'res://' + target.relative_to(ROOT).as_posix())
    import re
    runtime = re.sub(r'resource_name = "[^"]+"', f'resource_name = "{PREFIX}{key}"', runtime)
    if sign:
        runtime = runtime.replace('emission_energy_multiplier = 2.0', 'emission_energy_multiplier = 1.4')
        runtime = runtime.replace('texture_filter = 0', 'texture_filter = 5')
        runtime += '\ntexture_repeat = false\n'
    (MATERIALS/f'{key}.tres').write_text(runtime, encoding='utf-8')
    mat = bpy.data.materials.get(PREFIX + key) or bpy.data.materials.new(PREFIX + key)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    images = {}
    for channel in channels:
        im = bpy.data.images.load(str(target/f'{channel}.png'), check_existing=True)
        im.name = f'T_Level01_Art_{key}_{channel}'
        im.filepath = '//' + (target/f'{channel}.png').relative_to(ROOT).as_posix()
        im.colorspace_settings.name = 'sRGB' if channel in ('albedo','emission') else 'Non-Color'
        assert im.packed_file is None
        tex = nodes.new('ShaderNodeTexImage'); tex.image = im
        tex.extension = 'EXTEND' if sign else 'REPEAT'
        links.new(uv.outputs['UV'], tex.inputs['Vector'])
        images[channel] = tex
    links.new(images['albedo'].outputs['Color'], bsdf.inputs['Base Color'])
    separate = nodes.new('ShaderNodeSeparateColor')
    links.new(images['orm'].outputs['Color'], separate.inputs['Color'])
    links.new(separate.outputs['Green'], bsdf.inputs['Roughness'])
    links.new(separate.outputs['Blue'], bsdf.inputs['Metallic'])
    links.new(images['emission'].outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 1.4 if sign else 1.15
    if not sign:
        normal = nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value = .55
        links.new(images['normal'].outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    mat['godot_material_path'] = 'res://' + (MATERIALS/f'{key}.tres').relative_to(ROOT).as_posix()
    cache[key] = mat
    used[key] = dict(source=source_dir.relative_to(ROOT).as_posix(), material=mat['godot_material_path'],
                     textures={c:hashlib.sha256((target/f'{c}.png').read_bytes()).hexdigest() for c in channels})
    return mat

def bvec(p):
    return Vector((p[0], -p[2], p[1]))

def gvec(p):
    return Vector((p.x, p.z, -p.y))

def assign(obj, side, tile=3.0, top=None, bottom=None, fit=False):
    # A copied mesh preserves any linked collision/source objects sharing its data.
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    mats = [material(side), material(top or side), material(bottom or side)]
    slots = []
    for mat in mats:
        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        slots.append(obj.data.materials.find(mat.name))
    uv = obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    obj.data.uv_layers.active = uv; uv.active_render = True
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    for face in obj.data.polygons:
        n = gvec((normal_matrix @ face.normal).normalized())
        face.material_index = slots[1 if n.y > .6 else 2 if n.y < -.6 else 0]
        for li in face.loop_indices:
            p = gvec(obj.matrix_world @ obj.data.vertices[obj.data.loops[li].vertex_index].co)
            if abs(n.y) > .6:
                a,b = p.x, -p.z
            elif abs(n.z) >= abs(n.x):
                a,b = p.x * (1 if n.z >= 0 else -1), p.y
            else:
                a,b = p.z * (-1 if n.x >= 0 else 1), p.y
            uv.data[li].uv = (a/tile, b/tile)
        if fit:
            coords=[uv.data[li].uv.copy() for li in face.loop_indices]
            lo=Vector((min(p.x for p in coords),min(p.y for p in coords)))
            extent=Vector((max(p.x for p in coords),max(p.y for p in coords)))-lo
            for li,p in zip(face.loop_indices,coords):
                uv.data[li].uv=((p.x-lo.x)/max(extent.x,1e-6),(p.y-lo.y)/max(extent.y,1e-6))
    obj['art_material_note'] = f'{side}; top={top or side}; tile={tile}m'

def new_mesh(name, verts, faces, position=(0,0,0)):
    mesh = bpy.data.meshes.new('L01_ART_' + name + '_Mesh')
    mesh.from_pydata([bvec(v) for v in verts], [], faces); mesh.update()
    obj = bpy.data.objects.new('L01_ART_' + name, mesh)
    collection.objects.link(obj)
    obj.location = bvec(position)
    obj['art_owner'] = OWNER
    # matrix_world updates lazily in background Blender.
    bpy.context.view_layer.update()
    return obj

def collision(obj):
    mesh = obj.data.copy(); mesh.materials.clear()
    col = bpy.data.objects.new(obj.name + '_COL-colonly', mesh)
    collection.objects.link(col); col.matrix_world = obj.matrix_world.copy()
    col['art_owner'] = OWNER
    return col

def box(name, pos, size, mat='accent_dark_monolith', tile=3, top=None, solid=False, yaw=0):
    x,y,z = [v/2 for v in size]
    obj = new_mesh(name, [(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)],
                   [(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)], pos)
    # Godot XYZ and Blender X,-Z,Y both have positive determinant: winding retained.
    obj.rotation_euler.z = math.radians(yaw)
    bpy.context.view_layer.update()
    fit=mat in ('accent_machine_casing','accent_control_console','accent_datacenter','wall_vent_bank','wall_reactor_housing')
    assign(obj, mat, tile, top, fit=fit)
    if solid:
        collision(obj)
    placements.append(dict(name=obj.name, kind='box', position=pos, size=size, material=mat, collision=solid))
    return obj

def tube(name, points, radius, mat, solid=False, repeat_m=4, sides=24):
    points = [Vector(p) for p in points]
    verts, distances = [], [0.0]
    for i,p in enumerate(points):
        if i:
            distances.append(distances[-1] + (p-points[i-1]).length)
        tangent = (points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        rotation = Vector((0,1,0)).rotation_difference(tangent)
        for j in range(sides):
            angle = 2*math.pi*j/sides
            verts.append(p + rotation @ Vector((radius*math.cos(angle),0,-radius*math.sin(angle))))
    faces = []
    for i in range(len(points)-1):
        for j in range(sides):
            k=(j+1)%sides
            faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
    faces += [tuple(reversed(range(sides))), tuple((len(points)-1)*sides+j for j in range(sides))]
    obj = new_mesh(name, verts, faces)
    obj.data.materials.append(material(mat))
    obj.data.materials.append(material('accent_dark_monolith'))
    uv = obj.data.uv_layers.new(name='UVMap')
    for i,face in enumerate(obj.data.polygons):
        if i >= (len(points)-1)*sides:
            face.material_index=1
            continue
        face.use_smooth = True
        ring,segment = divmod(i,sides)
        coords=[(segment/sides,distances[ring]/repeat_m),((segment+1)/sides,distances[ring]/repeat_m),
                ((segment+1)/sides,distances[ring+1]/repeat_m),(segment/sides,distances[ring+1]/repeat_m)]
        for li,p in zip(face.loop_indices,coords):
            uv.data[li].uv=p
    if solid:
        collision(obj)
    placements.append(dict(name=obj.name, kind='tube', points=[list(p) for p in points], radius=radius, material=mat, collision=solid))
    return obj

def cylinder(name, pos, radius, height, mat, solid=True):
    x,y,z = pos
    return tube(name, [(x,y-height/2,z),(x,y+height/2,z)], radius, mat, solid, height)

def sign(name, asset, pos, width, yaw=0, stand=False):
    ratio = signs[asset]['dimensions'][1]/signs[asset]['dimensions'][0]
    height = width*ratio
    rotation = math.radians(yaw)
    normal = Vector((math.sin(rotation),0,math.cos(rotation)))
    right = Vector((math.cos(rotation),0,-math.sin(rotation)))
    if stand:
        box(name+'_Post', (pos[0],max(.1,(pos[1]-height/2)/2),pos[2]-.18),
            (.22,max(.2,pos[1]-height/2),.22), solid=True)
        box(name+'_Foot',(pos[0],.13,pos[2]-.18),(.8,.26,.8),solid=True)
    box(name+'_Frame', tuple(Vector(pos)-normal*.075),(width+.14,height+.14,.14),'accent_billboard_support',3,yaw=yaw)
    verts=[-right*width/2+Vector((0,-height/2,0)),right*width/2+Vector((0,-height/2,0)),
           right*width/2+Vector((0,height/2,0)),-right*width/2+Vector((0,height/2,0))]
    obj=new_mesh(name+'_Sign',verts,[(0,1,2,3)],pos)
    obj.data.materials.append(material(asset,True))
    uv=obj.data.uv_layers.new(name='UVMap')
    for li,p in zip(obj.data.polygons[0].loop_indices,[(0,0),(1,0),(1,1),(0,1)]):
        uv.data[li].uv=p
    placements.append(dict(name=obj.name,kind='sign',asset=asset,position=pos,width=width,height=height))

# Material assignments are restricted to existing architectural and combat meshes.
# Leave the 344m authored floor, atlas props, skyline, robot and palette test panels alone.
architectural = {
 'L01_Arena01_TestBuilding_02':('wall_megablock',6,'floor_rooftop'),
 'L01_Arena01_TestBuilding_03':('wall_corporate',6,'floor_rooftop'),
 'L01_Arena01_TestBuilding_04':('wall_dark_concrete',6,'floor_rooftop'),
 'L01_Arena01_TestBuilding_07':('wall_dark_concrete',6,'floor_rooftop'),
 'L01_Arena01_TestBuilding_05':('wall_tech_spine',4,'floor_grated'),
 'L01_Arena01_TestBuilding_06':('wall_maintenance',6,'floor_rooftop'),
 'L01_Arena01_TestBuilding_06.001':('wall_reinforced',4,'floor_grated'),
 'L01_Arena01_TestBuilding_06.002':('wall_reinforced',4,'floor_service_walkway'),
}
for name,(mat,tile,top) in architectural.items():
    assign(bpy.data.objects[name],mat,tile,top,'ceiling_utility')
    changed.append(name)

layout=json.loads((ROOT/'Scenes/Levels/Level_01/combat_layout.json').read_text())
floor_mats=['floor_diamond_deck','floor_access_tiles','floor_metal_deck','floor_maintenance','floor_rooftop']
for item in layout['boxes']:
    name=item['name']; obj=bpy.data.objects[name+'-col']
    mat='wall_painted_utility'; top='floor_diamond_deck'; tile=3
    if 'RoutePad' in name:
        mat=top=floor_mats[int(name[-1])]; tile=4
    elif 'Pillar' in name:
        mat='wall_cable_riser'
    elif 'Low' in name or 'Sill' in name:
        mat='wall_reinforced'
    elif 'HighNest' in name or 'Bypass' in name:
        mat='wall_maintenance'; top='floor_grated'
    elif 'Wallrun' in name:
        mat='wall_transit_acoustic'; tile=4
    elif 'DuckRoof' in name:
        mat='wall_tech_spine'; top='floor_access_tiles'
    elif 'Screen' in name:
        mat='wall_megablock'
    assign(obj,mat,tile,top,'ceiling_light_baffle')
    changed.append(obj.name)

# Five service stations sit beyond the pad edges, leaving the combat lanes open.
stations=[('Arrival',78,35,False),('Crossing',139,-12,True),('Nest',141,-49,False),
          ('Bypass',78,-82,True),('Final',139,-121,False)]
for index,(name,x,z,tank) in enumerate(stations):
    box(name+'_Plinth',(x,.16,z),(7,.32,7),'floor_grated',3,solid=True)
    box(name+'_Cabinet',(x-1.5,1.8,z-1),(2.6,3,2),'accent_machine_casing',3,top='ceiling_ventilation',solid=True)
    box(name+'_Control',(x-1.5,1.9,z+.025),(1.9,1.15,.06),'accent_control_console',1.9)
    box(name+'_Vent',(x+1.4,1.2,z+1.6),(2.4,1.8,2),'wall_vent_bank',2.4,top='floor_grated',solid=True)
    if tank:
        cylinder(name+'_Reservoir',(x+1.5,3.3,z-1.6),1.0,5.9,'wrap_tank_shell')
        for y in (.5,5.9):
            cylinder(name+f'_Band{y}',(x+1.5,y,z-1.6),1.065,.18,'wrap_insulated_pipe',False)
    else:
        cylinder(name+'_Riser',(x+1.5,3.1,z-1.6),.65,5.5,'wrap_vent_shaft')
    tube(name+'_Feed',[(x-1.5,3.3,z-1),(x-1.5,4.4,z-1),(x+1.5,4.4,z-1.6)],.16,'wrap_heavy_pipe',False)
    sign(name+'_Service','service_strip',(x-1.5,3.55,z+.075),2.7)
    sign(name+'_Warning','warning_panel',(x+1.4,1.25,z+2.64),.9)

# Readable signage is attached to architecture, with only two freestanding entries.
sign('Arrival_Transit','horizontal_billboard',(96,1.65,44.43),6.3)
sign('Crossing_Code','numeric_code',(116,3.8,-18.52),2.1)
sign('Nest_Notice','dirty_lightbox',(126,2.3,-44.92),3.8)
sign('Bypass_Code','numeric_code',(96,3.8,-79.52),2.1)
sign('Final_Notice','inactive_billboard',(104,2.25,-116.42),2.3)
sign('Entry_Totem','vertical_neon',(80,3.25,48),1.0,stand=True)
sign('Exit_Totem','stacked_signage',(135,3.6,-140),1.8,stand=True)

# Utility trunk along the outside of the combat route; elbows and couplings are
# actual geometry. Supports are all at x=146, outside the widest existing pad.
trunk=[(146,1.2,42),(146,5.2,42)]
for i in range(1,7):
    a=math.pi*.5*i/6
    trunk.append((146,5.2+1.2*math.sin(a),40.8+1.2*math.cos(a)))
trunk += [(146,6.4,-131.8)]
for i in range(1,7):
    a=math.pi*.5*i/6
    trunk.append((146,5.2+1.2*math.cos(a),-131.8-1.2*math.sin(a)))
trunk.append((146,1.2,-133))
tube('Main_Coolant_Pipe',trunk,.38,'wrap_heavy_pipe',True,4)
for i,z in enumerate((33,7,-22,-55,-86,-118)):
    box(f'PipeSupport_{i}',(146,3,z),(.48,6,.48),'wall_reinforced',3,solid=True)
    tube(f'PipeCoupler_{i}',[(146,6.4,z-.23),(146,6.4,z+.23)],.46,'wrap_insulated_pipe',False,.46)
    if i in (2,4):
        tube(f'Branch_{i}',[(146,6.4,z),(140,6.4,z),(139,5.4,z),(139,3,z)],.22,'wrap_conduit_cluster',True,4)

# A reactor / coolant landmark outside the high-nest arena, not in its firing lanes.
box('Power_Plinth',(154,.3,-65),(12,.6,12),'floor_access_tiles',4,solid=True)
for i,x in enumerate((150.5,157.5)):
    cylinder(f'Power_Chamber{i}',(x,4.1,-67),1.45,7,'wrap_coolant_chamber')
    cylinder(f'Power_Base{i}',(x,.9,-67),1.65,.65,'wrap_pressure_column')
    cylinder(f'Power_Cap{i}',(x,7.7,-67),1.6,.5,'wrap_insulated_pipe')
    tube(f'Power_Return{i}',[(x,7.5,-67),(x,8.4,-67),(154,8.4,-67)],.18,'wrap_heavy_pipe',False)
box('Power_Switchgear',(154,2.5,-70.9),(3.4,4.4,1.4),'wall_reactor_housing',3.4,solid=True)
box('Power_Console',(154,1.35,-60.5),(3.4,2.1,1.2),'accent_control_console',3.4,solid=True)
sign('Power_HV','warning_panel',(154,3.6,-70.17),1.6)
sign('Power_Vertical','vertical_neon',(157.5,4.5,-65.5),1.1)

# Training courtyard: wall-attached service bays give the large masses human scale.
for i,x in enumerate((-8,0,8)):
    box(f'Training_Vent_{i}',(x,3.0,-8.17),(3.4,3.8,.24),'wall_vent_bank',3.4)
    box(f'Training_Sill_{i}',(x,1.0,-7.94),(3.8,.18,.65),'accent_dark_monolith',3.8)
sign('Training_Corporate','corporate_panel',(0,16,-8.14),12)
sign('Training_Ad','panel_ad',(8,8,-8.12),3.3)
for i,x in enumerate((-12.8,-14.0)):
    tube(f'Training_Drain_{i}',[(x,.3,-20),(x,18,-20),(x,19,-21),(x,19,-27)],.38,'wrap_heavy_pipe',True,4)
    for y in (1,7,13,17):
        cylinder(f'Training_Collar_{i}_{y}',(x,y,-20),.45,.22,'wrap_insulated_pipe',False)
box('Training_Data',(17,2.2,3),(6,4.4,2.5),'accent_datacenter',3,top='ceiling_tech',solid=True)
box('Training_Workshop',(25,1.4,3),(3.2,2.8,2.5),'accent_machine_casing',3.2,solid=True)
sign('Training_Service','dirty_lightbox',(17,3.1,4.33),3.5)
sign('Training_Door','service_strip',(-8,7,-8.02),3.2)

for name,snapshot in original.items():
    assert geometry(bpy.data.objects[name]) == snapshot, 'Original geometry/transform changed: ' + name
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before_hash, 'Concurrent source edit; aborting save'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
report=dict(owner=OWNER, backup=backup.relative_to(ROOT).as_posix(), before_sha256=before_hash,
            after_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            original_objects_preserved=len(original), material_assignments=changed,
            materials=used, placements=placements,
            geometry_objects=sum(o.get('art_owner') == OWNER for o in bpy.data.objects),
            new_colliders=sum(o.get('art_owner') == OWNER and o.name.endswith('-colonly') for o in bpy.data.objects))
(MATERIALS/'placement_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/f'apply_{stamp}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('LEVEL01_ART_SAVED ' + json.dumps({k:report[k] for k in ('original_objects_preserved','geometry_objects','new_colliders')}))
print('MATERIALS',len(used),'PLACEMENTS',len(placements),'REASSIGNED',len(changed))
