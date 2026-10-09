"""One-time additive setup. Never rerun against a user's existing LEVEL_PROXY."""
import importlib.util
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REPORT=ROOT/'Docs/Reviews/LocalProxyV04'
spec=importlib.util.spec_from_file_location('local_proxy_generator',HERE/'generator.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sys.path.insert(0,str(HERE.parent/'LevelBlockout'))
from metrics import load_metrics


def bind(obj, source, group, mode=0, drivers=True):
    mod=obj.modifiers.new('V04 Local Proxy Fill','NODES');mod.node_group=group
    mod.show_in_editmode=True;mod.show_on_cage=False
    ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    mod[ids['Proxy']]=source
    mod[ids['Cutter']]=bpy.data.objects.get('LEVEL_CUTTER')
    mod[ids['Output Mode']]=mode
    for name,kind,value,low,high,desc in module.CONTROLS:
        mod[ids[name]]=source.get(name,value)
        if drivers:
            fc=mod.driver_add('["'+ids[name]+'"]');fc.driver.type='SUM'
            var=fc.driver.variables.new();var.name='control';var.type='SINGLE_PROP';var.targets[0].id=source;var.targets[0].data_path='["'+name+'"]'
    return mod


def main():
    assert 'LEVEL_PROXY' not in bpy.data.objects, 'Existing authoring mesh: refusing one-time setup.'
    assert module.NAME not in bpy.data.node_groups
    assert (REPORT/'baseline_objects.json').exists()
    metrics=load_metrics();(REPORT/'movement_metrics.json').write_text(json.dumps(metrics,indent=2))
    original=bpy.data.objects['UX_TEST_V04_PROXY']
    if original.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    coll=bpy.data.collections.new('V04_LOCAL_PROXY_AUTHORING');bpy.context.scene.collection.children.link(coll)
    internal=bpy.data.collections.new('V04_LOCAL_INTERNAL');bpy.context.scene.collection.children.link(internal);internal.hide_viewport=True;internal.hide_render=True
    proxy=bpy.data.objects.new('LEVEL_PROXY',original.data.copy());coll.objects.link(proxy);proxy.matrix_world=original.matrix_world.copy()
    proxy.display_type='WIRE';proxy.show_in_front=False;proxy.hide_render=True;proxy.color=(.94,.66,.18,1)
    proxy['authoring']='Ordinary editable closed volume. Tab / E. Native GN reacts; no apply or Python regeneration.'
    proxy['source_reference']='UX_TEST_V04_PROXY retained unchanged with authored topology.'
    for name,kind,value,low,high,desc in module.CONTROLS:
        proxy[name]=value
        ui={'description':desc}
        if low is not None:ui.update(min=low,max=high,soft_min=low,soft_max=high)
        proxy.id_properties_ui(name).update(**ui)
    wedge=bpy.data.objects.new('V04L_UNIT_WEDGE',bpy.data.objects['V02_INTERNAL_UNIT_RAMP'].data.copy());internal.objects.link(wedge);wedge.hide_render=True;wedge.hide_select=True
    group=module.build(metrics['values'],wedge)
    # Object identity, data, modifiers and links of the V02 reference remain.
    old=bpy.data.objects.get('LEVEL_GENERATED_OUTPUT')
    if old:old.name='V02_GENERATED_OUTPUT_REFERENCE'
    hosts=[]
    for name,mode in [('LEVEL_GENERATED_OUTPUT',0),('GRAPPLE_CANDIDATES',1)]:
        obj=bpy.data.objects.new(name,bpy.data.meshes.new(name+'_HOST'));coll.objects.link(obj)
        obj.parent=proxy;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
        obj.hide_select=True;obj.display_type='SOLID';bind(obj,proxy,group,mode)
        if mode:obj.hide_render=True
        hosts.append(obj)
    for name in ['V04_PROXY_CHUNKS','V03_FLOW_COURSE','V02_OUTPUT','BLOCKOUT_OUTPUT','LEVEL_AUTHORING']:
        c=bpy.data.collections.get(name)
        if c:c.hide_viewport=True;c.hide_render=True
    original.hide_set(True);original.hide_render=True
    for name in ['LEVEL_VOLUME','LEVEL_CUTTER']:
        o=bpy.data.objects.get(name)
        if o:o.hide_set(True)
    for o in bpy.context.selected_objects:o.select_set(False)
    proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
    bpy.context.view_layer.update()
    print(json.dumps({'group':group.name,'nodes':len(group.nodes),'source':[len(proxy.data.vertices),len(proxy.data.polygons)],'old_source_preserved':original.name,'renamed_reference':old.name if old else None,'hosts':[o.name for o in hosts]}))


if __name__=='__main__':main()
