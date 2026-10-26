"""
Shelf rails (draft): the dincase mounting angle, lengthened to run past the
back of the case so the two rails can be tied together by a rear cross
brace and carried on slides as a pull-out shelf. Build123D port of
build_shelf_rail.py (parts and assembly; the drawing is not ported).

Inputs: specs/shelf-rail-left.yaml and shelf-rail-right.yaml (mirror
images: same parameters apart from `hand`).

Per rail: 50x50x2 angle, upright outside the case. Four M5 tapped holes in
the upright on the track line: rear roller, lock screw and front roller at
the same positions relative to the case as the mounting angle, plus a stop
screw. Two more, lower down, carry the drawer-slide rollers on the outside
(see slide.py). Two M5 clearance holes in the base leg where it runs past
the case, for the rear cross brace.

Two-stage pull-out: with the lock screw left out, the case rolls forward on
its own track rollers until the stop screw meets the rib between the
pockets (stop_travel_mm). Then the rail itself runs out on the slide.

Axes: X across the case, Y up (case bottom at 0), Z front (+, handle).
"""
import mount as bm
import roller as br
from kit import IDENT, Y_TO_NEG_X, Y_TO_POS_X, Kit, finish, place, place_axis
from mount import angle_profile
from roller import ROLLER_D, ROLLER_H, SPACER_H
from spec import handed

LEFT, RIGHT = handed("shelf-rail-left", "shelf-rail-right")
for _name, _built in (("roller", br.ROLLER_REQ), ("spacer", br.SPACER_REQ),
                      ("screw", br.SCREW_REQ)):
    for _req in (LEFT, RIGHT):
        if _req.use(_name).id != _built.id:
            raise ValueError("%s uses a different %s than roller.py builds"
                             % (_req.name, _name))
SCREW = LEFT.use("screw")

P = LEFT
CASE_W = P["case_w_mm"]
CASE_D = P["case_d_mm"]
CHANNEL_Y = tuple(P["channel_y_mm"])
POCKET_END_Z = P["pocket_end_z_mm"]
RIB_FRONT_Z = P["rib_front_z_mm"]
RIB_T = P["rib_t_mm"]
ENTRY_SLOT = tuple(P["entry_slot_z_mm"])
END_CLEAR = P["end_clear_mm"]
ROLLER_SPACING = P["roller_spacing_mm"]
LEG = P["angle_leg_mm"]
T = P["angle_t_mm"]
FRONT_MARGIN = P["front_margin_mm"]
REAR_OVERHANG = P["rear_overhang_mm"]
SIDE_GAP = P["side_gap_mm"]
TAP_DRILL = P["tap_drill_mm"]
BRACE_D = P["brace_hole_d_mm"]
BRACE_FROM_REAR = list(P["brace_holes_from_rear_mm"])
BRACE_FROM_HEEL = P["brace_holes_from_heel_mm"]
STOP_TRAVEL = P["stop_travel_mm"]
SLIDE_Y = P["slide_axis_y_mm"]
SLIDE_FROM_REAR = P["slide_roller_from_rear_mm"]
SLIDE_SPACING = P["slide_roller_spacing_mm"]
SCREW_D = SCREW["thread_d_mm"]
SCREW_L = SCREW["length_mm"]
HEAD_H = SCREW["head_h_mm"]

# ------------------------------------------------------------------- derived
AXIS_Y = sum(CHANNEL_Y) / 2
FRONT_Z = POCKET_END_Z - ROLLER_D / 2 - END_CLEAR       # locked rollers
REAR_Z = FRONT_Z - ROLLER_SPACING
LOCK_Z = RIB_FRONT_Z + SCREW_D / 2                      # thread on the rib
STOP_Z = LOCK_Z + STOP_TRAVEL                           # meets the rib later
UPRIGHT_X = CASE_W / 2 + SIDE_GAP                       # upright inner face
OUTER_X = UPRIGHT_X + T
HOLE_Y = T + AXIS_Y                                     # from the heel
RAIL_Z0 = -CASE_D / 2 - REAR_OVERHANG                   # rear end (asm)
RAIL_Z1 = FRONT_Z + FRONT_MARGIN                        # front end (asm)
RAIL_LEN = RAIL_Z1 - RAIL_Z0
HOLES_FROM_REAR = [REAR_Z - RAIL_Z0, LOCK_Z - RAIL_Z0, STOP_Z - RAIL_Z0,
                   FRONT_Z - RAIL_Z0]
SLIDE_HOLE_Y = T + SLIDE_Y                              # from the heel
SLIDE_FROM_REAR_ALL = [SLIDE_FROM_REAR, SLIDE_FROM_REAR + SLIDE_SPACING]
SLIDE_Z = [RAIL_Z0 + h for h in SLIDE_FROM_REAR_ALL]    # asm, case locked

assert ROLLER_D < CHANNEL_Y[1] - CHANNEL_Y[0], "roller wider than channel"
_drop_front = ENTRY_SLOT[1] - ROLLER_D / 2
assert _drop_front - ROLLER_SPACING + ROLLER_D / 2 < -CASE_W / 2, \
    "rear roller can't start behind the case"
assert REAR_Z + ROLLER_D / 2 < RIB_FRONT_Z - RIB_T, "rear roller hits the rib"
assert max(BRACE_FROM_REAR) + BRACE_D / 2 < REAR_OVERHANG, \
    "brace holes must be in the overhang, behind the case"
assert REAR_Z - STOP_TRAVEL - ROLLER_D / 2 >= -CASE_D / 2, \
    "at full case travel the rear roller leaves its lip"
assert STOP_Z + SCREW_D / 2 < FRONT_Z - ROLLER_D / 2, "stop screw hits roller"
# Slide roller standoffs (dia 14 at SLIDE_Y) must clear the screw heads and
# tips on the track line.
assert min(abs(a - b) for a in SLIDE_Z
           for b in (REAR_Z, LOCK_Z, STOP_Z, FRONT_Z)) > 15, \
    "slide roller standoff hits a screw on the track line"


# ---------------------------------------------------------------------- part
def build_rail(req, sign):
    """sign +1: left rail (base leg runs +X from the heel); -1: right.
    Heel on the origin, upright outer face at X=0, rear end at Z=0."""
    k = Kit()
    s = sign
    angle_profile(k, LEG, T, s)
    k.boss(RAIL_LEN, midplane=False)                  # Z 0 -> RAIL_LEN
    # Upright: rear roller, lock screw, stop screw, front roller (M5
    # tapped), and low down the slide rollers.
    k.sketch("x", 0)
    for z in HOLES_FROM_REAR:
        k.circle((0, HOLE_Y, z), TAP_DRILL)
    for z in SLIDE_FROM_REAR_ALL:
        k.circle((0, SLIDE_HOLE_Y, z), TAP_DRILL)
    k.cut(10)
    # Base leg, behind the case: rear cross brace bolts (M5 clearance).
    k.sketch("y", 0)
    for z in BRACE_FROM_REAR:
        k.circle((s * BRACE_FROM_HEEL, 0, z), BRACE_D)
    k.cut(10)
    name = "Shelf_Rail_" + ("L" if sign > 0 else "R")
    return finish(k.part, "%s %s" % (name, req.id), req.colour)


def build():
    return {"left": build_rail(LEFT, +1), "right": build_rail(RIGHT, -1)}


# ------------------------------------------------------------------ assembly
SCREW_IGNORE = {("M5x12_Button", "Shelf_Rail_L"),
                ("M5x12_Button", "Shelf_Rail_R"),
                ("M5x12_Button", "Roller_Spacer")}


def place_shelf(parts, case_parts, rails_dz=0.0, case_dz=0.0, lock=True):
    """Case, both rails, track rollers, spacers and screws. rails_dz moves
    the rails (slide travel); case_dz moves the case further along the
    rails (case travel, up to STOP_TRAVEL). The stop screw is always fitted;
    the lock screw only if `lock` (it would stop the case travelling).
    parts: rails (left, right), roller, spacer, screw."""
    dz = rails_dz
    out = [place(p, IDENT, (0, 0, rails_dz + case_dz)) for p in case_parts]
    head_face = UPRIGHT_X - SPACER_H
    for s, rail in ((-1, parts["left"]), (1, parts["right"])):
        x0 = s * UPRIGHT_X
        out.append(place(rail, IDENT, (s * OUTER_X, -T, RAIL_Z0 + dz)))
        inward = Y_TO_NEG_X if s > 0 else Y_TO_POS_X
        outward = Y_TO_POS_X if s > 0 else Y_TO_NEG_X
        for z in (REAR_Z + dz, FRONT_Z + dz):
            out.append(place_axis(parts["roller"], inward, (x0, AXIS_Y, z),
                                  (x0, x0 - s * ROLLER_H)))
            out.append(place_axis(parts["spacer"], inward, (x0, AXIS_Y, z),
                                  (x0, x0 - s * SPACER_H)))
            out.append(place_axis(parts["screw"], outward,
                                  (s * head_face, AXIS_Y, z),
                                  (s * (head_face - bm.HEAD_H),
                                   s * (head_face + SCREW_L))))
        for z in ((LOCK_Z, STOP_Z) if lock else (STOP_Z,)):
            out.append(place_axis(parts["screw"], inward,
                                  (s * OUTER_X, AXIS_Y, z + dz),
                                  (s * (OUTER_X - SCREW_L),
                                   s * (OUTER_X + HEAD_H))))
    return out
