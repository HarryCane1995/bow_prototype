"""Read-only evaluated geometry evidence and consistent review-camera setup."""
import bpy, json, math, hashlib, collections
from pathlib import Path
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'Docs/Reviews/V02GameplayCorrection'
REPORT.mkdir(parents=True, exist_ok=True)


def analyze():
    output = bpy.data.objects['LEVEL_GENERATED_OUTPUT']
    ev = output.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    vertices = [v.co.copy() for v in mesh.vertices]
    faces = [list(p.vertices) for p in mesh.polygons]
    groups = collections.defaultdict(list)
    top_area = support_area = wall_area = 0
    for p in mesh.polygons:
        key = tuple(mesh.attributes[n].data[p.index].value for n in ('v02_zone', 'v02_band', 'v02_part'))
        groups[key].append(p)
        if key[2] == 10 and p.normal.z > .99: top_area += p.area
        if key[2] in (30, 62): support_area += p.area
        if mesh.attributes['v02_role'].data[p.index].value == 1: wall_area += p.area
    bounds = {}
    for key, polygons in groups.items():
        points = [vertices[v] for p in polygons for v in p.vertices]
        bounds[key] = [[min(v[i] for v in points), max(v[i] for v in points)] for i in range(3)]
    bvh = BVHTree.FromPolygons(vertices, faces)
    air = []
    for key, polygons in groups.items():
        if key[2] != 10: continue
        tops = [p for p in polygons if p.normal.z > .99]
        if not tops: continue
        p = max(tops, key=lambda p:p.area)
        sample = sum((vertices[v] for v in p.vertices), Vector()) / len(p.vertices)
        sample.z = bounds[key][2][0] - .04
        hit = bvh.ray_cast(sample, Vector((0,0,-1)), 100)[0]
        air.append({'zone':key[0], 'band':key[1], 'clearance_below_m':None if hit is None else sample.z-hit.z})
    result = {
        'vertices':len(vertices), 'faces':len(faces),
        'hash':hashlib.sha256(json.dumps({'v':[list(v) for v in vertices], 'f':faces},sort_keys=True).encode()).hexdigest(),
        'plate_count':sum(k[2]==10 for k in groups),
        'support_count':sum(k[2] in (30,62) for k in groups),
        'access_flight_count':sum(k[2] in (20,21) for k in groups),
        'bridge_count':sum(100<=k[2]<=108 for k in groups),
        'plate_top_area_m2':top_area, 'support_surface_area_m2':support_area, 'wall_surface_area_m2':wall_area,
        'under_plate_samples':air,
        'boxes':{','.join(map(str,k)):v for k,v in bounds.items()},
        'warnings':[w.message for w in ev.modifiers[0].node_warnings],
    }
    ev.to_mesh_clear()
    return result


def prepare(seed, phase):
    out = bpy.data.objects['LEVEL_GENERATED_OUTPUT']; mod = out.modifiers[0]
    ids = {s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    mod[ids['Seed']] = seed
    out.update_tag(); bpy.context.view_layer.update()
    result = analyze(); result.update(seed=seed, phase=phase)
    path = REPORT / (phase + '_' + str(seed) + '.json')
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            s=area.spaces.active; s.lens=50
            s.region_3d.view_distance=290; s.region_3d.view_location=(0,0,10)
            s.region_3d.view_rotation=Euler((math.radians(66),0,math.radians(-33))).to_quaternion()
            s.region_3d.update();area.tag_redraw()
    print(json.dumps({k:v for k,v in result.items() if k not in ('boxes','under_plate_samples')}))


def screenshot(seed, phase):
    area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
    with bpy.context.temp_override(area=area):
        bpy.ops.screen.screenshot_area(filepath=str(REPORT/(phase+'_'+str(seed)+'.png')))
