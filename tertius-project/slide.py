"""
Drawer slide (draft) for the dincase shelf: the shelf rails pull out of the
trunk on a fixed angle each side, and the case rolls a further
stop_travel_mm forward on its own track rollers. Build123D port of
build_slide.py.

Section, right-hand side (the left is a mirror image):

    shelf rail upright | spacer | slide roller | lane | fixed rail upright
                         collar   (30 dia)       1.5    (keeper inside it,
                                                         above the roller)
    shelf rail base leg  ---------------------------  ride 3 mm
    fixed rail leg       ---------------------------  (rollers run on it)

Two slide rollers per side sit low on the OUTSIDE of the shelf rail and
run on the fixed rail's leg, which lies 3 mm under the shelf rail's base
leg. Printed keepers bolted inside the fixed rail's upright sit over the
rollers: when the shelf is out, the case hangs ahead of the rollers and
the rear roller pushes up on the keeper. The front keeper has a lug that
is the end stop.

Shut, a printed shoe under the front of the shelf rail rides onto a thin
landing pad on the fixed leg and lifts the shelf front 0.5 mm, so the shut
drawer rests on the pad and the rear rollers instead of the keepers.

Screws and keeper bolts are not modelled; their holes are.

Axes as shelf_rail.py: X across, Y up (case bottom 0), Z front (+),
shelf coordinates with the drawer shut and the case locked.
"""
import roller as br
import shelf_rail as sr
from kit import (IDENT, TURN_Y180, Y_TO_NEG_X, Y_TO_POS_X, Kit,
                 chamfer_circle, finish, place, place_axis)
from mount import angle_profile
from spec import handed, spec

ROLLER = spec("slide-roller")
SPACER = spec("slide-spacer")
RAIL_L, RAIL_R = handed("slide-rail-left", "slide-rail-right")
KEEPER = spec("slide-keeper")
KFRONT_L, KFRONT_R = handed("slide-keeper-front-left",
                            "slide-keeper-front-right")
PAD, SHOE = spec("landing-pad"), spec("slide-shoe")
if SPACER.use("roller").id != ROLLER.id:
    raise ValueError("slide-spacer.yaml uses a different roller")

R = RAIL_L
# Roller
RD, RH = ROLLER["roller_d_mm"], ROLLER["roller_h_mm"]
R_BORE, R_CBORE = ROLLER["bore_d_mm"], ROLLER["cbore_d_mm"]
SPIN, BELOW = ROLLER["spin_gap_mm"], ROLLER["head_below_top_mm"]
HEAD_D, HEAD_H = ROLLER["head_d_mm"], ROLLER["head_h_mm"]
CHAMF = ROLLER["bed_chamfer_mm"]
BORE_LEN = RH - HEAD_H - SPIN - BELOW
# Spacer
SPIGOT_D = R_BORE - SPACER["running_fit_mm"]
S_BORE = SPACER["bore_d_mm"]
COLLAR_D, STANDOFF = SPACER["collar_d_mm"], SPACER["standoff_mm"]
SPACER_H = STANDOFF + BORE_LEN + SPIN
# Fixed rail
LEG, T = R["angle_leg_mm"], R["angle_t_mm"]
RIDE, LANE = R["ride_mm"], R["lane_clear_mm"]
F_FRONT, F_REAR = R["front_z_mm"], R["rear_z_mm"]
F_LEN = F_FRONT - F_REAR
K_CLEAR, K_INNER = R["keeper_clear_mm"], R["keeper_inner_x_mm"]
K_SEGS = R["keeper_segments"]
F_BOLT_D = R["bolt_d_mm"]
# Keepers
K_LEN, K_W, K_H = KEEPER["length_mm"], KEEPER["width_mm"], KEEPER["height_mm"]
K_BOLT_D = KEEPER["bolt_d_mm"]
K_CB_D, K_CB_DEPTH = KEEPER["cbore_d_mm"], KEEPER["cbore_depth_mm"]
LUG_T, LUG_Y = KFRONT_L["lug_t_mm"], KFRONT_L["lug_bottom_y_mm"]

# ------------------------------------------------------------------- derived
LEG_TOP = -sr.T - RIDE                       # fixed leg top (Y)
HEEL_Y = LEG_TOP - T                         # fixed rail heel (Y)
ROLLER_X0 = sr.OUTER_X + STANDOFF            # roller face nearest the case
ROLLER_X1 = ROLLER_X0 + RH
F_INNER = ROLLER_X1 + LANE                   # fixed upright, |x|
F_OUTER = F_INNER + T
K_BOTTOM = LEG_TOP + RD + K_CLEAR            # keeper underside (Y)
K_Y = K_BOTTOM + K_H / 2                     # keeper centre / bolt line
K_X = K_INNER + K_W / 2                      # keeper centre, |x|
K_HOLE_Y = K_Y - HEEL_Y                      # bolt line from the fixed heel
SEG_Z0 = [F_REAR + i * K_LEN for i in range(K_SEGS)]
F_HOLES = sorted([z0 - F_REAR + b for z0 in SEG_Z0[:-1]
                  for b in KEEPER["bolts_from_end_mm"]] +
                 [SEG_Z0[-1] - F_REAR + b
                  for b in KFRONT_L["bolts_from_end_mm"]])

# Travel: the front slide roller stops against the front keeper's lug.
SLIDE_TRAVEL = (F_FRONT - LUG_T - RD / 2) - sr.SLIDE_Z[1]
CASE_TRAVEL = sr.STOP_TRAVEL

assert abs(sr.SLIDE_Y - (LEG_TOP + RD / 2)) < 1e-6, \
    "shelf rail slide_axis_y_mm doesn't put the roller on the fixed leg"
assert K_INNER + K_W == F_INNER, "keeper must reach the fixed upright"
assert K_SEGS * K_LEN == F_LEN, "keeper segments must fill the fixed rail"
assert K_INNER > sr.OUTER_X + sr.HEAD_H + 1, "keeper hits the lock heads"
assert K_INNER < ROLLER_X1 - 6, "keeper barely covers the roller"
assert F_INNER - LEG < sr.UPRIGHT_X, "fixed leg doesn't reach under the shelf"
assert K_Y + K_H / 2 < HEEL_Y + LEG, "keeper above the fixed upright"
assert (HEAD_D - R_BORE) / 2 >= 0.6, "screw head barely overlaps the roller"
assert (SPIGOT_D - 5.0) / 2 >= 1.2, "spigot wall too thin round the thread"
assert sr.SLIDE_Z[0] - RD / 2 > F_REAR, "rear roller off the back, shut"
assert LUG_Y > LEG_TOP, "lug must clear the fixed leg"


# --------------------------------------------------------------------- parts
def build_roller():
    part = br.counterbored_roller(RD, RH, R_BORE, R_CBORE, BORE_LEN, CHAMF)
    return finish(part, "Slide_Roller " + ROLLER.id, ROLLER.colour)


def build_spacer():
    k = Kit()
    k.sketch("y", 0)
    k.circle((0, 0, 0), COLLAR_D)
    k.circle((0, 0, 0), S_BORE)
    k.boss(STANDOFF, midplane=False)
    k.sketch("y", STANDOFF)
    k.circle((0, STANDOFF, 0), SPIGOT_D)
    k.circle((0, STANDOFF, 0), S_BORE)
    k.boss(SPACER_H - STANDOFF, midplane=False)
    part = chamfer_circle(k.part, 0, COLLAR_D, SPACER["bed_chamfer_mm"])
    return finish(part, "Slide_Spacer " + SPACER.id, SPACER.colour)


def build_fixed(req, sign):
    """As the shelf rail: heel on the origin, upright outer face at X=0,
    leg towards +X for sign +1 (left), rear end at Z=0."""
    k = Kit()
    angle_profile(k, LEG, T, sign)
    k.boss(F_LEN, midplane=False)
    k.sketch("x", 0)
    for z in F_HOLES:
        k.circle((0, K_HOLE_Y, z), F_BOLT_D)
    k.cut(10)
    name = "Slide_Rail_" + ("L" if sign > 0 else "R")
    return finish(k.part, "%s %s" % (name, req.id), req.colour)


def build_keeper(req, bolts, inner, lug, name):
    """Centred on its own origin, as fitted: `inner` is the sign of the X
    face nearest the case (-1 for the right side). Bolts run across X, heads
    sunk in the inner face. `lug`: end stop hanging from the front end."""
    k = Kit()
    w, h, L = K_W / 2, K_H / 2, K_LEN / 2
    k.sketch("z", 0)
    k.box("z", -w, w, -h, h, 0)
    k.boss(K_LEN)
    if lug:
        k.sketch("z", L - LUG_T / 2)
        k.box("z", -w, w, LUG_Y - K_Y, -h + 1, L - LUG_T / 2)
        k.boss(LUG_T)
    zs = [b - L for b in bolts]
    k.sketch("x", 0)
    for z in zs:
        k.circle((0, 0, z), K_BOLT_D)
    k.cut(K_W + 10)
    k.sketch("x", inner * w)
    for z in zs:
        k.circle((inner * w, 0, z), K_CB_D)
    k.cut(2 * K_CB_DEPTH)
    return finish(k.part, "%s %s" % (name, req.id), req.colour)


def build_strip(req, name, pts):
    """Pad / shoe: profile (y, z) extruded across X, centred on X=0."""
    k = Kit()
    k.sketch("x", 0)
    k.poly([(0, y, z) for y, z in pts])
    k.boss(req["width_mm"])
    return finish(k.part, "%s %s" % (name, req.id), req.colour)


def build():
    p = {"slide_roller": build_roller(), "slide_spacer": build_spacer(),
         "rail_l": build_fixed(RAIL_L, +1), "rail_r": build_fixed(RAIL_R, -1),
         "keeper": build_keeper(KEEPER, KEEPER["bolts_from_end_mm"], -1,
                                False, "Slide_Keeper"),
         "kfront_l": build_keeper(KFRONT_L, KFRONT_L["bolts_from_end_mm"],
                                  +1, True, "Slide_Keeper_Front_L"),
         "kfront_r": build_keeper(KFRONT_R, KFRONT_R["bolts_from_end_mm"],
                                  -1, True, "Slide_Keeper_Front_R")}
    L, H, rp = PAD["length_mm"] / 2, PAD["height_mm"], PAD["ramp_mm"]
    p["pad"] = build_strip(PAD, "Landing_Pad",
                           [(0, -L), (0, L), (H, L - rp), (H, -L + rp)])
    L, H, c = SHOE["length_mm"] / 2, SHOE["height_mm"], SHOE["end_chamfer_mm"]
    p["shoe"] = build_strip(SHOE, "Slide_Shoe",
                            [(0, -L), (0, L), (-H + c, L), (-H, L - c),
                             (-H, -L + c), (-H + c, -L)])
    return p


# ------------------------------------------------------------------ assembly
def assembly(p, case_parts, rails_dz, case_dz, lock):
    """The shelf on its slides. p: shelf and slide parts. Returns the
    placed parts and the part pairs that overlap by design."""
    out = sr.place_shelf(p, case_parts, rails_dz, case_dz, lock)
    mid = K_LEN / 2
    for s in (-1, 1):
        outward = Y_TO_POS_X if s > 0 else Y_TO_NEG_X
        for z in sr.SLIDE_Z:
            z += rails_dz
            out.append(place_axis(p["slide_spacer"], outward,
                                  (s * sr.OUTER_X, sr.SLIDE_Y, z),
                                  (s * sr.OUTER_X,
                                   s * (sr.OUTER_X + SPACER_H))))
            out.append(place_axis(p["slide_roller"], outward,
                                  (s * ROLLER_X0, sr.SLIDE_Y, z),
                                  (s * ROLLER_X0, s * ROLLER_X1)))
        out.append(place(p["rail_l" if s < 0 else "rail_r"], IDENT,
                         (s * F_OUTER, HEEL_Y, F_REAR)))
        turn = IDENT if s > 0 else TURN_Y180       # plain keeper: either
        for z0 in SEG_Z0[:-1]:
            out.append(place(p["keeper"], turn, (s * K_X, K_Y, z0 + mid)))
        out.append(place(p["kfront_l" if s < 0 else "kfront_r"], IDENT,
                         (s * K_X, K_Y, SEG_Z0[-1] + mid)))
        out.append(place(p["pad"], IDENT,
                         (s * PAD["centre_x_mm"], LEG_TOP,
                          PAD["centre_z_mm"])))
        out.append(place(p["shoe"], IDENT,
                         (s * SHOE["centre_x_mm"], -sr.T,
                          SHOE["centre_z_mm"] + rails_dz)))
    ignore = set(sr.SCREW_IGNORE)
    if rails_dz == 0:                 # shoe on the pad: the 0.5 mm lift
        ignore.add(("Landing_Pad", "Slide_Shoe"))
    return out, ignore
