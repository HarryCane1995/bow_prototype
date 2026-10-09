"""Isolated 12-asset direct .blend import; never touches production scenes."""
import bpy,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA';DEST=QA/'GodotSanity';DEST.mkdir(exist_ok=True)
records=json.loads((QA/'candidate_manifest.json').read_text())['buildings']
selected=['HR003','HR007','HR013','HR018','HR025','HR027','HR036','HR057','HR064','HR070','HR083','HR100']
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highrise100_UV_Candidate.blend'))
scene=bpy.data.scenes.new('UV_Material_Sanity_12');bpy.context.window.scene=scene
cols=[];selection=[]
for j,id in enumerate(selected):
    r=next(r for r in records if r['id']==id);c=bpy.data.collections[r['collection']];cols.append(c.name);scene.collection.children.link(c)
    root=bpy.data.objects[id];root.location=((j%4)*240,(j//4)*240,0)
    selection.append(dict(id=id,category=r['category'],height=r['bounds_m'][2],triangles=r['metrics']['triangles'],position=list(root.location)))
for s in list(bpy.data.scenes):
    if s!=scene:bpy.data.scenes.remove(s)
used={o.name for o in scene.objects}
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
    src=Path(bpy.path.abspath(img.filepath));key=src.parent.name;dest=DEST/'Textures'/key/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);img.filepath=f'//Textures/{key}/{src.name}'
for img in list(bpy.data.images):
    if img not in needed:bpy.data.images.remove(img)
for m in list(bpy.data.materials):
    if not m.users:bpy.data.materials.remove(m)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(DEST/'Samples.blend'),compress=True)
(DEST/'selected.json').write_text(json.dumps(selection,indent=2));shutil.copyfile(ROOT/'Tools/Environment/Highrise100/qa_godot.gd',DEST/'sanity.gd')
(DEST/'project.godot').write_text('''config_version=5
[application]
config/name="Bow / Highrise UV material QA / 12 samples"
[display]
window/size/viewport_width=1600
window/size/viewport_height=1100
[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
environment/defaults/default_clear_color=Color(0.12,0.16,0.2,1)
''')
print('GODOT_UV_SAMPLE_STAGED',selected)
