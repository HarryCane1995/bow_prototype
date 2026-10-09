"""Read/evaluate the saved .blend in a separate background process. Never save it."""
import bpy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'Docs/Reviews/LocalProxyV05'
result={};bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
for name in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']:
    obj=bpy.data.objects[name];e=obj.evaluated_get(dg);m=e.to_mesh();coords=[tuple(round(c,5) for c in v.co) for v in m.vertices];faces=sorted(tuple(sorted(coords[i] for i in p.vertices)) for p in m.polygons)
    result[name]={'vertices':len(m.vertices),'faces':len(m.polygons),'hash':hashlib.sha256(repr(faces).encode()).hexdigest(),'drivers_valid':all(fc.driver.is_valid for fc in obj.animation_data.drivers),'warnings':[str(w) for w in obj.modifiers[0].node_warnings]};e.to_mesh_clear()
source=bpy.data.objects['LEVEL_PROXY'];result['source']={'vertices':len(source.data.vertices),'faces':len(source.data.polygons),'modifiers':len(source.modifiers),'seed':source['Seed']}
result['texts']={n:len(bpy.data.texts[n].as_string()) for n in ['V05_QUICKSTART','V05_MANUAL_TEST_CHECKLIST']};result['library_count']=len(bpy.data.collections['V05_GAMEPLAY_MESH_LIBRARY'].objects);result['autoexec_enabled']=bpy.context.preferences.filepaths.use_scripts_auto_execute
(REPORT/'saved_file_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('V05_SAVED_VERIFIED',json.dumps(result))
