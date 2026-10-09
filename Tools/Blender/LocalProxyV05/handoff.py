"""Save the Blender-only deliverable, current author edits and a preservation audit."""
import bpy,hashlib,json,math
from pathlib import Path
from mathutils import Vector,Euler
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;REPORT=ROOT/'Docs/Reviews/LocalProxyV05'


def meshhash(o):
    return hashlib.sha256(repr(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])).encode()).hexdigest() if o.type=='MESH' else None


def main():
    source=bpy.data.objects['LEVEL_PROXY']
    # Flush normal Edit Mode data only; no mesh-building operation on the source.
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    baseline=json.loads((REPORT/'baseline_objects.json').read_text());changes=[];missing=[];stale_world_cache=[]
    persisted=json.loads((REPORT/'baseline_transforms.json').read_text())
    for name,before in baseline.items():
        o=bpy.data.objects.get(name)
        if not o:missing.append(name);continue
        # Hidden-object world caches can be stale in either session. Compare
        # persisted local transforms/parenting with the independently reopened
        # pre-V05 backup, without making reference objects visible or editable.
        transform={'basis':[list(r) for r in o.matrix_basis],'parent':o.parent.name if o.parent else None,'parent_inverse':[list(r) for r in o.matrix_parent_inverse]}
        if before['matrix']!=[list(r) for r in o.matrix_world]:stale_world_cache.append(name)
        mesh_changed=before['mesh']!=meshhash(o)
        matrix_changed=persisted[name]!=transform
        modifiers_changed=before['mods']!=[list((m.name,m.type,m.node_group.name if m.type=='NODES' and m.node_group else None)) for m in o.modifiers]
        if mesh_changed or matrix_changed or modifiers_changed:changes.append({'object':name,'mesh_changed':mesh_changed,'matrix_changed':matrix_changed,'modifiers_changed':modifiers_changed})
    unexpected=[r for r in changes if r['object'] not in ['LEVEL_PROXY','LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']]
    assert not missing and not unexpected,(missing,unexpected)
    assert len(source.modifiers)==0
    hashes=json.loads((REPORT/'baseline_godot_files.json').read_text());drift=[name for name,h in hashes.items() if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h]
    assert not drift,drift
    assert not [o for o in bpy.data.objects if o.name.startswith('TEST_LPV05_') or o.name.startswith('_V05_RENDER')]
    for name in ['V05_QUICKSTART','V05_MANUAL_TEST_CHECKLIST']:
        t=bpy.data.texts.get(name) or bpy.data.texts.new(name);t.clear();t.write((REPORT/(name+'.txt')).read_text(encoding='utf-8'));t.cursor_set(0)
    t=bpy.data.texts.get('V05_CONTROLS_PANEL.py') or bpy.data.texts.new('V05_CONTROLS_PANEL.py');t.clear();t.write((HERE/'panel.py').read_text(encoding='utf-8'));t.use_module=False
    exec(compile(t.as_string(),'V05_CONTROLS_PANEL.py','exec'),{'__name__':'__main__'})
    for o in bpy.data.collections['V05_GAMEPLAY_MESH_LIBRARY'].objects:
        o['allowed_scale']='Uniform 0.65–1.35; RAMP uniform <=1 with extra X factor cot(angle)=0.364–1.0 for 45–70 degrees. No unbounded stretch.'
    for o in bpy.context.selected_objects:o.select_set(False)
    source.hide_set(False);source.select_set(True);bpy.context.view_layer.objects.active=source;bpy.context.tool_settings.mesh_select_mode=(False,False,True);bpy.context.view_layer.update()
    # Bounds are used ONLY for camera framing, never for generator layout.
    points=[source.matrix_world@v.co for v in source.data.vertices]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    for area in bpy.context.screen.areas:
        s=area.spaces.active
        if area.type=='TEXT_EDITOR':s.text=bpy.data.texts['V05_QUICKSTART'];s.top=0
        elif area.type=='VIEW_3D':
            s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.show_cavity=True;s.shading.cavity_type='BOTH';s.overlay.show_overlays=True
            s.region_3d.view_location=(low+high)/2;s.region_3d.view_distance=max((high-low).length*1.25,35);s.region_3d.view_rotation=Euler((math.radians(60),0,math.radians(25))).to_quaternion();s.region_3d.update()
        area.tag_redraw()
    bpy.context.workspace.name='V05_LOCAL_VARIETY'
    result={'version':'GN_LevelProxyGenerator_v05','changes':changes,'missing':missing,'unexpected_changes':unexpected,'source_vertices':len(source.data.vertices),'source_faces':len(source.data.polygons),'source_hash':meshhash(source),'source_has_modifiers':len(source.modifiers),'live_author_edits_preserved':baseline['LEVEL_PROXY']['mesh']!=meshhash(source),'godot_files_unchanged':len(hashes),'godot_drift':drift,'library_count':42,'old_v04_group_preserved':'GN_LevelProxyGenerator_v04' in bpy.data.node_groups,'controls':{k:source[k] for k in ['Seed','Length Variation','Debug Span Colors','Preview Quality','Use Cutter']},'drivers_valid':{n:all(fc.driver.is_valid for fc in bpy.data.objects[n].animation_data.drivers) for n in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']},'active':source.name,'computer_use':False,'godot_export_or_qa':False,'human_test':'not performed','nodes':len(bpy.data.node_groups['GN_LevelProxyGenerator_v05'].nodes),'foundation_nodes':len(bpy.data.node_groups['GN_V05_LocalSections_FromV04'].nodes)}
    result['reference_world_cache_stale_basis_verified']=stale_world_cache
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,check_existing=False)
    result['file']=bpy.data.filepath;result['blend_sha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();(REPORT/'handoff.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
