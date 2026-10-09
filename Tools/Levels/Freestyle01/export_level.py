"""Run in Blender after saving. Exports whitelisted collections, never rebuilds source."""
import bpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
EXPORTS = SOURCE.parent.parent / 'Exports'

def export_level():
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError('Open Level_Freestyle_01.blend first; export refused for another source.')
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        raise RuntimeError('Switch to Object Mode before export.')
    EXPORTS.mkdir(parents=True, exist_ok=True)
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    states = {o: (o.hide_get(), o.hide_select) for o in bpy.context.scene.objects}
    collection_states = {c:c.hide_viewport for c in bpy.data.collections}
    object_visibility = {o:o.hide_viewport for o in bpy.context.scene.objects}
    layer_states = {}
    def enable_layers(layer):
        layer_states[layer] = (layer.exclude,layer.hide_viewport)
        layer.exclude = False
        layer.hide_viewport = False
        for child in layer.children: enable_layers(child)
    try:
        enable_layers(bpy.context.view_layer.layer_collection)
        for col in bpy.data.collections: col.hide_viewport=False
        for obj in bpy.context.scene.objects: obj.hide_viewport=False
        for filename, collections in [
            ('Level_Freestyle_01.glb', ('LEVEL_GEO', 'GAMEPLAY_MARKERS')),
            ('Level_Freestyle_01_DEV.glb', ('DEV_MECHANICS_REFERENCE',)),
        ]:
            bpy.ops.object.select_all(action='DESELECT')
            objects = {o for name in collections for o in bpy.data.collections[name].all_objects}
            for obj in objects:
                if obj.name.endswith('-noimp'):
                    continue
                obj.hide_set(False)
                obj.hide_select = False
                obj.select_set(True)
            bpy.ops.export_scene.gltf(filepath=str(EXPORTS / filename), export_format='GLB',
                use_selection=True, export_yup=True, export_apply=True,
                export_animations=False, export_cameras=False, export_lights=False,
                export_extras=True, export_materials='EXPORT')
            print('FREESTYLE_EXPORTED', filename)
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        for obj, (hidden, locked) in states.items():
            obj.hide_set(hidden)
            obj.hide_select = locked
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
        for obj,hidden in object_visibility.items(): obj.hide_viewport=hidden
        for col,hidden in collection_states.items(): col.hide_viewport=hidden
        for layer,(excluded,hidden) in reversed(list(layer_states.items())):
            layer.exclude=excluded
            layer.hide_viewport=hidden

if __name__ == '__main__':
    export_level()
