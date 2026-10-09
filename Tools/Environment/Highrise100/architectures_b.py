"""Fifty authored high-rise silhouettes for the second half of Highrise100.

No Blender state is touched here.  The caller supplies the geometry/material
adapter; dimensions are metres and every recipe stands on z=0.  The variant
index selects a separate construction, never a random seed or detail preset.
"""

from math import cos, sin, pi


NAMES = {
    "retro": ["Foundry Ziggurat", "Twin Courtyard", "Cross Reliquary", "Sawtooth Crown", "Octagon Regency"],
    "maintenance": ["Service Cleft", "Gantry Keep", "Repair Stack", "Silo Annex", "Plant Cathedral"],
    "exoskeleton": ["Diamond Carapace", "Ladder Twins", "Crossbrace Monolith", "Splayed Cage", "Three Tube Frame"],
    "suspended": ["Raised Citadel", "Spine Cantilevers", "Hanging Cradle", "Habitable Truss", "Tripod Lantern"],
    "transit": ["Rail Gateway", "Crossing Terminal", "Platform Funnel", "Terrace Interchange", "Radial Junction"],
    "datacenter": ["Vent Stack", "Server Canyon", "Cooling Chimneys", "Rack Terraces", "Armored Archive"],
    "civic": ["Crown Assembly", "Court of Towers", "Civic Needle", "Sky Forum", "Civic Bastion"],
    "mixed_use": ["Market and Needles", "Terraced Quarter", "Hotel Hinge", "Stacked Districts", "Atrium City"],
    "buttress": ["Flying Piers", "Raking Fortress", "Stepped Abutments", "Split Cathedral", "Four Petal Keep"],
    "hero": ["Broken Halo", "Giant Keyhole", "Sky Cathedral", "Helix Citadel", "Crown of Bridges"],
}


def _mass(t, name, x, y, z, w, d, h, mat="facade", rot=0):
    t.box(name, (x, y, z + h / 2), (w, d, h), mat, rot)


def _post(t, name, x, y, z, height, width=3, mat="concrete"):
    _mass(t, name, x, y, z, width, width, height, mat)


def _frame(t, name, x, y, z, w, d, height, width=3):
    for ix in (-1, 1):
        for iy in (-1, 1):
            _post(t, "%s_%s_%s" % (name, ix, iy), x + ix*w/2, y + iy*d/2, z, height, width, "metal")


def _bands(t, x, y, z0, z1, w, d, count=4, mat="metal"):
    for j in range(1, count+1):
        t.band(x, y, z0 + (z1-z0)*j/(count+1), w, d, 1.4, mat)


def _cross(t, name, a, b, c, d, width=2.3):
    a, b, c, d = [(*p[:2], max(p[2], width*.75)) for p in (a, b, c, d)]
    t.beam(name + "_a", a, b, width, "metal")
    t.beam(name + "_b", c, d, width, "metal")


def _ground_brace(t, name, x, y, target, width=4.0, mat="concrete"):
    # A real ground shoe keeps the cross section of a sloping beam above z=0.
    _mass(t, name+"_shoe", x, y, 0, width*1.5, width*1.5, width*.75, mat)
    t.beam(name, (x, y, width*.75), target, width, mat)


def _retrofit_grid(t, x, y, w, d, h, floors=5):
    # The old concrete frame sits outside the existing regular window sheets.
    for xx in (-w*.46, 0, w*.46):
        _mass(t, "old_concrete_pier", x+xx, y-d*.505, 0, 1.4, 1.4, h, "concrete")
    for j in range(1, floors+1):
        t.band(x, y, h*j/(floors+1), w+1.1, d+1.1, 1.6, "concrete")


def _external_lift(t, x, y, h, w=5.2, d=5.2):
    _mass(t, "new_external_lift", x, y, 0, w, d, h, "service")
    for side in (-1, 1):
        _mass(t, "new_lift_rail", x+side*w*.44, y-d*.51, 0, .45, .60, h+1.4, "metal")
    _mass(t, "new_lift_machine", x, y, h, w*1.2, d*1.15, 3.1, "metal")


def _retro(t, v, w, d, h):
    if v == 0:
        # Deep street wall, then four progressively narrower occupied terraces.
        t.podium(w*1.15, d*1.15, h*.10)
        levels = [(0, .10, .33, 1, 1), (0, .43, .27, .78, .82),
                  (0, .70, .17, .56, .64), (0, .87, .13, .32, .42)]
        for j, (x, z, hh, ww, dd) in enumerate(levels):
            _mass(t, "tier_%d" % j, x, 0, h*z, w*ww, d*dd, h*hh)
            t.band(x, 0, h*(z+hh)-1.2, w*ww+2, d*dd+2, 2.4, "concrete")
        for x in (-w*.45, w*.45):
            _post(t, "masonry_rib", x, -d*.50, h*.1, h*.32, 3.2)
        t.roof(0, 0, h, w*.3, d*.4, 1)
        t.tag("stepped_masonry", "four_setbacks", "central_crown")
    elif v == 1:
        # H plan with an open street-facing court and two unequal chimney crowns.
        for x, hh in ((-w*.32, h), (w*.32, h*.82)):
            _mass(t, "court_wing", x, 0, 0, w*.40, d, hh)
            _bands(t, x, 0, 0, hh, w*.40+1, d+1, 5, "concrete")
            _mass(t, "wing_cap", x, d*.08, hh, w*.28, d*.64, h*.045, "secondary")
            t.roof(x, d*.08, hh+h*.045, w*.25, d*.58, 0)
        _mass(t, "rear_court_link", 0, d*.32, 0, w*.28, d*.36, h*.43, "secondary")
        _mass(t, "high_crossing", 0, -d*.10, h*.63, w*.27, d*.44, h*.065, "secondary")
        t.tag("open_court", "unequal_twins", "rear_spine", "elevated_bridge")
    elif v == 2:
        # Cruciform church-like tower: broad transept and four falling shoulders.
        t.podium(w*1.14, d*1.12, h*.065)
        _mass(t, "nave", 0, 0, h*.065, w*.48, d, h*.75)
        _mass(t, "transept", 0, 0, h*.065, w, d*.48, h*.59, "secondary")
        for x in (-w*.40, w*.40):
            _mass(t, "side_buttress", x, 0, h*.065, w*.18, d*.35, h*.69, "concrete")
        for y in (-d*.42, d*.42):
            _mass(t, "end_pier", 0, y, h*.065, w*.25, d*.16, h*.82, "secondary")
        t.taper("eight_sided_spire", [(h*.815, w*.26, d*.30, 0, 0),
                (h*.94, w*.15, d*.18, 0, 0), (h, w*.10, d*.12, 0, 0)], "secondary", 8)
        t.antenna(0, 0, h, h*.075)
        t.tag("cruciform", "flying_shoulders", "tapered_crown")
    elif v == 3:
        # Strong continuous front, five rearward bays with descending top line.
        t.podium(w*1.08, d*1.12, h*.075)
        _mass(t, "lower_slab", 0, 0, h*.075, w, d, h*.42)
        for j in range(3):
            x = (j-1)*w*.32
            hh = h*(.925-j*.14)
            _mass(t, "sawtooth_bay_%d" % j, x, d*.04, h*.075, w*.34, d*.76, hh)
            t.band(x, d*.04, h*.075+hh, w*.35, d*.79, 2.1, "concrete")
            t.roof(x, d*.04, h*.075+hh+1.1, w*.30, d*.68, j)
        for j in range(5):
            x = -w*.47 + j*w*.235
            _post(t, "front_rib_%d" % j, x, -d*.515, h*.075, h*.42, 2.2)
        t.tag("sawtooth_skyline", "deep_lower_slab", "stepped_rear_bays")
    else:
        # Rounded civic-deco mass with a broad low drum and a narrow octagonal shaft.
        t.taper("octagon_plinth", [(0, w*.66, d*.66, 0, 0),
                (h*.12, w*.66, d*.66, 0, 0)], "concrete", 8)
        t.taper("octagon_shaft", [(h*.12, w*.49, d*.49, 0, 0),
                (h*.72, w*.49, d*.49, 0, 0),
                (h*.84, w*.38, d*.38, 0, 0)], "facade", 8)
        t.taper("crown_drum", [(h*.84, w*.35, d*.35, 0, 0),
                (h*.95, w*.35, d*.35, 0, 0),
                (h, w*.21, d*.21, 0, 0)], "secondary", 8)
        for j in range(8):
            a = pi*j/4
            _post(t, "deco_fin_%d" % j, cos(a)*w*.50, sin(a)*d*.50, h*.12, h*.54, 2.0)
        t.roof(0, 0, h, w*.28, d*.28, 1)
        t.tag("octagonal", "deco_fins", "drum_plinth", "tiered_crown")


def _maintenance(t, v, w, d, h):
    t.tag("old_new_retrofit", "old_regular_window_grid", "new_steel_secondary_layer")
    if v == 0:
        # Usable towers separated by a visible services trench.
        for x, hh in ((-w*.33, h), (w*.33, h*.76)):
            _mass(t, "old_concrete_wing", x, 0, 0, w*.38, d, hh, "concrete")
            # Discrete window bays sit in the massive old wall; their shallow
            # boxes embed 0.18 m into it and project 0.42 m, below the old belts.
            for offset in (-w*.095, w*.095):
                _mass(t, "old_vertical_window_bay", x+offset, -d*.50-.12,
                      hh*.07, w*.060, .60, hh*.80)
            side = -1 if x < 0 else 1
            for yy in (-d*.25, d*.23):
                _mass(t, "old_side_window_bay", x+side*(w*.19+.12), yy,
                      hh*.09, .60, d*.12, hh*.76)
            _mass(t, "rear_stair_window_bay", x, d*.50+.12,
                  hh*.10, w*.066, .60, hh*.73, "secondary")
            _retrofit_grid(t, x, 0, w*.38, d, hh)
            t.roof(x, 0, hh, w*.34, d*.82, 0)
        _mass(t, "service_spine", 0, d*.32, 0, w*.19, d*.20, h*.94, "service")
        for j in range(7):
            z = h*(.12+j*.105)
            t.band(0, 0, z, w*.28, d*.85, 1.6, "metal")
            for y in (-d*.38, d*.38):
                t.beam("service_truss", (-w*.14, y, z), (w*.14, y, z+h*.07), 1.3, "metal")
        for x in (-w*.055, w*.055):
            t.cylinder("riser", (x, -d*.08, h*.48), 1.4, h*.92, "metal", 8)
        _external_lift(t, w*.48, d*.35, h*.78, 4.2, 5.2)
        _mass(t, "replacement_face_module", -w*.33, -d*.53, h*.51, w*.30, 2.1, h*.18, "secondary")
        _mass(t, "replacement_module_steel_sill", -w*.33, -d*.515,
              h*.51-1.2, w*.32, d*.06+2.4, 1.2, "metal")
        t.tag("service_cleft", "unequal_wings", "exposed_risers", "maintenance_landings",
              "concrete_majority_old_shell", "separate_vertical_window_bays", "new_replacement_face_module")
    elif v == 1:
        # Occupied shaft offset inside a freestanding maintenance gantry.
        _mass(t, "offset_shaft", -w*.10, d*.03, 0, w*.72, d*.72, h*.84)
        _retrofit_grid(t, -w*.10, d*.03, w*.72, d*.72, h*.84, 7)
        _frame(t, "gantry", 0, 0, 0, w, d, h, 3.2)
        for z in (h*.30, h*.58, h*.84, h):
            # Perimeter walkway, deliberately not a filled slab across the air gap.
            for y in (-d*.50, d*.50):
                _mass(t, "gantry_long_walk", 0, y, z-1, w+3, 3, 2, "metal")
            for x in (-w*.50, w*.50):
                _mass(t, "gantry_short_walk", x, 0, z-1, 3, d+3, 2, "metal")
        _mass(t, "hoist_head", w*.25, 0, h*.84, w*.30, d*.54, h*.11, "service")
        t.beam("hoist_rail", (-w*.53, 0, h), (w*.66, 0, h), 3.2, "metal")
        _external_lift(t, w*.38, d*.29, h*.84, 4.5, 4.5)
        t.roof(-w*.13, d*.02, h*.84, w*.45, d*.50, 2)
        t.tag("open_gantry", "offset_core", "perimeter_walkways", "hoist_head")
    elif v == 2:
        # Heavy independent repair blocks held by one full-height rear core.
        _mass(t, "rear_service_core", 0, d*.30, 0, w*.42, d*.40, h, "service")
        _mass(t, "load_bearing_base", 0, 0, 0, w*.78, d*.83, h*.19, "concrete")
        _mass(t, "old_window_front", 0, -d*.426, h*.025, w*.71, 1.1, h*.12)
        for j in range(4):
            x = (-1 if j % 2 else 1)*w*.13
            z = h*(.19+j*.185)
            _mass(t, "repair_volume_%d" % j, x, -d*.12, z, w*.82, d*.68, h*.14)
            _mass(t, "replacement_cassette_%d" % j, x, -d*.476, z+h*.02,
                  w*.52, 1.4, h*.095, "secondary")
            t.band(x, -d*.12, z, w*.86, d*.74, 2.2, "metal")
            for y in (-d*.43, d*.20):
                t.beam("cantilever_strut", (0, y, max(0, z-h*.10)),
                       (x+(-1 if x < 0 else 1)*w*.38, y, z), 2.1, "metal")
        t.roof(0, d*.30, h, w*.37, d*.34, 0)
        t.tag("staggered_repair_blocks", "rear_core", "replacement_facade_cassettes", "raking_supports")
    elif v == 3:
        # Two exposed process silos beside a conventional occupied annex.
        _mass(t, "old_concrete_annex", -w*.24, 0, 0, w*.55, d*.92, h*.89, "concrete")
        for offset in (-w*.135, w*.135):
            _mass(t, "annex_old_window_strip", -w*.24+offset, -d*.46-.12,
                  h*.045, w*.075, .60, h*.76)
            _mass(t, "annex_rear_window_strip", -w*.24+offset, d*.46+.12,
                  h*.075, w*.060, .60, h*.70)
        for yy in (-d*.24, d*.10):
            _mass(t, "annex_side_window_strip", -w*.515-.12, yy,
                  h*.06, .60, d*.13, h*.70)
        # A visibly newer front cassette occupies only one upper bay.  A steel
        # sill ties it to the old shell; the rest remains quiet concrete.
        _mass(t, "annex_new_front_cassette", -w*.105, -d*.46-.80,
              h*.57, w*.19, 1.85, h*.17, "secondary")
        _mass(t, "annex_cassette_steel_sill", -w*.105, -d*.46-.90,
              h*.57-1.2, w*.22, 2.20, 1.20, "metal")
        _retrofit_grid(t, -w*.24, 0, w*.55, d*.92, h*.89, 7)
        for j, yy in enumerate((-d*.23, d*.23)):
            x = w*.29
            hh = h*(1 if j == 0 else .73)
            t.cylinder("silo_%d" % j, (x, yy, hh/2), min(w*.19, d*.20), hh, "service", 12)
            for z in (hh*.15, hh*.40, hh*.66, hh*.90):
                t.cylinder("silo_collar", (x, yy, z), min(w*.20, d*.21), 2.1, "metal", 12)
            t.antenna(x, yy, hh, h*.035)
            for z in (h*.25, h*.52):
                _mass(t, "annex_skywalk", w*.07, yy, z, w*.33, 4, 3, "metal")
        t.roof(-w*.24, 0, h*.89, w*.46, d*.82, 1)
        _external_lift(t, -w*.49, d*.37, h*.89, 4.5, 4.5)
        t.tag("process_silos", "offset_annex", "circular_rectangular_mix", "narrow_skywalks",
              "concrete_majority_old_shell", "isolated_window_strips", "new_steel_supported_cassette")
    else:
        # Tall industrial nave, narrow corner stacks and a broken elevated plant crown.
        _mass(t, "plant_nave", 0, 0, 0, w*.64, d*.69, h*.59)
        _retrofit_grid(t, 0, 0, w*.64, d*.69, h*.59, 5)
        for x in (-w*.43, w*.43):
            for y in (-d*.41, d*.41):
                _mass(t, "plant_pier", x, y, 0, w*.18, d*.18, h*.94, "service")
        _mass(t, "upper_plant", 0, d*.12, h*.72, w*.83, d*.45, h*.19, "secondary")
        for x in (-w*.43, w*.43):
            t.beam("nave_roof_brace", (x, -d*.41, h*.59), (x, d*.41, h*.75), 2.4, "metal")
        for j in range(3):
            _mass(t, "rooftop_stack", (j-1)*w*.24, d*.12, h*.91, w*.13, d*.25, h*.09, "service")
        t.roof(0, 0, h*.59, w*.51, d*.56, 2)
        t.screen(w*.12, -d*.36, h*.42, w*.29, h*.13, 2)
        _external_lift(t, -w*.28, d*.37, h*.72, 5.2, 4.3)
        t.tag("industrial_nave", "four_plant_piers", "open_crown_gap", "triple_stacks")


def _exoskeleton(t, v, w, d, h):
    if v == 0:
        t.taper("tapered_core", [(0, w*.50, d*.50, 0, 0),
                (h*.32, w*.47, d*.47, 0, 0), (h*.62, w*.38, d*.38, 0, 0)], "facade", 8)
        t.taper("upper_carapace", [(h*.78, w*.34, d*.34, 0, 0),
                (h, w*.29, d*.29, 0, 0)], "secondary", 8)
        _mass(t, "rear_transfer_spine", 0, d*.25, h*.62, w*.32, d*.15, h*.16, "service")
        # Five structural bays; staggered diagonals meet at real ring nodes.
        for j in range(5):
            z0, z1 = h*j/5, h*(j+1)/5
            rx0, rx1 = w*(.52-.20*j/5), w*(.52-.20*(j+1)/5)
            ry0, ry1 = d*(.52-.20*j/5), d*(.52-.20*(j+1)/5)
            for k in range(8):
                a, b = k*pi/4, (k+1)*pi/4
                if j % 2:
                    a, b = b, a
                t.beam("diagonal_bay", (cos(a)*rx0, sin(a)*ry0, max(.9, z0)),
                       (cos(b)*rx1, sin(b)*ry1, z1), 1.5, "metal")
                t.beam("ring_chord", (cos(a)*rx1, sin(a)*ry1, z1),
                       (cos(b)*rx1, sin(b)*ry1, z1), 1.8, "metal")
        t.roof(0, 0, h, w*.40, d*.40, 1)
        t.tag("octagonal_taper", "five_structural_bays", "open_transfer_slot", "narrow_crown")
    elif v == 1:
        for x, hh in ((-w*.33, h), (w*.33, h*.91)):
            _mass(t, "ladder_finger", x, 0, 0, w*.37, d*.80, hh)
            _frame(t, "finger_posts", x, 0, 0, w*.39, d*.84, hh+3, 2.0)
            _bands(t, x, 0, 0, hh, w*.41, d*.86, 7)
            t.roof(x, 0, hh, w*.30, d*.68, 0)
        for z in (h*.24, h*.54, h*.83):
            _mass(t, "ladder_rung", 0, 0, z, w*.34, d*.41, h*.05, "secondary")
        t.tag("ladder_twins", "triple_occupied_rungs", "full_height_air_slot", "unequal_crowns")
    elif v == 2:
        _mass(t, "offset_core", -w*.04, d*.02, 0, w*.84, d*.82, h*.73)
        _mass(t, "rear_upper_core", -w*.04, d*.25, h*.73, w*.62, d*.32, h*.21, "secondary")
        _frame(t, "mega_columns", 0, 0, 0, w, d, h, 3.7)
        for j in range(3):
            z0, z1 = h*j/3, h*(j+1)/3
            for y in (-d*.50,):
                _cross(t, "front_X", (-w*.50, y, z0), (w*.50, y, z1),
                       (w*.50, y, z0), (-w*.50, y, z1), 3.2)
            for x in (-w*.50, w*.50):
                t.beam("side_compression", (x, -d*.50, max(1.8, z0)),
                       (x, d*.50, z1), 2.7, "metal")
            t.band(0, 0, z1, w+3, d+3, 2.6, "metal")
        t.band(0, 0, h*.94, w+3, d+3, 3, "metal")
        _mass(t, "roof_box", w*.13, d*.10, h*.94, w*.44, d*.46, h*.06, "service")
        t.tag("three_front_mega_X", "open_upper_frame", "rear_upper_core", "three_structural_belts")
    elif v == 3:
        # Narrow feet with an inhabited widening body and four splayed compression legs.
        t.taper("flaring_body", [(h*.08, w*.24, d*.24, 0, 0),
                (h*.62, w*.51, d*.46, 0, 0), (h*.80, w*.47, d*.45, 0, 0)], "facade", 8)
        _mass(t, "ground_service", 0, 0, 0, w*.39, d*.40, h*.15, "service")
        for sx in (-1, 1):
            for sy in (-1, 1):
                foot = (sx*w*.22, sy*d*.22, 0)
                shoulder = (sx*w*.49, sy*d*.44, h*.62)
                top = (sx*w*.44, sy*d*.43, h)
                _ground_brace(t, "splayed_leg", foot[0], foot[1], shoulder, 3.5, "metal")
                t.beam("crown_leg", shoulder, top, 2.7, "metal")
        for z, ww, dd in ((h*.32, w*.69, d*.65), (h*.62, w*1.02, d*.94),
                          (h*.80, w*.95, d*.91), (h*.97, w*.90, d*.87)):
            t.band(0, 0, z, ww, dd, 2.6, "metal")
        _mass(t, "rear_roof_access", 0, d*.28, h*.80, w*.25, d*.23, h*.17, "service")
        t.roof(0, 0, h*.97+1.3, w*.62, d*.58, 2)
        t.tag("flared_body", "narrow_feet", "four_structural_belts", "open_frame_crown")
    else:
        points = [(-w*.28, -d*.20, h*.83), (w*.28, -d*.20, h), (0, d*.28, h*.91)]
        for j, (x, y, hh) in enumerate(points):
            t.taper("tube_%d" % j, [(0, w*.245, d*.26, x, y),
                    (hh, w*.22, d*.235, x, y)], "facade", 8)
            for k in range(4):
                a = k*pi/2
                _ground_brace(t, "tube_rib", x+cos(a)*w*.25, y+sin(a)*d*.265,
                              (x+cos(a)*w*.225, y+sin(a)*d*.24, hh), 2, "metal")
            t.roof(x, y, hh, w*.30, d*.31, j)
        for z in (h*.31, h*.64):
            for j in range(3):
                x0, y0, _ = points[j]
                x1, y1, _ = points[(j+1)%3]
                t.beam("tube_bridge", (x0, y0, z), (x1, y1, z), 4, "metal")
        t.tag("three_octagonal_tubes", "triangular_plan", "unequal_heights", "ring_skywalks")


def _suspended(t, v, w, d, h):
    if v == 0:
        for x in (-w*.39, w*.39):
            for y in (-d*.38, d*.38):
                _post(t, "citadel_pier", x, y, 0, h*.39, min(w,d)*.13)
        _mass(t, "raised_lower_city", 0, 0, h*.33, w, d, h*.38)
        _mass(t, "upper_offset_city", w*.10, d*.09, h*.71, w*.70, d*.72, h*.29, "secondary")
        t.band(0, 0, h*.33, w*1.06, d*1.06, 4, "metal")
        _mass(t, "lift_core", -w*.31, d*.27, 0, w*.21, d*.25, h*.72, "service")
        t.roof(w*.10, d*.09, h, w*.59, d*.61, 1)
        t.tag("four_open_piers", "raised_occupied_mass", "off_center_upper_city", "street_void")
    elif v == 1:
        _mass(t, "central_anchor", 0, d*.16, 0, w*.28, d*.40, h, "service")
        for j in range(4):
            side = -1 if j % 2 == 0 else 1
            z = h*(.15+j*.19)
            x = side*w*.22
            _mass(t, "suspended_wing_%d" % j, x, -d*.08, z, w*.78, d*.75, h*.125)
            for yy in (-d*.35, d*.20):
                t.beam("wing_suspender", (side*w*.05, yy, z+h*.18),
                       (side*w*.59, yy, z+h*.12), 1.8, "metal")
            t.band(x, -d*.08, z, w*.82, d*.80, 2.2, "metal")
        t.roof(0, d*.16, h, w*.22, d*.32, 0)
        t.tag("single_spine", "alternating_cantilevers", "suspension_rods", "four_open_slots")
    elif v == 2:
        for x in (-w*.42, w*.42):
            _mass(t, "cradle_mast", x, 0, 0, w*.16, d*.36, h, "service")
        _mass(t, "top_transfer", 0, 0, h*.92, w*1.03, d*.42, h*.08, "metal")
        _mass(t, "hanging_pod", 0, 0, h*.39, w*.67, d, h*.36)
        for xx in (-w*.25, w*.25):
            for yy in (-d*.38, d*.38):
                t.beam("hanger", (xx, yy, h*.75), (xx, 0, h*.94), 2, "metal")
        _mass(t, "pod_keel", 0, 0, h*.34, w*.60, d*.85, h*.05, "service")
        _mass(t, "ground_station", 0, d*.13, 0, w*.54, d*.64, h*.10, "secondary")
        t.roof(0, 0, h*.75, w*.55, d*.82, 0)
        t.tag("paired_masts", "suspended_central_pod", "long_hangers", "free_understory")
    elif v == 3:
        for x, hh in ((-w*.44, h), (w*.44, h*.86)):
            _mass(t, "bridge_core", x, 0, 0, w*.24, d*.78, hh, "secondary")
            t.roof(x, 0, hh, w*.19, d*.65, 1)
        _mass(t, "habitable_bridge", 0, 0, h*.51, w*.71, d, h*.27)
        for yy in (-d*.51, d*.51):
            for j in range(3):
                x0, x1 = -w*.36+j*w*.24, -w*.36+(j+1)*w*.24
                _cross(t, "habitable_truss", (x0, yy, h*.51), (x1, yy, h*.78),
                       (x1, yy, h*.51), (x0, yy, h*.78), 2.8)
        _mass(t, "low_link", 0, d*.20, h*.16, w*.72, d*.23, h*.055, "service")
        t.tag("occupied_mega_bridge", "unequal_end_cores", "double_height_void", "exposed_bridge_truss")
    else:
        t.taper("lantern", [(h*.42, w*.37, d*.37, 0, 0),
                (h*.74, w*.56, d*.52, 0, 0), (h*.91, w*.43, d*.40, 0, 0),
                (h, w*.22, d*.22, 0, 0)], "facade", 8)
        for j in range(3):
            a = -pi/2 + j*2*pi/3
            foot = (cos(a)*w*.62, sin(a)*d*.61, 0)
            joint = (cos(a)*w*.24, sin(a)*d*.24, h*.47)
            _ground_brace(t, "tripod_leg", foot[0], foot[1], joint, min(w,d)*.12, "concrete")
            t.beam("tripod_rib", joint, (cos(a)*w*.49, sin(a)*d*.46, h*.76), 3, "metal")
        _post(t, "central_lift", 0, 0, 0, h*.47, min(w,d)*.15, "service")
        t.roof(0, 0, h, w*.27, d*.27, 2)
        t.tag("tripod_base", "faceted_lantern", "flared_shoulders", "pointed_crown")


def _transit(t, v, w, d, h):
    if v == 0:
        for x, hh in ((-w*.36, h), (w*.36, h*.82)):
            _mass(t, "gateway_tower", x, 0, 0, w*.38, d*.85, hh)
            t.roof(x, 0, hh, w*.33, d*.73, 0)
        _mass(t, "station_concourse", 0, 0, h*.24, w*1.2, d, h*.10, "secondary")
        for yy in (-d*.31, d*.31):
            _mass(t, "rail_deck", 0, yy, h*.22, w*1.48, 5, 2.4, "metal")
            for xx in (-w*.68, w*.68):
                _post(t, "rail_end_support", xx, yy, 0, h*.22, 3.1)
        _mass(t, "upper_gateway_link", 0, d*.13, h*.64, w*.34, d*.36, h*.05, "service")
        t.tag("rail_gateway", "open_ground_passage", "unequal_towers", "extended_station_decks")
    elif v == 1:
        # A diagonal terminal passes through a lower concourse and meets an offset shaft.
        t.podium(w*.96, d*.83, h*.11)
        _mass(t, "terminal_tower", -w*.14, d*.10, h*.11, w*.56, d*.67, h*.89)
        _mass(t, "terminal_annex", w*.29, -d*.18, h*.11, w*.39, d*.57, h*.44, "secondary")
        _mass(t, "diagonal_terminal", 0, -d*.10, h*.20, w*1.56, d*.44, h*.08, "secondary", 25)
        for xx in (-w*.59, w*.59):
            x, y = xx*cos(pi*25/180), -d*.10+xx*sin(pi*25/180)
            _post(t, "terminal_support", x, y, 0, h*.20, 4.5)
        t.beam("track_edge_a", (-w*.70, -d*.51, h*.20), (w*.70, d*.15, h*.20), 2.4, "metal")
        t.roof(-w*.14, d*.10, h, w*.48, d*.58, 1)
        t.roof(w*.29, -d*.18, h*.55, w*.31, d*.46, 0)
        t.tag("diagonal_terminal", "offset_tower", "lower_annex", "transport_cantilevers")
    elif v == 2:
        _mass(t, "central_service", 0, 0, 0, w*.33, d*.36, h*.30, "service")
        for xx in (-w*.39, w*.39):
            for yy in (-d*.35, d*.35):
                _ground_brace(t, "platform_rake", xx, yy, (xx*.54, yy*.57, h*.31), 4.0, "concrete")
        t.taper("funnel_tower", [(h*.26, w*.31, d*.31, 0, 0),
                (h*.51, w*.49, d*.49, 0, 0), (h, w*.31, d*.31, 0, 0)], "facade", 8)
        for xx in (-w*.50, w*.50):
            _mass(t, "side_station", xx, 0, h*.22, w*.33, d*1.22, h*.075, "secondary")
            for yy in (-d*.52, d*.52):
                _post(t, "station_leg", xx, yy, 0, h*.22, 3)
        t.roof(0, 0, h, w*.39, d*.39, 2)
        t.tag("tapered_transit_funnel", "raking_ground_legs", "paired_side_platforms", "narrow_base")
    elif v == 3:
        for side in (-1, 1):
            x = side*w*.34
            hh = h*(1 if side == -1 else .84)
            _mass(t, "terrace_core", x, d*.12, 0, w*.34, d*.62, hh)
            for j in range(3):
                z, ht = h*j*.19, h*.19
                _mass(t, "terrace_front", x, -d*(.32-.08*j), z,
                      w*.36, d*(.35-.05*j), ht, "secondary")
            t.roof(x, d*.12, hh, w*.28, d*.51, 0)
        _mass(t, "interchange_atrium", 0, d*.05, h*.08, w*.34, d*.74, h*.14, "glass")
        for z, yy in ((h*.10, -d*.46), (h*.33, d*.24), (h*.60, d*.02)):
            _mass(t, "circulation_bridge", 0, yy, z, w*.50, d*.17, h*.035, "service")
        t.tag("terraced_twins", "recessed_station_atrium", "three_circulation_levels", "unequal_spires")
    else:
        # Radial transfer decks anchor an octagonal transport tower.
        t.taper("junction_plinth", [(0, w*.39, d*.42, 0, 0),
                (h*.18, w*.53, d*.57, 0, 0)], "service", 8)
        t.taper("junction_tower", [(h*.18, w*.38, d*.41, 0, 0),
                (h*.76, w*.38, d*.41, 0, 0), (h, w*.24, d*.27, 0, 0)], "facade", 12)
        for j, angle in enumerate((0, 60, 120)):
            _mass(t, "radial_deck_%d" % j, 0, 0, h*(.12+j*.055), w*1.52, d*.21, h*.04, "secondary", angle)
            a = pi*angle/180
            for side in (-1, 1):
                _post(t, "radial_support", side*cos(a)*w*.66, side*sin(a)*w*.66,
                      0, h*(.12+j*.055), 3.8)
        t.roof(0, 0, h, w*.31, d*.33, 1)
        t.tag("radial_transfer_decks", "round_tower", "flared_station_base", "tapered_top")


def _datacenter(t, v, w, d, h):
    if v == 0:
        t.podium(w*1.10, d*1.12, h*.10)
        _mass(t, "sealed_rack_core", 0, 0, h*.10, w*.82, d*.78, h*.82, "service")
        for j in range(5):
            z = h*(.15+j*.155)
            _mass(t, "occupied_band", 0, -d*.01, z, w*.86, d*.82, h*.08, "secondary")
            for xx in (-w*.48, w*.48):
                _mass(t, "cooling_fin", xx, 0, z, w*.12, d*.91, h*.105, "metal")
        _mass(t, "control_cap", -w*.06, 0, h*.92, w*.55, d*.64, h*.08)
        t.roof(-w*.06, 0, h, w*.47, d*.54, 2)
        t.tag("sealed_server_core", "five_cooling_bands", "deep_side_fins", "offset_control_cap")
    elif v == 1:
        # Two full-height banks and recessed bridges leave a cooling canyon exposed.
        for xx, hh in ((-w*.33, h*.87), (w*.33, h)):
            _mass(t, "server_bank", xx, 0, 0, w*.38, d, hh, "service")
            _mass(t, "control_face", xx, -d*.41, 0, w*.40, d*.18, hh*.90, "secondary")
            _bands(t, xx, 0, 0, hh, w*.40, d*1.02, 8)
            t.roof(xx, 0, hh, w*.31, d*.78, 2)
        for j in range(4):
            _mass(t, "recessed_cooling_link", 0, d*.24, h*(.13+j*.20), w*.34, d*.40, h*.05, "metal")
        for j in range(3):
            t.cylinder("canyon_conduit", ((j-1)*w*.057, d*.37, h*.43), 1.1, h*.83, "metal", 8)
        t.tag("server_canyon", "unequal_banks", "rear_cooling_links", "exposed_triple_conduit")
    elif v == 2:
        _mass(t, "data_block", 0, 0, 0, w*.90, d*.87, h*.63, "service")
        _mass(t, "occupied_admin", -w*.24, -d*.40, 0, w*.40, d*.24, h*.55)
        _mass(t, "roof_control", -w*.18, 0, h*.63, w*.40, d*.58, h*.21, "secondary")
        for j, (xx, yy, hh) in enumerate(((w*.27, -d*.22, h), (w*.27, d*.22, h*.91), (-w*.24, d*.26, h*.96))):
            radius = min(w,d)*.145
            t.cylinder("cooling_chimney_%d" % j, (xx, yy, h*.63+(hh-h*.63)/2), radius, hh-h*.63, "metal", 12)
            t.cylinder("chimney_lip", (xx, yy, hh), radius*1.17, 2.8, "service", 12)
        for j in range(4):
            t.band(0, 0, h*(.12+j*.12), w*.93, d*.90, 2.1, "metal")
        t.roof(-w*.18, 0, h*.84, w*.33, d*.45, 0)
        t.tag("low_sealed_monolith", "three_cooling_chimneys", "admin_front", "roof_control_tower")
    elif v == 3:
        for j in range(4):
            z = h*j*.25
            xx = -w*.07*j
            yy = d*.04*j
            ww, dd = w*(1-.15*j), d*(1-.13*j)
            _mass(t, "rack_terrace_%d" % j, xx, yy, z, ww, dd, h*.25, "service")
            _mass(t, "rack_window_strip", xx, yy-dd*.48, z+h*.06, ww*.90, 2.1, h*.085, "secondary")
            if j < 3:
                t.roof(xx+ww*.35, yy, z+h*.25, ww*.20, dd*.65, 2)
            t.band(xx, yy, z+h*.245, ww+1.8, dd+1.8, 2.2, "metal")
        t.roof(-w*.21, d*.12, h, w*.42, d*.49, 2)
        _mass(t, "coolant_spine", -w*.43, d*.22, 0, w*.12, d*.27, h*.97, "metal")
        t.tag("four_rack_terraces", "diagonal_setbacks", "side_coolant_spine", "terrace_equipment")
    else:
        # Inward-sloping armored shell around a thinner glass observation spire.
        t.taper("armored_archive", [(0, w*.55, d*.54, 0, 0),
                (h*.58, w*.52, d*.51, 0, 0), (h*.77, w*.33, d*.33, 0, 0)], "service", 8)
        _mass(t, "observation_spire", 0, 0, h*.68, w*.39, d*.38, h*.32, "secondary")
        for k in range(8):
            a = k*pi/4
            _ground_brace(t, "archive_armor_rib", cos(a)*w*.56, sin(a)*d*.55,
                          (cos(a)*w*.35, sin(a)*d*.35, h*.77), 3.0, "metal")
        for yy in (-d*.535, d*.535):
            _mass(t, "low_service_gallery", 0, yy, h*.08, w*.66, 3.2, h*.10, "secondary")
        t.roof(0, 0, h, w*.32, d*.31, 0)
        t.tag("armored_octagon", "inward_sloping_shell", "observation_spire", "radial_armor_ribs")


def _civic(t, v, w, d, h):
    if v == 0:
        t.podium(w*1.28, d*1.20, h*.085)
        _mass(t, "assembly_shaft", 0, 0, h*.085, w*.69, d*.69, h*.65)
        _mass(t, "upper_assembly", 0, 0, h*.735, w, d*.91, h*.16, "secondary")
        for xx in (-w*.38, w*.38):
            t.beam("assembly_haunch", (xx*.55, 0, h*.61), (xx, 0, h*.755), 5, "concrete")
        _mass(t, "crown_chamber", 0, d*.08, h*.895, w*.52, d*.53, h*.105)
        t.roof(0, d*.08, h, w*.43, d*.44, 0)
        for xx in (-w*.50, -w*.25, 0, w*.25, w*.50):
            _post(t, "colonnade", xx, -d*.58, 0, h*.08, 2.6)
        t.tag("civic_plinth", "oversailing_assembly", "haunched_supports", "crown_chamber")
    elif v == 1:
        # Three towers form an open civic court; rear hall connects their feet.
        _mass(t, "rear_hall", 0, d*.32, 0, w*1.04, d*.36, h*.18, "concrete")
        for j, (xx, yy, hh) in enumerate(((-w*.38, 0, h*.81), (w*.38, 0, h*.81), (0, d*.26, h))):
            _mass(t, "court_tower_%d" % j, xx, yy, 0, w*.32, d*.52, hh)
            _mass(t, "tower_lantern", xx, yy, hh-h*.07, w*.35, d*.56, h*.07, "secondary")
            t.roof(xx, yy, hh, w*.25, d*.42, j)
        for xx in (-w*.20, w*.20):
            _mass(t, "court_upper_link", xx, d*.23, h*.61, w*.28, d*.21, h*.045, "service")
        t.tag("three_tower_court", "rear_civic_hall", "open_forecourt", "symmetric_wings_tall_rear")
    elif v == 2:
        t.podium(w*1.06, d*1.12, h*.08)
        t.taper("civic_needle", [(h*.08, w*.45, d*.45, 0, 0),
                (h*.46, w*.40, d*.40, 0, 0), (h*.83, w*.24, d*.24, 0, 0),
                (h, w*.11, d*.11, 0, 0)], "facade", 8)
        for xx in (-w*.38, w*.38):
            _mass(t, "needle_shoulder", xx, 0, h*.08, w*.22, d*.55, h*.25, "secondary")
        _mass(t, "ceremonial_axis", 0, -d*.46, h*.08, w*.22, d*.15, h*.32, "concrete")
        for j in range(4):
            z = h*(.40+j*.12)
            r = .42-(z/h-.40)*.40
            t.band(0, 0, z, w*r*1.65, d*r*1.65, 1.8, "concrete")
        t.antenna(0, 0, h, h*.10)
        t.tag("slender_civic_needle", "low_paired_shoulders", "ceremonial_front_axis", "continuous_taper")
    elif v == 3:
        for xx in (-w*.35, w*.35):
            _mass(t, "forum_support_tower", xx, d*.04, 0, w*.32, d*.68, h*.82)
        _mass(t, "elevated_forum", 0, 0, h*.69, w*1.10, d, h*.16, "secondary")
        _mass(t, "forum_front_loggia", 0, -d*.46, h*.62, w*1.05, d*.10, h*.07, "concrete")
        for xx in (-w*.47, -w*.24, 0, w*.24, w*.47):
            _post(t, "loggia_column", xx, -d*.46, h*.69, h*.16, 2.2)
        _mass(t, "assembly_back_crown", 0, d*.22, h*.85, w*.55, d*.49, h*.15)
        t.roof(0, d*.22, h, w*.46, d*.40, 0)
        t.tag("sky_forum", "twin_support_towers", "elevated_loggia", "open_central_portal")
    else:
        t.taper("civic_bastion", [(0, w*.62, d*.61, 0, 0),
                (h*.15, w*.62, d*.61, 0, 0), (h*.26, w*.46, d*.46, 0, 0)], "concrete", 8)
        _mass(t, "bastion_tower", 0, 0, h*.26, w*.68, d*.68, h*.57)
        for xx in (-w*.35, w*.35):
            for yy in (-d*.34, d*.34):
                _mass(t, "bastion_corner", xx, yy, h*.20, w*.18, d*.19, h*.72, "secondary")
        _mass(t, "civic_crown", 0, 0, h*.83, w*.38, d*.40, h*.17, "secondary")
        t.band(0, 0, h*.82, w*.79, d*.79, 3, "concrete")
        t.roof(0, 0, h, w*.30, d*.31, 1)
        t.tag("broad_octagonal_bastion", "four_corner_turrets", "central_crown", "deep_plinth")


def _mixed_use(t, v, w, d, h):
    if v == 0:
        _mass(t, "market_block", 0, 0, 0, w*1.14, d*1.12, h*.17, "secondary")
        _mass(t, "market_arcade", 0, -d*.59, 0, w*.85, d*.12, h*.07, "concrete")
        for xx, yy, hh, ww, dd in ((-w*.27, d*.08, h*.83, w*.38, d*.56),
                                  (w*.28, -d*.13, h*.64, w*.36, d*.57)):
            _mass(t, "market_needle", xx, yy, h*.17, ww, dd, hh)
            t.roof(xx, yy, h*.17+hh, ww*.84, dd*.84, 1)
        _mass(t, "market_skywalk", 0, 0, h*.43, w*.28, d*.24, h*.045, "service")
        t.screen(0, -d*.57-0.2, h*.125, w*.37, h*.06, 1)
        t.tag("market_podium", "unequal_offset_needles", "short_skywalk", "street_arcade")
    elif v == 1:
        # Three residential terraces occupy different depths, with a rear office blade.
        _mass(t, "rear_office_blade", -w*.08, d*.30, 0, w*.61, d*.38, h)
        for j in range(3):
            z = j*h*.20
            _mass(t, "residential_terrace_%d" % j, w*.08*j, -d*.12+d*.05*j,
                  z, w*(1-.17*j), d*(.71-.12*j), h*.20, "secondary")
            t.band(w*.08*j, -d*.12+d*.05*j, z+h*.20, w*(1.02-.17*j), d*(.73-.12*j), 1.8, "concrete")
        _mass(t, "front_shop_bar", 0, -d*.48, 0, w*1.08, d*.19, h*.065, "glass")
        t.roof(-w*.08, d*.30, h, w*.52, d*.31, 0)
        t.tag("three_residential_terraces", "rear_office_blade", "front_shop_bar", "asymmetric_setbacks")
    elif v == 2:
        # L-shaped hotel rotated around a solid hinge, and a narrow independent office top.
        t.podium(w*1.04, d*1.08, h*.10)
        _mass(t, "hotel_long_wing", -w*.20, 0, h*.10, w*.47, d, h*.61)
        _mass(t, "hotel_short_wing", w*.14, d*.30, h*.10, w*.62, d*.40, h*.47, "secondary")
        _mass(t, "hinge_tower", -w*.21, d*.28, h*.71, w*.41, d*.43, h*.29, "secondary")
        _mass(t, "hinge_service", -w*.20, d*.29, 0, w*.21, d*.23, h*.74, "service")
        _mass(t, "low_court_pavilion", w*.18, -d*.19, h*.10, w*.40, d*.43, h*.105, "glass")
        t.roof(-w*.21, d*.28, h, w*.34, d*.35, 0)
        t.roof(w*.20, d*.30, h*.57, w*.36, d*.32, 1)
        t.tag("L_plan_hotel", "recessed_court", "hinge_office_tower", "lower_court_pavilion")
    elif v == 3:
        # Distinct neighborhoods transfer their loads through a continuous rear core.
        _mass(t, "district_backbone", 0, d*.29, 0, w*.37, d*.31, h, "service")
        for j, (xx, yy, ww, dd) in enumerate(((-.10, 0, 1, .95), (.13, -.05, .86, .81),
                                             (-.11, .04, .73, .80), (.08, .04, .59, .65))):
            z = h*j*.25
            _mass(t, "district_%d" % j, w*xx, d*yy, z, w*ww, d*dd, h*.22,
                  "facade" if j % 2 == 0 else "secondary")
            t.band(w*xx, d*yy, z+h*.22, w*(ww+.04), d*(dd+.04), 2.8, "concrete")
            if j < 3:
                _frame(t, "transfer_columns", w*xx, d*yy, z+h*.22, w*ww*.62, d*dd*.62, h*.03, 3.1)
        _mass(t, "top_community_room", w*.08, d*.04, h*.97, w*.37, d*.40, h*.03, "glass")
        t.roof(w*.08, d*.04, h, w*.29, d*.30, 2)
        t.tag("four_shifted_districts", "open_transfer_floors", "continuous_backbone", "community_top")
    else:
        # Tall open atrium remains readable because the bridges occupy only its rear half.
        for xx, hh, dd in ((-w*.34, h, d*.86), (w*.34, h*.78, d)):
            _mass(t, "atrium_flank", xx, 0, 0, w*.38, dd, hh)
            t.roof(xx, 0, hh, w*.31, dd*.83, 0)
        _mass(t, "rear_atrium_skin", 0, d*.35, 0, w*.32, d*.19, h*.74, "glass")
        for j in range(3):
            _mass(t, "community_link", 0, d*.13, h*(.18+j*.22), w*.34, d*.37, h*.07, "secondary")
        _mass(t, "public_lobby", 0, -d*.10, 0, w*.34, d*.71, h*.09, "glass")
        t.tag("open_tall_atrium", "unequal_flanks", "rear_glass_skin", "three_community_bridges")


def _buttress(t, v, w, d, h):
    if v == 0:
        _mass(t, "central_keep", 0, 0, 0, w*.58, d*.63, h*.92)
        _mass(t, "central_lantern", 0, 0, h*.92, w*.35, d*.39, h*.08, "secondary")
        for xx in (-w*.55, w*.55):
            for yy in (-d*.31, d*.31):
                _post(t, "flying_pier", xx, yy, 0, h*.39, 4.7)
                t.beam("flying_buttress", (xx, yy, h*.39), (xx*.49, yy*.70, h*.73), 4.4, "concrete")
        t.roof(0, 0, h, w*.28, d*.32, 0)
        t.tag("four_flying_buttresses", "narrow_central_keep", "outer_piers", "small_lantern")
    elif v == 1:
        t.taper("raking_body", [(0, w*.36, d*.39, 0, 0),
                (h*.80, w*.49, d*.45, w*.06, 0), (h, w*.34, d*.34, w*.10, 0)], "facade", 8)
        for xx in (-w*.70, w*.70):
            for yy in (-d*.47, d*.47):
                _ground_brace(t, "raking_ground_strut", xx, yy,
                              (xx*.54+w*.03, yy*.65, h*.70), 4.5, "concrete")
        _mass(t, "rear_service_bar", -w*.12, d*.40, 0, w*.37, d*.17, h*.51, "service")
        t.roof(w*.10, 0, h, w*.42, d*.41, 1)
        t.tag("raking_external_legs", "shifted_faceted_body", "widening_upper_mass", "rear_service_bar")
    elif v == 2:
        _mass(t, "step_core", 0, 0, 0, w*.44, d*.65, h)
        for side in (-1, 1):
            for j in range(3):
                xx = side*w*(.25+.125*j)
                hh = h*(.77-.21*j)
                _mass(t, "stepped_abutment", xx, 0, 0, w*.18, d*(.78+.09*j), hh,
                      "secondary" if j == 0 else "concrete")
                t.band(xx, 0, hh, w*.19, d*(.80+.09*j), 1.8, "metal")
        t.roof(0, 0, h, w*.35, d*.54, 0)
        t.tag("symmetric_stepped_abutments", "narrow_full_height_core", "broad_ground_footprint", "six_falling_shoulders")
    elif v == 3:
        for side in (-1, 1):
            xx = side*w*.32
            hh = h*(.91 if side == -1 else 1)
            _mass(t, "cathedral_flank", xx, 0, 0, w*.30, d*.78, hh)
            for yy in (-d*.53, d*.53):
                foot = (side*w*.59, yy, 0)
                _ground_brace(t, "cathedral_haunch", foot[0], foot[1], (xx, yy*.61, hh*.64), 4.6, "concrete")
            t.roof(xx, 0, hh, w*.23, d*.64, 1)
        _mass(t, "cathedral_rear_link", 0, d*.22, h*.56, w*.38, d*.28, h*.075, "secondary")
        t.tag("split_cathedral", "unequal_towers", "four_raking_haunches", "high_rear_link")
    else:
        # Four occupied petals become buttresses to a narrower central tower.
        t.taper("petal_core", [(0, w*.28, d*.28, 0, 0),
                (h*.85, w*.28, d*.28, 0, 0), (h, w*.17, d*.17, 0, 0)], "facade", 8)
        for j in range(4):
            a = j*pi/2
            x0, y0 = cos(a)*w*.33, sin(a)*d*.33
            t.taper("petal_%d" % j, [(0, w*.27, d*.27, x0, y0),
                    (h*.34, w*.24, d*.24, x0, y0),
                    (h*(.76 if j % 2 else .64), w*.13, d*.13, x0*.57, y0*.57)], "secondary", 8)
            _ground_brace(t, "petal_spine", x0*1.68, y0*1.68,
                          (x0*.80, y0*.80, h*(.76 if j % 2 else .64)), 3.2, "concrete")
        t.roof(0, 0, h, w*.22, d*.22, 2)
        t.tag("four_occupied_petals", "radial_buttressing", "faceted_plan", "pointed_central_keep")


def _hero(t, v, w, d, h):
    if v == 0:
        # A broken rectangular halo: three frame sides and a deliberately interrupted fourth.
        for xx, hh in ((-w*.41, h), (w*.41, h*.87)):
            _mass(t, "halo_side", xx, 0, 0, w*.24, d*.73, hh)
        _mass(t, "halo_top", -w*.17, d*.04, h*.87, w*.72, d*.63, h*.13, "secondary")
        _mass(t, "halo_low_crossing", 0, d*.16, h*.25, w*.71, d*.40, h*.09, "secondary")
        _mass(t, "halo_break_extension", w*.44, 0, h*.68, w*.31, d*.85, h*.12)
        for yy in (-d*.37, d*.37):
            t.beam("halo_corner_brace", (-w*.40, yy, h*.72), (-w*.13, yy, h*.91), 3.1, "metal")
        t.roof(-w*.19, d*.04, h, w*.49, d*.50, 0)
        t.roof(w*.44, 0, h*.80, w*.24, d*.68, 1)
        t.tag("broken_halo", "giant_open_void", "interrupted_right_crown", "low_crossing")
    elif v == 1:
        t.podium(w*1.13, d*1.06, h*.075)
        for xx in (-w*.34, w*.34):
            _mass(t, "keyhole_shank", xx, 0, h*.075, w*.33, d*.77, h*.51)
        _mass(t, "keyhole_haunch_left", -w*.22, 0, h*.585, w*.54, d*.87, h*.135)
        _mass(t, "keyhole_haunch_right", w*.22, 0, h*.585, w*.54, d*.87, h*.135)
        _mass(t, "keyhole_upper", 0, 0, h*.72, w*.96, d, h*.20, "secondary")
        _mass(t, "keyhole_top", -w*.10, d*.07, h*.92, w*.57, d*.60, h*.08)
        for yy in (-d*.45, d*.45):
            t.beam("keyhole_transfer", (-w*.43, yy, h*.59), (w*.43, yy, h*.72), 3.5, "metal")
        t.roof(-w*.10, d*.07, h, w*.47, d*.48, 2)
        t.tag("giant_keyhole", "broad_upper_city", "two_ground_shanks", "offset_top_block")
    elif v == 2:
        # Four ascending fingers and rear suspended nave, with an exposed front canyon.
        points = [(-.39, -.24, .69), (.39, -.24, .82), (-.29, .25, 1), (.29, .25, .93)]
        for j, (xx, yy, hh) in enumerate(points):
            _mass(t, "cathedral_finger_%d" % j, xx*w, yy*d, 0, w*.29, d*.39, h*hh)
            t.taper("finger_crown_%d" % j, [(h*hh, w*.15, d*.20, xx*w, yy*d),
                    (h*(hh+.06), w*.07, d*.09, xx*w, yy*d)], "secondary", 8)
        _mass(t, "suspended_nave", 0, d*.25, h*.57, w*.65, d*.41, h*.17, "secondary")
        for side in (-1, 1):
            t.beam("nave_rake", (side*w*.33, -d*.22, h*.38),
                   (side*w*.22, d*.25, h*.61), 4, "concrete")
        _mass(t, "low_apse", 0, d*.29, 0, w*.55, d*.40, h*.22, "service")
        t.roof(0, d*.25, h*.74, w*.45, d*.30, 1)
        t.tag("four_ascending_fingers", "front_canyon", "suspended_rear_nave", "faceted_crowns")
    elif v == 3:
        # A stepped rotary building, supported by a visible vertical core.
        _mass(t, "helix_spine", 0, 0, 0, w*.36, d*.38, h, "service")
        for j, angle in enumerate((0, 18, 36, 54, 72)):
            z = h*j*.20
            factor = 1-.075*j
            _mass(t, "rotary_district_%d" % j, 0, 0, z, w*factor, d*factor, h*.175,
                  "facade" if j % 2 == 0 else "secondary", angle)
            a = pi*angle/180
            for sign in (-1, 1):
                x, y = sign*w*factor*.34*cos(a), sign*w*factor*.34*sin(a)
                _post(t, "rotary_transfer", x, y, z+h*.175, h*.025, 3.5, "metal")
            _mass(t, "rotary_belt", 0, 0, z+h*.172, w*factor+2, d*factor+2, 2.4, "metal", angle)
        _mass(t, "helix_crown", 0, 0, h*.975, w*.37, d*.39, h*.025, "secondary", 72)
        t.roof(0, 0, h, w*.26, d*.27, 0)
        t.tag("five_rotating_districts", "central_load_spine", "open_transfer_floors", "spiral_silhouette")
    else:
        # Three monumental legs support a triangular network of occupied bridges.
        points = [(-w*.40, -d*.27, h*.91), (w*.40, -d*.27, h), (0, d*.36, h*.96)]
        for j, (xx, yy, hh) in enumerate(points):
            _mass(t, "crown_leg_%d" % j, xx, yy, 0, w*.27, d*.37, hh)
            t.roof(xx, yy, hh, w*.21, d*.29, j)
        # Beams are thick habitable tubes with facade material, rather than floating slabs.
        for j in range(3):
            a, b = points[j], points[(j+1)%3]
            for z in (h*.40, h*.77):
                t.beam("inhabited_crown_bridge", (a[0], a[1], z),
                       (b[0], b[1], z+h*.04), min(w,d)*.24, "secondary")
                t.beam("bridge_lower_chord", (a[0], a[1], z-min(w,d)*.14),
                       (b[0], b[1], z+h*.04-min(w,d)*.14), 2.6, "metal")
        _mass(t, "rear_transfer_station", 0, d*.36, h*.15, w*.52, d*.52, h*.12, "service")
        t.tag("three_monumental_legs", "triangular_skybridge_network", "double_bridge_level", "open_center")


_BUILDERS = {
    "retro": _retro,
    "maintenance": _maintenance,
    "exoskeleton": _exoskeleton,
    "suspended": _suspended,
    "transit": _transit,
    "datacenter": _datacenter,
    "civic": _civic,
    "mixed_use": _mixed_use,
    "buttress": _buttress,
    "hero": _hero,
}


def build(t, key, v, w, d, h):
    """Build one of the fifty distinct architecture recipes through adapter t."""
    if key not in _BUILDERS:
        raise ValueError("Unknown architecture family: %s" % key)
    if v not in range(5):
        raise ValueError("Architecture variant must be 0..4")
    if min(w, d, h) <= 0:
        raise ValueError("Building dimensions must be positive")
    t.tag(key, NAMES[key][v])
    _BUILDERS[key](t, v, w, d, h)
