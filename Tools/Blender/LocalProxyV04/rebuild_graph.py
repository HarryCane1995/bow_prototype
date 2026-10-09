"""Rebuild only our native graph; preserve all source meshes and control values."""
import bpy
import importlib.util
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('local_proxy_generator',HERE/'generator.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sys.path.insert(0,str(HERE.parent/'LevelBlockout'))
from metrics import load_metrics
old=bpy.data.node_groups[module.NAME]
users=[m for o in bpy.data.objects for m in o.modifiers if m.type=='NODES' and m.node_group==old]
old.name=module.NAME+'_REPLACED'
new=module.build(load_metrics()['values'],bpy.data.objects['V04L_UNIT_WEDGE'])
for m in users:m.node_group=new
bpy.data.node_groups.remove(old)
bpy.context.view_layer.update()
print('REBUILT',new.name,len(new.nodes),'nodes;',len(users),'hosts; source meshes untouched')
