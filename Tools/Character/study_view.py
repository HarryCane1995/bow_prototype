"""Visible, static silhouette selection. N-panel > Silhouette > A/B/C.
This is a Blender review helper, not a character rig or game system.
"""
import bpy
from mathutils import Vector
class HERO_OT_study_variant(bpy.types.Operator):
 bl_idname='hero.study_variant';bl_label='Show proportion study'
 variant:bpy.props.StringProperty()
 def execute(self,context):
  for o in context.scene.objects:
   if o.type=='MESH' and o.data.shape_keys:
    for key in o.data.shape_keys.key_blocks:
     if key.name!='Basis':key.value=1 if key.name==self.variant else 0
  context.scene['selected_variant']=self.variant
  return {'FINISHED'}
class HERO_PT_study(bpy.types.Panel):
 bl_label='Silhouette studies';bl_idname='HERO_PT_study';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Silhouette'
 def draw(self,context):
  self.layout.label(text='CLAY ONLY / awaiting selection')
  for name,label in [('A_Concept','A - Concept proportions'),('B_Powerful','B - More powerful'),('C_AnimeLean','C - Anime lean')]:
   self.layout.operator('hero.study_variant',text=label).variant=name
  self.layout.label(text='No rig / no game integration')
for cls in [HERO_OT_study_variant,HERO_PT_study]:bpy.utils.register_class(cls)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   s=area.spaces.active;s.overlay.show_overlays=False;s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.light='STUDIO';s.show_region_ui=True
   s.region_3d.view_perspective='ORTHO';s.region_3d.view_distance=3.1;s.region_3d.view_location=(0,0,1.07)
   s.region_3d.view_rotation=Vector((-.45,1,.04)).to_track_quat('Z','Y')
