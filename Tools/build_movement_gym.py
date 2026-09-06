"""Generate only Level_Movement_Gym; existing levels and player are inputs.

Run from the repository root. Geometry is ordinary editable Godot primitives.
The adjacent JSON describes the same layout for reproducible playtests.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'Scenes/Levels/Level_Movement_Gym'
DEST.mkdir(parents=True, exist_ok=True)
subs, nodes, cells = [], [], []
names = ['FLOW', 'SLIDE FLOW', 'WALLRUN', 'WALL CHAIN', 'GRAPPLE',
         'GRAPPLE + AIR', 'MIXED ROUTE', 'DIAGONALS', 'MASTERY']
palette = {'floor': (.46,.49,.52), 'wall': (.72,.43,.18), 'anchor': (.1,.7,.82),
           'edge': (.77,.23,.18), 'start': (.22,.7,.4), 'stripe': (.88,.88,.78)}
for key,c in palette.items():
    subs += [f'[sub_resource type="StandardMaterial3D" id="mat_{key}"]\nalbedo_color = Color({c[0]},{c[1]},{c[2]},1)\nroughness = 1.0\n']

def box(name, xyz, size, material='floor', parent='Geometry', solid=True):
    ident='b'+str(len(subs)); vec=lambda x:', '.join(str(round(v,4)) for v in x)
    subs.append(f'[sub_resource type="BoxMesh" id="{ident}m"]\nsize = Vector3({vec(size)})\nmaterial = SubResource("mat_{material}")\n')
    if solid:
        subs.append(f'[sub_resource type="BoxShape3D" id="{ident}s"]\nsize = Vector3({vec(size)})\n')
        nodes.append(f'[node name="{name}" type="StaticBody3D" parent="{parent}"]\nposition = Vector3({vec(xyz)})\n')
        nodes.append(f'[node name="Mesh" type="MeshInstance3D" parent="{parent}/{name}"]\nmesh = SubResource("{ident}m")\n')
        nodes.append(f'[node name="Collision" type="CollisionShape3D" parent="{parent}/{name}"]\nshape = SubResource("{ident}s")\n')
    else: nodes.append(f'[node name="{name}" type="MeshInstance3D" parent="{parent}"]\nposition = Vector3({vec(xyz)})\nmesh = SubResource("{ident}m")\n')

def platform(name, start, end, x=0, width=14, height=0):
    if end <= start: return
    box(name,(x,height-1,-(start+end)/2),(width,2,end-start))
    for d in [start+.25,end-.25]:box(name+'_edge'+str(round(d,2)).replace('.','_'),(x,height+.012,-d),(width,.025,.3),'stripe',solid=False)

def wall(name,start,end,side,height=12):
    box(name,(side*5.0,height/2-2,-(start+end)/2),(1,height+4,end-start),'wall')

def anchor(name,d,x=0,y=10):
    nodes.append(f'[node name="{name}" parent="Anchors" instance=ExtResource("anchor")]\nposition = Vector3({x},{y},{-d})\n')
    # Thin non-colliding cross makes the original small detection sphere legible.
    box(name+'Back',(x,y,-d+.4),(2,.10,.10),'anchor',parent='Anchors',solid=False)
    box(name+'Stem',(x,y,-d+.4),(.10,2,.10),'anchor',parent='Anchors',solid=False)

platform('Start',-12,8,width=18)
section_starts=[]
cursor=8
for sec in range(9):
    start=cursor; section_starts.append(start)
    kind=['jump','slide','wall','chain','hook','hook_air','mixed','diagonal','mastery'][sec]
    section_length=300 if kind in ['mixed','mastery'] else 240
    cursor+=section_length
    length=100 if kind in ['mixed','mastery'] else 80 if kind in ['chain','hook_air'] else 60 if kind=='hook' else 40
    for j in range(section_length//length):
        s=start+j*length; side=-1 if j%2==0 else 1
        cell={'id':len(cells),'section':sec,'kind':kind,'start':s,'end':s+length,'side':side,'height':0}
        if kind in ['jump','slide','diagonal']:
            gap=6 if kind=='jump' else 11 if kind=='slide' else 14
            a=s+18; b=a+gap
            x=0 if kind!='diagonal' else (-6 if j%2==0 else 6)
            nx=0 if kind!='diagonal' else -x
            platform(f'S{sec}_{j}Approach',s,a,x=0 if kind=='diagonal' and j==0 else x,width=26 if kind=='diagonal' and j==0 else 16 if kind=='diagonal' else 14)
            platform(f'S{sec}_{j}Land',b,s+length,x=nx,width=16 if kind=='diagonal' else 14)
            cell.update(gap_start=a,gap_end=b,approach_x=x,landing_x=nx)
            if kind=='slide':
                box(f'S{sec}_{j}SlideLintel',(0,1.9,-(s+10)),(14,1,3),'wall')
                cell['slide_at']=s+5
        elif kind=='wall':
            a=s+10;b=s+34
            platform(f'S{sec}_{j}Approach',s,a);platform(f'S{sec}_{j}Land',b,s+length)
            wall(f'S{sec}_{j}Wall',a-7,b+2,side)
            cell.update(gap_start=a,gap_end=b,approach_x=side*3.8,landing_x=0,wall_jump=(j%3==1))
        elif kind=='chain':
            a=s+16;b=s+58
            platform(f'S{sec}_{j}Approach',s,a);platform(f'S{sec}_{j}Land',b,s+length,width=18)
            wall(f'S{sec}_{j}WallA',a-8,s+38,side);wall(f'S{sec}_{j}WallB',s+37,b+3,-side,height=18)
            cell.update(gap_start=a,gap_end=b,approach_x=side*3.8,landing_x=-side*3.8,wall_jump_at=s+25)
        elif kind in ['hook','hook_air']:
            a=s+15;b=s+(40 if kind=='hook' else 51)
            platform(f'S{sec}_{j}Approach',s,a,width=18);platform(f'S{sec}_{j}Land',b,s+length,width=20)
            ax=0 if kind=='hook' else side*4;ad=s+(30 if kind=='hook' else 38)
            anchor(f'S{sec}_{j}Anchor',ad,ax,10)
            cell.update(gap_start=a,gap_end=b,approach_x=0,landing_x=0,anchor=[ax,10,-ad],hook_at=s+9)
        else:
            a=s+18;b=s+60
            landing_x=-side*3.8 if j<2 else 0
            platform(f'S{sec}_{j}Approach',s,a,x=side*3.8,width=16)
            platform(f'S{sec}_{j}Land',b,s+length,x=landing_x,width=24,height=2 if kind=='mastery' and j==1 else 0)
            box(f'S{sec}_{j}ExitLine',(landing_x,(2 if kind=='mastery' and j==1 else 0)+.035,-s-length+5),(2,.04,6),'stripe',solid=False)
            wall(f'S{sec}_{j}Wall',s+11,s+36,side)
            anchor(f'S{sec}_{j}Anchor',s+43,-side*1.5,12)
            cell.update(gap_start=a,gap_end=b,approach_x=side*3.8,landing_x=landing_x,anchor=[-side*1.5,12,-s-43],hook_at=s+30,wall_jump_at=s+27,slide_at=s+5)
        cells.append(cell)
    nodes.append(f'[node name="Section{sec+1}" type="Label3D" parent="Signs"]\nposition = Vector3(0,4.5,{-start-6})\ntext = "{sec+1:02}  {names[sec]}"\nfont_size = 56\npixel_size = 0.009\nno_depth_test = false\n')
    box(f'CheckpointStripe{sec}',(0,.03,-start-1),(14,.04,1.3),'start',solid=False)

finish=cursor
platform('Finish',finish,finish+35,width=24)
box('FinishStripe',(0,.03,-finish-3),(24,.04,3),'start',solid=False)
for sec in range(10):
    d=section_starts[sec] if sec<9 else finish
    nodes.append(f'[node name="Spawn{sec}" type="Marker3D" parent="Spawns"]\nposition = Vector3(0,0.1,{0 if sec==0 else -d-2})\n')
    nodes.append(f'[node name="Gate{sec}" type="Area3D" parent="Checkpoints"]\nposition = Vector3(0,8,{-d})\ncollision_layer = 0\ncollision_mask = 1\nmetadata/index = {sec}\n')
    nodes.append(f'[node name="Shape" type="CollisionShape3D" parent="Checkpoints/Gate{sec}"]\nshape = SubResource("gate")\n')

subs += ['[sub_resource type="BoxShape3D" id="gate"]\nsize = Vector3(36,24,1)\n',
'''[sub_resource type="Environment" id="environment"]
background_mode = 1
background_color = Color(0.12,0.15,0.19,1)
ambient_light_source = 2
ambient_light_color = Color(0.85,0.89,1,1)
ambient_light_energy = 0.75
tonemap_mode = 0
''']
header='''[gd_scene format=3]
[ext_resource type="PackedScene" path="res://Scenes/Player.tscn" id="player"]
[ext_resource type="PackedScene" path="res://Scenes/GrappleAnchor.tscn" id="anchor"]
[ext_resource type="Script" path="res://Scripts/Levels/MovementGym/MovementGymCourse.cs" id="course"]
[ext_resource type="Script" path="res://Scripts/UI/CrosshairUI.cs" id="crosshair"]
'''
root='''[node name="Level_Movement_Gym" type="Node3D"]
script = ExtResource("course")
PlayerScene = ExtResource("player")
SectionNames = Array[String](NAMES)
[node name="Player" parent="." instance=ExtResource("player")]
position = Vector3(0,0.1,0)
[node name="Geometry" type="Node3D" parent="."]
[node name="Anchors" type="Node3D" parent="."]
[node name="Checkpoints" type="Node3D" parent="."]
[node name="Spawns" type="Node3D" parent="."]
[node name="Signs" type="Node3D" parent="."]
[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("environment")
[node name="Light" type="DirectionalLight3D" parent="."]
rotation_degrees = Vector3(-55,-30,0)
light_energy = 0.85
shadow_enabled = true
[node name="HUD" type="CanvasLayer" parent="."]
layer = 2
[node name="Readout" type="Label" parent="HUD"]
offset_left = 22.0
offset_top = 18.0
theme_override_colors/font_color = Color(1,1,1,1)
theme_override_colors/font_shadow_color = Color(0,0,0,1)
theme_override_constants/shadow_offset_x = 2
theme_override_constants/shadow_offset_y = 2
text = "MOVEMENT GYM"
[node name="Crosshair" type="Control" parent="HUD"]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
mouse_filter = 2
script = ExtResource("crosshair")
'''.replace('NAMES',json.dumps(names))
(DEST/'Level_Movement_Gym.tscn').write_text(header+'\n'+'\n'.join(subs)+root+'\n'.join(nodes),encoding='utf-8')
(DEST/'course_layout.json').write_text(json.dumps({'length':finish,'sections':names,'cells':cells},indent=2),encoding='utf-8')
print(f'Generated {len(cells)} encounters; finish at {finish} m')
