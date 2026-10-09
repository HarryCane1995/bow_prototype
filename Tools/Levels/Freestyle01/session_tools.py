"""Blender session N-panel. Run this file or embedded FREESTYLE_TOOLS text after reopening."""
import bpy
import runpy
import math
from pathlib import Path
from mathutils import Euler

ROOT = Path(bpy.data.filepath).resolve().parents[4]

class FREESTYLE_OT_export(bpy.types.Operator):
    bl_idname = 'freestyle.save_export'
    bl_label = 'Save + Export to Godot'
    def execute(self, context):
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        runpy.run_path(str(ROOT / 'Tools/Levels/Freestyle01/export_level.py'), run_name='__main__')
        self.report({'INFO'}, 'Source saved; main and DEV GLBs exported. Godot: focus editor, then F6.')
        return {'FINISHED'}

class FREESTYLE_OT_snap(bpy.types.Operator):
    bl_idname = 'freestyle.snap_size'
    bl_label = 'Set blockout grid'
    step: bpy.props.FloatProperty(default=0.5)
    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.overlay.grid_scale = self.step
                area.spaces.active.overlay.grid_subdivisions = 1
                if hasattr(area.spaces.active.overlay, 'grid_scale_unit'):
                    area.spaces.active.overlay.grid_scale_unit = 'METERS'
        context.scene.tool_settings.snap_elements = {'INCREMENT'}
        context.scene.tool_settings.use_snap_grid_absolute = True
        self.report({'INFO'}, f'Grid {self.step} m; adaptive perspective grid still depends on zoom. Exact moves: G, axis, value.')
        return {'FINISHED'}

class FREESTYLE_PT_tools(bpy.types.Panel):
    bl_label = 'Freestyle Level'
    bl_idname = 'FREESTYLE_PT_tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Freestyle'
    def draw(self, context):
        layout = self.layout
        layout.label(text='1 Blender unit = 1 Godot metre')
        row = layout.row(align=True)
        for name in ('Canvas','Metrics','Kit'):
            row.operator('freestyle.focus_view', text=name).view=name
        row = layout.row(align=True)
        for step in (0.25, 0.5, 1.0):
            row.operator('freestyle.snap_size', text=f'{step:g} m').step = step
        layout.prop(context.scene.tool_settings, 'use_snap', text='Snap (Shift+Tab)')
        layout.operator('freestyle.save_export')
        layout.label(text='LEVEL_GEO: meshes ending -col')
        layout.label(text='Guides never export')
        layout.label(text='F1 reset | F3 kit | F5 readout')
        for name in ('DEV_METRICS','GRAPPLE_GUIDES','DEV_MECHANICS_REFERENCE'):
            col = bpy.data.collections.get(name)
            if col:
                layout.prop(col, 'hide_viewport', text='Hide '+name)

class FREESTYLE_OT_view(bpy.types.Operator):
    bl_idname = 'freestyle.focus_view'
    bl_label = 'Focus authoring view'
    view: bpy.props.StringProperty(default='Canvas')
    def execute(self, context):
        centre,distance={'Canvas':((-10,-10,0),55),'Metrics':((-66,4,4),85),'Kit':((78,8,4),75)}[self.view]
        for area in context.screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.region_3d.view_location=centre
                space.region_3d.view_distance=distance
                space.region_3d.view_rotation=Euler((math.radians(45),0,0),'XYZ').to_quaternion()
                space.region_3d.view_perspective='PERSP'
        return {'FINISHED'}

for cls in (FREESTYLE_OT_export, FREESTYLE_OT_snap, FREESTYLE_OT_view, FREESTYLE_PT_tools):
    previous = getattr(bpy.types, cls.__name__, None)
    if previous:
        bpy.utils.unregister_class(previous)
    bpy.utils.register_class(cls)
