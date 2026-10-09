"""Reopen real source, audit all 100 assets, prepare six direct-.blend Godot samples."""
import bpy,json,hashlib,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';SANITY=OUT/'GodotSanity'
data=json.loads((OUT/'manifest.json').read_text());records=data['buildings']
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100.blend'))
errors=[];checks=[]
for r in records:
    c=bpy.data.collections.get(r['collection']);root=bpy.data.objects.get(r['id'])
    if c is None or root is None:errors.append(r['id']+': missing source');continue
    meshes=[o for o in c.objects if o.type=='MESH'];tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
    invalid_uv=sum(1 for o in meshes if not o.data.uv_layers)
    if tris!=r['metrics']['triangles'] or invalid_uv:errors.append(r['id']+': geometry/UV mismatch')
    missing=[];absolute=[]
    for o in meshes:
        for m in o.data.materials:
            for n in m.node_tree.nodes:
                if n.type=='TEX_IMAGE' and n.image:
                    if not Path(bpy.path.abspath(n.image.filepath)).is_file():missing.append(n.image.filepath)
                    if not n.image.filepath.startswith('//'):absolute.append(n.image.filepath)
    if missing or absolute:errors.append(r['id']+': image paths')
    if r['bounds_min'][2]<-.01:errors.append(r['id']+': below ground')
    checks.append(dict(id=r['id'],meshes=len(meshes),triangles=tris,has_uv=not invalid_uv,relative_paths=not absolute,textures_resolve=not missing,asset_marked=c.asset_data is not None,root_origin=list(root.location)))
baseline=json.loads((OUT/'QA/baseline.json').read_text());protected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in baseline['protected_sha256'].items()}
if not all(protected.values()):errors.append('Protected source changed since task baseline; do not overwrite')
audit=dict(count=len(checks),passed=not errors,errors=errors,checks=checks,protected_unchanged=protected,free_bytes=shutil.disk_usage(ROOT).free,
    source_sha256=hashlib.sha256((OUT/'Highrise100.blend').read_bytes()).hexdigest(),unique_geometry=len(set(r['geometry_only_sha256'] for r in records)))
(OUT/'QA/source_validation.json').write_text(json.dumps(audit,indent=2))
assert not errors,errors
if '--audit-only' in sys.argv:
    print('SOURCE_QA_PASS',len(checks));sys.exit(0)
selected=['HR007','HR029','HR047','HR057','HR064','HR097']
cols=[next(r['collection'] for r in records if r['id']==i) for i in selected]
# Do not save over the library. Start an isolated scene containing selected collection sources.
scene=bpy.data.scenes.new('Godot_Six_Archetypes');bpy.context.window.scene=scene
for j,name in enumerate(cols):
    c=bpy.data.collections[name];scene.collection.children.link(c)
    root=next(o for o in c.objects if o.type=='EMPTY');root.location=((j%3)*210,(j//3)*240,0)
for s in list(bpy.data.scenes):
    if s!=scene:bpy.data.scenes.remove(s)
used=set(o.name for o in scene.objects)
for o in list(bpy.data.objects):
    if o.name not in used:bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):
    if c.name not in cols:bpy.data.collections.remove(c)
needed=set()
for o in scene.objects:
    if o.type=='MESH':
        for m in o.data.materials:
            for n in m.node_tree.nodes:
                if n.type=='TEX_IMAGE' and n.image:needed.add(n.image)
for img in needed:
    src=Path(bpy.path.abspath(img.filepath));key=src.parent.name;dest=SANITY/'Textures'/key/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);img.filepath=f'//Textures/{key}/{src.name}'
for img in list(bpy.data.images):
    if img not in needed:bpy.data.images.remove(img)
for m in list(bpy.data.materials):
    if m.users==0:bpy.data.materials.remove(m)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(SANITY/'Samples.blend'),compress=True)
(SANITY/'selected.json').write_text(json.dumps(selected))
(SANITY/'project.godot').write_text('''config_version=5
[application]
config/name="Bow Highrise100 / Six Sample Sanity"
[display]
window/size/viewport_width=1600
window/size/viewport_height=1000
[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
environment/defaults/default_clear_color=Color(0.12,0.16,0.2,1)
''')
print('SOURCE_QA_PASS',len(checks),'SAMPLES',selected)
