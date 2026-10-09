"""Read-only .blend -> shared external-texture glTF. Never rebuilds/saves source."""
import bpy,json,sys,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];ART=ROOT/'Art/Environment/Highrise100';QA=ART/'RuntimeShowcase_QA';RUNTIME=ROOT/'Assets/Environment/Highrise100_Runtime'
subset='--subset' in sys.argv
DEST=QA/'SubsetImport' if subset else RUNTIME
DEST.mkdir(parents=True,exist_ok=True);(DEST/'Textures').mkdir(exist_ok=True)
baseline=json.loads((QA/'baseline.json').read_text());source=ART/'Highrise100.blend';source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha==baseline['source_sha256'],'Source changed during export pass'
records=json.loads((QA/'source_inspection.json').read_text())['buildings'];selected=['HR003','HR007','HR013','HR018','HR027','HR036','HR057','HR064','HR083','HR100'] if subset else [r['id'] for r in records]
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.data.scenes.new('Highrise100_Runtime');bpy.context.window.scene=scene
for r in records:
    if r['id'] in selected:scene.collection.children.link(bpy.data.collections[r['collection']])
needed={}
for o in scene.objects:
    if o.type!='MESH':continue
    for m in o.data.materials:
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image:
                path=Path(bpy.path.abspath(n.image.filepath));needed[n.image.name]=(n.image,path)
copied=[]
for image,path in needed.values():
    key=path.parent.name;channel=path.stem;name=key+'_'+channel+'.png';target=DEST/'Textures'/name
    shutil.copy2(path,target);image.name=name;image.filepath=str(target)
    copied.append(dict(file='Textures/'+name,source=path.relative_to(ART).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),colorspace=image.colorspace_settings.name))
path=DEST/'Highrise100.gltf'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLTF_SEPARATE',use_active_scene=True,export_keep_originals=True,export_texture_dir='Textures',export_tangents=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_apply=False,export_materials='EXPORT',export_yup=True)
gltf=json.loads(path.read_text());uris=[x['uri'] for x in gltf['images']]
assert all(not Path(p).is_absolute() and '..' not in Path(p).parts for p in uris),uris
assert len(uris)==len(set(uris)),'Duplicated texture references'
nodes={n['name'] for n in gltf['nodes']};assert set(selected)<=nodes
material_count=len(gltf['materials']);flat=[m['name'] for m in gltf['materials'] if 'baseColorTexture' not in m.get('pbrMetallicRoughness',{})]
report=dict(source_sha256=source_sha,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_sha,selected=selected,building_count=len(selected),mesh_count=len(gltf['meshes']),material_count=material_count,flat_materials=flat,image_count=len(uris),texture_count=len(gltf['textures']),copied_maps=copied,format='glTF separate + one binary + external shared PNGs',export_options=dict(keep_originals=True,tangents=True,animations=False,cameras=False,lights=False,extras=False),buildings=[r for r in records if r['id'] in selected])
(DEST/'export_manifest.json').write_text(json.dumps(report,indent=2));(QA/('subset_export.json' if subset else 'runtime_export.json')).write_text(json.dumps(report,indent=2))
if subset:(DEST/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Highrise100 material subset import"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
print('RUNTIME_EXPORT_PASS',len(selected),'materials',material_count,'images',len(uris),'textures',len(gltf['textures']),'flat',flat,'source_unchanged',report['source_unchanged'])
