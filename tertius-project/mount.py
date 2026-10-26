"""
Angle mount for the RolaCase: two 50x50x2 steel angles, legs under the
case. Each angle carries two 3D-printed rollers, one in each pocket of
that side's lock track, plus an M5 locking screw. M5x12 button heads
thread into the angles throughout. Build123D port of build_mount.py
(parts and assembly; the fabrication drawing is not ported).

    Mount_Angle   - 50x50x2 angle, 4 x M5 tapped holes
    M5x12_Button  - ISO 7380 style button head, simplified

Each side track has two pockets:
    front pocket  Z -71.5 -> +46: closed front end, lip from -51.5, and a
                  lip-free entry slot -71.5 -> -51.5 open to the bottom
    rib           Z -74 -> -71.5 (2.5 thick)
    rear pocket   Z -184 -> -74: open at the back end, lip full length
    channel       8 -> 26.5 up from the case bottom

Fitting the case: lower it so each front roller comes up through its
entry slot, slide it back ~98 mm, then thread the M5 locking screw in from
outside through the hole nearest the rear roller; its thread lands on the
rib, so the case can't slide forward to the entry slots again.

The two angles are identical: the lock hole is drilled near both ends so
either angle fits either side.

Axes: X across the case, Y up (case bottom at 0), Z front (+, handle).
"""
import math

import roller as br
from kit import (IDENT, TURN_Y180, Y_TO_NEG_X, Y_TO_POS_X, Kit, finish,
                 place, place_axis)
from roller import ROLLER_D, ROLLER_H, SPACER_H
from spec import spec

ANGLE_REQ = spec("mount-angle")
SCREW_REQ = ANGLE_REQ.use("screw")
for _name, _built in (("roller", br.ROLLER_REQ), ("spacer", br.SPACER_REQ),
                      ("screw", br.SCREW_REQ)):
    if ANGLE_REQ.use(_name).id != _built.id:
        raise ValueError("mount-angle.yaml uses a different %s than "
                         "roller.py builds" % _name)

CASE_W = ANGLE_REQ["case_w_mm"]
CHANNEL_Y = tuple(ANGLE_REQ["channel_y_mm"])
POCKET_END_Z = ANGLE_REQ["pocket_end_z_mm"]
RIB_FRONT_Z = ANGLE_REQ["rib_front_z_mm"]
RIB_T = ANGLE_REQ["rib_t_mm"]
ENTRY_SLOT = tuple(ANGLE_REQ["entry_slot_z_mm"])
END_CLEAR = ANGLE_REQ["end_clear_mm"]
ROLLER_SPACING = ANGLE_REQ["roller_spacing_mm"]
ANGLE_LEG = ANGLE_REQ["angle_leg_mm"]
ANGLE_T = ANGLE_REQ["angle_t_mm"]
ANGLE_END_MARGIN = ANGLE_REQ["angle_end_margin_mm"]
SIDE_GAP = ANGLE_REQ["side_gap_mm"]
TAP_DRILL = ANGLE_REQ["tap_drill_mm"]

SCREW_D = SCREW_REQ["thread_d_mm"]
SCREW_L = SCREW_REQ["length_mm"]
HEAD_D = SCREW_REQ["head_d_mm"]
HEAD_H = SCREW_REQ["head_h_mm"]
HEX_AF = SCREW_REQ["hex_af_mm"]
TIP_CHAMFER = SCREW_REQ["tip_chamfer_mm"]

# ------------------------------------------------------------------- derived
AXIS_Y = sum(CHANNEL_Y) / 2                              # roller axis height
FRONT_Z = POCKET_END_Z - ROLLER_D / 2 - END_CLEAR        # locked rollers
REAR_Z = FRONT_Z - ROLLER_SPACING
LOCK_Z = RIB_FRONT_Z + SCREW_D / 2                       # thread on the rib
UPRIGHT_X = CASE_W / 2 + SIDE_GAP                        # angle inner face
HOLE_Y = ANGLE_T + AXIS_Y                                # from angle heel
ANGLE_LEN = ROLLER_SPACING + 2 * ANGLE_END_MARGIN
ANGLE_Z0 = REAR_Z - ANGLE_END_MARGIN                     # rear end (asm)
LOCK_FROM_END = LOCK_Z - ANGLE_Z0
# Hole positions along the angle from its end; the lock hole is mirrored so
# the two angles are identical.
HOLES_FROM_END = sorted([ANGLE_END_MARGIN, LOCK_FROM_END,
                         ANGLE_LEN - LOCK_FROM_END,
                         ANGLE_LEN - ANGLE_END_MARGIN])

assert ROLLER_D < CHANNEL_Y[1] - CHANNEL_Y[0], "roller wider than channel"
# Install check: front roller in the slot, rear roller clear behind the case.
_drop_front = ENTRY_SLOT[1] - ROLLER_D / 2
assert _drop_front - ROLLER_SPACING + ROLLER_D / 2 < -CASE_W / 2, \
    "rear roller can't start behind the case - increase roller_spacing_mm"
assert REAR_Z + ROLLER_D / 2 < RIB_FRONT_Z - RIB_T, "rear roller hits the rib"


# ---------------------------------------------------------------------- parts
def angle_profile(k, leg, t, s=1):
    """50x50 angle section on the front plane: heel on the origin, upright
    up +Y, base leg towards s*X."""
    k.sketch("z", 0)
    k.poly([(0, 0, 0), (s * leg, 0, 0), (s * leg, t, 0), (s * t, t, 0),
            (s * t, leg, 0), (0, leg, 0)])


def build_angle():
    """Heel on the origin, upright leg up +Y, base leg out +X, length from
    Z=0 (one end) to +ANGLE_LEN."""
    k = Kit()
    angle_profile(k, ANGLE_LEG, ANGLE_T)
    k.boss(ANGLE_LEN, midplane=False)
    # Tapped holes through the upright.
    k.sketch("x", 0)
    for z in HOLES_FROM_END:
        k.circle((0, HOLE_Y, z), TAP_DRILL)
    k.cut(10)
    return finish(k.part, "Mount_Angle " + ANGLE_REQ.id, ANGLE_REQ.colour)


def build_screw():
    """Head bearing face on the origin, shank up +Y, head down -Y."""
    k = Kit()
    k.sketch("y", -HEAD_H / 2)
    k.circle((0, -HEAD_H / 2, 0), HEAD_D)
    k.boss(HEAD_H)
    shank = SCREW_L - TIP_CHAMFER
    k.sketch("y", shank / 2)
    k.circle((0, shank / 2, 0), SCREW_D)
    k.boss(shank)
    # Chamfered end (as on real screws), modelled as a short smaller step.
    k.sketch("y", shank + TIP_CHAMFER / 2)
    k.circle((0, shank + TIP_CHAMFER / 2, 0), SCREW_D - 1.5 * TIP_CHAMFER)
    k.boss(TIP_CHAMFER)
    r = HEX_AF / 3 ** 0.5
    k.sketch("y", -HEAD_H + 1.25)
    k.poly([(r * math.cos(math.radians(a)), 0, r * math.sin(math.radians(a)))
            for a in range(0, 360, 60)])
    k.cut(2.5)
    return finish(k.part, "M5x12_Button " + SCREW_REQ.id, SCREW_REQ.colour)


# ------------------------------------------------------------------ assembly
# Screws thread into the angles' and the spacers' tap-drill holes by design
# (the overlap is the thread engagement).
SCREW_IGNORE = {("M5x12_Button", "Mount_Angle"),
                ("M5x12_Button", "Roller_Spacer")}


def assembly(parts):
    """Both angle sets, placed round the case (case not included).
    parts: dict of built parts (angle, roller, spacer, screw)."""
    out = []
    head_face = UPRIGHT_X - SPACER_H        # roller screw head face (|x|)
    outer_face = UPRIGHT_X + ANGLE_T        # lock screw head face (|x|)
    for s in (1, -1):
        x0 = s * UPRIGHT_X
        # Left angle as modelled; right one turned end for end, so both
        # have their part Z=0 end at the back.
        out.append(place(parts["angle"], TURN_Y180 if s > 0 else IDENT,
                         (s * outer_face, -ANGLE_T,
                          ANGLE_Z0 + ANGLE_LEN if s > 0 else ANGLE_Z0)))
        inward = Y_TO_NEG_X if s > 0 else Y_TO_POS_X
        outward = Y_TO_POS_X if s > 0 else Y_TO_NEG_X
        for z in (REAR_Z, FRONT_Z):
            out.append(place_axis(parts["roller"], inward, (x0, AXIS_Y, z),
                                  (x0, x0 - s * ROLLER_H)))
            out.append(place_axis(parts["spacer"], inward, (x0, AXIS_Y, z),
                                  (x0, x0 - s * SPACER_H)))
            out.append(place_axis(parts["screw"], outward,
                                  (s * head_face, AXIS_Y, z),
                                  (s * (head_face - HEAD_H),
                                   s * (head_face + SCREW_L))))
        # Locking screw: in from outside, thread against the rib.
        out.append(place_axis(parts["screw"], inward,
                              (s * outer_face, AXIS_Y, LOCK_Z),
                              (s * (outer_face - SCREW_L),
                               s * (outer_face + HEAD_H))))
    return out
