"""Create or refresh the single reusable SIM_GRID Blender preview material."""

import bpy


MATERIAL_NAME = "SIM_GRID"
BASE_COLOR = (0.003, 0.008, 0.010, 1.0)
GRID_COLOR = (0.035, 0.920, 0.590, 1.0)


def _node(nodes, node_type, name, location):
    node = nodes.new(node_type)
    node.name = name
    node.label = name
    node.location = location
    return node


def _math(nodes, name, operation, location, second_value=None):
    node = _node(nodes, "ShaderNodeMath", name, location)
    node.operation = operation
    if second_value is not None:
        node.inputs[1].default_value = second_value
    return node


def ensure_sim_grid_material():
    duplicates = [
        material.name
        for material in bpy.data.materials
        if material.name.startswith(MATERIAL_NAME + ".")
    ]
    if duplicates:
        raise RuntimeError(
            "Refusing to create another SIM_GRID while duplicate materials exist: "
            + ", ".join(sorted(duplicates))
        )

    material = bpy.data.materials.get(MATERIAL_NAME)
    if material is None:
        material = bpy.data.materials.new(MATERIAL_NAME)

    material.use_fake_user = True
    material.use_nodes = True
    material.diffuse_color = GRID_COLOR
    material.metallic = 0.05
    material.roughness = 0.68
    material["simulation_material_semantic"] = MATERIAL_NAME
    material["godot_runtime_material"] = (
        "res://Assets/Materials/Simulation/sim_grid.tres"
    )
    material["blender_proxy_only"] = True

    tree = material.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output = _node(nodes, "ShaderNodeOutputMaterial", "Material Output", (1150, 120))
    shader = _node(nodes, "ShaderNodeBsdfPrincipled", "SIM_GRID Preview", (850, 120))
    shader.inputs["Metallic"].default_value = 0.05
    shader.inputs["Roughness"].default_value = 0.68
    shader.inputs["Emission Strength"].default_value = 2.2

    geometry = _node(nodes, "ShaderNodeNewGeometry", "World Position and Normal", (-1400, 180))
    normal_abs = _node(nodes, "ShaderNodeVectorMath", "Absolute Normal", (-1180, -300))
    normal_abs.operation = "ABSOLUTE"
    normal_components = _node(nodes, "ShaderNodeSeparateXYZ", "Normal Weights", (-970, -300))
    links.new(geometry.outputs["Normal"], normal_abs.inputs[0])
    links.new(normal_abs.outputs["Vector"], normal_components.inputs["Vector"])

    axis_lines = {}
    for index, axis in enumerate(("X", "Y", "Z")):
        y = 500 - index * 230
        wave = _node(nodes, "ShaderNodeTexWave", "Grid %s" % axis, (-1160, y))
        wave.wave_type = "BANDS"
        wave.bands_direction = axis
        wave.inputs["Scale"].default_value = 0.7
        wave.inputs["Distortion"].default_value = 0.0
        threshold = _math(nodes, "%s Line Width" % axis, "LESS_THAN", (-900, y), 0.065)
        links.new(geometry.outputs["Position"], wave.inputs["Vector"])
        links.new(wave.outputs["Factor"], threshold.inputs[0])
        axis_lines[axis] = threshold

    grid_yz = _math(nodes, "YZ Grid", "MAXIMUM", (-640, 360))
    grid_xz = _math(nodes, "XZ Grid", "MAXIMUM", (-640, 120))
    grid_xy = _math(nodes, "XY Grid", "MAXIMUM", (-640, -120))
    links.new(axis_lines["Y"].outputs[0], grid_yz.inputs[0])
    links.new(axis_lines["Z"].outputs[0], grid_yz.inputs[1])
    links.new(axis_lines["X"].outputs[0], grid_xz.inputs[0])
    links.new(axis_lines["Z"].outputs[0], grid_xz.inputs[1])
    links.new(axis_lines["X"].outputs[0], grid_xy.inputs[0])
    links.new(axis_lines["Y"].outputs[0], grid_xy.inputs[1])

    weighted_yz = _math(nodes, "YZ Normal Weight", "MULTIPLY", (-400, 360))
    weighted_xz = _math(nodes, "XZ Normal Weight", "MULTIPLY", (-400, 120))
    weighted_xy = _math(nodes, "XY Normal Weight", "MULTIPLY", (-400, -120))
    links.new(grid_yz.outputs[0], weighted_yz.inputs[0])
    links.new(normal_components.outputs["X"], weighted_yz.inputs[1])
    links.new(grid_xz.outputs[0], weighted_xz.inputs[0])
    links.new(normal_components.outputs["Y"], weighted_xz.inputs[1])
    links.new(grid_xy.outputs[0], weighted_xy.inputs[0])
    links.new(normal_components.outputs["Z"], weighted_xy.inputs[1])

    add_xy = _math(nodes, "Projected Grid A", "ADD", (-160, 260))
    add_xyz = _math(nodes, "Projected Grid", "ADD", (40, 180))
    links.new(weighted_yz.outputs[0], add_xy.inputs[0])
    links.new(weighted_xz.outputs[0], add_xy.inputs[1])
    links.new(add_xy.outputs[0], add_xyz.inputs[0])
    links.new(weighted_xy.outputs[0], add_xyz.inputs[1])

    scan_wave = _node(nodes, "ShaderNodeTexWave", "Animated Scan Pulse", (-630, -420))
    scan_wave.wave_type = "BANDS"
    scan_wave.bands_direction = "Z"
    scan_wave.inputs["Scale"].default_value = 0.28
    scan_wave.inputs["Phase Offset"].driver_add("default_value").driver.expression = "frame * 0.035"
    scan_threshold = _math(nodes, "Scan Width", "LESS_THAN", (-380, -420), 0.09)
    scan_strength = _math(nodes, "Scan Strength", "MULTIPLY", (-160, -420), 0.22)
    links.new(geometry.outputs["Position"], scan_wave.inputs["Vector"])
    links.new(scan_wave.outputs["Factor"], scan_threshold.inputs[0])
    links.new(scan_threshold.outputs[0], scan_strength.inputs[0])

    noise = _node(nodes, "ShaderNodeTexNoise", "Subtle Digital Noise", (-630, -650))
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.45
    noise_threshold = _math(nodes, "Noise Flecks", "GREATER_THAN", (-380, -650), 0.94)
    noise_strength = _math(nodes, "Noise Strength", "MULTIPLY", (-160, -650), 0.035)
    links.new(geometry.outputs["Position"], noise.inputs["Vector"])
    links.new(noise.outputs["Factor"], noise_threshold.inputs[0])
    links.new(noise_threshold.outputs[0], noise_strength.inputs[0])

    grid_plus_noise = _math(nodes, "Grid plus Noise", "ADD", (260, 80))
    grid_mask = _math(nodes, "Final Grid Mask", "MINIMUM", (440, 80), 1.0)
    scan_modulation = _math(nodes, "Grid Scan Modulation", "MULTIPLY", (440, -80))
    emission_add = _math(nodes, "Grid Emission Pulse", "ADD", (610, -80))
    emission_mask = _math(nodes, "Final Emission Mask", "MINIMUM", (770, -80), 1.0)
    links.new(add_xyz.outputs[0], grid_plus_noise.inputs[0])
    links.new(noise_strength.outputs[0], grid_plus_noise.inputs[1])
    links.new(grid_plus_noise.outputs[0], grid_mask.inputs[0])
    links.new(grid_mask.outputs[0], scan_modulation.inputs[0])
    links.new(scan_strength.outputs[0], scan_modulation.inputs[1])
    links.new(grid_mask.outputs[0], emission_add.inputs[0])
    links.new(scan_modulation.outputs[0], emission_add.inputs[1])
    links.new(emission_add.outputs[0], emission_mask.inputs[0])

    base_mix = _node(nodes, "ShaderNodeMixRGB", "Base and Grid", (610, 300))
    base_mix.inputs["Color1"].default_value = BASE_COLOR
    base_mix.inputs["Color2"].default_value = GRID_COLOR
    emission_mix = _node(nodes, "ShaderNodeMixRGB", "Grid Emission", (610, -120))
    emission_mix.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1.0)
    emission_mix.inputs["Color2"].default_value = GRID_COLOR
    links.new(grid_mask.outputs[0], base_mix.inputs["Factor"])
    links.new(emission_mask.outputs[0], emission_mix.inputs["Factor"])
    links.new(base_mix.outputs["Color"], shader.inputs["Base Color"])
    links.new(emission_mix.outputs["Color"], shader.inputs["Emission Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    return material


if __name__ == "__main__":
    sim_grid = ensure_sim_grid_material()
    print(
        "SIM_GRID proxy ready: material=%s nodes=%d users=%d fake_user=%s"
        % (
            sim_grid.name,
            len(sim_grid.node_tree.nodes),
            sim_grid.users,
            sim_grid.use_fake_user,
        )
    )
