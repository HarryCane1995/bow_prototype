"""Read saved current source and historical six-sample import; no source saves."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4];ART=ROOT/'Art/Environment/Highrise100';QA=ART/'RuntimeShowcase_QA'
bpy.ops.wm.open_mainfile(filepath=str(ART/'Highrise100.blend'))
manifest=json.loads((ART/'manifest.json').read_text());records=[];mats={};errors=[]
previous_exact=json.loads((ART/'UV_Material_QA/candidate_geometry.json').read_text())['after']
for r in manifest['buildings']:
    c=bpy.data.collections[r['collection']];root=bpy.data.objects[r['id']];points=[];canonical=[];triangles=0;meshes=0
    for o in c.objects:
        if o.type!='MESH':continue
        meshes+=1;vs=[o.matrix_world@v.co for v in o.data.vertices];points.extend(vs)
        canonical.extend(sorted(tuple(round(x,5) for x in vs[i]) for i in p.vertices) for p in o.data.polygons)
        triangles+=sum(len(p.vertices)-2 for p in o.data.polygons)
        for m in o.data.materials:
            if m.name in mats:continue
            nodes=m.node_tree.nodes;principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');images=[]
            for n in nodes:
                if n.type=='TEX_IMAGE' and n.image:
                    p=Path(bpy.path.abspath(n.image.filepath));images.append(dict(path=str(p.relative_to(ART)),name=n.image.name,colorspace=n.image.colorspace_settings.name,extension=n.extension,exists=p.exists(),sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None))
            mats[m.name]=dict(images=images,emission_strength=principled.inputs['Emission Strength'].default_value,base_color=list(principled.inputs['Base Color'].default_value),recipe=m.get('recipe'))
    low=[min(v[i] for v in points) for i in range(3)];high=[max(v[i] for v in points) for i in range(3)]
    signature=hashlib.sha256(json.dumps(sorted(canonical)).encode()).hexdigest()
    strict=[]
    for o in sorted(c.objects,key=lambda x:x.name):
        row=[o.name,o.type,list(map(list,o.matrix_local)),o.parent.name if o.parent else None]
        if o.type=='MESH':row.extend([[list(v.co) for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]])
        strict.append(row)
    exact=hashlib.sha256(json.dumps(strict).encode()).hexdigest()
    if any(abs(v)>1e-5 for v in root.location):errors.append(r['id']+' nonzero root position')
    records.append(dict(id=r['id'],name=r['name'],category=r['category'],collection=c.name,bounds_min=low,bounds_max=high,triangles=triangles,meshes=meshes,root_transform=[list(row) for row in root.matrix_local],geometry_matches_uv_pass=exact==previous_exact[r['id']],exact_geometry_sha256=exact))
options={p.identifier:dict(type=p.type,default=str(getattr(p,'default','')),description=p.description) for p in bpy.ops.export_scene.gltf.get_rna_type().properties if any(k in p.identifier for k in ('original','texture','format','tangent','image','selection','active_scene','extras'))}
(QA/'source_inspection.json').write_text(json.dumps(dict(buildings=records,materials=mats,errors=errors,blender=bpy.app.version_string,export_options=options),indent=2))
bpy.ops.wm.open_mainfile(filepath=str(ART/'GodotSanity/Samples.blend'))
flat=[];surface_count=0
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    for index in set(p.material_index for p in o.data.polygons):
        m=o.data.materials[index];surface_count+=1
        textures=[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        if not textures:
            p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            flat.append(dict(mesh=o.name,material=m.name,slot=index,faces=sum(1 for f in o.data.polygons if f.material_index==index),base_color=list(p.inputs['Base Color'].default_value),emission_color=list(p.inputs['Emission Color'].default_value),emission_strength=p.inputs['Emission Strength'].default_value))
(QA/'historical_73_of_75_source.json').write_text(json.dumps(dict(surfaces=surface_count,flat_surfaces=flat),indent=2))
print('SOURCE_INSPECTED',len(records),'triangles',sum(r['triangles'] for r in records),'unchanged_geometry',sum(r['geometry_matches_uv_pass'] for r in records),'material_count',len(mats),'errors',errors)
print('HISTORICAL_73_75',json.dumps(flat))
print('GLTF_OPTIONS',json.dumps(options))
