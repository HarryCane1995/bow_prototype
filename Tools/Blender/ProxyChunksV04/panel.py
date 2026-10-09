"""Optional convenience UI; native modifier evaluation never requires registration."""
import bpy
from proxy_api import NAME,context,TYPES

def attach(obj):
    mod=obj.modifiers.new(NAME,'NODES');mod.node_group=bpy.data.node_groups[NAME];mod.show_in_editmode=True;mod.show_on_cage=False
    for s in mod.node_group.interface.items_tree:
        if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.socket_type!='NodeSocketGeometry':mod[s.identifier]=s.default_value
    obj.update_tag();return mod

class V04_OT_attach(bpy.types.Operator):
    bl_idname='v04.attach_proxy';bl_label='Attach V04 to selected mesh';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,ctx):return ctx.mode=='OBJECT' and ctx.active_object and ctx.active_object.type=='MESH'
    def execute(self,ctx):
        try:context(ctx.active_object);self.report({'INFO'},'This proxy already has V04')
        except StopIteration:attach(ctx.active_object)
        return {'FINISHED'}

class V04_OT_add(bpy.types.Operator):
    bl_idname='v04.add_proxy';bl_label='Add a new proxy box';bl_options={'REGISTER','UNDO'}
    def execute(self,ctx):
        if ctx.mode!='OBJECT':self.report({'WARNING'},'Finish Edit Mode first');return {'CANCELLED'}
        mesh=bpy.data.meshes.new('PROXY_Chunk_SOURCE');mesh.from_pydata([(x,y,z) for z in [-.7,11.3] for y in [0,42] for x in [-6,6]],[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]);mesh.update()
        obj=bpy.data.objects.new('PROXY_Chunk',mesh);bpy.data.collections['V04_PROXY_CHUNKS'].objects.link(obj);obj.location=ctx.scene.cursor.location
        for o in ctx.selected_objects:o.select_set(False)
        obj.select_set(True);ctx.view_layer.objects.active=obj;attach(obj)
        return {'FINISHED'}

class V04_PT_proxy(bpy.types.Panel):
    bl_label='V04 Proxy Chunk';bl_idname='V04_PT_proxy';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Proxy V04'
    def draw(self,ctx):
        layout=self.layout;layout.operator('v04.add_proxy')
        obj=ctx.active_object
        if not obj or obj.type!='MESH':return
        try:mod,ids=context(obj)
        except StopIteration:layout.operator('v04.attach_proxy');return
        layout.label(text=obj.name)
        for name in ['Chunk Type','Seed','Density','Verticality','Openness','Wallrun Bias','Slide Bias','Arena Bias','Grapple Bias','Ramp Steepness','Obstacle Spacing','Orientation Randomness','Complexity','Show Direction','Use Exclusion']:
            layout.prop(mod,'["%s"]'%ids[name],text=name)
        if mod[ids['Use Exclusion']]:layout.prop(mod,'["%s"]'%ids['Exclusion Object'],text='Exclusion Object')
        layout.label(text='0 Auto / 1 Wallrun / 2 Slide / 3 Arena')
        layout.label(text='4 Descent / 5 Vertical / 6 Mixed / 7 Grapple')
        layout.label(text='Local +Y: entry to exit. Tab: source mesh.')
        layout.label(text='Shift+D: copy, then change Seed.')

def register():
    for cls in [V04_OT_attach,V04_OT_add,V04_PT_proxy]:
        old=getattr(bpy.types,cls.__name__,None)
        if old:bpy.utils.unregister_class(old)
        bpy.utils.register_class(cls)
