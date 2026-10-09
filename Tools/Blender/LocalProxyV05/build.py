"""Build native V05 and attach to existing hosts without changing LEVEL_PROXY mesh."""
import bpy
import importlib.util
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REPORT=ROOT/'Docs/Reviews/LocalProxyV05'
spec=importlib.util.spec_from_file_location('v05generator',HERE/'generator.py');gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
sys.path.insert(0,str(HERE.parent/'LevelBlockout'));from metrics import load_metrics


def attach(obj,source,group,mode=0,drivers=True):
    for m in list(obj.modifiers):
        if m.type=='NODES' and m.node_group and m.node_group.name.startswith('GN_LevelProxyGenerator_'):obj.modifiers.remove(m)
    if obj.animation_data:
        for fc in list(obj.animation_data.drivers):obj.driver_remove(fc.data_path)
    m=obj.modifiers.new('V05 Local Variety','NODES');m.node_group=group;m.show_in_editmode=True
    ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    m[ids['Proxy']]=source;m[ids['Cutter']]=bpy.data.objects.get('LEVEL_CUTTER');m[ids['Output Mode']]=mode
    for name,kind,value,low,high,desc in gen.CONTROLS:
        if name not in source:source[name]=value
        ui={'description':desc}
        if low is not None:ui.update(min=low,max=high,soft_min=low,soft_max=high)
        source.id_properties_ui(name).update(**ui)
        m[ids[name]]=source[name]
        if drivers:
            fc=m.driver_add('["'+ids[name]+'"]');fc.driver.type='SUM';v=fc.driver.variables.new();v.name='control';v.type='SINGLE_PROP';v.targets[0].id=source;v.targets[0].data_path='["'+name+'"]'
    source.update_tag();obj.update_tag();return m


def build_graph():
    manifest=json.loads((REPORT/'library_manifest.json').read_text());old=bpy.data.node_groups.get(gen.NAME)
    if old:old.name=gen.NAME+'_REPLACED'
    group=gen.build(load_metrics()['values'],manifest)
    if old:
        for o in bpy.data.objects:
            for m in o.modifiers:
                if m.type=='NODES' and m.node_group==old:m.node_group=group
        bpy.data.node_groups.remove(old)
    print('V05_GROUP',len(group.nodes));return group


def handoff_attach(group):
    source=bpy.data.objects['LEVEL_PROXY']
    refs=bpy.data.collections.get('V04_LOCAL_OUTPUT_REFERENCE')
    if not refs:
        refs=bpy.data.collections.new('V04_LOCAL_OUTPUT_REFERENCE');bpy.context.scene.collection.children.link(refs);refs.hide_viewport=True;refs.hide_render=True
        for name in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']:
            o=bpy.data.objects[name].copy();o.name='V04_REFERENCE_'+name;refs.objects.link(o)
    for name,mode in [('LEVEL_GENERATED_OUTPUT',0),('GRAPPLE_CANDIDATES',1)]:attach(bpy.data.objects[name],source,group,mode)
    bpy.context.view_layer.update();print('V05_ATTACHED; authored proxy mesh untouched')


if __name__=='__main__':build_graph()
