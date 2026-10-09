"""Developer-only graph iteration; preserves every manual mesh and modifier control.

Never a production runtime update dependency. Explicitly run only while changing
the construction recipe; ordinary Blender editing needs no script.
"""
import bpy,sys,importlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent/'LevelBlockout'))
import geometry,region
importlib.reload(geometry);importlib.reload(region)
from geometry import SpatialGraph,ROLES
from region import build_region
from metrics import load_metrics
import json,math
from mathutils import Euler
movement=load_metrics();M=movement['values']
EXPECTED=ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
assert Path(bpy.data.filepath)==EXPECTED
out=bpy.data.objects['LEVEL_GENERATED_OUTPUT'];old=out.modifiers[0]
assert old.node_group.name=='GN_LevelBlockout_Generator_v02'
previous={s.name:old[s.identifier] for s in old.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
old_main=old.node_group;old_region=bpy.data.node_groups['V02_SpatialBay']
old_main.name='V02_PREVIOUS_MAIN';old_region.name='V02_PREVIOUS_BAY'
out.modifiers.remove(old)
volume=bpy.data.objects['LEVEL_VOLUME'];cutter=bpy.data.objects['LEVEL_CUTTER'];spawn=bpy.data.objects['PLAYER_SPAWN'];wedge=bpy.data.objects['V02_INTERNAL_UNIT_RAMP']
cols={n:bpy.data.collections['V02_'+n] for n in ('VOLUME','CUTTER','OUTPUT','GUIDES','INTERNAL')}
source=(HERE/'build.py').read_text(encoding='utf-8')
# Only the graph-building block; object creation and authoring mesh data are untouched.
source=source[source.index('region=build_region(M,wedge)'):source.index('for o in bpy.context.selected_objects:')]
exec(compile(source,str(HERE/'build.py')+' [graph only]','exec'))
for s in mod.node_group.interface.items_tree:
    if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name in previous:mod[s.identifier]=previous[s.name]
bpy.data.node_groups.remove(old_main);bpy.data.node_groups.remove(old_region)
out.update_tag();bpy.context.view_layer.update()
for area in bpy.context.screen.areas:area.tag_redraw()
print('Rebuilt owned V02 graph; manual authoring meshes and controls preserved')
