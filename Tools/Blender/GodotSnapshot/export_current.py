"""One manual V06 snapshot export. Run from Blender Text Editor, in Object Mode.

Evaluates existing nodes only; never edits the Proxy or generation grammar.
"""
import bpy
import hashlib
import json
import math
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import closest_point_on_tri
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
DEST = SOURCE.parent.parent / 'Generated/GN_Blockout_Current.glb'
ROLES = ['run', 'receiving_catch', 'edge_wall', 'raised_platform', 'ramp',
         'bridge', 'arena_floor', 'vertical_pad', 'vertical_wall', 'required_helper', 'optional_helper']
ATTRS = ['section_id', 'placement_id', 'pattern_id', 'primitive_role', 'primitive_id',
         'primitive_scale_class', 'span_class', 'span_distance', 'grapple_required',
         'required_traversal', 'local_forward', 'occ_size', 'occ_x', 'occ_y', 'occ_z',
         'source_span', 'anchor_distance_from_approach', 'anchor_height', 'landing_distance']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def geometry(mesh):
    return {'vertices': [list(v.co) for v in mesh.vertices],
            'faces': [list(p.vertices) for p in mesh.polygons]}


def godot(v):
    return [round(float(v[0]), 6), round(float(v[2]), 6), round(float(-v[1]), 6)]


def records(host, mode):
    # A disposable host reads the SAME live inputs and the SAME node group.
    copy = host.copy()
    copy.data = host.data.copy()
    copy.name = 'TEMP_GN_SNAPSHOT_RECORDS'
    mesh = copy.data
    bpy.context.scene.collection.objects.link(copy)
    copy.animation_data_clear()
    mod = copy.modifiers[0]
    ids = {s.name: s.identifier for s in mod.node_group.interface.items_tree
           if s.item_type == 'SOCKET' and s.in_out == 'INPUT'}
    for key in mod.keys():
        mod[key] = host.modifiers[0][key]
    mod[ids['Output Mode']] = mode
    copy.update_tag()
    try:
        bpy.context.view_layer.update()
        obj = copy.evaluated_get(bpy.context.evaluated_depsgraph_get())
        data = obj.to_mesh()
        rows = []
        for v in data.vertices:
            row = {'position': list(v.co)}
            for name in ATTRS:
                attr = data.attributes.get(name)
                if attr and attr.domain == 'POINT':
                    item = attr.data[v.index]
                    row[name] = list(item.vector) if attr.data_type == 'FLOAT_VECTOR' else item.value
            rows.append(row)
        obj.to_mesh_clear()
        return rows
    finally:
        bpy.data.objects.remove(copy, do_unlink=True)
        bpy.data.meshes.remove(mesh)


def make_manifest(mesh, rows, helpers, matrix):
    mesh.calc_loop_triangles()
    triangles = [[mesh.vertices[i].co.copy() for i in t.vertices] for t in mesh.loop_triangles]
    bvh = BVHTree.FromPolygons([v.co for v in mesh.vertices], [t.vertices[:] for t in mesh.loop_triangles], all_triangles=True)
    targets, placements, omitted = [], [], []
    for row in rows:
        role = int(row['primitive_role'])
        if role >= 9:
            continue
        center = Vector(row['position'])
        axes = [Vector(row['occ_' + k]) for k in 'xyz']
        size = Vector(row['occ_size'])
        wall = role in (2, 8)
        eligible = []
        for tri in triangles:
            mid = sum(tri, Vector()) / 3
            if any(abs((mid-center).dot(a)) > s/2 + .004 for a, s in zip(axes, size)):
                continue
            normal = (tri[1]-tri[0]).cross(tri[2]-tri[0]).normalized()
            if (wall and abs(normal.z) < .2) or (not wall and normal.z > .15):
                eligible.append((tri, normal))
        meta = {k: v for k, v in row.items() if k not in ('position', 'occ_x', 'occ_y', 'occ_z')}
        meta['role'] = ROLES[role]
        meta['center'] = godot(matrix @ center)
        meta['local_forward'] = godot(matrix.to_3x3() @ Vector(row.get('local_forward', [1, 0, 0])))
        corners = [matrix @ (center + sum((axes[k]*size[k]*signs[k]/2 for k in range(3)), Vector()))
                   for signs in [(x,y,z) for x in [-1,1] for y in [-1,1] for z in [-1,1]]]
        converted = [godot(c) for c in corners]
        meta['bounds'] = [[min(c[k] for c in converted), max(c[k] for c in converted)] for k in range(3)]
        placements.append(meta)
        if not eligible:
            omitted.append({'placement_id': row['placement_id'], 'reason': 'no eligible face survives final clipping'})
            continue
        offsets = [(0, 0)]
        if role == 6:
            offsets += [(-.28,-.28), (-.28,.28), (.28,-.28), (.28,.28)]
        elif not wall and max(size.x, size.y) > 28:
            offsets += [(-.3,0), (.3,0)] if size.x >= size.y else [(0,-.3), (0,.3)]
        accepted = []
        for ordinal, (u,v) in enumerate(offsets):
            desired = center + axes[0]*size.x*u + axes[1]*size.y*v
            desired += -axes[1]*size.y/2 if wall else axes[2]*size.z/2
            choices = sorted([(closest_point_on_tri(desired, *tri), normal) for tri, normal in eligible],
                             key=lambda p: (p[0]-desired).length_squared)
            point, normal = choices[0]
            kind = 'WALLRUN' if wall else 'PASS_THROUGH' if role in (0,4,5) else 'LANDING'
            # Confirm a capsule-sized horizontal landing footprint on the final result.
            # If the chosen point is cut away or near an edge, try triangle interiors.
            if kind == 'LANDING':
                choices += [(sum(tri, Vector())/3, n) for tri,n in eligible]
                valid = []
                for p,n in choices:
                    if n.z < .707:
                        continue
                    support = True
                    for dx,dy in [(0,0),(.6,0),(-.6,0),(0,.6),(0,-.6)]:
                        hit = bvh.ray_cast(p + Vector((dx,dy,.15)), Vector((0,0,-1)), .35)
                        if hit[0] is None or hit[1].z < .707:
                            support = False
                            break
                    if support:
                        valid.append((p,n))
                if not valid:
                    omitted.append({'placement_id': row['placement_id'], 'region': ordinal,
                                    'reason': 'no supported landing footprint on surviving face'})
                    continue
                point, normal = min(valid, key=lambda p: (p[0]-desired).length_squared)
            if any((point-p).length < 2 for p in accepted):
                continue
            accepted.append(point)
            target = {k:meta.get(k) for k in ['section_id','placement_id','pattern_id','primitive_role',
                        'role','primitive_scale_class','span_class','span_distance','grapple_required','required_traversal']}
            target.update(id=f"p{row['placement_id']}_{ordinal}", type=kind,
                          position=godot(matrix @ point), normal=godot(matrix.to_3x3() @ normal),
                          radius=2.2 if wall else 2.5, vertical=role in (7,8), arena=role==6)
            targets.append(target)
    anchors = []
    for row in helpers:
        anchor = {k:v for k,v in row.items() if k not in ('occ_x','occ_y','occ_z','position')}
        anchor['id'] = f"a{row['placement_id']}"
        anchor['position'] = godot(matrix @ Vector(row['position']))
        if 'local_forward' in row:
            anchor['local_forward'] = godot(matrix.to_3x3() @ Vector(row['local_forward']))
        anchor['role'] = ROLES[int(row['primitive_role'])]
        anchors.append(anchor)
        targets.append({**anchor, 'type':'GRAPPLE', 'radius':0, 'vertical':False, 'arena':False})
    assert targets and len({t['id'] for t in targets}) == len(targets)
    return {'placements':placements, 'anchors':anchors, 'targets':targets, 'omitted_target_regions':omitted}


def export_current():
    assert Path(bpy.data.filepath).resolve() == SOURCE.resolve(), 'Open the Freestyle source first.'
    assert bpy.context.mode == 'OBJECT', 'Finish editing and Tab to Object Mode before export.'
    proxy = bpy.data.objects['LEVEL_PROXY']
    host = bpy.data.objects['LEVEL_GENERATED_OUTPUT']
    assert host.modifiers[0].node_group.name == 'GN_LevelProxyGenerator_v06'
    assert not proxy.get('Debug Placement Volumes'), 'Turn off placement debug before taking a gameplay snapshot.'
    before_proxy = digest(geometry(proxy.data))
    before_groups = {g.name: (len(g.nodes), len(g.links)) for g in bpy.data.node_groups}
    controls = {k:v for k,v in proxy.items() if isinstance(v, (int,float,bool))}
    bpy.context.view_layer.update()
    rows = records(host, 6)
    helpers = records(bpy.data.objects['GRAPPLE_CANDIDATES'], 5)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = host.evaluated_get(deps)
    warnings = [w.message for m in evaluated.modifiers if m.type=='NODES' for w in m.node_warnings]
    assert not warnings, warnings
    mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=deps)
    assert len(mesh.polygons)
    report = make_manifest(mesh, rows, helpers, host.matrix_world)
    geometry_hash = digest(geometry(mesh))
    mesh.transform(host.matrix_world)
    mesh.calc_loop_triangles()
    points = [godot(v.co) for v in mesh.vertices]
    report.update(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                  source=SOURCE.relative_to(ROOT).as_posix(), source_proxy_sha256=before_proxy,
                  proxy_vertices=len(proxy.data.vertices), proxy_faces=len(proxy.data.polygons),
                  controls=controls, geometry_sha256=geometry_hash,
                  vertices=len(mesh.vertices), polygons=len(mesh.polygons), triangles=len(mesh.loop_triangles),
                  bounds=[[min(p[k] for p in points), max(p[k] for p in points)] for k in range(3)],
                  coordinates='Godot world meters: Blender (x,y,z) -> (x,z,-y); source world transform baked',
                  collision='StaticBody3D + ConcavePolygonShape3D from every imported visual triangle',
                  coverage_semantics='Representative final-surface targets, not a reachability proof')
    # Probe the preserved wrapper spawn, never silently move it.
    world_bvh = BVHTree.FromPolygons([v.co for v in mesh.vertices], [t.vertices[:] for t in mesh.loop_triangles], all_triangles=True)
    wrapper = (ROOT/'Scenes/Levels/Level_Freestyle_01.tscn').read_text(encoding='utf-8')
    match = re.search(r'\[node name="PlayerSpawn"[^\]]*\]\s*position = Vector3\(([^)]+)\)', wrapper)
    assert match, 'Expected the explicit Freestyle PlayerSpawn marker.'
    spawn = [float(v) for v in match[1].split(',')]
    origin = Vector((spawn[0],-spawn[2],spawn[1]+.2))
    hit = world_bvh.ray_cast(origin, Vector((0,0,-1)), 1000)
    report['preserved_spawn'] = spawn
    report['spawn_surface_below'] = godot(hit[0]) if hit[0] is not None else None
    mat = bpy.data.materials.new('TEMP_SNAPSHOT_NEUTRAL')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (.48,.53,.58,1)
    bsdf.inputs['Roughness'].default_value = .85
    mesh.materials.clear(); mesh.materials.append(mat)
    for face in mesh.polygons:
        face.material_index = 0
    original_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new('TEMP_GN_SNAPSHOT_EXPORT')
    obj = bpy.data.objects.new('GN_Blockout_Surface', mesh)
    scene.collection.objects.link(obj)
    try:
        bpy.context.window.scene = scene
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        DEST.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(DEST), export_format='GLB', use_active_scene=True,
            use_selection=True, export_yup=True, export_apply=False, export_animations=False,
            export_cameras=False, export_lights=False, export_extras=False, export_materials='EXPORT')
    finally:
        bpy.context.window.scene = original_scene
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(scene)
        bpy.data.meshes.remove(mesh)
        bpy.data.materials.remove(mat)
    assert digest(geometry(proxy.data)) == before_proxy
    assert {g.name:(len(g.nodes),len(g.links)) for g in bpy.data.node_groups} == before_groups
    data = DEST.read_bytes()
    gltf = json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]])
    assert [n['name'] for n in gltf['nodes']] == ['GN_Blockout_Surface']
    assert len(gltf['meshes']) == 1
    report['glb_sha256'] = hashlib.sha256(data).hexdigest()
    # Save the current user-authored shape after all disposable export data is removed.
    # Current overwrites only: do not accumulate .blend1 or timestamped snapshots.
    versions = bpy.context.preferences.filepaths.save_version
    try:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
    finally:
        bpy.context.preferences.filepaths.save_version = versions
    report['source_file_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    DEST.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('GN_SNAPSHOT', json.dumps({k:report[k] for k in ['proxy_vertices','proxy_faces','triangles','bounds','spawn_surface_below']}),
          'targets',len(report['targets']),'anchors',len(report['anchors']))


if __name__ == '__main__':
    export_current()
