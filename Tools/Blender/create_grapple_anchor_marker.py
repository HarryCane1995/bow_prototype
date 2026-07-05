"""Create/update a Blender level-design marker for Godot grapple anchors.

Run from the repository root with Blender:
    blender Level_01_Blockout.blend --background --python Tools/Blender/create_grapple_anchor_marker.py

Or open Level_01_Blockout.blend in Blender, open this file in Scripting, and Run Script.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
BLEND_PATH = REPO_ROOT / "Level_01_Blockout.blend"
MARKER_COLLECTION = "30_GAMEPLAY_MARKERS"
MARKER_NAME = "GrappleAnchor_01"

# Source: res://Scenes/GrappleAnchor.tscn
GODOT_ANCHOR_SCENE = "res://Scenes/GrappleAnchor.tscn"
GODOT_MARKER_PREFIX = "GrappleAnchor"
GODOT_DETECTION_RADIUS_M = 0.6
GODOT_DEBUG_VISUAL_RADIUS_M = 0.25


def main() -> None:
    open_blend_file()
    collection = ensure_collection(MARKER_COLLECTION)
    marker = ensure_marker(collection)
    save_blend_file()
    print(f"Created/updated {MARKER_NAME} in {BLEND_PATH}")


def open_blend_file() -> None:
    current_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if current_path == BLEND_PATH.resolve():
        return

    if not BLEND_PATH.exists():
        raise FileNotFoundError(f"Expected Blender file was not found: {BLEND_PATH}")

    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    elif not any(child.name == collection.name for child in bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.link(collection)

    collection.color_tag = "COLOR_05"
    return collection


def ensure_marker(collection: bpy.types.Collection) -> bpy.types.Object:
    marker = bpy.data.objects.get(MARKER_NAME)
    if marker is None:
        marker = bpy.data.objects.new(MARKER_NAME, None)
        marker.empty_display_type = "SPHERE"
        marker.location = pick_default_location()
    elif marker.type != "EMPTY":
        # Keep the Godot-visible marker name on an Empty, not a mesh/collision object.
        old_transform = marker.matrix_world.copy()
        remove_object(marker)
        marker = bpy.data.objects.new(MARKER_NAME, None)
        marker.empty_display_type = "SPHERE"
        marker.matrix_world = old_transform

    link_to_collection(marker, collection)
    unlink_from_other_marker_collections(marker, collection)

    marker.empty_display_type = "SPHERE"
    marker.empty_display_size = GODOT_DETECTION_RADIUS_M
    marker.show_name = True
    marker.show_in_front = True
    marker.hide_viewport = False
    marker.hide_render = False
    marker.color = (0.1, 0.85, 1.0, 1.0)

    marker["godot_marker_type"] = GODOT_MARKER_PREFIX
    marker["godot_runtime_scene"] = GODOT_ANCHOR_SCENE
    marker["godot_detection_radius_m"] = GODOT_DETECTION_RADIUS_M
    marker["godot_debug_visual_radius_m"] = GODOT_DEBUG_VISUAL_RADIUS_M
    marker["note"] = "Level-design marker only. Runtime GrappleAnchor is instanced by ImportedLevelMarkerBinder."

    return marker


def pick_default_location() -> Vector:
    spawn = find_marker_object(("PlayerSpawn", "PlayerStart"))
    if spawn is not None:
        # Blender is Z-up. Put the first anchor slightly forward/sideways and above spawn.
        return spawn.location + Vector((2.5, -2.0, 2.4))

    # Fallback: readable, above the likely starting area, and away from world origin clutter.
    return Vector((2.5, -2.0, 3.0))


def find_marker_object(prefixes: tuple[str, ...]) -> bpy.types.Object | None:
    for obj in bpy.data.objects:
        for prefix in prefixes:
            if obj.name == prefix or obj.name.startswith(prefix + "_") or obj.name.startswith(prefix + "."):
                return obj

    return None


def link_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if obj.name not in collection.objects.keys():
        collection.objects.link(obj)


def unlink_from_other_marker_collections(obj: bpy.types.Object, keep_collection: bpy.types.Collection) -> None:
    for collection in list(obj.users_collection):
        if collection == keep_collection:
            continue

        if collection.name == MARKER_COLLECTION or collection == bpy.context.scene.collection:
            collection.objects.unlink(obj)


def remove_object(obj: bpy.types.Object) -> None:
    bpy.data.objects.remove(obj, do_unlink=True)


def save_blend_file() -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))


if __name__ == "__main__":
    main()
