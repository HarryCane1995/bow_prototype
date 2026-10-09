"""OBJ geometry + per-layer shader resources + a time-driven Godot scene."""
import json
from pathlib import Path
import shutil
from mesh_geometry import write_obj

HERE = Path(__file__).resolve().parent


def shader(layer):
    blend = 'blend_add' if layer['blend'] == 'ADDITIVE' else 'blend_mix'
    depth = 'depth_draw_always' if layer['depth_write'] else 'depth_draw_never'
    cull = 'cull_back' if layer['cull_back'] else 'cull_disabled'
    return f'''shader_type spatial;
render_mode unshaded, {blend}, {depth}, {cull};
uniform vec4 color_a : source_color = vec4(1.0);
uniform vec4 color_b : source_color = vec4(1.0);
uniform float opacity = 0.7;
uniform float emission_strength = 0.3;
uniform float wobble = 0.02;
uniform float shade_levels = 5.0;
uniform float quantization = 0.35;
uniform float dither_strength = 0.7;
uniform float soft_alpha = 0.15;
uniform bool flat_unshaded = false;
uniform bool dither_mode = false;
instance uniform float life_alpha = 0.0;
instance uniform float effect_time = 0.0;
instance uniform float tint_mix = 0.5;
varying vec3 view_normal;
varying vec3 view_position;
void vertex() {{
    VERTEX += normalize(VERTEX + vec3(0.0001)) * sin(dot(VERTEX,vec3(11.0,7.0,13.0))+floor(effect_time*12.0)*0.45)*wobble;
    view_normal = normalize(MODELVIEW_NORMAL_MATRIX * NORMAL);
    view_position = (MODELVIEW_MATRIX * vec4(VERTEX,1.0)).xyz;
}}
void fragment() {{
    vec3 normal = normalize(view_normal);
    vec3 light_dir = normalize((VIEW_MATRIX*vec4(-0.4,0.85,0.5,0.0)).xyz);
    float light = max(dot(normal,light_dir)*0.5+0.5,0.0);
    float shade = flat_unshaded ? 1.0 : 0.32+0.68*floor(light*shade_levels)/shade_levels;
    vec3 color = mix(color_a.rgb,color_b.rgb,clamp(UV.x*0.6+tint_mix*0.4,0.0,1.0));
    color = mix(color,floor(color*12.0+0.5)/12.0,quantization);
    float alpha = opacity*life_alpha*mix(1.0,pow(abs(dot(normal,normalize(-view_position))),0.5),soft_alpha);
    if(dither_mode) {{
        int x=int(mod(FRAGCOORD.x,4.0)); int y=int(mod(FRAGCOORD.y,4.0));
        float bayer[16] = float[16](0.0,8.0,2.0,10.0,12.0,4.0,14.0,6.0,3.0,11.0,1.0,9.0,15.0,7.0,13.0,5.0);
        float threshold=mix(0.5,(bayer[y*4+x]+0.5)/16.0,dither_strength);
        if(alpha<threshold){{discard;}} alpha=1.0;
    }}
    ALBEDO=color*(shade+emission_strength);
    ALPHA=alpha;
}}
'''


def color(value):
    # Godot resource source_color uniforms store sRGB Color; renderer converts them.
    return 'Color('+', '.join(str(int(value[i:i+2],16)/255) for i in (1,3,5))+', 1)'


def export(data, output, resource):
    output=Path(output);(output/'meshes').mkdir();(output/'materials').mkdir()
    recipe=data['recipe'];p=recipe['parameters']
    for name,mesh in data['meshes'].items():
        write_obj(mesh,output/'meshes'/f'{name}.obj')
    for key,layer in recipe['layers'].items():
        (output/'materials'/f'{key}.gdshader').write_text(shader(layer),encoding='utf-8')
        opacity=layer['opacity'];emission=layer['emission']*(p['core_brightness'] if key=='core' else 1)
        a,b=layer['color'],layer['color_b']
        if key=='smoke':
            def darken(c): return '#'+''.join(f'{round(int(c[i:i+2],16)*(1-p["smoke_darkness"]*.7)):02x}' for i in (1,3,5))
            a,b=darken(a),darken(b)
        text=f'''[gd_resource type="ShaderMaterial" load_steps=2 format=3]
[ext_resource type="Shader" path="{resource}/materials/{key}.gdshader" id="1"]
[resource]
shader = ExtResource("1")
shader_parameter/color_a = {color(a)}
shader_parameter/color_b = {color(b)}
shader_parameter/opacity = {opacity}
shader_parameter/emission_strength = {emission}
shader_parameter/wobble = {p['vertex_wobble']}
shader_parameter/shade_levels = {float(p['posterization'])}
shader_parameter/quantization = {p['palette_quantization']}
shader_parameter/dither_strength = {p['alpha_dithering']}
shader_parameter/soft_alpha = {layer['soft_alpha']}
shader_parameter/flat_unshaded = {str(layer['unshaded']).lower()}
shader_parameter/dither_mode = {str(layer['blend']=='DITHER').lower()}
'''
        (output/'materials'/f'{key}.tres').write_text(text,encoding='utf-8')
    for script in ('player.gd','review.gd'):
        shutil.copyfile(HERE/'mesh_godot'/script,output/script)
    manifest={key:value for key,value in data.items() if key!='meshes'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    refs=[f'[ext_resource type="Script" path="{resource}/player.gd" id="Player"]']
    refs.extend(f'[ext_resource type="ShaderMaterial" path="{resource}/materials/{key}.tres" id="Mat_{key}"]' for key in recipe['layers'])
    refs.extend(f'[ext_resource type="ArrayMesh" path="{resource}/meshes/{name}.obj" id="Mesh_{name}"]' for name in data['meshes'])
    root_name='MeshExplosion3D' if recipe['effect']=='MESH_EXPLOSION_3D' else 'ProceduralMeshEffect'
    nodes=[f'[node name="{root_name}" type="Node3D"]\nscript = ExtResource("Player")\nmanifest_path = "{resource}/manifest.json"',
           '[node name="Layers" type="Node3D" parent="."]']
    for key in recipe['layers']:
        nodes.append(f'[node name="{key}" type="Node3D" parent="Layers"]')
        for part in data['parts']:
            if part['layer']!=key:continue
            nodes.append(f'[node name="{part["name"]}" type="MeshInstance3D" parent="Layers/{key}"]\n'
                         f'mesh = ExtResource("Mesh_{part["mesh"]}")\nmaterial_override = ExtResource("Mat_{key}")\n'
                         'cast_shadow = 0\nvisible = false\nextra_cull_margin = 0.5')
    (output/'explosion.tscn').write_text(f'[gd_scene load_steps={len(refs)+1} format=3]\n\n'+'\n'.join(refs)+'\n\n'+'\n\n'.join(nodes)+'\n',encoding='utf-8')
    # Generic entry point is a lightweight alias; the legacy name remains valid.
    (output/'effect.tscn').write_text(f'[gd_scene load_steps=2 format=3]\n'
        f'[ext_resource type="PackedScene" path="{resource}/explosion.tscn" id="1"]\n'
        '[node name="Effect" instance=ExtResource("1")]\n',encoding='utf-8')
    # Reuse only the neutral stage construction from the sprite prototype; its
    # effect, shader and runtime player are all replaced by the mesh implementation.
    from godot_export import write_godot
    import tempfile
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        write_godot(tmp,resource,{'parameters':{'explosion_size':4}},dict(emission=False,cols=1,rows=1,frame_size=128,fps=16,frame_count=32))
        stage=(Path(tmp)/'review.tscn').read_text().replace('PSXExplosionReview','MeshExplosionReview')
    (output/'review.tscn').write_text(stage,encoding='utf-8')
    (output/'README.txt').write_text(recipe['effect']+': real triangle meshes; no billboard or flipbook.\n'
        'Open review.tscn. Drag to orbit, wheel to zoom; R restarts, Space pauses.\n'
        'Reusable effect: effect.tscn (explosion.tscn retained). Call restart(); seek(seconds) supports scrubbing. finished marks one-shot completion.\n'
        'OBJ files are generated outputs. Editable source is *.meshvfx.json plus Tools/Art/VFXFactory/mesh_*.py.\n'
        'Per-layer ShaderMaterials: alpha, additive, or Bayer dither/scissor. Instance uniforms isolate playback.\n'
        'Forward+ renderer (Godot 4.6). Transparent mesh overlaps can show alpha sorting artifacts; DITHER writes depth when enabled.\n'
        'No gameplay, collision, lights, camera-facing sprites, particle solver or character dependencies.\n',encoding='utf-8')
