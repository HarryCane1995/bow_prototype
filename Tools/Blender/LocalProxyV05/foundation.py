"""Extract and reuse the proven V04 local frames, cleaning and shaft lattice.

The original V04 node tree is never modified. Only dependencies of the exported
local sections remain in the copied subgroup; the old fill grammar is removed.
"""
import bpy

NAME='GN_V05_LocalSections_FromV04'


def build_foundation():
    assert NAME not in bpy.data.node_groups
    src=bpy.data.node_groups['GN_LevelProxyGenerator_v04'];tree=src.copy();tree.name=NAME
    oldout=next(n for n in tree.nodes if n.bl_idname=='NodeGroupOutput')
    horizontal=tree.nodes['Horizontal or inclined local patches'].outputs['Points']
    # The second local-point branch into the original first Join is the final
    # rounded shaft lattice. Follow links, do not depend on incidental node suffixes.
    joined=tree.nodes['Join Geometry']
    branches=[l.from_node for l in tree.links if l.to_node==joined]
    vertical=next(n for n in branches if any(l.from_node.bl_idname=='GeometryNodeSetPosition' and l.to_node==n for l in tree.links) and n!=branches[0]).outputs['Geometry']
    clean=tree.nodes['Evaluation-only coincident rings'].outputs['Geometry']
    stat=tree.nodes['Closed-volume guard']
    valid=next(l.to_node.outputs[0] for l in tree.links if l.from_node==stat and l.from_socket.name=='Sum')
    for link in list(tree.links):
        if link.to_node==oldout:tree.links.remove(link)
    for s in list(tree.interface.items_tree):
        if s.item_type=='SOCKET' and s.in_out=='OUTPUT':tree.interface.remove(s)
    for name,kind,value in [('Horizontal Patches','NodeSocketGeometry',horizontal),('Vertical Levels','NodeSocketGeometry',vertical),('Envelope','NodeSocketGeometry',clean),('Valid Volume','NodeSocketBool',valid)]:
        tree.interface.new_socket(name=name,in_out='OUTPUT',socket_type=kind);tree.links.new(value,oldout.inputs[name])
    keep={oldout};queue=[oldout]
    while queue:
        n=queue.pop()
        for link in tree.links:
            if link.to_node==n and link.from_node not in keep:keep.add(link.from_node);queue.append(link.from_node)
    for n in list(tree.nodes):
        if n not in keep:tree.nodes.remove(n)
    tree.description='Unchanged V04 local surface frames, cleaned authoritative volume and fixed-height shaft lattice. No whole-proxy bounds.'
    return tree
