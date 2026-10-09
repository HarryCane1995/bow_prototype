"""Export each evaluated V03 section with exact concave collision suffix and real grapple markers."""
import bpy,sys,json,hashlib,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from common import *

def export_current():
    assert bpy.context.mode=='OBJECT'
    obj,mod,ids=context();assert mod[ids['Section Preview']]==0,'Restore full route before game export.'
    source=evaluated();meta=sections(source);assert len(meta)==15
    controls={k:(mod[v].name if isinstance(mod[v],bpy.types.Object) else mod[v]) for k,v in ids.items()}
    original=bpy.context.window.scene;scene=bpy.data.scenes.new('TEMP_V03_EXPORT')
    mats=[];parts=[];vertices=[];triangles=0
    for mat in source.materials:
        copy=mat.copy() if mat else bpy.data.materials.new('EXPORT_V03_Default')
        if mat:copy.name='EXPORT_'+mat.name
        copy.use_nodes=True
        bsdf=next(n for n in copy.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value=mat.diffuse_color if mat else (.45,.48,.50,1);bsdf.inputs['Roughness'].default_value=.85;mats.append(copy)
    dest=ROOT/'Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01_GN_V03.glb'
    try:
        for s in meta:
            mesh=section_mesh(source,s['id']);parts.append(mesh)
            for i,mat in enumerate(mats):mesh.materials[i]=mat
            mesh.calc_loop_triangles();triangles+=len(mesh.loop_triangles);vertices.extend([list(v.co) for v in mesh.vertices])
            piece=bpy.data.objects.new('FLOW_%02d_%s-col'%(s['id'],s['kind']),mesh);scene.collection.objects.link(piece)
            piece['flow_section']=s['id'];piece['flow_kind']=s['kind'];piece['seed']=int(controls['Seed']);piece['layout_mode']=int(controls['Layout Mode'])
            if s['kind']=='GRAPPLE_CATCH':
                anchor=bpy.data.objects.new('GrappleAnchor_V03_%02d'%s['id'],None);scene.collection.objects.link(anchor);anchor.location=s['anchor']
        spawn=bpy.data.objects.new('PlayerSpawn_V03',None);scene.collection.objects.link(spawn);spawn.location=(0,0,.05)
        bpy.context.window.scene=scene
        for o in scene.objects:o.select_set(True)
        bpy.context.view_layer.objects.active=next(o for o in scene.objects if o.type=='MESH')
        bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_materials='EXPORT')
    finally:
        bpy.context.window.scene=original
        for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.scenes.remove(scene)
        for mesh in parts+[source]:bpy.data.meshes.remove(mesh)
        for mat in mats:
            if not mat.users:bpy.data.materials.remove(mat)
    payload=dest.read_bytes();size=struct.unpack_from('<I',payload,12)[0];gltf=json.loads(payload[20:20+size])
    assert len(gltf['meshes'])==15 and len(gltf['nodes'])==17
    report={'controls':controls,'sections':meta,'triangles':triangles,'bounds_blender':[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)],'glb_sha256':hashlib.sha256(payload).hexdigest(),'exported_nodes':[n['name'] for n in gltf['nodes']],'guide_exported':False}
    (REPORT/'godot_export.json').write_text(json.dumps(report,indent=2))
    print('V03 exported',len(meta),'sections',triangles,'triangles; preview guide excluded')
if __name__=='__main__':export_current()
