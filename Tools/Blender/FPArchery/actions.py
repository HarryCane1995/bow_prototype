"""Sparse keys for the existing first-person rig.

To update the existing controls and their precision variants in place:
blender -b Assets/Experiments/FPArchery/Source/FPArchery.blend -P Tools/Blender/FPArchery/actions.py -- --save
"""
import math
from dataclasses import dataclass, replace

import bpy
from mathutils import Quaternion, Vector

ZERO = (0, 0, 0)
LOOPS = {"FPV_IDLE", "FPV_READY", "FPV_FULL_DRAW_HOLD", "FPV_RUN_SWAY"}
NORMAL_TILT = 16.0
PRECISION_TILT = 90.0
PRECISION_ACTIONS = {f"FPV_PRECISION_{phase}": f"FPV_{phase}" for phase in
                     ("DRAW_START", "DRAW_CHARGE", "FULL_DRAW_HOLD", "RELEASE", "CANCEL_DRAW")}


@dataclass(frozen=True)
class Beat:
    draw: float = 0
    hand_draw: float | None = None
    spring: float = 0
    bow: tuple = ZERO
    bow_angles: tuple = ZERO
    hand: tuple = ZERO
    wrist: float = 0
    opening: float = 0
    root: tuple = ZERO
    root_angles: tuple = ZERO
    bank: float = 0
    grip_roll: float = 0
    elbow: tuple = ZERO
    digits: tuple | None = None
    palm_yaw: float = 0
    support_push: float = 0


READY = Beat(wrist=-7, elbow=(.015,.010,-.009))
CAUGHT = Beat(.18, wrist=-2, elbow=(.013,-.006,.014), grip_roll=-1.8)
HOLD = Beat(1, wrist=-2, elbow=(.036,-.045,.034))
PARKED = Beat(root=(.062,-.060,-.535), root_angles=(-42,12,-9),
              bow=(.014,-.006,-.024), elbow=(.004,.014,-.022))
REST = Beat(bow=(-.012,-.011,-.022), wrist=-9, elbow=(.012,.018,-.017))
AIR = Beat(root=(0,.004,.009), root_angles=(.6,-.3,0),
           wrist=-7, elbow=(.005,.015,-.004))
STRIDE = Beat(root=(-.014,-.011,-.029), root_angles=(-3.3,-3.2,.65),
              wrist=-6, elbow=(.018,.015,-.014))

# Distances are metres in camera space. The five FK values run thumb to pinky.
# Shared contact poses keep the scrubbable start, charge and hold interchangeable.
CLIPS = {
    "FPV_IDLE": [
        (1, REST), (34, replace(REST, bow=(-.010,-.008,-.018), wrist=-8, elbow=(.014,.016,-.012))),
        (69, replace(REST, bow=(-.013,-.011,-.023), wrist=-7.6, elbow=(.010,.021,-.011))),
        (99, replace(REST, bow=(-.015,-.013,-.025), wrist=-9.5, elbow=(.009,.020,-.019))), (133, REST)],
    "FPV_READY": [
        (1, READY), (24, replace(READY, bow=(.0008,.001,.0024), wrist=-6.4, grip_roll=.35, elbow=(.014,.008,-.006))),
        (52, replace(READY, bow=(-.0011,-.0008,-.0019), wrist=-7.3, grip_roll=-.2, elbow=(.018,.010,-.009))),
        (69, replace(READY, bow=(-.0005,-.0003,-.0012), wrist=-7.5, elbow=(.016,.012,-.011))), (85, READY)],
    "FPV_EQUIP": [
        (1, PARKED), (6, Beat(root=(.041,-.038,-.239), root_angles=(-19,7,-5),
                             wrist=-11, grip_roll=3,
                             elbow=(.005,.025,-.023))),
        (12, Beat(root=(.006,.002,-.018), root_angles=(-1.7,.5,-1.1),
                  wrist=-9, grip_roll=2,
                  elbow=(.018,.022,-.015))),
        (16, Beat(root=(-.006,.005,.009), root_angles=(1.3,-1.6,.65),
                  bow=(.004,.004,.003), wrist=-5,
                  elbow=(.024,.016,-.004))),
        (21, replace(READY, root=(-.002,0,.002), root_angles=(.35,-.35,0),
                     wrist=-7.5)), (27, READY)],
    "FPV_DRAW_START": [
        (1, READY),
        (3, Beat(.019, bow=(.001,-.002,-.002), bank=-1.2, grip_roll=2.6,
                 wrist=-11, elbow=(.022,.015,-.008))),
        (5, Beat(.048, bow=(.003,-.001,-.002), bank=-1.7, grip_roll=1.2,
                 wrist=-8, elbow=(.026,.010,.001))),
        (7, Beat(.091, bow=(.003,.001,0), bank=-.8, grip_roll=-2.8,
                 wrist=-4, elbow=(.022,.003,.010))),
        (9, Beat(.134, bow=(.001,.001,.001), bank=-.22, grip_roll=-2.5,
                 wrist=-2.6, elbow=(.016,-.002,.013))),
        (11, CAUGHT)],
    "FPV_DRAW_CHARGE": [
        (1, CAUGHT),
        (4, Beat(.248, bow=(.0008,.0018,.0021), bank=.34, grip_roll=-2.3,
                 wrist=-1.8, elbow=(.016,-.009,.016))),
        (7, Beat(.321, bow=(.0019,.0041,.0048), bank=.84, grip_roll=-2.8,
                 wrist=-1.5, elbow=(.019,-.013,.019))),
        (10, Beat(.396, bow=(.003,.006,.007), bank=1.25, grip_roll=-3.1,
                  wrist=-1.1, elbow=(.023,-.017,.022))),
        (22, Beat(.683, bow=(.004,.005,.010), bank=1.65, grip_roll=-2.7,
                  wrist=.4, elbow=(.044,-.030,.032))),
        (32, Beat(.898, bow=(.002,.002,.005), bank=.74, grip_roll=-1.35,
                  wrist=-.5, elbow=(.045,-.041,.038))),
        (37, Beat(.975, bow=(.0005,.0007,.0013), bank=.20, grip_roll=-.4,
                  wrist=-1.6, elbow=(.039,-.045,.036))), (41, HOLD)],
    "FPV_FULL_DRAW_HOLD": [
        (1, HOLD), (28, replace(HOLD, bow=(.00022,.00004,.00035), wrist=-2.09,
                               grip_roll=.10, elbow=(.0364,-.0452,.0342))),
        (53, replace(HOLD, bow=(-.00015,.00010,-.00020), wrist=-1.94,
                     grip_roll=-.08, elbow=(.0359,-.0448,.0343))),
        (72, replace(HOLD, bow=(-.00022,.00004,-.00025), wrist=-1.96,
                     grip_roll=-.03, elbow=(.0358,-.0451,.0339))), (91, HOLD)],
    "FPV_RELEASE": [
        (1, HOLD),
        (2, Beat(.42, 1.006, bow=(.001,.002,.001), bow_angles=(.5,-.4,-.25), support_push=.012,
                 hand=(.004,-.007,.003), wrist=-2, grip_roll=-1.2, palm_yaw=3,
                 elbow=(.041,-.050,.036), digits=(.24,.55,.055,-.055,-.07))),
        (3, Beat(.035, 1.020, bow=(.002,-.002,.005), bow_angles=(1.7,-1.35,-.65), support_push=.030,
                 hand=(.009,-.014,.008), wrist=-1.2, grip_roll=-3.1, palm_yaw=8,
                 elbow=(.050,-.058,.044), digits=(.61,.99,.31,.025,-.05))),
        (4, Beat(0, 1.032, -.58, bow=(.001,-.007,.008), bow_angles=(3.1,-2.7,-1.1), support_push=.043,
                 hand=(.015,-.021,.016), wrist=.5, grip_roll=-4.4, palm_yaw=14,
                 elbow=(.060,-.063,.050), digits=(.81,1.04,.77,.34,.09))),
        (6, Beat(0, 1.038, .32, bow=(-.003,-.005,.009), bow_angles=(2.2,-1.7,-.7), support_push=.044,
                 hand=(.020,-.029,.022), wrist=1.8, grip_roll=-2.1, palm_yaw=18,
                 elbow=(.071,-.063,.060), digits=(.78,1.02,.94,.73,.43))),
        (8, Beat(0, 1.008, -.15, bow=(-.004,.001,.005), bow_angles=(.45,.95,.36), support_push=.029,
                 hand=(.028,-.026,.025), wrist=1, grip_roll=1.3, palm_yaw=16,
                 elbow=(.074,-.059,.060), digits=(.64,.96,.87,.81,.62))),
        (11, Beat(0, .846, .066, bow=(-.004,.002,.003), bow_angles=(-.8,.65,.18), support_push=.011,
                  hand=(.045,-.016,.028), wrist=-3, grip_roll=.7, palm_yaw=9,
                  elbow=(.070,-.043,.049), digits=(.58,.89,.73,.63,.53))),
        (15, Beat(0, .581, -.018, bow=(-.003,.001,.001), bow_angles=(.26,-.20,-.09), support_push=.002,
                  hand=(.061,-.008,.034), wrist=-7.5, elbow=(.052,-.023,.034), palm_yaw=4,
                  digits=(.60,.79,.59,.43,.34))),
        (18, Beat(0, .380, -.006, bow=(-.002,.0004,0), hand=(.021,-.007,.010),
                  wrist=-8.0, palm_yaw=1.4, elbow=(.039,-.012,.021),
                  digits=(.28,.32,.23,.18,.13))),
        (21, Beat(0, .182, bow=(-.001,0,-.001), wrist=-7, elbow=(.028,-.004,.010))),
        (25, replace(READY, bow=(0,0,-.0007), wrist=-7.3,
                     elbow=(.017,.007,-.004))), (28, READY)],
    "FPV_CANCEL_DRAW": [
        (1, HOLD), (5, Beat(.950, bow=(0,-.001,-.0006), wrist=-1.4, grip_roll=-1.2,
                            elbow=(.040,-.042,.033))),
        (12, Beat(.604, bow=(-.001,-.003,-.002), bank=-.7, grip_roll=-2.7,
                  wrist=-.8, elbow=(.038,-.024,.021))),
        (18, Beat(.265, bow=(-.002,-.002,-.002), bank=-.45, grip_roll=-2.4,
                  wrist=-2.9, elbow=(.020,-.010,.014))),
        (21, Beat(.124, bow=(-.001,-.001,-.001), bank=-.15, grip_roll=-1.8,
                  wrist=-4.4, elbow=(.014,-.001,.008))),
        (24, Beat(.034, wrist=-8, elbow=(.016,.006,-.002))),
        (27, READY)],
    "FPV_UNEQUIP": [
        (1, READY), (5, Beat(bow=(-.001,-.001,.002), bow_angles=(.42,-.45,0),
                            wrist=-8, elbow=(.019,.013,-.005))),
        (10, Beat(root=(.005,-.008,-.031), root_angles=(-3.5,1.8,-1.4),
                  wrist=-9, grip_roll=1.2,
                  elbow=(.018,.018,-.012))),
        (16, Beat(root=(.027,-.032,-.214), root_angles=(-19,7,-4),
                  bow=(.009,-.005,-.014), wrist=-7,
                  grip_roll=2.5, elbow=(.009,.021,-.023))),
        (23, PARKED)],
    "FPV_RUN_SWAY": [
        (1, STRIDE), (6, replace(STRIDE, root=(-.010,-.020,-.039), root_angles=(-4.4,-2.7,.5),
                                wrist=-7.4, grip_roll=1.5,
                                elbow=(.026,.004,-.008))),
        (13, replace(STRIDE, root=(.002,-.003,-.015), root_angles=(-1.6,-.25,-.14),
                     wrist=-5.4, grip_roll=-.9,
                     elbow=(.020,.008,-.018))),
        (21, replace(STRIDE, root=(.014,-.012,-.029), root_angles=(-3.5,2.3,-.7),
                     elbow=(.008,.018,-.015))),
        (26, replace(STRIDE, root=(.009,-.021,-.037), root_angles=(-4.2,1.8,-.5),
                     wrist=-6.9, grip_roll=1.1,
                     elbow=(.007,.008,-.009))),
        (33, replace(STRIDE, root=(-.002,-.002,-.016), root_angles=(-1.8,-.55,.14),
                     wrist=-5.5, grip_roll=-1.2,
                     elbow=(.014,.009,-.017))), (41, STRIDE)],
    "FPV_JUMP": [
        (1, READY), (5, Beat(root=(.001,-.010,-.022), root_angles=(-2.3,.8,0),
                            wrist=-8, grip_roll=1.4,
                            elbow=(.023,.005,-.003))),
        (12, Beat(root=(-.003,.008,.015), root_angles=(1.1,-.6,.18),
                  wrist=-5.2, grip_roll=-1.5,
                  elbow=(.014,.022,-.013))),
        (20, replace(AIR, root=(-.001,.005,.013), elbow=(.004,.017,-.007))), (30, AIR)],
    "FPV_LAND": [
        (1, AIR), (4, Beat(root=(.004,-.016,-.039), root_angles=(-3.8,1.55,-.4),
                          wrist=-9, grip_roll=2.8,
                          elbow=(.020,.005,-.002))),
        (8, Beat(root=(-.002,.002,.006), root_angles=(.7,-.5,.18),
                 wrist=-5.3, grip_roll=-1.6,
                 elbow=(.022,.022,-.017))),
        (13, replace(READY, root=(.0005,-.001,-.003), root_angles=(-.25,.16,0),
                     wrist=-7.8, grip_roll=.55,
                     elbow=(.012,.012,-.008))), (19, READY)],
}


def in_bone_axes(p, v):
    return p.bone.matrix_local.to_3x3().transposed() @ Vector(v)


def angle_tuple(angles):
    pitch, bank, yaw = map(math.radians, angles)
    return (Quaternion((0,0,1), yaw) @ Quaternion((0,1,0), bank)
            @ Quaternion((1,0,0), pitch))


def key_transform(p, frame, offset, rotation):
    axes = p.bone.matrix_local.to_quaternion()
    p.location = in_bone_axes(p, offset)
    p.rotation_quaternion = axes.inverted() @ rotation @ axes
    p.keyframe_insert("location", frame=frame, group=p.name)
    p.keyframe_insert("rotation_quaternion", frame=frame, group=p.name)


def support_draw(clip, beat):
    if clip == "FPV_RELEASE" and beat.hand_draw is not None:
        # The string is already forward while the supporting hand is still braced.
        return max(beat.draw, min(1.0, beat.hand_draw))
    return beat.draw


def sample_bow(rig):
    """Read the real axle centres and nocking line after evaluating the rig."""
    animation = rig.animation_data_create()
    current = animation.action
    animation.action = None
    controls = rig.pose.bones["CTRL_Draw"]
    previous = controls["draw_amount"], controls["spring"]
    samples = {}
    for amount in {min(1.0, support_draw(name, pose)) for name, beats in CLIPS.items() for _, pose in beats}:
        controls["draw_amount"], controls["spring"] = float(amount), 0.0
        rig.update_tag()
        bpy.context.view_layer.update()
        bones = rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
        grip = bones["BowGrip"]
        unplace = grip.bone.matrix_local @ grip.matrix.inverted()
        samples[amount] = (unplace @ bones["CTRL_String"].head, bones["MCH_ArrowRest"].bone.head_local.copy(),
                           unplace @ bones["BowCamUpper"].head, unplace @ bones["BowCamLower"].head)
    controls["draw_amount"], controls["spring"] = previous
    animation.action = current
    return samples


def grip_turn(axis, full_tilt, draw, grip_roll):
    ready, held = (-14.0, -24.0) if full_tilt == PRECISION_TILT else (48.0, 58.0)
    return Quaternion(axis, math.radians(ready + (held - ready) * draw + .35 * grip_roll))


def bow_placement(sample, draw, grip, pose, full_tilt, up):
    nock, index_rest, top, bottom = sample
    lift = 1.0 - (1.0 - draw) ** 1.5
    ready_nock = Vector((.028, .530, -.187))
    # Keep the canted shaft above the riser in projection. The upright
    # stance brings the string hand closer to the centre of the view.
    held_nock = Vector((.005, .260, -.068)) if full_tilt == PRECISION_TILT else Vector((.047, .273, -.024))
    anchor = ready_nock.lerp(held_nock, draw) + Vector(pose.bow)
    contact = grip + grip_turn(up, full_tilt, draw, pose.grip_roll) @ (index_rest - grip)
    axis = (contact - nock).normalized()
    forward = (Vector((0, 14, 0)) - anchor).normalized()
    # Project the two moving axles into the camera. At ready the upper axle
    # points right. Each aiming mode has its own full-draw screen angle.
    tilt = math.radians(full_tilt * lift + pose.bank)
    desired = Vector((math.cos(tilt), 0, math.sin(tilt)))
    aligned = axis.rotation_difference(forward)
    span = aligned @ (top - bottom)
    lateral = span - span.dot(forward) * forward
    desired_perp = desired - desired.dot(forward) * forward
    roll = math.atan2(forward.dot(lateral.cross(desired_perp)), lateral.dot(desired_perp))
    orientation = Quaternion(forward, roll) @ aligned
    for _ in range(3):
        a = anchor + orientation @ (top - nock)
        b = anchor + orientation @ (bottom - nock)
        x, z = a.x/a.y - b.x/b.y, a.z/a.y - b.z/b.y
        difference = math.atan2(desired.x*z - desired.z*x, desired.x*x + desired.z*z)
        orientation = Quaternion(forward, difference) @ orientation
    # Recoil and the start of lowering can move the sight. Bank during the
    # draw was solved about the sight itself, so the arrow still points through it.
    orientation = angle_tuple(pose.bow_angles) @ orientation
    return anchor - orientation @ (nock - grip) - grip, orientation


FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def key_fingers(bones, frame, pose, brace, forward, up):
    # The fingers stay curled on the nocked arrow and open at the break. Spread
    # happens at the base joint, so the second and third hinges still bend in a plane.
    extension = pose.digits or tuple(pose.opening * v for v in (1.04,1.23,.82,.48,.31))
    pressure = min(1.05, .78*brace + max(0.0, -pose.grip_roll)*.065)
    for side in ("R", "L"):
        for number, finger in enumerate(FINGERS):
            for joint in range(3):
                p = bones[f"{finger}{joint+1}.{side}"]
                if side == "R":
                    hinge = (-.38,-.70,-.95)[joint] * extension[number]
                    if finger == "Thumb":
                        hinge *= -.72
                    spread = (.24,.22,.064,-.13,-.29)[number] * extension[number]
                else:
                    hinge = (-.020,-.040,-.052)[joint] * pressure
                    hinge *= (-.6,.72,1.0,.83,.66)[number]
                    spread = 0.0
                rotation = Quaternion(in_bone_axes(p, up), hinge)
                if joint == 0 and spread:
                    rotation = Quaternion(in_bone_axes(p, forward), spread) @ rotation
                p.rotation_quaternion = rotation
                p.keyframe_insert("rotation_quaternion", frame=frame, group=p.name)


def control_paths():
    paths = {f'pose.bones["CTRL_Draw"]["{p}"]' for p in ("draw_amount", "spring", "preview_arrow")}
    for name in ("CTRL_Master", "CTRL_BowGrip", "CTRL_Grip.L", "CTRL_DrawHand.R"):
        paths.update(f'pose.bones["{name}"].{p}' for p in ("location", "rotation_quaternion"))
    for side in ("L", "R"):
        paths.update(f'pose.bones["{name}.{side}"].location' for name in ("Clavicle","CTRL_Elbow"))
        for finger in FINGERS:
            paths.update(f'pose.bones["{finger}{n}.{side}"].rotation_quaternion' for n in (1,2,3))
    return paths


def action_controls(action, slot, paths):
    curves = {}
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(slot)
            if bag:
                curves.update({(c.data_path, c.array_index): c for c in bag.fcurves if c.data_path in paths})
    return curves


def match_tangents(ending, beginning):
    """Give both sides of a shared contact or loop seam the same velocity."""
    for channel in ending.keys() & beginning.keys():
        left = ending[channel].keyframe_points
        right = beginning[channel].keyframe_points
        if len(left) < 2 or len(right) < 2 or "preview_arrow" in channel[0]:
            continue
        before, end = left[-2], left[-1]
        start, after = right[0], right[1]
        if abs(end.co.y - start.co.y) > .00001:
            continue
        dt1, dt2 = end.co.x-before.co.x, after.co.x-start.co.x
        v1, v2 = (end.co.y-before.co.y)/dt1, (after.co.y-start.co.y)/dt2
        speed = 2*v1*v2/(v1+v2) if v1*v2 > 0 else 0.0
        end.handle_left_type = start.handle_right_type = "FREE"
        end.handle_left = (end.co.x-dt1/3, end.co.y-speed*dt1/3)
        start.handle_right = (start.co.x+dt2/3, start.co.y+speed*dt2/3)


def finish_curves(curves):
    for curve in curves.values():
        for point in curve.keyframe_points:
            point.interpolation = "CONSTANT" if "preview_arrow" in curve.data_path else "BEZIER"
            point.handle_left_type = point.handle_right_type = "AUTO_CLAMPED"


def match_contacts(written):
    for name in LOOPS | {"FPV_PRECISION_FULL_DRAW_HOLD"}:
        match_tangents(written[name], written[name])
    match_tangents(written["FPV_DRAW_START"], written["FPV_DRAW_CHARGE"])
    match_tangents(written["FPV_PRECISION_DRAW_START"], written["FPV_PRECISION_DRAW_CHARGE"])


def key_offset(bone, frame, offset):
    bone.location = in_bone_axes(bone, offset)
    bone.keyframe_insert("location", frame=frame, group=bone.name)


def write_support_tracks(rig):
    """Pose the left arm against the existing bow. All positions below are root-relative."""
    source = rig.animation_data
    scene = bpy.context.scene
    active_before = source.action
    frame_before, subframe_before = scene.frame_current, scene.frame_subframe
    bones = rig.pose.bones
    root, grip = bones["Root"], bones["BowGrip"]
    palm, pole, clavicle = (bones[name] for name in ("CTRL_Grip.L", "CTRL_Elbow.L", "Clavicle.L"))
    upper, forearm = bones["UpperArm.L"].bone, bones["Forearm.L"].bone
    # The mechanical sleeve can swivel around the forearm independently of
    # elbow flexion. Keep its dorsal plate facing the body throughout the draw.
    constraints = bones["Forearm.L"].constraints
    sleeve = constraints.get("Support sleeve swivel") or constraints.new("LOCKED_TRACK")
    sleeve.name = "Support sleeve swivel"
    sleeve.target, sleeve.subtarget = rig, root.name
    sleeve.lock_axis, sleeve.track_axis = "LOCK_Y", "TRACK_Z"
    axis = (grip.bone.tail_local - grip.bone.head_local).normalized()
    palm_axis = (palm.bone.tail_local - palm.bone.head_local).normalized()
    palm_offset = palm.bone.head_local - grip.bone.head_local
    paths = {bone.path_from_id("location") for bone in (palm, pole, clavicle)}
    paths.add(palm.path_from_id("rotation_quaternion"))
    written = {}
    for name, motion in {**{n: n for n in CLIPS}, **PRECISION_ACTIONS}.items():
        source.action = bpy.data.actions[name]
        for curve in action_controls(source.action, source.action_slot, paths).values():
            curve.keyframe_points.clear()
        for frame, beat in CLIPS[motion]:
            scene.frame_set(frame)
            grip_pose = root.bone.matrix_local @ root.matrix.inverted() @ grip.matrix
            bow_rotation = grip_pose.to_quaternion() @ grip.bone.matrix_local.to_quaternion().inverted()
            brace = min(1.0, support_draw(motion, beat))
            # Turn around the handle so the fingers keep their wrap as the bow cants.
            tilt = PRECISION_TILT if name in PRECISION_ACTIONS else NORMAL_TILT
            turn = grip_turn(axis, tilt, brace, beat.grip_roll)
            key_transform(palm, frame, turn @ palm_offset - palm_offset, turn)
            rotation = bow_rotation @ turn
            wrist = grip_pose.translation + rotation @ palm_offset
            # Continue the actual palm centreline through the wrist by one forearm
            # length. Place the shoulder and pole on this triangle so IK can reach
            # the grip without bending the wrist or stretching either arm segment.
            fore_direction = rotation @ palm_axis
            elbow = wrist - fore_direction * forearm.length
            shoulder_guide = upper.head_local + Vector((.025, .045, .012)) * brace
            shoulder_guide.y += .58 * beat.support_push
            to_shoulder = (shoulder_guide - elbow).normalized()
            # Extend the upper arm with the draw, leaving a soft elbow at release.
            shoulder = elbow + to_shoulder.slerp(-fore_direction, .45 * brace) * upper.length
            key_offset(clavicle, frame, shoulder - upper.head_local)
            arm_line = (wrist - shoulder).normalized()
            bend = elbow - shoulder
            outward = (bend - arm_line * arm_line.dot(bend)).normalized()
            key_offset(pole, frame, elbow + .25 * outward - pole.bone.head_local)
        curves = action_controls(source.action, source.action_slot, paths)
        finish_curves(curves)
        written[name] = curves
    match_contacts(written)
    source.action = active_before
    scene.frame_set(frame_before, subframe=subframe_before)


def create_actions(rig, travel=None, right=None, forward=None, up=None, *, update_existing=False):
    bones = rig.pose.bones
    source = rig.animation_data_create()
    slider = bones["CTRL_Draw"]
    hand = bones["CTRL_DrawHand.R"]
    active_before = source.action
    frame_before = bpy.context.scene.frame_current
    if update_existing:
        missing = set(CLIPS) - set(bpy.data.actions.keys())
        if missing:
            raise ValueError(f"Missing Actions on the source rig: {sorted(missing)}")
    wrist_from_nock = hand.bone.head_local - slider.bone.head_local
    samples = sample_bow(rig)
    if travel is None:
        travel = samples[1.0][0] - samples[0.0][0]
    if forward is None:
        forward = (bones["ArrowSocket"].bone.tail_local - bones["ArrowSocket"].bone.head_local).normalized()
    if up is None:
        up = (bones["BowGrip"].bone.tail_local - bones["BowGrip"].bone.head_local).normalized()
    paths = control_paths()
    written = {}
    motions = {name: name for name in CLIPS}
    motions.update(PRECISION_ACTIONS)
    for name, motion in motions.items():
        beats = CLIPS[motion]
        max_tilt = PRECISION_TILT if name in PRECISION_ACTIONS else NORMAL_TILT
        action = bpy.data.actions.get(name) if update_existing else None
        if action is None:
            action = bpy.data.actions.new(name)
        action.use_fake_user = True
        action.use_frame_range = True
        action.frame_start, action.frame_end = beats[0][0], beats[-1][0]
        action.use_cyclic = motion in LOOPS
        source.action = action
        if update_existing:
            for curve in action_controls(action, source.action_slot, paths).values():
                curve.keyframe_points.clear()
        for frame, pose in beats:
            d = pose.draw
            # At release the supporting shoulder initially stays braced while
            # the string travels forward. These two channels have distinct arcs.
            h = pose.hand_draw if motion == "FPV_RELEASE" and frame < 21 and pose.hand_draw is not None else d
            brace = support_draw(motion, pose)
            # Blender ID properties preserve the assigned Python storage type.
            # An integer endpoint would quantize the interpolated driver to 0/1.
            slider["draw_amount"], slider["spring"] = float(d), float(pose.spring)
            for prop in ("draw_amount", "spring"):
                slider.keyframe_insert(f'["{prop}"]', frame=frame, group=slider.name)
            if frame == beats[0][0] or motion == "FPV_RELEASE":
                slider["preview_arrow"] = motion != "FPV_RELEASE" or frame == 1 or frame >= 21
                slider.keyframe_insert('["preview_arrow"]', frame=frame, group=slider.name)
            key_transform(bones["CTRL_Master"], frame, pose.root, angle_tuple(pose.root_angles))
            lift = min(1.0, brace)
            grip_rest = bones["BowGrip"].bone.head_local
            placement, orientation = bow_placement(samples[lift], lift, grip_rest, pose, max_tilt, up)
            # Camera forward is +Y in this Blender rig. Drive the gripped bow and
            # its IK target together, leaving the string hand free at the cheek.
            push = Vector((0, pose.support_push, 0))
            key_transform(bones["CTRL_BowGrip"], frame, placement + push, orientation)
            wrist_rot = Quaternion(forward, math.radians(6*d + pose.wrist))
            # Keep the nocking fingers on their authored trajectory as the bow
            # rolls independently about the shaft in the supporting hand.
            hand_orientation = orientation
            if max_tilt != PRECISION_TILT and lift > 0:
                _, hand_orientation = bow_placement(samples[lift], lift, grip_rest, pose, PRECISION_TILT, up)
            # Turn the loaded glove about the nock as it moves from carry to aim.
            relaxed = max(0.0, 1.0 - brace/.36)
            if relaxed:
                relaxed = relaxed*relaxed*(3.0 - 2.0*relaxed)
                world_wrist = (hand_orientation @ wrist_rot).slerp(wrist_rot, relaxed)
                wrist_rot = hand_orientation.inverted() @ world_wrist
            # A forearm approaches the face from the side. Rotate about the
            # actual captured nock to keep the palm readable through the lift.
            carry_roll = -8.0*lift if max_tilt == NORMAL_TILT else 0.0
            counter_roll = math.radians(-13.5*lift - 16.0*math.sin(math.pi*lift) - carry_roll)
            hand_turn = Quaternion((0, 0, 1), math.radians(pose.palm_yaw)) @ Quaternion((0, 1, 0), counter_roll)
            wrist_rot = orientation.inverted() @ hand_turn @ hand_orientation @ wrist_rot
            reach = Vector(pose.hand) - push
            offset = (travel*(h - d - pose.spring*.074) + orientation.inverted() @ reach
                      + wrist_rot @ wrist_from_nock - wrist_from_nock)
            key_transform(hand, frame, offset, wrist_rot)
            # The scapula initiates the pull; the bend plane carries the elbow
            # a fraction behind the wrist at the break and on ground impact.
            right_elbow = Vector(pose.elbow)
            key_offset(bones["Clavicle.R"], frame, Vector((.012,-.022,.018))*brace + right_elbow*.17)
            key_offset(bones["CTRL_Elbow.R"], frame, right_elbow)
            key_fingers(bones, frame, pose, brace, forward, up)
        curves = action_controls(action, source.action_slot, paths)
        finish_curves(curves)
        written[name] = curves
    match_contacts(written)
    write_support_tracks(rig)
    source.action = active_before if update_existing else bpy.data.actions["FPV_DRAW_CHARGE"]
    bpy.context.scene.frame_set(frame_before)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Update the authored controls on the open FPArchery source.")
    parser.add_argument("--left-grip-only", action="store_true", help="Update only the left wrist, elbow and clavicle tracks.")
    save = parser.add_mutually_exclusive_group(required=True)
    save.add_argument("--save", action="store_true", help="Save to the opened .blend.")
    save.add_argument("--output", help="Save an explicit working copy.")
    options = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not bpy.data.filepath:
        parser.error("Open the existing FPArchery.blend before applying its Actions.")
    rig = bpy.data.objects["FPArcheryRig"]
    if options.left_grip_only:
        write_support_tracks(rig)
    else:
        create_actions(rig, update_existing=True)
    destination = bpy.path.abspath(options.output) if options.output else bpy.data.filepath
    result = bpy.ops.wm.save_as_mainfile(filepath=destination, compress=True)
    if result != {"FINISHED"}:
        raise RuntimeError(f"Could not save {destination}: {result}")
