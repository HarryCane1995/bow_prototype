"""Editable hard-surface meshes for the isolated first-person archery rig.

Every part is built in armature rest space. The four output meshes have rigid
weights so that the gaps at the joints and the panels' hard edges survive posing.
"""

import math

import bpy
from mathutils import Vector


_X = Vector((1, 0, 0))
_Y = Vector((0, 1, 0))
_Z = Vector((0, 0, 1))

# Display-space paint chips. The shader and viewport swatches expect linear RGB.
_FINISHES = {
    "Seal": ((0.17, 0.20, 0.22), 0.15, 0.57, 0.0),
    "Carbon": ((0.25, 0.29, 0.32), 0.48, 0.38, 0.0),
    "Gunmetal": ((0.38, 0.44, 0.47), 0.62, 0.36, 0.0),
    "Alloy": ((0.62, 0.67, 0.68), 0.68, 0.29, 0.0),
    "Ceramic": ((0.73, 0.76, 0.73), 0.27, 0.36, 0.0),
    "Amber": ((0.96, 0.47, 0.16), 0.27, 0.34, 0.20),
    "Ice": ((0.51, 0.83, 0.82), 0.32, 0.34, 0.35),
    "Filament": ((0.73, 0.80, 0.78), 0.12, 0.47, 0.22),
}


def _material(name):
    material_name = "Arc_" + name
    existing = bpy.data.materials.get(material_name)
    if existing:
        return existing
    display, metallic, roughness, glow = _FINISHES[name]
    linear = tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in display)
    rgba = (*linear, 1.0)
    material = bpy.data.materials.new(material_name)
    material.diffuse_color = rgba
    material.use_nodes = True
    surface = material.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = rgba
    surface.inputs["Metallic"].default_value = metallic
    surface.inputs["Roughness"].default_value = roughness
    if glow:
        surface.inputs["Emission Color"].default_value = rgba
        surface.inputs["Emission Strength"].default_value = glow
    return material


def _unit_plane(vector, axis):
    projected = vector - axis * vector.dot(axis)
    if projected.length_squared < 0.000001:
        fallback = min((_X, _Y, _Z), key=lambda reference: abs(axis.dot(reference)))
        projected = fallback - axis * fallback.dot(axis)
    return projected.normalized()


def _axes(start, end, dorsal):
    axis = (end - start).normalized()
    top = _unit_plane(dorsal, axis)
    return axis, top.cross(axis), top


def _limits(value, low, high):
    return min(high, max(low, value))


_CHAMFER = (
    (1.0, -0.55), (1.0, 0.55), (0.67, 1.0), (-0.67, 1.0),
    (-1.0, 0.55), (-1.0, -0.55), (-0.67, -1.0), (0.67, -1.0),
)
_OVAL = tuple((math.cos(math.tau * i / 16), math.sin(math.tau * i / 16)) for i in range(16))


class _Mesh:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.finishes = []
        self.bone_indices = {}

    def add(self, bone, vertices, faces, finish):
        start = len(self.vertices)
        self.vertices.extend(tuple(p) for p in vertices)
        count = len(self.vertices) - start
        self.bone_indices.setdefault(bone, []).extend(range(start, start + count))
        self.faces.extend(tuple(start + i for i in face) for face in faces)
        if isinstance(finish, str):
            self.finishes.extend([finish] * len(faces))
        else:
            self.finishes.extend(finish)

    def rings(self, bone, rings, finish, edge_finishes=None):
        count = len(rings[0])
        vertices = [v for ring in rings for v in ring]
        faces = [tuple(reversed(range(count)))]
        materials = [finish]
        for row in range(len(rings) - 1):
            for col in range(count):
                nxt = (col + 1) % count
                a = row * count
                faces.append((a + col, a + nxt, a + count + nxt, a + count + col))
                materials.append(edge_finishes.get(col, finish) if edge_finishes else finish)
        last = (len(rings) - 1) * count
        faces.append(tuple(last + col for col in range(count)))
        materials.append(finish)
        self.add(bone, vertices, faces, materials)

    def section(self, bone, start, end, top, profile, finish, polygon=_CHAMFER, edges=None):
        _, width, depth = _axes(start, end, top)
        rings = [[start.lerp(end, t) + width * (x * rx) + depth * (y * ry) for x, y in polygon]
                 for t, rx, ry in profile]
        self.rings(bone, rings, finish, edges)

    def round(self, bone, start, end, profile, finish, sides=16, top=_Z):
        circle = [(math.cos(math.tau * i / sides), math.sin(math.tau * i / sides)) for i in range(sides)]
        self.section(bone, start, end, top, [(t, radius, radius) for t, radius in profile], finish, circle)

    def stud(self, bone, center, axle, radius, half_length, finish, sides=16):
        self.round(bone, center - axle * half_length, center + axle * half_length,
                   [(0.0, radius * 0.84), (0.16, radius), (0.84, radius), (1.0, radius * 0.84)],
                   finish, sides)

    def path(self, bone, rows, side_hint, finish, edges=None):
        # Use the individual span direction so the bevel runs around each knee.
        rings = []
        for i, (center, rx, ry) in enumerate(rows):
            tangent = (rows[min(i + 1, len(rows) - 1)][0] - rows[max(i - 1, 0)][0]).normalized()
            across = _unit_plane(side_hint, tangent)
            depth = tangent.cross(across)
            rings.append([center + across * (x * rx) + depth * (y * ry) for x, y in _CHAMFER])
        self.rings(bone, rings, finish, edges)

    def make_object(self, rig):
        mesh_data = bpy.data.meshes.new(self.name + "_Mesh")
        mesh_data.from_pydata(self.vertices, [], self.faces)
        mesh_data.update()
        # Blend normals along the round seals and long panel crowns. Hinges,
        # chamfers and the outer edges of raised plates keep their hard breaks.
        mesh_data.polygons.foreach_set("use_smooth", [True] * len(mesh_data.polygons))
        mesh_data.set_sharp_from_angle(angle=math.radians(30))
        object_ = bpy.data.objects.new(self.name, mesh_data)
        rig.users_collection[0].objects.link(object_)
        object_.parent = rig
        for bone, indices in self.bone_indices.items():
            group = object_.vertex_groups.new(name=bone)
            group.add(indices, 1.0, 'REPLACE')
        slots = list(dict.fromkeys(self.finishes))
        for name in slots:
            mesh_data.materials.append(_material(name))
        slot_indices = {key: i for i, key in enumerate(slots)}
        mesh_data.polygons.foreach_set("material_index", [slot_indices[key] for key in self.finishes])
        modifier = object_.modifiers.new("Rigid articulation", 'ARMATURE')
        modifier.object = rig
        return object_


class _Casing:
    """Segmented armour laid over a tapered oval cross-section."""

    def __init__(self, mesh, bone, start, end, top, radii):
        self.mesh, self.bone = mesh, bone
        self.start, self.end = start, end
        _, self.across, self.top = _axes(start, end, top)
        self.radii = radii

    def surface(self, t, angle, offset):
        for (a, aw, ah), (b, bw, bh) in zip(self.radii, self.radii[1:]):
            if t <= b:
                f = _limits((t - a) / (b - a), 0.0, 1.0)
                w, h = aw + (bw - aw) * f, ah + (bh - ah) * f
                break
        else:
            _, w, h = self.radii[-1]
        angle = math.radians(angle)
        return (self.start.lerp(self.end, t) + self.across * (math.sin(angle) * (w + offset))
                + self.top * (math.cos(angle) * (h + offset)))

    def plate(self, sections, finish, thickness, facets=4, edge='Gunmetal'):
        # The raised center and recessed rim give the exposed perimeter a bevel.
        vertices, faces, finishes = [], [], []
        cols = facets + 1
        rows = len(sections)
        layer = rows * cols
        for face in range(2):
            for row, (t, left, right) in enumerate(sections):
                for col in range(cols):
                    angle = left + (right - left) * col / facets
                    at_edge = col in (0, cols - 1) or row in (0, rows - 1)
                    height = -0.0004 if face else thickness * (0.72 if at_edge else 1.0)
                    vertices.append(self.surface(t, angle, height))
        for row in range(rows - 1):
            for col in range(facets):
                i = row * cols + col
                face = (i, i + cols, i + cols + 1, i + 1)
                faces.extend([face, tuple(j + layer for j in reversed(face))])
                finishes.extend([finish, edge])
        perimeter = list(range(cols))
        perimeter += [row * cols + cols - 1 for row in range(1, rows)]
        perimeter += list(range(layer - 2, layer - cols - 1, -1))
        perimeter += [row * cols for row in range(rows - 2, 0, -1)]
        for i, j in zip(perimeter, perimeter[1:] + perimeter[:1]):
            faces.append((i, j, j + layer, i + layer))
            finishes.append(edge)
        self.mesh.add(self.bone, vertices, faces, finishes)


def _bearing(mesh, bone, center, axle, radius, half_width, accent='Gunmetal'):
    mesh.stud(bone, center, axle, radius, half_width, 'Seal', 20)
    for sign in (-1.0, 1.0):
        outer = center + axle * (sign * half_width)
        mesh.stud(bone, outer, axle, radius * 0.86, half_width * 0.14, 'Gunmetal', 16)
        mesh.stud(bone, outer + axle * (sign * half_width * 0.17), axle,
                  radius * 0.60, half_width * 0.075, accent, 16)
        mesh.stud(bone, outer + axle * (sign * half_width * 0.27), axle,
                  radius * 0.36, half_width * 0.05, 'Carbon', 8)


def _hand(mesh, bones, side, wrist, scale):
    hand = 'Hand.' + side
    fingers = ('Index', 'Middle', 'Ring', 'Pinky')
    bases = [bones[f'{f}1.{side}'].head_local.copy() for f in fingers]
    tips = [bones[f'{f}3.{side}'].tail_local.copy() for f in fingers]
    knuckles = sum(bases, Vector()) / len(bases)
    axis = (knuckles - wrist).normalized()
    span = (bases[0] - bases[-1]).length
    across = _unit_plane(bases[0] - bases[-1], axis)
    dorsal = axis.cross(across).normalized()
    curl = sum(tips, Vector()) / len(tips) - knuckles
    if dorsal.dot(curl) > 0.0:
        dorsal.negate()
    width = _limits(span * 0.64, 0.029 * scale, 0.050 * scale)
    depth = width * 0.48
    palm = [(0.0, width * 0.55, depth * 0.63), (0.13, width * 0.70, depth * 0.79),
            (0.39, width * 0.93, depth), (0.74, width, depth * 0.98),
            (0.94, width * 0.98, depth * 0.74), (1.04, width * 0.79, depth * 0.64)]
    mesh.section(hand, wrist, knuckles, dorsal, palm, 'Carbon', _OVAL)
    palm_casing = _Casing(mesh, hand, wrist, knuckles, dorsal, palm)
    palm_casing.plate([(0.16, -33, 20), (0.25, -53, 34), (0.55, -65, 44),
                       (0.78, -58, 48), (0.89, -36, 33)],
                      'Gunmetal', 0.0045 * scale, facets=5, edge='Carbon')
    palm_casing.plate([(0.28, -24, -14), (0.38, -33, -9), (0.67, -34, -8),
                       (0.76, -24, -13)], 'Ceramic', 0.0065 * scale, facets=2)
    palm_casing.plate([(0.28, 10, 14), (0.39, 8, 18), (0.65, 11, 20)],
                      'Ice' if side == 'L' else 'Amber', 0.0063 * scale, facets=2)
    # The gameplay camera sees the heel of the palm during the hold.
    sign = 1 if side == 'R' else -1

    def palmar(rows, finish, height, facets=4):
        mirrored = [(t, min(sign * a, sign * b), max(sign * a, sign * b)) for t, a, b in rows]
        palm_casing.plate(mirrored, finish, height * scale, facets, edge='Carbon')

    palmar([(0.13, 121, 157), (0.22, 96, 168), (0.40, 88, 172),
            (0.60, 101, 162), (0.75, 119, 152), (0.78, 130, 144)], 'Gunmetal', 0.0037)
    palmar([(0.23, 172, 211), (0.37, 174, 241), (0.64, 165, 249),
            (0.81, 158, 225), (0.93, 167, 197)], 'Seal', 0.0030)
    palmar([(0.25, 110, 117), (0.31, 104, 117), (0.59, 111, 120),
            (0.64, 117, 121)], 'Alloy', 0.0041, 2)
    palmar([(0.25, 148, 151), (0.28, 145, 151), (0.47, 146, 150)],
           'Amber' if side == 'R' else 'Ice', 0.0044, 2)

    finger_radius = _limits(span / 6.5, 0.0067 * scale, 0.0105 * scale)
    for digit, width_factor in [('Thumb', 1.17), ('Index', 1.0), ('Middle', 1.04),
                                ('Ring', 0.95), ('Pinky', 0.80)]:
        segments = [bones[f'{digit}{i}.{side}'] for i in (1, 2, 3)]
        first = segments[0]
        first_dir = (first.tail_local - first.head_local).normalized()
        if digit == 'Thumb':
            hinge = first_dir.cross(segments[1].tail_local - segments[1].head_local)
            hinge = hinge.normalized() if hinge.length_squared > 0.0000001 else across
        else:
            hinge = across
        for number, segment in enumerate(segments):
            start, end = segment.head_local.copy(), segment.tail_local.copy()
            direction = (end - start).normalized()
            knuckle_axis = _unit_plane(hinge, direction)
            outside = direction.cross(knuckle_axis).normalized()
            if number == 0 and outside.dot(dorsal) < 0.0:
                hinge = -hinge
                knuckle_axis = -knuckle_axis
                outside = -outside
            radius = finger_radius * width_factor * (1.0 - 0.095 * number)
            name = segment.name
            mesh.stud(name, start, knuckle_axis, radius * 0.88, radius * 0.88, 'Gunmetal', 12)
            mesh.stud(name, start, knuckle_axis, radius * 0.44, radius * 0.96, 'Alloy', 8)
            profile = [(0.12, radius * 0.69, radius * 0.67), (0.23, radius, radius * 0.97),
                       (0.62, radius * 0.97, radius * 0.94), (0.88, radius * 0.81, radius * 0.79),
                       (0.98, radius * (0.49 if number == 2 else 0.59), radius * 0.56)]
            mesh.section(name, start, end, outside, profile, 'Carbon',
                         edges={1: 'Gunmetal', 2: 'Ceramic' if number < 2 else 'Gunmetal',
                                3: 'Gunmetal', 5: 'Gunmetal', 6: 'Seal', 7: 'Gunmetal'})
    return dorsal


def _arm(bones, side):
    mesh = _Mesh('ArmShell_' + side)
    upper, fore, hand = ('UpperArm.' + side, 'Forearm.' + side, 'Hand.' + side)
    shoulder = bones[upper].head_local.copy()
    elbow = bones[fore].head_local.copy()
    wrist = bones[hand].head_local.copy()
    scale = _limits((wrist - elbow).length / 0.27, 0.80, 1.18)
    hand_top = _hand(mesh, bones, side, wrist, scale)
    upper_dir, fore_dir = (elbow - shoulder).normalized(), (wrist - elbow).normalized()
    elbow_axis = upper_dir.cross(fore_dir)
    elbow_axis = elbow_axis.normalized() if elbow_axis.length_squared > 0.0001 else _unit_plane(_X, fore_dir)
    fore_top = _unit_plane(-elbow.lerp(wrist, 0.5) + _Z * 0.34, fore_dir)
    upper_top = _unit_plane(-shoulder.lerp(elbow, 0.6) + _Z * 0.26, upper_dir)
    upper_profile = [(0.00, 0.047, 0.049), (0.10, 0.061, 0.065), (0.30, 0.060, 0.063),
                     (0.54, 0.055, 0.058), (0.76, 0.043, 0.048), (0.94, 0.033, 0.035),
                     (1.00, 0.032, 0.034)]
    upper_profile = [(t, a * scale, b * scale) for t, a, b in upper_profile]
    mesh.section(upper, shoulder, elbow, upper_top, upper_profile, 'Seal', _OVAL)
    upper_casing = _Casing(mesh, upper, shoulder, elbow, upper_top, upper_profile)
    upper_casing.plate([(0.055, -88, 88), (0.14, -125, 109), (0.25, -119, 105),
                        (0.39, -84, 94), (0.44, -59, 74)], 'Carbon', 0.009 * scale, facets=8)
    upper_casing.plate([(0.46, -35, 13), (0.52, -63, 47), (0.67, -66, 42),
                        (0.81, -32, 20), (0.83, -20, 10)], 'Gunmetal', 0.005 * scale, facets=4)
    _bearing(mesh, fore, elbow, elbow_axis, 0.043 * scale, 0.039 * scale, 'Alloy')

    fore_profile = [(0.00, 0.035, 0.037), (0.10, 0.046, 0.044), (0.20, 0.052, 0.051),
                    (0.33, 0.052, 0.052), (0.53, 0.045, 0.048), (0.69, 0.038, 0.041),
                    (0.85, 0.030, 0.031), (1.00, 0.025, 0.025)]
    fore_profile = [(t, a * scale, b * scale) for t, a, b in fore_profile]
    mesh.section(fore, elbow, wrist, fore_top, fore_profile, 'Seal', _OVAL)
    shell = _Casing(mesh, fore, elbow, wrist, fore_top, fore_profile)
    shell.plate([(0.09, -58, 61), (0.14, -92, 89), (0.29, -107, 103), (0.53, -111, 99),
                 (0.73, -94, 90), (0.83, -49, 62)], 'Carbon', 0.006 * scale, facets=9)
    shell.plate([(0.135, -40, -14), (0.19, -73, -8), (0.34, -76, -8), (0.53, -68, -11),
                 (0.68, -54, -17), (0.77, -36, -24)], 'Ceramic', 0.010 * scale, facets=4)
    shell.plate([(0.19, 13, 40), (0.24, 7, 66), (0.43, 7, 76), (0.61, 13, 67),
                 (0.77, 20, 45), (0.80, 25, 37)], 'Gunmetal', 0.010 * scale, facets=4)
    shell.plate([(0.245, -2.0, 1.6), (0.28, -3.2, 2.7), (0.48, -3.2, 2.7),
                 (0.51, -2.0, 1.7)], 'Amber' if side == 'R' else 'Ice', 0.008 * scale, facets=2)
    shell.plate([(0.55, -2.8, 2.4), (0.605, -2.6, 2.1)], 'Alloy', 0.008 * scale, facets=2)
    for sign in (-1, 1):
        for angle, radius, finish in ((112, 0.0060, 'Alloy'), (141, 0.0047, 'Gunmetal')):
            points = [shell.surface(t, sign * angle, 0.0005 * scale) for t in (0.12, 0.34, 0.75, 0.86)]
            for start, end in zip(points, points[1:]):
                mesh.round(fore, start, end, [(0, radius * scale), (1, radius * scale)], finish, 8)
    mesh.round(fore, elbow, wrist, [(0.839, 0.032 * scale), (0.855, 0.037 * scale),
                                   (0.891, 0.036 * scale), (0.908, 0.031 * scale)], 'Gunmetal', 14, fore_top)
    mesh.round(fore, elbow, wrist, [(0.912, 0.029 * scale), (0.924, 0.032 * scale),
                                   (0.95, 0.031 * scale), (0.958, 0.028 * scale)], 'Alloy', 14, fore_top)
    wrist_axle = _unit_plane(hand_top.cross(fore_dir), fore_dir)
    _bearing(mesh, hand, wrist, wrist_axle, 0.023 * scale, 0.022 * scale)
    return mesh


def _cam(mesh, bone, center, axle, up, radius, phase):
    """Offset rim, open web and index mark read even from the gameplay camera."""
    count = 28
    axle = axle.normalized()
    u = _unit_plane(up, axle)
    v = axle.cross(u)
    thickness = radius * 0.25
    sections = [(-1.0, 0.62), (-1.0, 0.91), (-0.71, 1.0), (-0.30, 1.0),
                (0.0, 0.94), (0.30, 1.0), (0.71, 1.0), (1.0, 0.91), (1.0, 0.62)]
    rings = []
    for depth, size in sections:
        ring = []
        for i in range(count):
            theta = math.tau * i / count
            reach = radius * (1.0 + 0.07 * math.cos(theta - phase)) * size
            ring.append(center + axle * depth * thickness + u * (reach * math.cos(theta))
                        + v * (reach * 0.89 * math.sin(theta)))
        rings.append(ring)
    vertices = [point for ring in rings for point in ring]
    faces, finishes = [], []
    for row in range(len(rings)):
        end_row = (row + 1) % len(rings)
        for i in range(count):
            j = (i + 1) % count
            faces.append((row * count + i, row * count + j, end_row * count + j, end_row * count + i))
            if row in (0, 7):
                finishes.append('Amber' if i in (3, 4, 5) else 'Gunmetal')
            else:
                finishes.append('Carbon' if row in (3, 4, 8) else 'Alloy')
    mesh.add(bone, vertices, faces, finishes)
    for i in range(3):
        a = phase + math.tau * i / 3
        direction = u * math.cos(a) + v * math.sin(a)
        tangent = axle.cross(direction)
        mesh.path(bone, [(center, 0.006, thickness * 0.65),
                         (center + direction * (0.30 * radius) + tangent * 0.004, 0.006, thickness * 0.60),
                         (center + direction * (0.64 * radius), 0.008, thickness * 0.63)],
                  tangent, 'Gunmetal')
    mesh.stud(bone, center, axle, radius * 0.27, thickness * 1.18, 'Alloy', 16)
    mesh.stud(bone, center, axle, radius * 0.13, thickness * 1.29, 'Carbon', 8)


def _riser(mesh, bones, grip, up, right, forward):
    name = 'BowGrip'
    bottom, top = grip - up * 0.058, grip + up * 0.057
    mesh.section(name, bottom, top, forward,
                 [(0.0, 0.013, 0.015), (0.06, 0.018, 0.020), (0.20, 0.016, 0.017),
                  (0.65, 0.0145, 0.018), (0.86, 0.017, 0.020), (1.0, 0.019, 0.022)], 'Seal')
    for t in (0.23, 0.36, 0.49, 0.62, 0.75):
        mesh.section(name, bottom, top, forward, [(t, 0.0155, 0.018), (t + 0.025, 0.0168, 0.020),
                                                 (t + 0.067, 0.0159, 0.019)], 'Carbon')
    for suffix, sign in [('Upper', 1), ('Lower', -1)]:
        pivot = bones['Bow' + suffix].head_local.copy()
        start = grip + up * (0.047 * sign)
        main = []
        for t, offset_x, offset_y, rx, ry in [
            (0.00, 0.000, 0.000, 0.018, 0.020), (0.10, -0.005, 0.002, 0.020, 0.023),
            (0.31, -0.025, 0.017, 0.017, 0.028), (0.50, -0.039, 0.026, 0.015, 0.024),
            (0.71, -0.033, 0.026, 0.013, 0.020), (0.91, -0.009, 0.010, 0.019, 0.023),
            (1.00, 0.000, 0.000, 0.020, 0.024),
        ]:
            main.append((start.lerp(pivot, t) + right * offset_x + forward * offset_y, rx, ry))
        mesh.path(name, main, right, 'Carbon', edges={1: 'Gunmetal', 3: 'Gunmetal', 5: 'Gunmetal'})
        # A slender opposing cheek leaves a real aperture in the forged frame.
        secondary = []
        for t, x, y, w, d in [(0.12, -0.002, -0.004, 0.012, 0.017),
                              (0.29, 0.013, -0.012, 0.009, 0.013),
                              (0.53, 0.023, -0.012, 0.007, 0.009),
                              (0.70, 0.019, -0.009, 0.006, 0.009),
                              (0.90, 0.004, -0.004, 0.012, 0.016),
                              (0.96, 0.000, 0.000, 0.014, 0.016)]:
            secondary.append((start.lerp(pivot, t) + right * x + forward * y, w, d))
        mesh.path(name, secondary, right, 'Gunmetal', edges={6: 'Alloy'})
        # The ceramic face is offset towards the camera on both halves.
        caps = []
        for i in (2, 3, 4, 5):
            center, width, depth = main[i]
            caps.append((center - forward * depth * 0.90, width * (0.46 if i in (2, 5) else 0.80), 0.004))
        mesh.path(name, caps, right, 'Ceramic', edges={0: 'Gunmetal', 4: 'Gunmetal'})
        _bearing(mesh, name, pivot, right, 0.029, 0.026, 'Alloy')

def _limb(mesh, bones, suffix, sign, up, right, forward):
    bone = 'Bow' + suffix
    pivot, end = bones[bone].head_local.copy(), bones[bone].tail_local.copy()
    for rail in (-1, 1):
        rows = []
        for t, separation, bend, rx, ry in [
            (-0.015, 0.012, 0.002, 0.014, 0.020), (0.09, 0.015, 0.009, 0.014, 0.021),
            (0.24, 0.020, 0.018, 0.011, 0.016), (0.47, 0.019, 0.024, 0.008, 0.012),
            (0.70, 0.014, 0.016, 0.006, 0.009), (0.86, 0.011, -0.001, 0.006, 0.008),
            (1.00, 0.016, 0.000, 0.007, 0.007),
        ]:
            center = pivot.lerp(end, t) + right * (rail * separation) + forward * bend
            rows.append((center, rx, ry))
        mesh.path(bone, rows, right, 'Carbon', edges={1: 'Gunmetal', 5: 'Alloy'})
        strips = []
        for idx, factor in [(1, 0.5), (2, 0.8), (3, 0.75), (4, 0.35)]:
            center, rx, ry = rows[idx]
            strips.append((center - forward * ry * 0.90, rx * factor, 0.0034))
        mesh.path(bone, strips, right, 'Ceramic' if rail == -1 else 'Gunmetal')
    # Root shroud and a single broad index bar on the rear deck.
    deck = [(pivot.lerp(end, t) - forward * depth, rx, ry)
            for t, depth, rx, ry in ((0.025, 0.004, 0.023, 0.019), (0.09, 0.006, 0.030, 0.021),
                                    (0.15, 0.002, 0.027, 0.017), (0.22, -0.003, 0.014, 0.010))]
    mesh.path(bone, deck, right, 'Gunmetal', edges={6: 'Carbon'})
    mesh.path(bone, [(pivot.lerp(end, 0.09) - forward * 0.028, 0.016, 0.002),
                     (pivot.lerp(end, 0.105) - forward * 0.027, 0.017, 0.002),
                     (pivot.lerp(end, 0.12) - forward * 0.025, 0.014, 0.002)], right, 'Amber')
    cam_bone = 'BowCam' + suffix
    cam_center = bones[cam_bone].head_local.copy()
    _cam(mesh, cam_bone, cam_center, right, up * sign,
         0.048 if sign > 0 else 0.044, math.radians(13 if sign > 0 else -26))


def _bow(bones):
    mesh = _Mesh('ArcBow')
    grip = bones['BowGrip'].head_local.copy()
    up = (bones['BowGrip'].tail_local - grip).normalized()
    forward = _unit_plane(bones['ArrowSocket'].tail_local - bones['ArrowSocket'].head_local, up)
    right = forward.cross(up).normalized()
    _riser(mesh, bones, grip, up, right, forward)
    for suffix, sign in [('Upper', 1), ('Lower', -1)]:
        _limb(mesh, bones, suffix, sign, up, right, forward)
        name = 'String' + suffix
        start, end = bones[name].head_local.copy(), bones[name].tail_local.copy()
        mesh.round(name, start, end, [(0, 0.00165), (1, 0.00165)], 'Filament', 8)
        mesh.round(name, start, end, [(0.947, 0.0018), (0.951, 0.00265),
                                     (0.986, 0.00265), (0.990, 0.0018)], 'Amber', 8)
    return mesh


def _arrow(bones):
    mesh = _Mesh('NockedArrow')
    bone = 'ArrowSocket'
    start = bones[bone].head_local.copy()
    direction = (bones[bone].tail_local - start).normalized()
    end = start + direction * 0.51
    mesh.round(bone, start, end, [(0.0, 0.0034), (0.022, 0.0044), (0.047, 0.0036),
                                  (0.32, 0.0034), (0.91, 0.0028), (0.96, 0.0028)], 'Gunmetal', 10)
    mesh.round(bone, start, end, [(0.928, 0.003), (0.934, 0.0050), (0.949, 0.0050),
                                  (0.955, 0.0035)], 'Amber', 8)
    mesh.round(bone, start, end, [(0.95, 0.0030), (0.958, 0.0067), (0.968, 0.0074),
                                  (1.0, 0.00055)], 'Alloy', 6)
    mesh.round(bone, start, end, [(0, 0.0049), (0.009, 0.0054), (0.024, 0.0049)], 'Amber', 10)
    _, across, dorsal = _axes(start, end, _Z)
    for i in range(3):
        twist = 0.34 + math.tau * i / 3.0
        out = dorsal * math.cos(twist) + across * math.sin(twist)
        normal = direction.cross(out)
        profile = [(0.018, 0.0030), (0.022, 0.0095), (0.028, 0.017), (0.039, 0.017),
                   (0.087, 0.0060), (0.089, 0.0030)]
        # Positive winding in the direction/out plane faces the tangent axis.
        profile.reverse()
        ring = [start + direction * distance + out * height for distance, height in profile]
        mesh.rings(bone, [[p - normal * 0.0009 for p in ring], [p + normal * 0.0009 for p in ring]],
                   'Amber' if i == 0 else 'Ceramic')
    return mesh


def build(rig):
    """Create and return two arms, the bow assembly and the independent arrow."""
    bones = rig.data.bones
    parts = (_arm(bones, 'L'), _arm(bones, 'R'), _bow(bones), _arrow(bones))
    return [part.make_object(rig) for part in parts]
