"""Create the original FP authoring scene. Re-export hand edits with export.py."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SOURCE = HERE.parents[2] / "Assets/Experiments/FPArchery/Source/FPArchery.blend"
V = Vector
UP = V((-.34, -.02, .94)).normalized()
RIGHT = V((.12, .99, .065)).cross(UP).normalized()
FORWARD = UP.cross(RIGHT).normalized()
GRIP = V((-.192, .658, -.154))
ROOT = V((0, 0, -.24))


def bow_vector(x, y, z):
    return RIGHT * x + FORWARD * y + UP * z


# The string exits the back grooves of the swept limb tips. In carry it runs
# straight between them, with the shaft guided by the supporting index finger.
LIMBS = (("Upper", .176, .502, -.081), ("Lower", -.163, -.462, -.074))
CAM_SWEEP = bow_vector(-.047, -.040, 0)
STRING_GROOVE = bow_vector(-.009, -.040, 0)
REST_HEIGHT = .040
string_ends = [GRIP + bow_vector(0, sweep, height) + CAM_SWEEP + STRING_GROOVE
               for _, _, height, sweep in LIMBS]
NOCK = string_ends[1].lerp(string_ends[0], (REST_HEIGHT-LIMBS[1][2])/(LIMBS[0][2]-LIMBS[1][2]))
TRAVEL = bow_vector(-.050, -.268, .072)
LEFT_WRIST = GRIP + bow_vector(-.060, -.051, -.045)
# The glove has its own bind pose. Its IK control seats that same grasp on the string.
DRAW_HAND_REST = GRIP + bow_vector(.045, -.160, .057)
RIGHT_WRIST = DRAW_HAND_REST + bow_vector(.111, -.050, -.050)
SHOULDERS = {"L": V((-.221, .032, -.261)), "R": V((.217, -.008, -.244))}
POLES = {"L": V((-.615, .315, -.437)), "R": V((.610, .030, -.400))}
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def elbow_position(shoulder, wrist, pole, upper, lower):
    line = wrist - shoulder
    distance = line.length
    line.normalize()
    bend = pole - shoulder
    bend = (bend - line * bend.dot(line)).normalized()
    along = (distance**2 + upper**2 - lower**2) / (2 * distance)
    return shoulder + along * line + math.sqrt(upper**2 - along**2) * bend


def finger_paths(side):
    # The pads meet the grip and the nocking line in rest space. FK rotations
    # change the curl about the individual hinges during reach and recovery.
    if side == "L":
        paths = {"Thumb": [(-.038, -.032, .012), (-.018, -.034, .032),
                           (.006, -.027, .036), (.022, -.008, .027)]}
        for index, name in enumerate(FINGERS[1:]):
            h = .026 - index * .0215
            short = .004 if name == "Pinky" else 0
            paths[name] = [(-.032, .005, h), (-.019, .030-short, h+.003),
                           (.005, .031-short, h+.002), (.020-short, .009, h-.004)]
        origin = GRIP
    else:
        paths = {"Thumb": [(.069, -.027, .005), (.052, -.033, .024),
                           (.030, -.020, .030), (.010, -.005, .021)]}
        for index, name in enumerate(FINGERS[1:]):
            h = .015 - index * .020
            short = (.0, .0, .005, .013)[index]
            paths[name] = [(.050+short, -.006-short, h), (.026+short, .013, h+.003),
                           (.005+short, .013, h+.001), (-.004+short, -.004, h-.003)]
        origin = DRAW_HAND_REST
    return {name: [origin + bow_vector(*point) for point in path]
            for name, path in paths.items()}


index_knuckles = finger_paths("L")["Index"]
# Shaft centre over the armour at the first hinge of the supporting finger.
REST = index_knuckles[0].lerp(index_knuckles[1], .92) + UP * .014 + RIGHT * .005


def make_rig():
    data = bpy.data.armatures.new("FPArchery")
    rig = bpy.data.objects.new("FPArcheryRig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    sets = {n: data.collections.new(n) for n in
            ("Placement", "Finger FK", "Deform", "Mechanism")}
    bpy.ops.object.mode_set(mode="EDIT")
    membership = {}

    def bone(name, head, tail, parent=None, group="Deform", roll_axis=None):
        b = data.edit_bones.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = data.edit_bones[parent]
        b.use_deform = group in ("Deform", "Finger FK")
        if roll_axis is not None:
            b.align_roll(roll_axis)
        membership[name] = group
        return b

    bone("CTRL_Master", ROOT, ROOT + V((0, .11, 0)), group="Placement")
    bone("Root", ROOT, ROOT + V((0, .08, 0)), "CTRL_Master")
    bone("CTRL_BowGrip", GRIP, GRIP + UP*.12, "Root", "Placement", -FORWARD)
    bone("BowGrip", GRIP, GRIP + UP*.12, "CTRL_BowGrip", roll_axis=-FORWARD)
    bone("CTRL_Draw", NOCK, NOCK + FORWARD*.09, "BowGrip", "Placement", UP)
    bone("MCH_DrawTravel", NOCK, NOCK + FORWARD*.08, "CTRL_Draw", "Mechanism", UP)
    bone("CTRL_String", NOCK, NOCK + FORWARD*.06, "MCH_DrawTravel", "Placement", UP)
    bone("MCH_ArrowRest", REST, REST + FORWARD*.035, "BowGrip", "Mechanism", UP)
    bone("ArrowSocket", NOCK, NOCK + FORWARD*.095, "CTRL_String", roll_axis=UP)
    for suffix, pivot_height, end_height, sweep in LIMBS:
        pivot = GRIP + bow_vector(0, .019, pivot_height)
        axle = GRIP + bow_vector(0, sweep, end_height) + CAM_SWEEP
        bone("Bow"+suffix, pivot, axle, "BowGrip", roll_axis=RIGHT)
        bone("BowCam"+suffix, axle, axle+RIGHT*.040, "Bow"+suffix, roll_axis=UP)
        bone("String"+suffix, axle+STRING_GROOVE, NOCK, "Bow"+suffix, roll_axis=RIGHT)

    elbows = {}
    for side, wrist, lengths in [("L", LEFT_WRIST, (.344, .319)),
                                  ("R", RIGHT_WRIST, (.322, .291))]:
        shoulder = SHOULDERS[side]
        elbow = elbow_position(shoulder, wrist, POLES[side], *lengths)
        elbows[side] = elbow
        path = finger_paths(side)
        knuckles = (path["Index"][0] + path["Pinky"][0])*.5
        parent = "BowGrip" if side == "L" else "CTRL_String"
        target = "CTRL_Grip.L" if side == "L" else "CTRL_DrawHand.R"
        axis = (elbow-shoulder).cross(wrist-elbow).normalized()
        suffix = "."+side
        bone("Clavicle"+suffix, V((shoulder.x*.29, -.003, -.238)), shoulder, "Root")
        bone("UpperArm"+suffix, shoulder, elbow, "Clavicle"+suffix, roll_axis=axis)
        bone("Forearm"+suffix, elbow, wrist, "UpperArm"+suffix, roll_axis=axis)
        contact_shift = NOCK - DRAW_HAND_REST if side == "R" else V((0, 0, 0))
        bone(target, wrist + contact_shift, knuckles + contact_shift, parent, "Placement", UP)
        bone("Hand"+suffix, wrist, knuckles, "Forearm"+suffix, roll_axis=UP)
        bone("CTRL_Elbow"+suffix, POLES[side], POLES[side]+V((0, .060, 0)),
             "Root", "Placement")
        for finger, joints in path.items():
            finger_parent = "Hand"+suffix
            for index in range(3):
                name = f"{finger}{index+1}{suffix}"
                bone(name, joints[index], joints[index+1], finger_parent, "Finger FK", UP)
                finger_parent = name
    data.edit_bones["MCH_ArrowRest"].parent = data.edit_bones["Index1.L"]
    bpy.ops.object.mode_set(mode="POSE")
    for name, group in membership.items():
        b = data.bones[name]
        for old in list(b.collections):
            old.unassign(b)
        sets[group].assign(b)
        b.color.palette = ("THEME04" if name.endswith(".L") else
                           "THEME02" if name.endswith(".R") else "THEME09")
    for col in list(data.collections):
        if col.name not in sets:
            data.collections.remove(col)
    sets["Deform"].is_visible = sets["Mechanism"].is_visible = False
    sets["Finger FK"].is_visible = False

    pb = rig.pose.bones
    slider = pb["CTRL_Draw"]
    for prop, lo, hi, description in [
            ("draw_amount", 0, 1, "Натяжение от свободной тетивы до полного удержания"),
            ("spring", -1, 1, "Короткое остаточное колебание плеч после отпускания")]:
        slider[prop] = 0.0
        slider.id_properties_ui(prop).update(min=lo, max=hi, description=description)

    def drive(owner, path, index, expression):
        driver = owner.driver_add(path, index).driver
        driver.type = "SCRIPTED"
        for key, prop in (("d", "draw_amount"), ("s", "spring")):
            var = driver.variables.new()
            var.name, var.type = key, "SINGLE_PROP"
            var.targets[0].id = rig
            var.targets[0].data_path = f'pose.bones["CTRL_Draw"]["{prop}"]'
        driver.expression = expression

    travel = pb["MCH_DrawTravel"]
    local = travel.bone.matrix_local.to_3x3().inverted() @ TRAVEL
    for i, v in enumerate(local):
        drive(travel, "location", i, f"{v:.8f}*(d + .074*s)")
    for suffix, sign in (("Upper", 1), ("Lower", -1)):
        for part, radians in (("Bow", .244), ("BowCam", .79)):
            p = pb[part+suffix]
            p.rotation_mode = "AXIS_ANGLE"
            axis = p.bone.matrix_local.to_3x3().inverted() @ RIGHT
            p.rotation_axis_angle = (0, *axis.normalized())
            drive(p, "rotation_axis_angle", 0, f"{radians*sign:.8f}*(d + .44*s)")
        p = pb["String"+suffix]
        stretch = p.constraints.new("STRETCH_TO")
        stretch.name, stretch.target, stretch.subtarget = "String to nock", rig, "CTRL_String"
        stretch.volume, stretch.rest_length = "NO_VOLUME", p.bone.length
    track = pb["ArrowSocket"].constraints.new("DAMPED_TRACK")
    track.name, track.target, track.subtarget = "Arrow along supporting index", rig, "MCH_ArrowRest"
    track.track_axis = "TRACK_Y"
    for side, target in [("L", "CTRL_Grip.L"), ("R", "CTRL_DrawHand.R")]:
        wrist_control = pb[target]
        # Calibrate pole roll with the IK endpoint at the deform arm's bind wrist.
        wrist_control.location = wrist_control.bone.matrix_local.to_3x3().transposed() @ (
            pb["Hand."+side].bone.head_local - wrist_control.bone.head_local)
        p = pb["Forearm."+side]
        ik = p.constraints.new("IK")
        ik.name, ik.target, ik.subtarget = "Wrist IK", rig, target
        ik.pole_target, ik.pole_subtarget, ik.chain_count = rig, "CTRL_Elbow."+side, 2
        ik.use_stretch = False
        # Solve rest roll once, on the actual Blender IK evaluator. The elbow's
        # intended pole plane stays unchanged when animators move the hand.
        def error(angle):
            ik.pole_angle = angle
            bpy.context.view_layer.update()
            return (p.head-elbows[side]).length_squared
        best = min(range(-180, 180, 5), key=lambda d: error(math.radians(d)))
        ik.pole_angle = math.radians(min((best+i*.1 for i in range(-49, 50)),
                                        key=lambda d: error(math.radians(d))))
        wrist_control.location = (0, 0, 0)
        rot = pb["Hand."+side].constraints.new("COPY_ROTATION")
        rot.name, rot.target, rot.subtarget = "Wrist orientation", rig, target
        rot.owner_space = rot.target_space = "POSE"
    for p in pb:
        if p.name.startswith(("CTRL_", "Clavicle", *FINGERS)):
            p.rotation_mode = "QUATERNION"
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def widgets(rig):
    coll = bpy.data.collections.new("Control shapes")
    bpy.context.scene.collection.children.link(coll)
    circle = [(math.cos(i*math.tau/24), 0, math.sin(i*math.tau/24)) for i in range(24)]
    outlines = {
        "Ring": circle,
        "Grip": [(-.65,0,-1),(.65,0,-1),(1,0,-.62),(1,0,.64),(.64,0,1),
                 (-.64,0,1),(-1,0,.65),(-1,0,-.64)],
        "Diamond": [(0,0,1),(.75,0,0),(0,0,-1),(-.75,0,0)],
        "Slider": [(-.30,-1,0),(.30,-1,0),(.30,.28,0),(.70,.28,0),
                   (0,1.2,0),(-.70,.28,0),(-.30,.28,0)]}
    shapes = {}
    for name, points in outlines.items():
        mesh = bpy.data.meshes.new("Shape "+name)
        mesh.from_pydata(points, [(i,(i+1)%len(points)) for i in range(len(points))], [])
        obj = bpy.data.objects.new("WGT_"+name, mesh)
        coll.objects.link(obj)
        shapes[name] = obj
    coll.hide_render = coll.hide_viewport = True
    for name, shape, scale in [
            ("CTRL_Master","Ring",.11), ("CTRL_BowGrip","Grip",.062),
            ("CTRL_Draw","Slider",.050), ("CTRL_String","Diamond",.024),
            ("CTRL_Grip.L","Ring",.039), ("CTRL_DrawHand.R","Ring",.042),
            ("CTRL_Elbow.L","Diamond",.040), ("CTRL_Elbow.R","Diamond",.040)]:
        p = rig.pose.bones[name]
        p.custom_shape = shapes[shape]
        p.use_custom_shape_bone_size = False
        p.custom_shape_scale_xyz = (scale,)*3


def preview_arrow(rig):
    # In the editor an animator can scrub the release without a game projectile.
    # In Godot the input edge owns the visible arrow and its free flight.
    slider = rig.pose.bones["CTRL_Draw"]
    slider["preview_arrow"] = True
    slider.id_properties_ui("preview_arrow").update(description="Стрела на тетиве в окне Blender")
    for prop in ("hide_render", "hide_viewport"):
        driver = bpy.data.objects["NockedArrow"].driver_add(prop).driver
        var = driver.variables.new()
        var.name, var.type = "show_arrow", "SINGLE_PROP"
        var.targets[0].id = rig
        var.targets[0].data_path = 'pose.bones["CTRL_Draw"]["preview_arrow"]'
        driver.expression = "1 - show_arrow"


def setup_workspace(rig):
    scene = bpy.context.scene
    camera = bpy.data.cameras.new("FP camera · 65 vertical")
    cam = bpy.data.objects.new("CAM_FirstPerson", camera)
    scene.collection.objects.link(cam)
    cam.rotation_euler = (math.pi/2, 0, 0)
    camera.sensor_fit = "VERTICAL"
    camera.lens = camera.sensor_height/(2*math.tan(math.radians(65)/2))
    camera.clip_start, camera.clip_end, camera.display_size = .01, 30, .08
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = 1, 133
    scene.name = "FPArchery"
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("Studio graphite")
    world.node_tree.nodes.get("Background").inputs[0].default_value = (.17,.21,.24,1)
    world.node_tree.nodes.get("Background").inputs[1].default_value = .65
    scene.world = world
    studio = bpy.data.collections.new("Authoring lights")
    scene.collection.children.link(studio)
    for name, pos, color, power, size in [
            ("Softbox", (-1.1,-.4,1.5), (1,.88,.76), 85, 1.35),
            ("Rim", (1.0,.9,.85), (.63,.79,1), 75, .9),
            ("Fill", (.6,-.45,.12), (.84,.92,1), 24, .85)]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size, light.color = power, "DISK", size, color
        obj = bpy.data.objects.new(name, light)
        studio.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (GRIP-Vector(pos)).to_track_quat("-Z","Y").to_euler()
        obj.hide_select = True
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for b in rig.data.bones:
        # Blender 5 moved selection to PoseBone.
        rig.pose.bones[b.name].select = b.name == "CTRL_Draw"
    rig.data.bones.active = rig.data.bones["CTRL_Draw"]
    for screen in bpy.data.screens:
        for area in screen.areas:
            s = area.spaces.active
            if area.type == "VIEW_3D":
                s.region_3d.view_perspective = "CAMERA"
                s.region_3d.view_camera_zoom = 2
                s.region_3d.view_distance = 1.4
                s.region_3d.view_location = GRIP
                s.overlay.show_floor = False
                s.overlay.show_axis_x = s.overlay.show_axis_y = False
                s.overlay.show_relationship_lines = False
                s.overlay.show_cursor = False
                s.overlay.show_extras = False
                s.shading.color_type = "MATERIAL"
                s.shading.show_shadows = True
                s.shading.show_cavity = True
                s.shading.cavity_type = "WORLD"
                s.clip_start = .006
            elif area.type == "DOPESHEET_EDITOR" and screen == bpy.context.screen:
                area.ui_type = "DOPESHEET"
                area.spaces.active.mode = "ACTION"


def main():
    if SOURCE.exists() and "--rebuild" not in sys.argv:
        raise RuntimeError("Source exists. Use export.py for hand edits, or -- --rebuild for a fresh rig.")
    from geometry import build
    from actions import create_actions
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = make_rig()
    build(rig)
    widgets(rig)
    preview_arrow(rig)
    create_actions(rig, TRAVEL, RIGHT, FORWARD, UP)
    setup_workspace(rig)
    bpy.context.scene.frame_set(9)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)
    print("FP_ARCHERY_SOURCE", SOURCE)


if __name__ == "__main__":
    main()
