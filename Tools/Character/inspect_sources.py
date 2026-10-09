import bpy, json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
result={}
for name in ['BlenderAssets/Bow_Assembly.blend','BlenderAssets/Bow.blend','Assets/Models/Player/FP_Hands_Blocking.blend','Assets/Models/Player/FP_Slide_Legs.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(root/name))
    result[name]={'meshes':[{'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'materials':[m.name if m else '' for m in o.data.materials]} for o in bpy.context.scene.objects if o.type=='MESH'], 'rigs':{o.name:[b.name for b in o.data.bones] for o in bpy.context.scene.objects if o.type=='ARMATURE'}}
(root/'.godot/hero-pass/source-audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
