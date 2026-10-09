"""Dedicated visible review process. Reloads our source only while it is unmodified in UI."""
import bpy,time
from pathlib import Path
from mathutils import Vector
SOURCE=Path(__file__).resolve().parents[2]/'Assets/Models/Characters/Hero/Hero_Kaze.blend'
stamp=SOURCE.stat().st_mtime
def frame():
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    s=area.spaces.active;s.overlay.show_overlays=False;s.shading.type='MATERIAL'
    s.region_3d.view_perspective='ORTHO';s.region_3d.view_distance=3.3
    s.region_3d.view_location=(0,0,1.03)
    s.region_3d.view_rotation=Vector((-.42,-1,.1)).to_track_quat('Z','Y')
def refresh():
 global stamp
 current=SOURCE.stat().st_mtime
 if current!=stamp and not bpy.data.is_dirty:
  stamp=current;bpy.ops.wm.open_mainfile(filepath=str(SOURCE));frame()
 return 3
frame();bpy.app.timers.register(refresh,first_interval=3,persistent=True)
