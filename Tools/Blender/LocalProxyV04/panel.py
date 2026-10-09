"""Optional controls UI only. Native generation and source properties need no script."""
import bpy

CONTROLS=['Seed','Density','Verticality','Openness','Route Complexity','Traversal Difficulty',
          'Wallrun Bias','Slide Bias','Grapple Bias','Ramp Presence','Ramp Steepness',
          'Orientation Randomness','Platform Density','Preview Quality','Use Cutter']


class V04L_PT_proxy(bpy.types.Panel):
    bl_label='V04 Local Proxy';bl_idname='V04L_PT_proxy'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='V04 Local'

    @classmethod
    def poll(cls,context):return context.active_object and context.active_object.name=='LEVEL_PROXY'

    def draw(self,context):
        obj=context.active_object;layout=self.layout
        layout.label(text='Tab / E: author the closed volume')
        for name in CONTROLS:
            if name in obj:layout.prop(obj,'["'+name+'"]',text=name)
        layout.label(text='Preview: 0 Manifold / 1 Exact')
        layout.label(text='Manual tests: V04_MANUAL_TEST_CHECKLIST')


def register():
    old=getattr(bpy.types,'V04L_PT_proxy',None)
    if old:bpy.utils.unregister_class(old)
    bpy.utils.register_class(V04L_PT_proxy)


if __name__=='__main__':register()
