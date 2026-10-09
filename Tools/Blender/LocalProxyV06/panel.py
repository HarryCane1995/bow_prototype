"""Optional UI only. Native GN never needs Python handlers or autoexec."""
import bpy
CONTROLS=['Seed','Density','Verticality','Openness','Route Complexity','Traversal Difficulty','Wallrun Bias','Slide Bias','Grapple Bias','Ramp Presence','Ramp Steepness','Orientation Randomness','Platform Density','Length Variation','Debug Span Colors','Debug Placement Volumes','Preview Quality','Use Cutter']
class V06_PT_proxy(bpy.types.Panel):
    bl_label='V06 Proxy Composition';bl_idname='V06_PT_proxy';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='V06 Local'
    def draw(self,context):
        layout=self.layout;obj=bpy.data.objects.get('LEVEL_PROXY')
        if not obj:layout.label(text='LEVEL_PROXY missing');return
        layout.label(text='Source: LEVEL_PROXY — Tab / Extrude')
        for key in CONTROLS:
            if key in obj:layout.prop(obj,'["'+key+'"]',text=key)
        layout.label(text='Clearance 0.3 m / native placement checks')
        layout.label(text='Tests: Text V06_MANUAL_TEST_CHECKLIST')
def register():
    for name in ['V04_PT_proxy','V05_PT_proxy','V06_PT_proxy']:
        cls=getattr(bpy.types,name,None)
        if cls:
            try:bpy.utils.unregister_class(cls)
            except RuntimeError:pass
    bpy.utils.register_class(V06_PT_proxy)
if __name__=='__main__':register()
