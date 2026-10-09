"""Copy only V05 rhythm dependencies; the reference node group stays untouched."""
import bpy
NAME='GN_V06_Rhythm_FromV05'
def build():
    if NAME in bpy.data.node_groups:return bpy.data.node_groups[NAME]
    tree=bpy.data.node_groups['GN_LevelProxyGenerator_v05'].copy();tree.name=NAME
    output=next(n for n in tree.nodes if n.bl_idname=='NodeGroupOutput')
    rhythm=tree.nodes['Points to Vertices'].outputs[0]
    assert tree.nodes['Points to Vertices'].inputs[0].links[0].from_node.name=='lp_center'
    for link in list(output.inputs[0].links):tree.links.remove(link)
    for s in list(tree.interface.items_tree):
        if s.item_type=='SOCKET' and s.in_out=='OUTPUT':tree.interface.remove(s)
    tree.interface.new_socket(name='Rhythm',in_out='OUTPUT',socket_type='NodeSocketGeometry');tree.links.new(rhythm,output.inputs['Rhythm'])
    keep={output};queue=[output]
    while queue:
        n=queue.pop()
        for link in tree.links:
            if link.to_node==n and link.from_node not in keep:keep.add(link.from_node);queue.append(link.from_node)
    for n in list(tree.nodes):
        if n not in keep:tree.nodes.remove(n)
    assert not any(n.bl_idname=='GeometryNodeObjectInfo' and n.inputs['Object'].default_value and n.inputs['Object'].default_value.name.startswith('V05_LIB') for n in tree.nodes)
    tree.description='V05 metric spans, required-marker envelope guard and Length Variation, with all mesh-library filling removed.'
    return tree
