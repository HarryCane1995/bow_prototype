"""Background-only independent reopen. Never save or affect the live Blender UI."""
import bpy,importlib.util,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV06'
sp=importlib.util.spec_from_file_location('verify_handoff',HERE/'handoff.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
# Invocation opens the backup first, proving the V05 graph/library survived.
original=h.fingerprint(bpy.data.node_groups['GN_LevelProxyGenerator_v05'])
original_library={o.name:h.load('baseline').meshhash(o) for o in bpy.data.collections['V05_GAMEPLAY_MESH_LIBRARY'].objects}
target=json.loads((REPORT/'handoff.json').read_text())['file'];bpy.ops.wm.open_mainfile(filepath=target)
qa=h.load('qa');result={'v05_graph_unchanged':original==h.fingerprint(bpy.data.node_groups['GN_LevelProxyGenerator_v05']),'v05_library_unchanged':original_library=={o.name:h.load('baseline').meshhash(o) for o in bpy.data.collections['V05_GAMEPLAY_MESH_LIBRARY'].objects},'outputs':{n:qa.q.snapshot(bpy.data.objects[n]) for n in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']},'source':qa.q.source_summary(bpy.data.objects['LEVEL_PROXY']),'autoexec_enabled':bpy.context.preferences.filepaths.use_scripts_auto_execute,'texts':{n:len(bpy.data.texts[n].as_string()) for n in ['V06_QUICKSTART','V06_MANUAL_TEST_CHECKLIST']}}
live=json.loads((REPORT/'live_before_save.json').read_text());result['matches_live']={n:v['hash']==live[n]['hash'] for n,v in result['outputs'].items()}
qa.REPORT=REPORT/'SavedSnapshot';qa.REPORT.mkdir(exist_ok=True)
saved_qa=qa.authored()
result['saved_source_qa']={k:v for k,v in saved_qa.items() if k in ['source','overlap','required','surface_containment','helper_containment','timing']}
(REPORT/'saved_file_verification.json').write_text(json.dumps(result,indent=2));print('V06_SAVED_VERIFIED',json.dumps(result))
