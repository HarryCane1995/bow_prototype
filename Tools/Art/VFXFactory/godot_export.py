"""Portable Godot assets generated inside each uniquely named export directory."""
from pathlib import Path
import shutil

TEMPLATES = Path(__file__).resolve().parent / 'godot'


def write_godot(output, resource_directory, recipe, metadata):
    output = Path(output)
    for name in ('flipbook.gdshader', 'flipbook.gd', 'review.gd'):
        shutil.copyfile(TEMPLATES / name, output / name)
    path = resource_directory
    emission = metadata['emission']
    material = f'''[gd_resource type="ShaderMaterial" load_steps=4 format=3]

[ext_resource type="Shader" path="{path}/flipbook.gdshader" id="1"]
[ext_resource type="Texture2D" path="{path}/color_sheet.png" id="2"]
[ext_resource type="Texture2D" path="{path}/{'emission_sheet.png' if emission else 'color_sheet.png'}" id="3"]

[resource]
resource_local_to_scene = true
shader = ExtResource("1")
shader_parameter/color_sheet = ExtResource("2")
shader_parameter/emission_sheet = ExtResource("3")
shader_parameter/atlas_grid = Vector2({metadata['cols']}, {metadata['rows']})
shader_parameter/frame_size = {float(metadata['frame_size'])}
shader_parameter/gutter = 2.0
shader_parameter/use_emission = {str(emission).lower()}
shader_parameter/emission_strength = 1.0
'''
    (output / 'explosion.tres').write_text(material, encoding='utf-8')
    size = recipe['parameters']['explosion_size']
    effect = f'''[gd_scene load_steps=4 format=3]

[ext_resource type="Script" path="{path}/flipbook.gd" id="1"]
[ext_resource type="Material" path="{path}/explosion.tres" id="2"]
[sub_resource type="QuadMesh" id="Quad"]
size = Vector2({size}, {size})

[node name="PSXExplosion" type="Node3D"]
script = ExtResource("1")
fps = {float(metadata['fps'])}
frame_count = {metadata['frame_count']}

[node name="Billboard" type="MeshInstance3D" parent="."]
position = Vector3(0, {size * .32}, 0)
cast_shadow = 0
material_override = ExtResource("2")
mesh = SubResource("Quad")
'''
    (output / 'explosion.tscn').write_text(effect, encoding='utf-8')
    review = f'''[gd_scene load_steps=9 format=3]

[ext_resource type="PackedScene" path="{path}/explosion.tscn" id="1"]
[ext_resource type="Script" path="{path}/review.gd" id="2"]
[sub_resource type="Environment" id="Environment"]
background_mode = 1
background_color = Color(0.024, 0.033, 0.041, 1)
ambient_light_source = 3
ambient_light_color = Color(0.5, 0.57, 0.6, 1)
ambient_light_energy = 0.65
tonemap_mode = 0
[sub_resource type="StandardMaterial3D" id="FloorMaterial"]
albedo_color = Color(0.065, 0.09, 0.10, 1)
roughness = 0.9
[sub_resource type="PlaneMesh" id="FloorMesh"]
material = SubResource("FloorMaterial")
size = Vector2(16, 16)
[sub_resource type="StandardMaterial3D" id="CubeMaterial"]
albedo_color = Color(0.23, 0.29, 0.3, 1)
roughness = 0.8
[sub_resource type="BoxMesh" id="CubeMesh"]
material = SubResource("CubeMaterial")
size = Vector3(1, 1, 1)

[node name="PSXExplosionReview" type="Node3D"]
script = ExtResource("2")
[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment")
[node name="Floor" type="MeshInstance3D" parent="."]
position = Vector3(0, -0.03, 0)
mesh = SubResource("FloorMesh")
[node name="ReferenceCube" type="MeshInstance3D" parent="."]
position = Vector3(-2.7, 0.5, 0)
mesh = SubResource("CubeMesh")
[node name="Light" type="DirectionalLight3D" parent="."]
rotation_degrees = Vector3(-55, -30, 0)
light_energy = 1.4
[node name="Camera3D" type="Camera3D" parent="."]
position = Vector3(4.5, 3.1, 7.5)
current = true
fov = 43.0
[node name="Explosion" parent="." instance=ExtResource("1")]
loop = true
'''
    (output / 'review.tscn').write_text(review, encoding='utf-8')
    (output / 'IMPORT_README.txt').write_text(
        'Open review.tscn in Godot 4.6. R / RESTART replays; Space / PAUSE pauses.\n'
        'Reusable effect: explosion.tscn. Call restart(); finished signal marks one-shot end.\n'
        'Every instance duplicates its ShaderMaterial. No gameplay nodes or input map changes.\n'
        'Straight alpha, sRGB color/emission, row-major frames with 2 px transparent gutters.\n'
        'Shader forces nearest filtering and no repeat. Use lossless texture import; disable mipmaps.\n'
        'No normal/ORM: this is a baked, unlit 2D billboard, not a physical volume.\n'
        'Preview emission is local sprite radiance; it does not light nearby geometry.\n'
        'Keep the generated directory in its exported res:// path (or update its resource links).\n', encoding='utf-8')
