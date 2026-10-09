"""Build the new version without replacing V05 or editing the authored mesh."""
import bpy,importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def module(name):
    sp=importlib.util.spec_from_file_location('v06_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def build_graph():
    module('foundation').build();manifest=module('library').build();gen=module('generator');old=bpy.data.node_groups.get(gen.NAME)
    if old:old.name=gen.NAME+'_REPLACED'
    sys.path.insert(0,str(HERE.parent/'LevelBlockout'));from metrics import load_metrics
    new=gen.build(load_metrics()['values'],manifest)
    if old:
        for o in bpy.data.objects:
            for m in o.modifiers:
                if m.type=='NODES' and m.node_group==old:m.node_group=new
        bpy.data.node_groups.remove(old)
    print('V06_BUILT',len(new.nodes),'nodes; source untouched');return new
def attach():
    gen=module('generator');group=bpy.data.node_groups[gen.NAME];source=bpy.data.objects['LEVEL_PROXY']
    c=bpy.data.collections.get('V05_OUTPUT_REFERENCE')
    if not c:
        c=bpy.data.collections.new('V05_OUTPUT_REFERENCE');bpy.context.scene.collection.children.link(c);c.hide_viewport=True;c.hide_render=True
        for name in ['LEVEL_GENERATED_OUTPUT','GRAPPLE_CANDIDATES']:
            ref=bpy.data.objects[name].copy();ref.name='V05_REFERENCE_'+name;c.objects.link(ref)
    for name,mode in [('LEVEL_GENERATED_OUTPUT',0),('GRAPPLE_CANDIDATES',1)]:
        obj=bpy.data.objects[name]
        for m in list(obj.modifiers):
            if m.type=='NODES' and m.node_group and m.node_group.name.startswith('GN_LevelProxyGenerator_'):obj.modifiers.remove(m)
        if obj.animation_data:
            for fc in list(obj.animation_data.drivers):obj.driver_remove(fc.data_path)
        m=obj.modifiers.new('V06 Composition','NODES');m.node_group=group;m.show_in_editmode=True
        ids={s.name:s.identifier for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
        m[ids['Proxy']]=source;m[ids['Cutter']]=bpy.data.objects.get('LEVEL_CUTTER');m[ids['Output Mode']]=mode
        for key,kind,value,lo,hi,desc in gen.CONTROLS:
            if key not in source:source[key]=value
            ui={'description':desc}
            if lo is not None:ui.update(min=lo,max=hi,soft_min=lo,soft_max=hi)
            source.id_properties_ui(key).update(**ui);m[ids[key]]=source[key]
            fc=m.driver_add('["'+ids[key]+'"]');fc.driver.type='SUM';v=fc.driver.variables.new();v.name='control';v.type='SINGLE_PROP';v.targets[0].id=source;v.targets[0].data_path='["'+key+'"]'
        obj.update_tag()
    source.update_tag();bpy.context.view_layer.update();print('V06_ATTACHED')
if __name__=='__main__':build_graph()
