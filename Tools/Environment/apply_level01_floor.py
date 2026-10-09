"""Apply the existing Surface Factory export to the single Level_01 arena floor.

Run: blender --background --python Tools/Environment/apply_level01_floor.py
Only this floor's UVs and material assignment are edited. Geometry stays authored.
"""
import bpy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Level_01_Blockout.blend'
OUT = ROOT / '.godot/level01-floor'
OUT.mkdir(parents=True, exist_ok=True)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
source_mtime = SOURCE.stat().st_mtime_ns
backup = OUT / ('Level_01_Blockout_before_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
shutil.copy2(SOURCE, backup)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

floor = bpy.data.objects['L01_Arena01_TestFloor_01']
assert floor.type == 'MESH' and len(floor.data.polygons) == 1
assert floor.data.users == 1, 'Shared floor mesh requires an explicit ownership decision'
assert (floor.matrix_world.to_3x3().inverted().transposed() @ floor.data.polygons[0].normal).normalized().z > .99
asset = 'tech_wall_627708735'
mat_name = 'M_Level01_Floor_TechWall_627708735'
mat = bpy.data.materials.get(mat_name)
if mat is None:
    mat = bpy.data.materials.new(mat_name)
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (800, 0)
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (520, 0)
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
uv = nodes.new('ShaderNodeUVMap')
uv.uv_map = 'UVMap'
uv.location = (-750, 0)
mapping = nodes.new('ShaderNodeMapping')
mapping.location = (-560, 0)
# Match the existing Godot .tres UV scale. UVs themselves are world meters / 6.
# The final texture footprint is 6 / 1.5 = 4 meters per tile in both applications.
mapping.inputs['Scale'].default_value = (1.5, 1.5, 1)
links.new(uv.outputs['UV'], mapping.inputs['Vector'])

def image_node(channel, color_space, y):
    relative = f'//Assets/Textures/Levels/Level_01/FacadeFactory/{asset}_{channel}.png'
    assert Path(bpy.path.abspath(relative)).is_file()
    image = bpy.data.images.load(bpy.path.abspath(relative), check_existing=True)
    image.name = f'T_Level01_FloorTechWall_{channel}'
    image.filepath = relative
    image.colorspace_settings.name = color_space
    assert image.packed_file is None
    texture = nodes.new('ShaderNodeTexImage')
    texture.name = channel.title() + '_Texture'
    texture.image = image
    texture.extension = 'REPEAT'
    texture.interpolation = 'Linear'
    texture.location = (-300, y)
    links.new(mapping.outputs['Vector'], texture.inputs['Vector'])
    return texture

albedo = image_node('albedo', 'sRGB', 400)
normal = image_node('normal', 'Non-Color', -200)
orm = image_node('orm', 'Non-Color', 100)
emission = image_node('emission', 'sRGB', -500)
links.new(albedo.outputs['Color'], bsdf.inputs['Base Color'])
separate = nodes.new('ShaderNodeSeparateColor')
separate.location = (0, 100)
links.new(orm.outputs['Color'], separate.inputs['Color'])
links.new(separate.outputs['Green'], bsdf.inputs['Roughness'])
links.new(separate.outputs['Blue'], bsdf.inputs['Metallic'])
normal_map = nodes.new('ShaderNodeNormalMap')
normal_map.location = (0, -200)
normal_map.inputs['Strength'].default_value = .55
links.new(normal.outputs['Color'], normal_map.inputs['Color'])
links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
links.new(emission.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.35
mat['godot_material_path'] = 'res://Assets/Materials/Environment/FacadeFactory/Generated/' + asset + '.tres'
mat['surface_factory_detail'] = 'Separate detail maps remain opt-in; the structural normal is unchanged.'

slot = next((i for i, material in enumerate(floor.data.materials) if material == mat), None)
if slot is None:
    slot = len(floor.data.materials)
    floor.data.materials.append(mat)
floor.data.polygons[0].material_index = slot
uv_layer = floor.data.uv_layers.get('UVMap') or floor.data.uv_layers.new(name='UVMap')
floor.data.uv_layers.active = uv_layer
uv_layer.active_render = True
for loop in floor.data.loops:
    world = floor.matrix_world @ floor.data.vertices[loop.vertex_index].co
    uv_layer.data[loop.index].uv = (world.x / 6.0, world.y / 6.0)
floor['floor_texture_tile_meters'] = 4.0
floor['floor_surface_factory_asset'] = asset

assert SOURCE.stat().st_mtime_ns == source_mtime, 'Source changed during edit; refusing to overwrite'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash, 'Source hash changed; refusing to overwrite'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
report = {'object': floor.name, 'faces_changed': [0], 'material': mat_name,
          'godot_material': mat['godot_material_path'], 'tile_meters': 4.0,
          'uv_meters_per_unit': 6.0, 'material_uv_scale': 1.5,
          'backup': str(backup), 'source_before_sha256': source_hash,
          'source_after_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
(OUT / 'apply_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LEVEL01_FLOOR_APPLIED=' + json.dumps(report))
