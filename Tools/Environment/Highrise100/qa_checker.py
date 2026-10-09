"""Temporary numbered directional checker focused on ranked offender faces."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
sys.path.insert(0,str(Path(__file__).resolve().parent));from build_library import aim
args=sys.argv[sys.argv.index('--')+1:];phase=args[0]
source=(QA/'Before/Highrise100.blend') if phase=='before' else OUT/'Highrise100_UV_Candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
if phase=='before':
    for img in bpy.data.images:
        if img.source=='FILE':img.filepath=str(OUT/img.filepath.removeprefix('//').replace('\\','/'))
records={r['id']:r for r in json.loads((QA/'Before/manifest.json').read_text())['buildings']}
recs={r['key']:r for r in json.loads((OUT/'materials.json').read_text())}
import csv
rows=list(csv.DictReader((QA/'Independent/before_surfaces.csv').open(encoding='utf-8-sig')))
select=['HR003','HR027','HR036','HR037','HR039','HR065','HR098','HR100'];chosen=[]
for id in select:
    eligible=[r for r in rows if r['building_id']==id and r['recipe_key'].startswith('f') and r['recipe_key'][1:2].isdigit()]
    chosen.append(max(eligible,key=lambda r:float(r['relative_anisotropy_max'])))
scene=bpy.data.scenes['Neutral_Preview'];bpy.context.window.scene=scene;cam=scene.camera;inst=bpy.data.objects['PREVIEW_INSTANCE']
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.eevee.taa_render_samples=16
grid=bpy.data.images.load(str(QA/'numbered_checker.png'));folder=QA/'Checker';folder.mkdir(exist_ok=True)
for row in chosen:
    record=records[row['building_id']];col=bpy.data.collections[record['collection']];inst.instance_collection=col
    originals=[]
    for o in col.objects:
        if o.type!='MESH':continue
        for i,m in enumerate(o.data.materials):
            originals.append((o,i,m));key=m.get('uv_qa_source_key',m.name.removeprefix('H100_'));rec=recs.get(key,{})
            width=float(m.get('uv_qa_tile_width_m',42 if key.startswith('f') and key[1:2].isdigit() else 12))
            height=float(m.get('uv_qa_facade_crop_height_px',1024))/rec['parameters']['floor_height']*record['parameters']['floor_pitch'] if rec.get('mode','').startswith('UNIQUE_FACADE') else float(m.get('uv_qa_tile_height_m',12))
            debug=bpy.data.materials.new('QA_ONLY_CHECKER');debug.use_nodes=True;n=debug.node_tree.nodes;l=debug.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.8
            tc=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(width/4,height/4,1);l.new(tc.outputs['UV'],scale.inputs[0])
            tex=n.new('ShaderNodeTexImage');tex.image=grid;tex.extension='REPEAT';l.new(scale.outputs['Vector'],tex.inputs['Vector']);l.new(tex.outputs['Color'],p.inputs['Base Color']);l.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.2
            o.data.materials[i]=debug
    o=bpy.data.objects[row['mesh']];p=o.data.polygons[int(row['surface'])];pts=[o.matrix_world@o.data.vertices[i].co for i in p.vertices];center=sum(pts,Vector())/len(pts);normal=o.matrix_world.to_3x3()@p.normal
    cam.location=center+normal*250;aim(cam,center);cam.data.ortho_scale=38
    scene.render.filepath=str(folder/(record['id']+'_'+phase+'.png'));bpy.ops.render.render(write_still=True)
    for obj,i,mat in originals:obj.data.materials[i]=mat
    print('CHECKER',phase,record['id'],row['mesh'],row['surface'],flush=True)
(folder/(phase+'_faces.json')).write_text(json.dumps(chosen,indent=2))
print('CHECKER_DONE_TEMPORARY_NOT_SAVED')
