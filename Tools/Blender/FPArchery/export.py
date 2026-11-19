"""blender -b --python-exit-code 1 -P Tools/Blender/FPArchery/export.py

Open the saved source, sample its evaluated IK and drivers, and export only the
visible meshes and deform rig. All destructive operations stay in this process.
"""
import json
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "Assets/Experiments/FPArchery"
SOURCE = ASSETS / "Source/FPArchery.blend"
MODEL = ASSETS / "FPArchery.glb"


def samples(rig, actions):
    scene = bpy.context.scene
    bones = [b for b in rig.data.bones if b.use_deform]
    parents = {}
    rest_inverse = {}
    for bone in bones:
        parent = next((b for b in bone.parent_recursive if b.use_deform), None)
        parents[bone.name] = parent.name if parent else None
        rest = parent.matrix_local.inverted_safe() @ bone.matrix_local if parent else bone.matrix_local
        rest_inverse[bone.name] = rest.inverted_safe()
    clips = {}
    for action in actions:
        rig.animation_data.action = action
        first, last = map(round, action.frame_range)
        channels = {b.name: [] for b in bones}
        for frame in range(first, last+1):
            scene.frame_set(frame)
            solved = rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
            matrices = {b.name: solved[b.name].matrix.copy() for b in bones}
            for name, global_matrix in matrices.items():
                parent = parents[name]
                relative = matrices[parent].inverted_safe() @ global_matrix if parent else global_matrix
                loc, quat, scale = (rest_inverse[name] @ relative).decompose()
                channel = channels[name]
                if channel:
                    quat.make_compatible(channel[-1][1])
                channel.append((loc, quat, scale))
        clips[action.name] = (channels, action.use_cyclic)
    return bones, parents, clips


def create_export_rig(source, bones, parents, shaft_length):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    data = bpy.data.armatures.new("FPArchery_Runtime")
    rig = bpy.data.objects.new("FPArcheryModel", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for b in bones:
        clone = data.edit_bones.new(b.name)
        clone.head, clone.tail = b.head_local, b.tail_local
        clone.matrix = b.matrix_local
        clone.length = b.length
    for name, parent in parents.items():
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
    # A leaf at the visible tip survives import as a joint without skin weights.
    # It follows the same ArrowSocket that deforms every vertex of the shaft.
    socket = data.edit_bones["ArrowSocket"]
    shaft_forward = (socket.tail - socket.head).normalized()
    tip = data.edit_bones.new("ArrowTip")
    tip.head = socket.head + shaft_forward * shaft_length
    tip.tail = tip.head + shaft_forward * .025
    tip.roll, tip.parent = socket.roll, socket
    # Export the invisible contact on the left index with its actual parent.
    index_contact = source.data.bones["MCH_ArrowRest"]
    guide = data.edit_bones.new("ArrowRest")
    guide.head, guide.tail = index_contact.head_local, index_contact.tail_local
    guide.matrix, guide.length = index_contact.matrix_local, index_contact.length
    guide.parent = data.edit_bones[index_contact.parent.name]
    bpy.ops.object.mode_set(mode="OBJECT")
    for mesh in list(source.children):
        if mesh.type == "MESH":
            if mesh.name == "NockedArrow":
                for channel in ("hide_viewport", "hide_render"):
                    mesh.driver_remove(channel)
                    setattr(mesh, channel, False)
            mesh.parent = rig
            for modifier in mesh.modifiers:
                if modifier.type == "ARMATURE":
                    modifier.object = rig
            mesh.select_set(True)
    return rig


def write_actions(rig, clips, fps):
    metadata = {}
    for name, (bones, loop) in clips.items():
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        slot = action.slots.new("OBJECT", rig.name)
        strip = action.layers.new("Evaluated pose").strips.new(type="KEYFRAME")
        bag = strip.channelbag(slot, ensure=True)
        for bone, poses in bones.items():
            count = len(poses)
            for group, path in enumerate(("location", "rotation_quaternion", "scale")):
                values = [tuple(pose[group]) for pose in poses]
                fixed = all(max(column)-min(column) < 1e-6 for column in zip(*values))
                for axis in range(len(values[0])):
                    curve = bag.fcurves.new(f'pose.bones["{bone}"].{path}', index=axis)
                    points = [(i, row[axis]) for i, row in enumerate(values)]
                    if fixed:
                        points = [points[0], points[-1]]
                    curve.keyframe_points.add(len(points))
                    curve.keyframe_points.foreach_set("co", [v for pair in points for v in pair])
                    for key in curve.keyframe_points:
                        key.interpolation = "LINEAR"
                    curve.update()
        action.use_frame_range = True
        action.frame_start, action.frame_end = 0, count-1
        action.use_cyclic = loop
        metadata[name] = {"duration_seconds": (count-1)/fps, "loop": loop}
    rig.animation_data_create().action = bpy.data.actions["FPV_READY"]
    return metadata


def export_flight_arrow(to_socket, shaft_length):
    # Export the same authored arrow with the tip at the projectile origin.
    # Its shaft then follows contact points during flight and when embedded.
    arrow = bpy.data.objects["NockedArrow"]
    mesh = arrow.data.copy()
    mesh.transform(Matrix.Translation((0, -shaft_length, 0)) @ to_socket)
    obj = bpy.data.objects.new("FlightArrow", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(ASSETS/"FlightArrow.glb"),
                              use_selection=True, export_animations=False,
                              export_skins=False, export_texcoords=False)


def export():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = bpy.data.objects["FPArcheryRig"]
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    actions = [a for a in bpy.data.actions if a.name.startswith("FPV_")]
    bones, parents, clips = samples(rig, actions)
    arrow = bpy.data.objects["NockedArrow"]
    to_socket = rig.data.bones["ArrowSocket"].matrix_local.inverted() @ arrow.matrix_local
    shaft_length = max((to_socket @ v.co).y for v in arrow.data.vertices)
    runtime = create_export_rig(rig, bones, parents, shaft_length)
    bpy.data.objects.remove(rig, do_unlink=True)
    for action in actions:
        bpy.data.actions.remove(action)
    metadata = write_actions(runtime, clips, fps)
    scene.frame_start = 0
    scene.frame_set(0)
    # Bake has already sampled every frame. The glTF writer can encode these
    # local transforms directly and trim redundant channels and repeated keys.
    bpy.ops.export_scene.gltf(
        filepath=str(MODEL), export_format="GLB", use_selection=True,
        export_animations=True, export_animation_mode="ACTIONS",
        export_force_sampling=False, export_anim_single_armature=True,
        export_frame_range=False, export_skins=True, export_morph=False,
        export_cameras=False, export_lights=False, export_texcoords=False,
        export_optimize_animation_size=True, export_yup=True,
        export_all_influences=False, export_extras=False,
    )
    MODEL.with_suffix(".animations.json").write_text(
        json.dumps({"clips": metadata}, indent=2) + "\n", encoding="utf-8")
    settings = MODEL.with_suffix(".glb.import")
    if not settings.exists():
        # Both the rest tracks and the sub-millimetre hold matter in first
        # person. Godot's default optimizer flattens the authored breathing arc.
        settings.write_text(
            '[remap]\nimporter="scene"\ntype="PackedScene"\n\n'
            '[deps]\nsource_file="res://Assets/Experiments/FPArchery/FPArchery.glb"\n\n'
            '[params]\nmeshes/generate_lods=false\nskins/use_named_skins=true\n'
            'animation/import=true\nanimation/fps=60\nanimation/trimming=false\n'
            'animation/remove_immutable_tracks=false\nanimation/import_rest_as_RESET=false\n'
            'import_script/path="res://Scripts/Editor/Import/V2AnimationPostImport.gd"\n'
            '_subresources={"nodes":{"PATH:AnimationPlayer":{"optimizer/enabled":false}}}\n',
            encoding="utf-8")
    export_flight_arrow(to_socket, shaft_length)
    print("FP_ARCHERY_EXPORT", len(clips), "actions", len(parents), "deform bones; tip marker at", shaft_length, MODEL)


if __name__ == "__main__":
    export()
