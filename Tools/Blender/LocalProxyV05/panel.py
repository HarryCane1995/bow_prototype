"""Optional convenience panel. Core evaluation and drivers require no Python runtime."""
import bpy
CONTROLS=['Seed','Length Variation','Density','Verticality','Openness','Route Complexity',
          'Traversal Difficulty','Wallrun Bias','Slide Bias','Grapple Bias','Ramp Presence',
          'Ramp Steepness','Orientation Randomness','Platform Density','Debug Span Colors',
          'Preview Quality','Use Cutter']


class V05_PT_proxy(bpy.types.Panel):
    bl_label='V05 Local Variety';bl_idname='V05_PT_proxy'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='V05 Local'
    @classmethod
    def poll(cls,ctx):return ctx.active_object and ctx.active_object.name=='LEVEL_PROXY'
    def draw(self,ctx):
        layout=self.layout;obj=ctx.active_object
        layout.label(text='Tab / E: authored volume')
        for name in CONTROLS:
            if name in obj:layout.prop(obj,'["'+name+'"]',text=name)
        layout.label(text='Preview 0: Manifold / 1: Exact')
        layout.label(text='Large pink marker: required grapple')
        layout.label(text='V05_MANUAL_TEST_CHECKLIST')


def register():
    for name in ['V05_PT_proxy','V04L_PT_proxy','V04_PT_proxy']:
        old=getattr(bpy.types,name,None)
        if old:bpy.utils.unregister_class(old)
    bpy.utils.register_class(V05_PT_proxy)


if __name__=='__main__':register()
