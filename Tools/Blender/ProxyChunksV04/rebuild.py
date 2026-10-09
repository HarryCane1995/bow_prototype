"""Developer graph revision only. Never replaces authored proxy meshes or transforms."""
import bpy,sys,importlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent/'LevelBlockout'))
import generator;importlib.reload(generator)
from metrics import load_metrics
old=bpy.data.node_groups[generator.NAME]
instances=[]
for obj in bpy.data.objects:
    for mod in obj.modifiers:
        if mod.type=='NODES' and mod.node_group==old:
            values={s.name:mod[s.identifier] for s in old.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry'}
            instances.append((obj,mod,values))
new=generator.build(load_metrics()['values'],bpy.data.objects['V04_UNIT_WEDGE'])
for obj,mod,values in instances:
    mod.node_group=new
    for s in new.interface.items_tree:
        if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry':mod[s.identifier]=values.get(s.name,s.default_value)
    obj.update_tag()
bpy.data.node_groups.remove(old);new.name=generator.NAME;bpy.context.view_layer.update()
for mat in list(bpy.data.materials):
    if mat.name.startswith('M_V04_') and not mat.users:bpy.data.materials.remove(mat)
print('Revised V04 graph; preserved',len(instances),'proxy meshes and modifier values')
