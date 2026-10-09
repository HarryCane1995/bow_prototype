"""Preserve the live authored file and immutable V05 reference before V06."""
import bpy,json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];REPORT=ROOT/'Docs/Reviews/LocalProxyV06'
def meshhash(o):
    return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest() if o.type=='MESH' else None
def state(o):
    return {'mesh':meshhash(o),'basis':[list(r) for r in o.matrix_basis],'parent':o.parent.name if o.parent else None,'parent_inverse':[list(r) for r in o.matrix_parent_inverse],'mods':[(m.name,m.type,m.node_group.name if m.type=='NODES' and m.node_group else None) for m in o.modifiers]}
def main():
    REPORT.mkdir(parents=True,exist_ok=True);(REPORT/'.gdignore').touch()
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    backup=REPORT/('before_v06_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True,check_existing=False)
    (REPORT/'baseline_objects.json').write_text(json.dumps({o.name:state(o) for o in bpy.data.objects},indent=2))
    extensions={'.tscn','.cs','.gd','.tres','.gdshader','.glb','.gltf','.godot'}
    paths=[p for folder in ['Scenes','Scripts','Resources','Assets'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in extensions]+[ROOT/'project.godot']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (REPORT/'baseline_godot_files.json').write_text(json.dumps(hashes,indent=2))
    refs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Tools/Blender/LocalProxyV05').glob('*.py')}
    (REPORT/'baseline_v05_files.json').write_text(json.dumps(refs,indent=2))
    sys.path.insert(0,str(ROOT/'Tools/Blender/LevelBlockout'));from metrics import load_metrics
    metrics=load_metrics();(REPORT/'movement_metrics.json').write_text(json.dumps(metrics,indent=2))
    print('V06_BASELINE',backup,'objects',len(bpy.data.objects),'godot_hashes',len(hashes),'air',metrics['values']['air_jump'])
if __name__=='__main__':main()
