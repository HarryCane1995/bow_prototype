"""Read Level_01 and save ONLY an isolated UV/material review copy.

blender --background --factory-startup --python Tools/Art/FacadeFactory/prepare_review_blend.py
No source rebuild, mesh coordinates, topology or modifiers are changed.
"""
import hashlib
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"Level_01_Blockout.blend"
OUT=ROOT/"Assets/Models/Environment/FacadeReview/Facade_Review_Buildings.blend"
REVIEW=ROOT/"Tools/Art/FacadeFactory/review"
CHOICES={
    1:("EXOSKELETON_TOWER",42),3:("CORPORATE_MONOLITH",42),
    4:("OFFICE_GRID",103),5:("INDUSTRIAL_TOWER",42),
    6:("MEGABLOCK",17),7:("OFFICE_GRID",271),
    8:("LANDMARK_TECH",103),10:("LANDMARK_TECH",42),
}


def mesh_signature(obj):
    payload=([list(v.co) for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons],
             [list(r) for r in obj.matrix_local],[(m.name,m.type) for m in obj.modifiers])
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()


def components(mesh):
    parent=list(range(len(mesh.vertices)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    for e in mesh.edges:
        parent[find(e.vertices[0])]=find(e.vertices[1])
    groups={}
    for v in mesh.vertices:
        groups.setdefault(find(v.index),[]).append(v.index)
    lookup={}
    for indices in groups.values():
        coords=[mesh.vertices[i].co for i in indices]
        bounds=([min(v[a] for v in coords) for a in range(3)],
                [max(v[a] for v in coords) for a in range(3)])
        for i in indices:lookup[i]=bounds
    return lookup


def uv_facade(obj, tower_z):
    mesh=obj.data
    uv=mesh.uv_layers.new(name="FacadeUV")
    lookup=components(mesh)
    for poly in mesh.polygons:
        lo,hi=lookup[poly.vertices[0]]
        # Vertical faces: full sheet per connected architectural mass. Roof faces
        # retain the original material. Bevel evaluates the authored face UVs.
        axis=0 if abs(poly.normal.y)>=abs(poly.normal.x) else 1
        flip=poly.normal.y>0 if axis==0 else poly.normal.x<0
        for li in poly.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co
            u=(v[axis]-lo[axis])/max(hi[axis]-lo[axis],.001)
            if flip:u=1-u
            uv.data[li].uv=(.004+.992*u,.004+.992*(v.z-tower_z[0])/max(tower_z[1]-tower_z[0],.001))
        if abs(poly.normal.z)<.6:
            poly.material_index=1


def preview_material(preset,seed):
    stem=f"{preset.lower()}_s{seed}_512x1024"
    mat=bpy.data.materials.new("M_Level01_Facade_"+stem);mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    for channel,socket in [("albedo","Base Color"),("emission","Emission Color")]:
        path=ROOT/f"Assets/Textures/Levels/Level_01/FacadeFactory/{stem}_{channel}.png"
        img=bpy.data.images.load(str(path),check_existing=True)
        # Relative to the isolated .blend source, not the original level.
        img.filepath="//"+Path(__import__('os').path.relpath(path,OUT.parent)).as_posix()
        tex=mat.node_tree.nodes.new("ShaderNodeTexImage");tex.image=img
        mat.node_tree.links.new(tex.outputs["Color"],bsdf.inputs[socket])
    bsdf.inputs["Roughness"].default_value=.72
    bsdf.inputs["Emission Strength"].default_value=1.2
    return mat


def main():
    before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    roots=[o for o in bpy.data.objects if o.parent is None and o.name.startswith("L01_Skyline_")
           and int(o.name.split("_")[2]) in CHOICES]
    roots.sort(key=lambda o:o.name)
    assert len(roots)==8
    keep={o.name for r in roots for o in [r,*r.children_recursive]}
    for obj in list(bpy.data.objects):
        if obj.name not in keep:bpy.data.objects.remove(obj,do_unlink=True)
    report=[]
    for index,r in enumerate(roots):
        num=int(r.name.split("_")[2]);preset,seed=CHOICES[num]
        mat=preview_material(preset,seed)
        entry=dict(source_root=r.name,preset=preset,seed=seed,uv_meshes=[],geometry_preserved=[],omitted=[])
        # Display miniature preserves the source's anisotropic proportions.
        r.location=((index%4-1.5)*30,-(index//4)*42,0)
        r.rotation_euler=(0,0,0)
        r.scale*=.06
        r["facade_preset"]=preset;r["facade_seed"]=seed
        wall_vertices=[v.co.z for o in r.children if o.type=="MESH"
                       and (o.name.endswith(("_body","_glass")) or "HabitatRaft" in o.name
                            or "StructuralWall" in o.name or "SuspendedObservatory" in o.name)
                       and "VerticalJoint" not in o.name for v in o.data.vertices]
        tower_z=(min(wall_vertices),max(wall_vertices))
        for obj in list(r.children_recursive):
            if obj.type!="MESH":continue
            if "COL-colonly" in obj.name or "WindowBands" in obj.name:
                # Existing window quads would compete with the semantic raster windows.
                # Remove only from the review copy; frame, braces, signs stay present.
                entry["omitted"].append(obj.name);bpy.data.objects.remove(obj,do_unlink=True);continue
            sig=mesh_signature(obj)
            coords=[v.co for v in obj.data.vertices]
            dims=[max(v[a] for v in coords)-min(v[a] for v in coords) for a in range(3)]
            candidate=(obj.name.endswith(("_body","_glass")) or "HabitatRaft" in obj.name or "StructuralWall" in obj.name or "SuspendedObservatory" in obj.name)
            candidate=candidate and dims[2]>9 and max(dims[:2])>8 and "VerticalJoint" not in obj.name
            if candidate:
                obj.data=obj.data.copy()
                obj.data.materials.append(mat)
                uv_facade(obj,tower_z)
                entry["uv_meshes"].append(obj.name)
            assert mesh_signature(obj)==sig,f"Geometry changed: {obj.name}"
            entry["geometry_preserved"].append(obj.name)
        assert entry["uv_meshes"],r.name
        report.append(entry)
    # Delete unused original material/image IDs so the copy has no orphan absolute paths.
    for mesh in list(bpy.data.meshes):
        if not mesh.users:bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users <= int(mat.use_fake_user):bpy.data.materials.remove(mat)
    used_images={n.image for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes
                 if n.type=="TEX_IMAGE" and n.image is not None}
    for img in list(bpy.data.images):
        if img not in used_images:bpy.data.images.remove(img)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT),check_existing=False,relative_remap=False)
    for img in used_images:
        assert img.filepath.startswith("//") and Path(bpy.path.abspath(img.filepath)).is_file(),img.filepath
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
    result=dict(source="res://Level_01_Blockout.blend",source_sha256=before,source_unchanged=True,
                review="res://"+OUT.relative_to(ROOT).as_posix(),towers=report,
                relative_images_resolve=True,
                image_paths=[i.filepath for i in bpy.data.images if i.source=="FILE"])
    (REVIEW/"blender_review_validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("FACADE_REVIEW_BLEND_OK towers=8 source_unchanged=true",flush=True)


if __name__=="__main__":main()
