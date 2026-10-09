"""Add/update only the owned combat collection in the canonical Level_01 source.

Run with Blender --background --python Tools/Blender/add_combat_graybox.py.
Layout uses Godot XYZ; geometry is authored with Blender Z-up. No existing training
object, material, transform or collider is rebuilt. Simulation slots use the existing
SIM_GRID_03 semantic and the existing Godot post-import replacement.
"""
import bpy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "Level_01_Blockout.blend"
COLLECTION = "50_COMBAT_GRAYBOX"
OWNER = "level01_combat_draft_v1"


def signature(obj):
    result = [obj.name, obj.type, list(sum((list(row) for row in obj.matrix_world), []))]
    if obj.type == "MESH":
        result += [[[float(v) for v in vertex.co] for vertex in obj.data.vertices],
                   [list(poly.vertices) for poly in obj.data.polygons],
                   [slot.material.name if slot.material else None for slot in obj.material_slots]]
    return result


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
old = {obj.name: signature(obj) for obj in bpy.data.objects if obj.get("combat_owner") != OWNER}
collection = bpy.data.collections.get(COLLECTION)
if collection is None:
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
material = bpy.data.materials["SIM_GRID_03"]
layout = json.loads((REPO / "Scenes/Levels/Level_01/combat_layout.json").read_text())
for item in layout["boxes"]:
    name = item["name"] + "-col"
    obj = bpy.data.objects.get(name)
    if obj is not None and obj.get("combat_owner") != OWNER:
        raise RuntimeError("Refusing to replace unrelated object " + name)
    if obj is None:
        mesh = bpy.data.meshes.new(name + "_Mesh")
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj["combat_owner"] = OWNER
        obj.data.materials.append(material)
    # Outward winding matters for both Godot backface culling and trimesh collision.
    mesh = obj.data
    mesh.clear_geometry()
    mesh.from_pydata(
        [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)], [],
        [(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)])
    mesh.update()
    assert all(poly.center.dot(poly.normal) > 0 for poly in mesh.polygons), name
    x,y,z = item["position"]
    sx,sy,sz = item["size"]
    obj.location = (x, -z, y)
    obj.scale = (sx/2, sz/2, sy/2)

for name, original in old.items():
    assert signature(bpy.data.objects[name]) == original, "Unrelated source changed: " + name
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print("COMBAT_SOURCE_SAVED " + json.dumps({"new_boxes":len(layout["boxes"]), "preserved_objects":len(old)}))
