"""Dedicated mask viewport; no rendering loop, no changes to other Blender windows."""
import bpy
from pathlib import Path
from mathutils import Vector
SOURCE=Path(__file__).resolve().parent.parent/'Hero_Mask_Visual.blend'
stamp=SOURCE.stat().st_mtime
def frame():
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    s=area.spaces.active;s.overlay.show_overlays=False;s.shading.type='MATERIAL'
    s.region_3d.view_perspective='ORTHO';s.region_3d.view_distance=.61
    s.region_3d.view_location=(0,0,.15);s.region_3d.view_rotation=Vector((.45,-1,.2)).to_track_quat('Z','Y')
def refresh():
 global stamp
 current=SOURCE.stat().st_mtime
 if current!=stamp and not bpy.data.is_dirty:
  stamp=current;bpy.ops.wm.open_mainfile(filepath=str(SOURCE));frame()
 return 4
frame();bpy.app.timers.register(refresh,first_interval=4,persistent=True)
