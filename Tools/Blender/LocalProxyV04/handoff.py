"""Persist documentation and Blender-only handoff; verify preserved input assets."""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Euler

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV04'


def meshhash(o):
    return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest() if o.type=='MESH' else None


def main():
    baseline=json.loads((REPORT/'baseline_objects.json').read_text());changed=[];missing=[]
    for name,expected in baseline.items():
        actual='V02_GENERATED_OUTPUT_REFERENCE' if name=='LEVEL_GENERATED_OUTPUT' else name
        o=bpy.data.objects.get(actual)
        if not o:missing.append(name);continue
        mods=[list((m.name,m.type,m.node_group.name if m.type=='NODES' and m.node_group else None)) for m in o.modifiers]
        if meshhash(o)!=expected['mesh'] or [list(r) for r in o.matrix_world]!=expected['matrix'] or mods!=expected['mods']:changed.append(name)
    assert not missing and not changed,(missing,changed)
    original=bpy.data.objects['UX_TEST_V04_PROXY'];proxy=bpy.data.objects['LEVEL_PROXY']
    # The user may keep authoring while API work proceeds. Preserve those live
    # edits; equality to our initial copy is deliberately NOT a save condition.
    assert proxy.data!=original.data and not proxy.modifiers
    godot=json.loads((REPORT/'baseline_godot_files.json').read_text())
    drift=[name for name,digest in godot.items() if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    assert not drift,drift
    for name in ['V04_QUICKSTART','V04_MANUAL_TEST_CHECKLIST']:
        text=bpy.data.texts.get(name) or bpy.data.texts.new(name);text.clear();text.write((REPORT/(name+'.txt')).read_text(encoding='utf-8'));text.cursor_set(0)
    panel=bpy.data.texts.get('V04_CONTROLS_PANEL.py') or bpy.data.texts.new('V04_CONTROLS_PANEL.py');panel.clear();panel.write((HERE/'panel.py').read_text(encoding='utf-8'));panel.use_module=False
    exec(compile(panel.as_string(),'V04_CONTROLS_PANEL.py','exec'),{'__name__':'__main__'})
    # The earlier bounds-based convenience panel would offer to attach the old
    # generator to LEVEL_PROXY. Hide that panel for this session, retain its text.
    previous=getattr(bpy.types,'V04_PT_proxy',None)
    if previous:bpy.utils.unregister_class(previous)
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:o.select_set(False)
    proxy.hide_set(False);proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
    bpy.context.tool_settings.mesh_select_mode=(False,False,True)
    bpy.context.view_layer.update()
    for a in bpy.context.screen.areas:
        s=a.spaces.active
        if a.type=='TEXT_EDITOR':s.text=bpy.data.texts['V04_QUICKSTART'];s.top=0
        elif a.type=='PROPERTIES':
            s.use_pin_id=False;s.pin_id=None
            try:s.context='OBJECT'
            except TypeError:pass
        elif a.type=='VIEW_3D':
            s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.show_cavity=True;s.shading.cavity_type='BOTH';s.overlay.show_overlays=True
            s.region_3d.view_location=(140,-9,13);s.region_3d.view_distance=115;s.region_3d.view_rotation=Euler((math.radians(60),0,math.radians(25))).to_quaternion();s.region_3d.update()
        a.tag_redraw()
    bpy.context.workspace.name='V04_LOCAL_PROXY'
    bpy.context.view_layer.update()
    group=bpy.data.node_groups['GN_LevelProxyGenerator_v04']
    result={'preserved_original_objects':len(baseline),'missing':missing,'changed_mesh_transform_or_modifier':changed,'source_copy_hash':meshhash(proxy),'source_faces':len(proxy.data.polygons),'source_vertices':len(proxy.data.vertices),'live_edits_since_initial_copy_preserved':meshhash(proxy)!=baseline['UX_TEST_V04_PROXY']['mesh'],'old_reference_renamed':'LEVEL_GENERATED_OUTPUT -> V02_GENERATED_OUTPUT_REFERENCE','godot_files_unchanged':len(godot),'godot_drift':drift,'remaining_qa_objects':[o.name for o in bpy.data.objects if o.name.startswith('TEST_LPV04_')],'nodes':len(group.nodes),'bounding_box_nodes':sum(n.bl_idname=='GeometryNodeBoundBox' for n in group.nodes),'active':proxy.name,'mode':bpy.context.mode,'controls':{k:proxy[k] for k in ['Seed','Preview Quality','Use Cutter']},'drivers':{name:all(fc.driver.is_valid for fc in bpy.data.objects[name].animation_data.drivers) for name in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']},'computer_use_calls':0,'godot_qa_or_export':False,'human_ui_test':'NOT PERFORMED; user will test'}
    assert not result['remaining_qa_objects']
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,check_existing=False)
    result['blend']=bpy.data.filepath;result['blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
    (REPORT/'handoff.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
