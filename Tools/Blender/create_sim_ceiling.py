"""Create the editable Geometry Nodes simulation ceiling in Level_01."""

import math
import os
import runpy

import bpy


OBJECT_NAME = "ENV_SimCeiling_GN"
COLLECTION_NAME = "ENV_Simulation"
NODE_GROUP_NAME = "GN_SimCeiling"
MODIFIER_NAME = "Simulation Ceiling"

DEFAULTS = {
    "Size X": 1000.0,
    "Size Y": 1000.0,
    "Cell Size": 8.0,
    "Gap": 1.0,
    "Base Thickness": 18.5,
    "Height Variation": 50.0,
    "Vertical Offset Variation": 2.94,
    "Horizontal Jitter": 2.02,
    "Density": 1.0,
    "Seed": 140,
    "Edge Angle": math.radians(90.0),
    "Edge Angle Tolerance": math.radians(5.0),
    "Edge Radius": 0.08,
}


def _node(nodes, node_type, name, location):
    node = nodes.new(node_type)
    node.name = name
    node.label = name
    node.location = location
    return node


def _math(nodes, name, operation, location, value=None):
    node = _node(nodes, "ShaderNodeMath", name, location)
    node.operation = operation
    if value is not None:
        node.inputs[1].default_value = value
    return node


def _random_float(nodes, name, location, minimum, maximum):
    node = _node(nodes, "FunctionNodeRandomValue", name, location)
    node.data_type = "FLOAT"
    # Random Value exposes duplicate socket names for its vector/float/int modes.
    node.inputs[2].default_value = minimum
    node.inputs[3].default_value = maximum
    return node


def _seed_offset(nodes, links, group_input, offset, name, location):
    node = _math(nodes, name, "ADD", location, offset)
    links.new(group_input.outputs["Seed"], node.inputs[0])
    return node


def _new_input(interface, name, socket_type, default, minimum, maximum, subtype=None):
    socket = interface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)
    socket.default_value = default
    socket.min_value = minimum
    socket.max_value = maximum
    if subtype is not None:
        socket.subtype = subtype
    return socket


def _build_node_group(face_material, edge_material):
    old_group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if old_group is not None and old_group.users == 0:
        bpy.data.node_groups.remove(old_group)

    group = bpy.data.node_groups.new(NODE_GROUP_NAME, "GeometryNodeTree")
    interface = group.interface
    interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    _new_input(interface, "Size X", "NodeSocketFloat", DEFAULTS["Size X"], 10.0, 2000.0)
    _new_input(interface, "Size Y", "NodeSocketFloat", DEFAULTS["Size Y"], 10.0, 2000.0)
    _new_input(interface, "Cell Size", "NodeSocketFloat", DEFAULTS["Cell Size"], 2.0, 20.0)
    _new_input(interface, "Gap", "NodeSocketFloat", DEFAULTS["Gap"], 0.05, 4.0)
    _new_input(interface, "Base Thickness", "NodeSocketFloat", DEFAULTS["Base Thickness"], 0.5, 100.0)
    _new_input(interface, "Height Variation", "NodeSocketFloat", DEFAULTS["Height Variation"], 0.0, 100.0)
    _new_input(
        interface,
        "Vertical Offset Variation",
        "NodeSocketFloat",
        DEFAULTS["Vertical Offset Variation"],
        0.0,
        10.0,
    )
    _new_input(interface, "Horizontal Jitter", "NodeSocketFloat", DEFAULTS["Horizontal Jitter"], 0.0, 3.0)
    _new_input(interface, "Density", "NodeSocketFloat", DEFAULTS["Density"], 0.5, 1.0)
    _new_input(interface, "Seed", "NodeSocketInt", DEFAULTS["Seed"], 0, 100000)
    _new_input(
        interface,
        "Edge Angle",
        "NodeSocketFloat",
        DEFAULTS["Edge Angle"],
        0.0,
        math.pi,
        "ANGLE",
    )
    _new_input(
        interface,
        "Edge Angle Tolerance",
        "NodeSocketFloat",
        DEFAULTS["Edge Angle Tolerance"],
        0.0,
        math.radians(45.0),
        "ANGLE",
    )
    _new_input(interface, "Edge Radius", "NodeSocketFloat", DEFAULTS["Edge Radius"], 0.01, 0.5)

    nodes = group.nodes
    links = group.links
    group_input = _node(nodes, "NodeGroupInput", "Ceiling Controls", (-1500, 100))
    group_output = _node(nodes, "NodeGroupOutput", "Ceiling Geometry", (1050, 100))

    grid = _node(nodes, "GeometryNodeMeshGrid", "Architectural Grid", (-1200, 520))
    links.new(group_input.outputs["Size X"], grid.inputs["Size X"])
    links.new(group_input.outputs["Size Y"], grid.inputs["Size Y"])

    count_x_divide = _math(nodes, "Cells X", "DIVIDE", (-1420, 700))
    count_x_floor = _math(nodes, "Whole Cells X", "FLOOR", (-1230, 700))
    count_x_add = _math(nodes, "Grid Vertices X", "ADD", (-1040, 700), 1.0)
    links.new(group_input.outputs["Size X"], count_x_divide.inputs[0])
    links.new(group_input.outputs["Cell Size"], count_x_divide.inputs[1])
    links.new(count_x_divide.outputs[0], count_x_floor.inputs[0])
    links.new(count_x_floor.outputs[0], count_x_add.inputs[0])
    links.new(count_x_add.outputs[0], grid.inputs["Vertices X"])

    count_y_divide = _math(nodes, "Cells Y", "DIVIDE", (-1420, 860))
    count_y_floor = _math(nodes, "Whole Cells Y", "FLOOR", (-1230, 860))
    count_y_add = _math(nodes, "Grid Vertices Y", "ADD", (-1040, 860), 1.0)
    links.new(group_input.outputs["Size Y"], count_y_divide.inputs[0])
    links.new(group_input.outputs["Cell Size"], count_y_divide.inputs[1])
    links.new(count_y_divide.outputs[0], count_y_floor.inputs[0])
    links.new(count_y_floor.outputs[0], count_y_add.inputs[0])
    links.new(count_y_add.outputs[0], grid.inputs["Vertices Y"])

    index = _node(nodes, "GeometryNodeInputIndex", "Cell Index", (-1450, -80))
    density_random = _random_float(nodes, "Rare Controlled Gaps", (-1220, 250), 0.0, 1.0)
    links.new(index.outputs["Index"], density_random.inputs["ID"])
    links.new(group_input.outputs["Seed"], density_random.inputs["Seed"])
    density_compare = _math(nodes, "Density Selection", "LESS_THAN", (-990, 250))
    links.new(density_random.outputs[1], density_compare.inputs[0])
    links.new(group_input.outputs["Density"], density_compare.inputs[1])

    mesh_to_points = _node(nodes, "GeometryNodeMeshToPoints", "Grid Cells", (-760, 500))
    mesh_to_points.mode = "VERTICES"
    mesh_to_points.inputs["Radius"].default_value = 0.1
    links.new(grid.outputs["Mesh"], mesh_to_points.inputs["Mesh"])
    links.new(density_compare.outputs[0], mesh_to_points.inputs["Selection"])

    position = _node(nodes, "GeometryNodeInputPosition", "Grid Position", (-1450, -390))
    noise_scale_base = _math(nodes, "Noise Cluster Scale", "MULTIPLY", (-1240, -430), 5.0)
    noise_scale = _math(nodes, "Noise Scale Reciprocal", "DIVIDE", (-1040, -430))
    noise_scale.inputs[0].default_value = 1.0
    links.new(group_input.outputs["Cell Size"], noise_scale_base.inputs[0])
    links.new(noise_scale_base.outputs[0], noise_scale.inputs[1])
    scaled_position = _node(nodes, "ShaderNodeVectorMath", "Low Frequency Position", (-820, -430))
    scaled_position.operation = "SCALE"
    links.new(position.outputs["Position"], scaled_position.inputs[0])
    links.new(noise_scale.outputs[0], scaled_position.inputs["Scale"])
    height_noise = _node(nodes, "ShaderNodeTexNoise", "Clustered Height Field", (-590, -430))
    height_noise.noise_dimensions = "3D"
    height_noise.inputs["Scale"].default_value = 1.0
    height_noise.inputs["Detail"].default_value = 2.0
    height_noise.inputs["Roughness"].default_value = 0.55
    links.new(scaled_position.outputs["Vector"], height_noise.inputs["Vector"])

    height_min = _math(nodes, "Lower Relief", "MULTIPLY", (-590, -660), -0.65)
    height_max = _math(nodes, "Upper Relief", "MULTIPLY", (-590, -780), 0.9)
    links.new(group_input.outputs["Height Variation"], height_min.inputs[0])
    links.new(group_input.outputs["Height Variation"], height_max.inputs[0])
    noise_range = _node(nodes, "ShaderNodeMapRange", "Architectural Height Clusters", (-340, -430))
    noise_range.clamp = True
    noise_range.inputs["From Min"].default_value = 0.0
    noise_range.inputs["From Max"].default_value = 1.0
    links.new(height_noise.outputs["Factor"], noise_range.inputs["Value"])
    links.new(height_min.outputs[0], noise_range.inputs["To Min"])
    links.new(height_max.outputs[0], noise_range.inputs["To Max"])

    small_random = _random_float(nodes, "Small Cell Height Variation", (-590, -950), -0.18, 0.18)
    small_seed = _seed_offset(nodes, links, group_input, 17.0, "Height Seed", (-820, -1050))
    links.new(index.outputs["Index"], small_random.inputs["ID"])
    links.new(small_seed.outputs[0], small_random.inputs["Seed"])
    small_height = _math(nodes, "Small Height Detail", "MULTIPLY", (-340, -950))
    links.new(small_random.outputs[1], small_height.inputs[0])
    links.new(group_input.outputs["Height Variation"], small_height.inputs[1])
    height_add = _math(nodes, "Combined Relief", "ADD", (-100, -500))
    links.new(noise_range.outputs["Result"], height_add.inputs[0])
    links.new(small_height.outputs[0], height_add.inputs[1])
    thickness_add = _math(nodes, "Block Thickness", "ADD", (100, -500))
    links.new(group_input.outputs["Base Thickness"], thickness_add.inputs[0])
    links.new(height_add.outputs[0], thickness_add.inputs[1])
    thickness = _math(nodes, "Safe Block Thickness", "MAXIMUM", (300, -500), 0.75)
    links.new(thickness_add.outputs[0], thickness.inputs[0])

    vertical_random = _random_float(nodes, "Vertical Offset Pattern", (-340, -1120), -1.0, 1.0)
    vertical_seed = _seed_offset(nodes, links, group_input, 31.0, "Vertical Seed", (-590, -1230))
    links.new(index.outputs["Index"], vertical_random.inputs["ID"])
    links.new(vertical_seed.outputs[0], vertical_random.inputs["Seed"])
    vertical_offset = _math(nodes, "Vertical Offset", "MULTIPLY", (-100, -1120))
    links.new(vertical_random.outputs[1], vertical_offset.inputs[0])
    links.new(group_input.outputs["Vertical Offset Variation"], vertical_offset.inputs[1])
    half_height = _math(nodes, "Hang Below Ceiling", "MULTIPLY", (300, -680), -0.5)
    links.new(thickness.outputs[0], half_height.inputs[0])
    center_z = _math(nodes, "Block Center Z", "ADD", (500, -680))
    links.new(half_height.outputs[0], center_z.inputs[0])
    links.new(vertical_offset.outputs[0], center_z.inputs[1])

    horizontal_random = _node(nodes, "FunctionNodeRandomValue", "Horizontal Jitter Pattern", (-590, -1380))
    horizontal_random.data_type = "FLOAT_VECTOR"
    horizontal_random.inputs["Min"].default_value = (-1.0, -1.0, 0.0)
    horizontal_random.inputs["Max"].default_value = (1.0, 1.0, 0.0)
    horizontal_seed = _seed_offset(nodes, links, group_input, 47.0, "Horizontal Seed", (-820, -1490))
    links.new(index.outputs["Index"], horizontal_random.inputs["ID"])
    links.new(horizontal_seed.outputs[0], horizontal_random.inputs["Seed"])
    horizontal_scale = _node(nodes, "ShaderNodeVectorMath", "Controlled Horizontal Jitter", (-340, -1380))
    horizontal_scale.operation = "SCALE"
    links.new(horizontal_random.outputs["Value"], horizontal_scale.inputs[0])
    links.new(group_input.outputs["Horizontal Jitter"], horizontal_scale.inputs["Scale"])
    z_vector = _node(nodes, "ShaderNodeCombineXYZ", "Vertical Placement", (710, -680))
    links.new(center_z.outputs[0], z_vector.inputs["Z"])
    total_offset = _node(nodes, "ShaderNodeVectorMath", "Block Offset", (710, -890))
    total_offset.operation = "ADD"
    links.new(horizontal_scale.outputs["Vector"], total_offset.inputs[0])
    links.new(z_vector.outputs["Vector"], total_offset.inputs[1])

    set_position = _node(nodes, "GeometryNodeSetPosition", "Offset Ceiling Cells", (-480, 480))
    links.new(mesh_to_points.outputs["Points"], set_position.inputs["Geometry"])
    links.new(total_offset.outputs["Vector"], set_position.inputs["Offset"])

    cell_span = _math(nodes, "Cell Span", "SUBTRACT", (-120, 710))
    links.new(group_input.outputs["Cell Size"], cell_span.inputs[0])
    links.new(group_input.outputs["Gap"], cell_span.inputs[1])
    scale_x_random = _random_float(nodes, "Scale X Variation", (-120, 940), 0.94, 1.03)
    scale_y_random = _random_float(nodes, "Scale Y Variation", (-120, 1080), 0.94, 1.03)
    scale_x_seed = _seed_offset(nodes, links, group_input, 59.0, "Scale X Seed", (-360, 980))
    scale_y_seed = _seed_offset(nodes, links, group_input, 71.0, "Scale Y Seed", (-360, 1140))
    links.new(index.outputs["Index"], scale_x_random.inputs["ID"])
    links.new(index.outputs["Index"], scale_y_random.inputs["ID"])
    links.new(scale_x_seed.outputs[0], scale_x_random.inputs["Seed"])
    links.new(scale_y_seed.outputs[0], scale_y_random.inputs["Seed"])
    scale_x = _math(nodes, "Block Scale X", "MULTIPLY", (120, 940))
    scale_y = _math(nodes, "Block Scale Y", "MULTIPLY", (120, 1080))
    links.new(cell_span.outputs[0], scale_x.inputs[0])
    links.new(scale_x_random.outputs[1], scale_x.inputs[1])
    links.new(cell_span.outputs[0], scale_y.inputs[0])
    links.new(scale_y_random.outputs[1], scale_y.inputs[1])
    block_scale = _node(nodes, "ShaderNodeCombineXYZ", "Block Dimensions", (390, 920))
    links.new(scale_x.outputs[0], block_scale.inputs["X"])
    links.new(scale_y.outputs[0], block_scale.inputs["Y"])
    links.new(thickness.outputs[0], block_scale.inputs["Z"])

    cube = _node(nodes, "GeometryNodeMeshCube", "Reusable Unit Block", (120, 480))
    cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    set_material = _node(nodes, "GeometryNodeSetMaterial", "Ceiling Faces - SIM_CEILING_DARK", (360, 480))
    set_material.inputs["Material"].default_value = face_material
    links.new(cube.outputs["Mesh"], set_material.inputs["Geometry"])
    instance = _node(nodes, "GeometryNodeInstanceOnPoints", "Ceiling Block Instances", (650, 310))
    links.new(set_position.outputs["Geometry"], instance.inputs["Points"])
    links.new(set_material.outputs["Geometry"], instance.inputs["Instance"])
    links.new(block_scale.outputs["Vector"], instance.inputs["Scale"])

    # Realization was already required by the direct Godot importer to avoid one
    # MeshInstance3D per block. Deriving edges after non-uniform block scaling also
    # keeps the curve profile at a constant world-space radius.
    realize = _node(nodes, "GeometryNodeRealizeInstances", "Godot Export and Uniform Edge Radius", (850, 310))
    links.new(instance.outputs["Instances"], realize.inputs["Geometry"])

    edge_angle = _node(nodes, "GeometryNodeInputMeshEdgeAngle", "Real Mesh Edge Angle", (760, -40))
    angle_delta = _math(nodes, "Angle Delta", "SUBTRACT", (970, -40))
    angle_abs = _math(nodes, "Absolute Angle Delta", "ABSOLUTE", (1170, -40))
    angle_tolerance = _math(nodes, "90 Degree Edge Tolerance", "LESS_THAN", (1370, -40))
    links.new(edge_angle.outputs["Unsigned Angle"], angle_delta.inputs[0])
    links.new(group_input.outputs["Edge Angle"], angle_delta.inputs[1])
    links.new(angle_delta.outputs[0], angle_abs.inputs[0])
    links.new(angle_abs.outputs[0], angle_tolerance.inputs[0])
    links.new(group_input.outputs["Edge Angle Tolerance"], angle_tolerance.inputs[1])

    mesh_to_curve = _node(nodes, "GeometryNodeMeshToCurve", "Ceiling Edges - 90 Degrees", (1080, 250))
    links.new(realize.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])
    links.new(angle_tolerance.outputs[0], mesh_to_curve.inputs["Selection"])

    profile = _node(nodes, "GeometryNodeCurvePrimitiveCircle", "Uniform Edge Profile", (1290, 410))
    profile.mode = "RADIUS"
    # Three sides are sufficient for a distant emissive outline and keep the
    # full 1000 m array materially cheaper than a smooth circular tube.
    profile.inputs["Resolution"].default_value = 3
    links.new(group_input.outputs["Edge Radius"], profile.inputs["Radius"])

    curve_to_mesh = _node(nodes, "GeometryNodeCurveToMesh", "Solid Emissive Edges", (1510, 250))
    links.new(mesh_to_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
    links.new(profile.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
    curve_to_mesh.inputs["Fill Caps"].default_value = False

    edge_material_node = _node(nodes, "GeometryNodeSetMaterial", "Ceiling Edges - SIM_EDGE_CEILING", (1730, 250))
    edge_material_node.inputs["Material"].default_value = edge_material
    links.new(curve_to_mesh.outputs["Mesh"], edge_material_node.inputs["Geometry"])

    join = _node(nodes, "GeometryNodeJoinGeometry", "Ceiling Faces and Edges", (1960, 310))
    links.new(realize.outputs["Geometry"], join.inputs["Geometry"])
    links.new(edge_material_node.outputs["Geometry"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], group_output.inputs["Geometry"])

    return group


def create_or_update_sim_ceiling():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    material_helper = runpy.run_path(
        os.path.join(repo_root, "Tools", "Blender", "ensure_sim_grid_material.py"),
        run_name="sim_grid_material_helper",
    )
    face_material, edge_material = material_helper["ensure_sim_ceiling_outline_materials"]()

    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)

    obj = bpy.data.objects.get(OBJECT_NAME)
    existing_values = {}
    if obj is not None:
        for existing_modifier in obj.modifiers:
            if existing_modifier.type != "NODES" or existing_modifier.node_group is None:
                continue
            for item in existing_modifier.node_group.interface.items_tree:
                if getattr(item, "item_type", None) != "SOCKET" or getattr(item, "in_out", None) != "INPUT":
                    continue
                try:
                    existing_values[item.name] = existing_modifier[item.identifier]
                except (KeyError, TypeError):
                    pass
    if obj is None:
        mesh = bpy.data.meshes.new(OBJECT_NAME + "_Source")
        mesh.from_pydata([(0.0, 0.0, 0.0)], [], [])
        obj = bpy.data.objects.new(OBJECT_NAME, mesh)
        obj.location = (2.0, 35.0, 181.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj["decorative_only"] = True
    obj["collision"] = False
    obj["simulation_material_semantic"] = "SIM_CEILING_DARK + SIM_EDGE_CEILING"
    obj.data.materials.clear()

    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    old_group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if old_group is not None and old_group.users == 0:
        bpy.data.node_groups.remove(old_group)
    group = _build_node_group(face_material, edge_material)
    modifier = obj.modifiers.new(MODIFIER_NAME, "NODES")
    modifier.node_group = group
    for item in group.interface.items_tree:
        if getattr(item, "item_type", None) == "SOCKET" and getattr(item, "in_out", None) == "INPUT":
            if item.name in DEFAULTS:
                modifier[item.identifier] = existing_values.get(item.name, DEFAULTS[item.name])

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj, modifier, face_material, edge_material


if __name__ == "__main__":
    ceiling, modifier, face_material, edge_material = create_or_update_sim_ceiling()
    print(
        "Simulation ceiling ready: object=%s collection=%s modifier=%s materials=%s,%s"
        % (
            ceiling.name,
            ceiling.users_collection[0].name,
            modifier.name,
            face_material.name,
            edge_material.name,
        )
    )
