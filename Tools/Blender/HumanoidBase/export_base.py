"""Regenerate GLBs from the current manually editable source; never rebuild geometry."""
import bpy,json,hashlib,struct
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'Assets/Characters/BaseHumanoid'
source=BASE/'Source/Humanoid_Base.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
manifest={'source':'Source/Humanoid_Base.blend','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'axes':'Blender +Z up / -Y model front -> Godot +Y up / +Z model front','unit':'meter','exports':{}}
for kind in ['Male','Female']:
    rig=bpy.data.objects[kind+'_Rig'];body=bpy.data.objects[kind+'_Body']
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
    rig.location=(0,0,0);rig.rotation_euler=(0,0,0);rig.scale=(1,1,1)
    for o in bpy.context.selected_objects:o.select_set(False)
    rig.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.context.view_layer.update()
    path=BASE/'Exports'/('Humanoid_'+kind+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),check_existing=False,export_format='GLB',
        use_selection=True,export_yup=True,export_apply=True,export_animations=False,
        export_skins=True,export_influence_nb=4,export_all_influences=False,
        export_armature_object_remove=True,export_rest_position_armature=True,
        export_materials='EXPORT',export_cameras=False,export_lights=False,export_extras=False)
    raw=path.read_bytes();n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n])
    assert len(doc['skins'])==1
    assert len(doc['skins'][0]['joints'])==53
    assert not doc.get('animations')
    manifest['exports'][kind]={'path':str(path.relative_to(BASE)).replace('\\','/'),
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'joints':53,'animations':0,
        'meshes':len(doc['meshes']),'materials':len(doc.get('materials',[]))}
(BASE/'Review/export_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('HUMANOID_EXPORT_PASS',json.dumps(manifest))
