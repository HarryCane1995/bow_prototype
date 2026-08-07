"""Create or refresh the reusable SIM_GRID Blender preview palette."""

import bpy


MATERIAL_NAME = "SIM_GRID"
PALETTE = (
    {
        "name": "SIM_GRID",
        "runtime": "res://Assets/Materials/Simulation/sim_grid.tres",
        "base_color": (0.0, 0.0, 0.0, 1.0),
        "grid_color": (0.12325788, 0.36399, 0.23282236, 1.0),
        "cell_size": 1.6,
        "line_width": 0.005,
        "emission_strength": 3.85,
        "scan_speed": 1.95,
        "scan_strength": 2.0,
        "noise_strength": 0.225,
    },
    {
        "name": "SIM_GRID_02",
        "runtime": "res://Assets/Materials/Simulation/sim_grid_02.tres",
        "base_color": (0.002, 0.008, 0.015, 1.0),
        "grid_color": (0.08, 0.72, 1.0, 1.0),
        "cell_size": 2.4,
        "line_width": 0.008,
        "emission_strength": 1.8,
        "scan_speed": 0.2,
        "scan_strength": 0.2,
        "noise_strength": 0.006,
    },
    {
        "name": "SIM_GRID_03",
        "runtime": "res://Assets/Materials/Simulation/sim_grid_03.tres",
        "base_color": (0.002, 0.008, 0.003, 1.0),
        "grid_color": (0.05, 0.95, 0.18, 1.0),
        "cell_size": 0.55,
        "line_width": 0.018,
        "emission_strength": 2.5,
        "scan_speed": 1.1,
        "scan_strength": 0.75,
        "noise_strength": 0.08,
    },
    {
        "name": "SIM_GRID_04",
        "runtime": "res://Assets/Materials/Simulation/sim_grid_04.tres",
        "base_color": (0.001, 0.0005, 0.006, 1.0),
        "grid_color": (0.75, 0.12, 1.0, 1.0),
        "cell_size": 2.0,
        "line_width": 0.02,
        "emission_strength": 1.2,
        "scan_speed": 0.65,
        "scan_strength": 1.35,
        "noise_strength": 0.02,
    },
    {
        "name": "SIM_GRID_05",
        "runtime": "res://Assets/Materials/Simulation/sim_grid_05.tres",
        "base_color": (0.012, 0.002, 0.0005, 1.0),
        "grid_color": (1.0, 0.22, 0.025, 1.0),
        "cell_size": 1.25,
        "line_width": 0.015,
        "emission_strength": 2.8,
        "scan_speed": 0.45,
        "scan_strength": 0.55,
        "noise_strength": 0.14,
    },
)
CEILING_PRESET = {
    "name": "SIM_GRID_CEILING",
    "runtime": "res://Assets/Materials/Simulation/sim_grid_ceiling.tres",
    "base_color": (0.001, 0.004, 0.009, 1.0),
    "grid_color": (0.32, 0.78, 1.0, 1.0),
    "cell_size": 3.2,
    "line_width": 0.009,
    "emission_strength": 1.4,
    "scan_speed": 0.12,
    "scan_strength": 0.16,
    "noise_strength": 0.012,
}


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


def _find_numbered_duplicates():
    canonical_names = {preset["name"] for preset in PALETTE + (CEILING_PRESET,)}
    duplicates = []
    for material in bpy.data.materials:
        if any(material.name.startswith(name + ".") for name in canonical_names):
            duplicates.append(material.name)
    return sorted(duplicates)


def _build_preview_material(preset):
    material_name = preset["name"]
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(material_name)

    base_color = preset["base_color"]
    grid_color = preset["grid_color"]
    cell_size = preset["cell_size"]
    line_width = preset["line_width"]
    emission_strength = preset["emission_strength"]
    scan_speed = preset["scan_speed"]
    scan_strength_value = preset["scan_strength"]
    noise_strength_value = preset["noise_strength"]

    material.use_fake_user = True
    material.use_nodes = True
    material.diffuse_color = grid_color
    material.metallic = 0.05
    material.roughness = 0.68
    material["simulation_material_semantic"] = material_name
    material["godot_runtime_material"] = preset["runtime"]
    material["blender_proxy_only"] = True
    material["sim_grid_parameters"] = (
        "cell_size=%s;line_width=%s;emission=%s;scan_speed=%s;"
        "scan_strength=%s;noise=%s"
        % (
            cell_size,
            line_width,
            emission_strength,
            scan_speed,
            scan_strength_value,
            noise_strength_value,
        )
    )

    tree = material.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output = _node(nodes, "ShaderNodeOutputMaterial", "Material Output", (1150, 120))
    shader = _node(nodes, "ShaderNodeBsdfPrincipled", "%s Preview" % material_name, (850, 120))
    shader.inputs["Metallic"].default_value = 0.05
    shader.inputs["Roughness"].default_value = 0.68
    shader.inputs["Emission Strength"].default_value = emission_strength

    geometry = _node(nodes, "ShaderNodeNewGeometry", "World Position and Normal", (-1400, 180))
    normal_abs = _node(nodes, "ShaderNodeVectorMath", "Absolute Normal", (-1180, -300))
    normal_abs.operation = "ABSOLUTE"
    normal_components = _node(nodes, "ShaderNodeSeparateXYZ", "Normal Weights", (-970, -300))
    links.new(geometry.outputs["Normal"], normal_abs.inputs[0])
    links.new(normal_abs.outputs["Vector"], normal_components.inputs["Vector"])

    axis_lines = {}
    proxy_scale = 0.7 / max(cell_size, 0.001)
    proxy_line_width = min(max(line_width * 2.6, 0.01), 0.2)
    for index, axis in enumerate(("X", "Y", "Z")):
        y = 500 - index * 230
        wave = _node(nodes, "ShaderNodeTexWave", "Grid %s" % axis, (-1160, y))
        wave.wave_type = "BANDS"
        wave.bands_direction = axis
        wave.inputs["Scale"].default_value = proxy_scale
        wave.inputs["Distortion"].default_value = 0.0
        threshold = _math(nodes, "%s Line Width" % axis, "LESS_THAN", (-900, y), proxy_line_width)
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
    scan_wave.inputs["Scale"].default_value = 0.28 / max(cell_size, 0.001)
    scan_wave.inputs["Phase Offset"].driver_add("default_value").driver.expression = (
        "frame * %.6f" % (scan_speed * 0.1)
    )
    scan_threshold = _math(nodes, "Scan Width", "LESS_THAN", (-380, -420), 0.09)
    scan_strength = _math(
        nodes,
        "Scan Strength",
        "MULTIPLY",
        (-160, -420),
        min(scan_strength_value * 0.25, 0.65),
    )
    links.new(geometry.outputs["Position"], scan_wave.inputs["Vector"])
    links.new(scan_wave.outputs["Factor"], scan_threshold.inputs[0])
    links.new(scan_threshold.outputs[0], scan_strength.inputs[0])

    noise = _node(nodes, "ShaderNodeTexNoise", "Subtle Digital Noise", (-630, -650))
    noise.inputs["Scale"].default_value = 5.0 / max(cell_size, 0.001)
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.45
    noise_cutoff = 1.0 - min(0.05 + noise_strength_value * 0.4, 0.25)
    noise_threshold = _math(nodes, "Noise Flecks", "GREATER_THAN", (-380, -650), noise_cutoff)
    noise_strength = _math(nodes, "Noise Strength", "MULTIPLY", (-160, -650), noise_strength_value)
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
    base_mix.inputs["Color1"].default_value = base_color
    base_mix.inputs["Color2"].default_value = grid_color
    emission_mix = _node(nodes, "ShaderNodeMixRGB", "Grid Emission", (610, -120))
    emission_mix.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1.0)
    emission_mix.inputs["Color2"].default_value = grid_color
    links.new(grid_mask.outputs[0], base_mix.inputs["Factor"])
    links.new(emission_mask.outputs[0], emission_mix.inputs["Factor"])
    links.new(base_mix.outputs["Color"], shader.inputs["Base Color"])
    links.new(emission_mix.outputs["Color"], shader.inputs["Emission Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    return material


def ensure_sim_grid_material():
    duplicates = _find_numbered_duplicates()
    if duplicates:
        raise RuntimeError(
            "Refusing to create another SIM_GRID while duplicate materials exist: "
            + ", ".join(sorted(duplicates))
        )

    return _build_preview_material(PALETTE[0])


def ensure_sim_grid_palette(preserve_existing_primary=True):
    duplicates = _find_numbered_duplicates()
    if duplicates:
        raise RuntimeError(
            "Refusing to build SIM_GRID palette while duplicate materials exist: "
            + ", ".join(duplicates)
        )

    materials = []
    for preset in PALETTE:
        existing = bpy.data.materials.get(preset["name"])
        if preserve_existing_primary and preset["name"] == MATERIAL_NAME and existing is not None:
            materials.append(existing)
        else:
            materials.append(_build_preview_material(preset))
    return materials


def ensure_sim_grid_ceiling_material():
    duplicates = _find_numbered_duplicates()
    if duplicates:
        raise RuntimeError(
            "Refusing to build SIM_GRID_CEILING while duplicate materials exist: "
            + ", ".join(duplicates)
        )
    return _build_preview_material(CEILING_PRESET)


if __name__ == "__main__":
    palette = ensure_sim_grid_palette(preserve_existing_primary=True)
    print("SIM_GRID palette ready: %s" % ", ".join(material.name for material in palette))
