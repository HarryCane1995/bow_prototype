"""Optional session UI. Graph evaluation does not depend on this panel or Python."""
import bpy
from common import context,set_controls
from chunks import save_chunk

class V03_OT_preset(bpy.types.Operator):
    bl_idname='v03.flow_preset';bl_label='Flow preset';bl_options={'REGISTER','UNDO'}
    mode:bpy.props.IntProperty(default=0)
    def execute(self,context_ui):
        set_controls(**{'Layout Mode':self.mode,'Seed':[17,41,109][self.mode],'Section Preview':0,'Use Cutter':False,'Steep Angle':45})
        return {'FINISHED'}

class V03_OT_save_chunk(bpy.types.Operator):
    bl_idname='v03.save_chunk';bl_label='Save isolated section .blend'
    def execute(self,context_ui):
        obj,mod,ids=context();sid=int(mod[ids['Section Preview']])-1
        if sid<0:self.report({'WARNING'},'Choose Section Preview 1-15 first');return {'CANCELLED'}
        path=save_chunk(sid);self.report({'INFO'},path);return {'FINISHED'}

class V03_PT_flow(bpy.types.Panel):
    bl_label='V03 Flow Course';bl_idname='V03_PT_flow';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Flow V03'
    def draw(self,context_ui):
        layout=self.layout
        if 'LEVEL_FLOW_OUTPUT' not in bpy.data.objects:return
        obj,mod,ids=context();row=layout.row(align=True)
        for mode,title in enumerate(['Balanced 17','Vertical 41','Speed 109']):row.operator('v03.flow_preset',text=title).mode=mode
        for name in ['Seed','Layout Mode','Verticality','Openness','Density','Route Complexity','Traversal Difficulty','Grapple Presence','Wall Angle Jitter','Steep Angle','Use Cutter','Section Preview','Section Colors','Flow Guide']:
            layout.prop(mod,'["%s"]'%ids[name],text=name)
        layout.label(text='Preview: 0 all / 1-15 one section')
        layout.operator('v03.save_chunk')
        layout.label(text='35-45 deg: grounded descent')
        layout.label(text='55-70 deg: airborne drop + catch')

def register():
    for cls in (V03_OT_preset,V03_OT_save_chunk,V03_PT_flow):
        previous=getattr(bpy.types,cls.__name__,None)
        if previous:bpy.utils.unregister_class(previous)
        bpy.utils.register_class(cls)
