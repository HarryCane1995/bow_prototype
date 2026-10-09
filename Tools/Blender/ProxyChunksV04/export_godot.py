"""Export independent authored proxy results; no whole-level generation step."""
import bpy,sys,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from proxy_api import *

def export_current():
    assert bpy.context.mode=='OBJECT'
    proxies=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith(('TEST_','UX_TEST')) and any(m.type=='NODES' and m.node_group and m.node_group.name==NAME for m in o.modifiers)]
    assert proxies
    original=bpy.context.window.scene;scene=bpy.data.scenes.new('TEMP_V04_EXPORT');parts=[];materials={};records=[];triangles=0
    destination=ROOT/'Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01_Proxy_V04.glb'
    try:
        for obj in sorted(proxies,key=lambda o:o.name):
            record=summary(obj);mod,ids=context(obj)
            record['controls']={k:(mod[v].name if isinstance(mod[v],bpy.types.Object) else mod[v]) for k,v in ids.items()}
            for name in ['entry','exit','anchor']:record[name+'_world']=list(obj.matrix_world@Vector(record[name]))
            mesh=extracted(obj,world=True);parts.append(mesh)
            for i,mat in enumerate(mesh.materials):
                if mat not in materials:
                    copy=mat.copy() if mat else bpy.data.materials.new('EXPORT_V04_Default');copy.use_nodes=True
                    bsdf=next(n for n in copy.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=mat.diffuse_color if mat else (.4,.45,.5,1);bsdf.inputs['Roughness'].default_value=.85;materials[mat]=copy
                mesh.materials[i]=materials[mat]
            mesh.calc_loop_triangles();triangles+=len(mesh.loop_triangles);record['triangles']=len(mesh.loop_triangles)
            piece=bpy.data.objects.new(obj.name+'-col',mesh);scene.collection.objects.link(piece);piece['proxy_source']=obj.name;piece['seed']=int(record['controls']['Seed']);piece['chunk_type']=record['type']
            if record['type']=='GRAPPLE':
                anchor=bpy.data.objects.new('GrappleAnchor_V04_'+obj.name,None);anchor.location=record['anchor_world'];scene.collection.objects.link(anchor)
            records.append(record)
        spawn=bpy.data.objects.new('PlayerSpawn_V04',None);spawn.location=(0,0,.05);scene.collection.objects.link(spawn)
        bpy.context.window.scene=scene
        for o in scene.objects:o.select_set(True)
        bpy.context.view_layer.objects.active=next(o for o in scene.objects if o.type=='MESH')
        bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_active_scene=True,use_selection=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_materials='EXPORT')
    finally:
        bpy.context.window.scene=original
        for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.scenes.remove(scene)
        for mesh in parts:bpy.data.meshes.remove(mesh)
        for mat in materials.values():
            if not mat.users:bpy.data.materials.remove(mat)
    payload=destination.read_bytes();size=struct.unpack_from('<I',payload,12)[0];gltf=json.loads(payload[20:20+size]);assert len(gltf['meshes'])==len(proxies)
    report={'chunks':records,'mesh_count':len(proxies),'triangles':triangles,'glb_sha256':hashlib.sha256(payload).hexdigest(),'nodes':[n['name'] for n in gltf['nodes']],'guide_exported':False}
    (REPORT/'godot_export.json').write_text(json.dumps(report,indent=2));print('V04_EXPORTED',len(proxies),'independent chunks',triangles,'triangles')
if __name__=='__main__':export_current()
