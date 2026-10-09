"""Export the current evaluated V02 result; never rebuild manual authoring meshes."""
import bpy
import hashlib
import json
import shutil
import struct
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
DEST = SOURCE.parent.parent / 'Exports/Level_Freestyle_01_GN_V02.glb'
REPORT = Path(globals().get('REPORT_OVERRIDE', ROOT / 'Docs/Reviews/GNLevelBlockoutV02'))


def export_current():
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError('Open the Freestyle source before exporting V02.')
    if bpy.context.mode != 'OBJECT':
        raise RuntimeError('Finish the current Edit Mode operation before export.')
    source = bpy.data.objects['LEVEL_GENERATED_OUTPUT']
    modifier = source.modifiers.get('GN_LevelBlockout_Generator_v02')
    if modifier is None:
        raise RuntimeError('Expected the V02 Geometry Nodes modifier.')
    ids = {s.name: s.identifier for s in modifier.node_group.interface.items_tree
           if s.item_type == 'SOCKET' and s.in_out == 'INPUT'}
    controls = {name: (value.name if isinstance(value, bpy.types.Object) else value)
                for name, identifier in ids.items() for value in [modifier[identifier]]}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(depsgraph)
    warnings = [w.message for w in evaluated.modifiers[0].node_warnings]
    if warnings:
        raise RuntimeError('Resolve GN warnings before export: ' + repr(warnings))
    mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True,
                                          depsgraph=depsgraph)
    if not len(mesh.polygons):
        bpy.data.meshes.remove(mesh)
        raise RuntimeError('Evaluated V02 geometry is empty.')
    mesh.transform(source.matrix_world)
    # The lab uses viewport material colors. Mirror those into temporary Principled
    # materials for glTF; do not rewrite the user's Blender materials.
    export_materials = []
    for index, material in enumerate(mesh.materials):
        if material is None:
            continue
        copy = material.copy()
        copy.name = 'EXPORT_' + material.name
        copy.use_nodes = True
        bsdf = next(n for n in copy.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = material.diffuse_color
        bsdf.inputs['Metallic'].default_value = 0
        bsdf.inputs['Roughness'].default_value = .85
        mesh.materials[index] = copy
        export_materials.append(copy)
    mesh.calc_loop_triangles()
    geometry = {'v': [list(v.co) for v in mesh.vertices],
                'f': [list(p.vertices) for p in mesh.polygons]}
    report = {
        'source': SOURCE.relative_to(ROOT).as_posix(),
        'export': DEST.relative_to(ROOT).as_posix(),
        'controls': controls, 'vertices': len(mesh.vertices),
        'polygons': len(mesh.polygons), 'triangles': len(mesh.loop_triangles),
        'geometry_sha256': hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest(),
        'bounds_blender': [[min(v.co[i] for v in mesh.vertices), max(v.co[i] for v in mesh.vertices)]
                           for i in range(3)],
        'collision': 'Godot -col suffix: static concave triangle mesh from the evaluated result',
    }
    # Keep an explicit previous-disk snapshot before saving the current live authoring state.
    backup = SOURCE.parent / 'Backups' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-before-v02-godot')
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(SOURCE, backup / SOURCE.name)
    report['previous_disk_backup'] = backup.relative_to(ROOT).as_posix()
    original_scene = bpy.context.window.scene
    export_scene = bpy.data.scenes.new('TEMP_V02_GODOT_EXPORT')
    export_scene.unit_settings.system = 'METRIC'
    export_scene.unit_settings.scale_length = 1
    obj = bpy.data.objects.new('GN_V02_Level-col', mesh)
    export_scene.collection.objects.link(obj)
    obj['generator'] = 'GN_LevelBlockout_Generator_v02'
    obj['seed'] = int(controls['Seed'])
    obj['source_geometry_sha256'] = report['geometry_sha256']
    spawn = bpy.data.objects.new('PlayerSpawn_V02', None)
    spawn.location = (0, 0, .05)
    export_scene.collection.objects.link(spawn)
    try:
        bpy.context.window.scene = export_scene
        obj.select_set(True)
        spawn.select_set(True)
        bpy.context.view_layer.objects.active = obj
        DEST.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(DEST), export_format='GLB',
            use_selection=True, use_active_scene=True, export_yup=True, export_apply=True,
            export_animations=False, export_cameras=False, export_lights=False,
            export_extras=True, export_materials='EXPORT')
    finally:
        bpy.context.window.scene = original_scene
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.objects.remove(spawn, do_unlink=True)
        bpy.data.scenes.remove(export_scene)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        for material in export_materials:
            if material.users == 0:
                bpy.data.materials.remove(material)
    payload = DEST.read_bytes()
    json_size = struct.unpack_from('<I', payload, 12)[0]
    gltf = json.loads(payload[20:20 + json_size])
    names = sorted(n['name'] for n in gltf.get('nodes', []))
    if names != ['GN_V02_Level-col', 'PlayerSpawn_V02'] or len(gltf.get('meshes', [])) != 1:
        raise RuntimeError('Unexpected GLB export contents: ' + repr(names))
    report['exported_nodes'] = names
    # Only authoring data is saved; the temporary evaluated export copy is gone.
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
    report['glb_sha256'] = hashlib.sha256(DEST.read_bytes()).hexdigest()
    report['source_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / 'godot_export.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('V02_GODOT_EXPORTED', json.dumps(report))


if __name__ == '__main__':
    export_current()
