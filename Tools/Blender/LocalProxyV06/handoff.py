"""Audit preservation, embed instructions and save the current authored file."""
import bpy,importlib.util,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV06'
def load(name):
    sp=importlib.util.spec_from_file_location('v06_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def fingerprint(tree):
    rows=[]
    for n in tree.nodes:
        props={}
        for key in ['operation','data_type','domain','input_type','transform_space','solver','primary_axis','secondary_axis']:
            if hasattr(n,key):props[key]=getattr(n,key)
        inputs=[]
        for s in n.inputs:
            if not hasattr(s,'default_value'):continue
            value=s.default_value
            if isinstance(value,bpy.types.ID):value=value.name
            elif not isinstance(value,(str,int,float,bool,type(None))):
                try:value=list(value)
                except TypeError:value=str(value)
            inputs.append([s.identifier,value])
        rows.append([n.name,n.bl_idname,n.node_tree.name if n.bl_idname=='GeometryNodeGroup' else None,props,inputs])
    links=sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier,l.multi_input_sort_id) for l in tree.links)
    return hashlib.sha256(json.dumps([sorted(rows),links],sort_keys=True).encode()).hexdigest()
def main():
    src=bpy.data.objects['LEVEL_PROXY']
    if src.mode=='EDIT':src.update_from_editmode()
    baseline=json.loads((REPORT/'baseline_objects.json').read_text());state=load('baseline').state;missing=[];changes=[]
    for name,before in baseline.items():
        o=bpy.data.objects.get(name)
        if not o:missing.append(name);continue
        now=json.loads(json.dumps(state(o)))
        if before!=now:changes.append({'object':name,'fields':[k for k in now if before[k]!=now[k]]})
    unexpected=[r for r in changes if r['object'] not in ['LEVEL_PROXY','LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']]
    assert not missing and not unexpected,(missing,unexpected)
    assert len(src.modifiers)==0
    hashes=json.loads((REPORT/'baseline_godot_files.json').read_text());v05hashes=json.loads((REPORT/'baseline_v05_files.json').read_text())
    drift=[n for n,h in (hashes|v05hashes).items() if not (ROOT/n).exists() or hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]
    assert not drift,drift
    assert not [o.name for o in bpy.data.objects if o.name.startswith('TEST_LPV06_')]
    for name in ['V06_QUICKSTART','V06_MANUAL_TEST_CHECKLIST']:
        t=bpy.data.texts.get(name) or bpy.data.texts.new(name);t.clear();t.write((REPORT/(name+'.txt')).read_text(encoding='utf-8'));t.cursor_set(0)
    t=bpy.data.texts.get('V06_CONTROLS_PANEL.py') or bpy.data.texts.new('V06_CONTROLS_PANEL.py');t.clear();t.write((HERE/'panel.py').read_text(encoding='utf-8'));t.use_module=False
    exec(compile(t.as_string(),'V06_CONTROLS_PANEL.py','exec'),{'__name__':'__main__'})
    src.id_properties_ui('Platform Density').update(description='V04 elevation lattice spacing, sampled every third beat in V06 (9.3–14.4 m before omissions).')
    if not getattr(bpy.context.window,'modal_operators',[]):
        for o in bpy.context.selected_objects:o.select_set(False)
        src.hide_set(False);src.select_set(True);bpy.context.view_layer.objects.active=src
    src['Debug Span Colors']=False;src['Debug Placement Volumes']=False;src['Preview Quality']=0;src.update_tag()
    bpy.context.view_layer.update();qa=load('qa');live={n:qa.q.snapshot(bpy.data.objects[n]) for n in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']}
    (REPORT/'live_before_save.json').write_text(json.dumps(live,indent=2))
    for area in bpy.context.screen.areas:
        if area.type=='TEXT_EDITOR':area.spaces.active.text=bpy.data.texts['V06_QUICKSTART'];area.spaces.active.top=0
        elif area.type=='VIEW_3D':area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL'
    bpy.context.workspace.name='V06_LOCAL_COMPOSITION'
    result={'version':'GN_LevelProxyGenerator_v06','source':qa.q.source_summary(src),'source_modifiers':len(src.modifiers),'changes':changes,'missing':missing,'unexpected_changes':unexpected,'godot_files_unchanged':len(hashes),'v05_builder_files_unchanged':len(v05hashes),'v05_library_count':len(bpy.data.collections['V05_GAMEPLAY_MESH_LIBRARY'].objects),'v05_node_count':len(bpy.data.node_groups['GN_LevelProxyGenerator_v05'].nodes),'v05_fingerprint':fingerprint(bpy.data.node_groups['GN_LevelProxyGenerator_v05']),'v06_node_count':len(bpy.data.node_groups['GN_LevelProxyGenerator_v06'].nodes),'controls':{k:src[k] for k in load('panel').CONTROLS},'active':bpy.context.object.name if bpy.context.object else None,'drivers_valid':{n:all(f.driver.is_valid for f in bpy.data.objects[n].animation_data.drivers) for n in live},'computer_use':False,'godot_export_or_qa':False,'human_test':'not performed'}
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,check_existing=False)
    result['file']=bpy.data.filepath;result['blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();(REPORT/'handoff.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
