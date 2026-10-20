"""
Drawer slide (draft) for the dincase shelf: the shelf rails pull out of the
trunk on a fixed angle each side, and the case rolls a further
stop_travel_mm forward on its own track rollers.

Run with SolidWorks open, after build_shelf_rail.py:
    python build_slide.py

Section, right-hand side (the left is a mirror image):

    shelf rail upright | spacer | slide roller | lane | fixed rail upright
                         collar   (30 dia)       1.5    (keeper inside it,
                                                         above the roller)
    shelf rail base leg  ---------------------------  ride 3 mm
    fixed rail leg       ---------------------------  (rollers run on it)

Two slide rollers per side sit low on the OUTSIDE of the shelf rail and
run on the fixed rail's leg, which lies 3 mm under the shelf rail's base
leg, so the slide adds only about 7 mm under the case. Printed keepers
bolted inside the fixed rail's upright sit over the rollers: when the shelf
is out, the case hangs ahead of the rollers and the rear roller pushes up
on the keeper. The front keeper has the closest bolts (that is where the
rear roller presses at full travel) and a lug that is the end stop. The
keeper bolts go on through the fixed upright, so they also mount it.

Shut, a printed shoe under the front of the shelf rail rides onto a thin
landing pad on the fixed leg and lifts the shelf front 0.5 mm, so the shut
drawer rests on the pad and the rear rollers instead of the keepers.

Inputs: specs/slide-*.yaml, landing-pad.yaml, slide-shoe.yaml and the
shelf rail specs. Makes parts/Slide_*.SLDPRT, Landing_Pad, Slide_Shoe,
their STLs, and two fit-check assemblies:
    Dincase_Slide.SLDASM       - shut, lock screws in
    Dincase_Slide_Open.SLDASM  - rails out by full slide travel, case
                                 rolled forward by stop_travel_mm
Screws and keeper bolts are not modelled; their holes are.

Axes as build_shelf_rail.py: X across, Y up (case bottom 0), Z front (+),
shelf coordinates with the drawer shut and the case locked.
"""
import os

from partnum import load_requirements, write_build_record

import build_mount as bm
import build_roller as br
import build_shelf_rail as sr
from swkit import (HERE, PARTS_DIR, IDENT, NUL, Kit, byref_int, call, colour,
                   connect, fix_all, interferences, new_part, place,
                   save_and_keep)


def spec(name):
    return load_requirements(os.path.join(HERE, "specs", name + ".yaml"))


ROLLER = spec("slide-roller")
SPACER = spec("slide-spacer")
RAIL_L, RAIL_R = spec("slide-rail-left"), spec("slide-rail-right")
KEEPER = spec("slide-keeper")
KFRONT_L, KFRONT_R = (spec("slide-keeper-front-left"),
                      spec("slide-keeper-front-right"))
PAD, SHOE = spec("landing-pad"), spec("slide-shoe")
for a, b in ((RAIL_L, RAIL_R), (KFRONT_L, KFRONT_R)):
    pa, pb = dict(a.params), dict(b.params)
    if (pa.pop("hand"), pb.pop("hand")) != ("left", "right") or pa != pb:
        raise SystemExit("%s / %s must differ only in `hand`"
                         % (a.path.name, b.path.name))
if SPACER.use("roller").id != ROLLER.id:
    raise SystemExit("slide-spacer.yaml uses a different roller")

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
STEEL = tuple(R.get("appearance", {}).get("colour", (0.62, 0.64, 0.66)))
ORANGE = tuple(ROLLER.get("appearance", {}).get("colour", (0.95, 0.55, 0.1)))
GREY = tuple(SPACER.get("appearance", {}).get("colour", (0.6, 0.6, 0.6)))
GREEN = tuple(KEEPER.get("appearance", {}).get("colour", (0.2, 0.55, 0.45)))

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
CASE_BACK_SHUT = -sr.CASE_D / 2

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
def props(model, req, desc, material="PETG"):
    pm = model.Extension.CustomPropertyManager("")
    for key, val in (("Description", desc), ("Material", material),
                     ("PartNo", req.id)):
        pm.Add3(key, 30, val, 2)


def build_roller(sw):
    model = new_part(sw)
    model.SketchManager.AddToDB = False
    front, top, right = br.base_planes(model)
    br.start_sketch(model, top)
    br.circle(model, RD, RD * 0.7)
    br.circle(model, R_BORE, R_BORE * 0.4)
    br.extrude(model, RH)
    br.start_sketch(model, br.offset_plane(model, top, RH))
    br.circle(model, R_CBORE, R_CBORE * 0.5)
    br.cut_mid(model, 2 * (RH - BORE_LEN))
    br.chamfer_bottom_edge(model, RD, CHAMF)
    colour(model, ORANGE)
    props(model, ROLLER, "dincase slide roller")
    return save_and_keep(sw, model, "Slide_Roller")


def build_spacer(sw):
    model = new_part(sw)
    model.SketchManager.AddToDB = False
    front, top, right = br.base_planes(model)
    br.start_sketch(model, top)
    br.circle(model, COLLAR_D, COLLAR_D * 0.7)
    br.circle(model, S_BORE, S_BORE * 0.4)
    br.extrude(model, STANDOFF)
    br.start_sketch(model, br.offset_plane(model, top, STANDOFF))
    br.circle(model, SPIGOT_D, SPIGOT_D * 0.7)
    br.circle(model, S_BORE, S_BORE * 0.4)
    br.extrude(model, SPACER_H - STANDOFF)
    br.chamfer_bottom_edge(model, COLLAR_D, SPACER["bed_chamfer_mm"])
    colour(model, GREY)
    props(model, SPACER, "dincase slide roller spacer")
    return save_and_keep(sw, model, "Slide_Spacer")


def build_fixed(sw, req, sign):
    """As the shelf rail: heel on the origin, upright outer face at X=0,
    leg towards +X for sign +1 (left), rear end at Z=0."""
    model = new_part(sw)
    k = Kit(sw, model)
    s = sign
    k.sketch(k.front)
    k.poly([(0, 0, 0), (s * LEG, 0, 0), (s * LEG, T, 0), (s * T, T, 0),
            (s * T, LEG, 0), (0, LEG, 0)])
    k.boss(F_LEN, midplane=False)
    k.sketch(k.right)
    for z in F_HOLES:
        k.circle((0, K_HOLE_Y, z), F_BOLT_D)
    k.cut(10)
    colour(model, STEEL)
    props(model, req, "dincase slide fixed rail %s"
          % ("LH" if s > 0 else "RH"), "Mild steel")
    return save_and_keep(sw, model, "Slide_Rail_" + ("L" if s > 0 else "R"))


def build_keeper(sw, req, bolts, inner, lug, name):
    """Centred on its own origin, as fitted: `inner` is the sign of the X
    face nearest the case (-1 for the right side). Bolts run across X, heads
    sunk in the inner face. `lug`: end stop hanging from the front end."""
    model = new_part(sw)
    k = Kit(sw, model)
    w, h, L = K_W / 2, K_H / 2, K_LEN / 2
    k.sketch(k.front)
    k.box("z", -w, w, -h, h, 0)
    k.boss(K_LEN)
    if lug:
        k.sketch(k.zplane(L - LUG_T / 2))
        k.box("z", -w, w, LUG_Y - K_Y, -h + 1, L - LUG_T / 2)
        k.boss(LUG_T)
    zs = [b - L for b in bolts]
    k.sketch(k.right)
    for z in zs:
        k.circle((0, 0, z), K_BOLT_D)
    k.cut(K_W + 10)
    k.sketch(k.xplane(inner * w))
    for z in zs:
        k.circle((inner * w, 0, z), K_CB_D)
    k.cut(2 * K_CB_DEPTH)
    colour(model, GREEN)
    props(model, req, "dincase slide keeper")
    return save_and_keep(sw, model, name)


def build_strip(sw, req, name, pts):
    """Pad / shoe: profile (y, z) extruded across X, centred on X=0."""
    model = new_part(sw)
    k = Kit(sw, model)
    k.sketch(k.right)
    k.poly([(0, y, z) for y, z in pts])
    k.boss(req["width_mm"])
    colour(model, GREEN)
    props(model, req, "dincase slide " + name.split("_")[-1].lower())
    return save_and_keep(sw, model, name)


def build_parts(sw):
    p = {}
    p["roller"] = build_roller(sw)
    p["spacer"] = build_spacer(sw)
    p["rail_l"] = build_fixed(sw, RAIL_L, +1)
    p["rail_r"] = build_fixed(sw, RAIL_R, -1)
    p["keeper"] = build_keeper(sw, KEEPER, KEEPER["bolts_from_end_mm"], -1,
                               False, "Slide_Keeper")
    p["kfront_l"] = build_keeper(sw, KFRONT_L, KFRONT_L["bolts_from_end_mm"],
                                 +1, True, "Slide_Keeper_Front_L")
    p["kfront_r"] = build_keeper(sw, KFRONT_R, KFRONT_R["bolts_from_end_mm"],
                                 -1, True, "Slide_Keeper_Front_R")
    L, H, rp = PAD["length_mm"] / 2, PAD["height_mm"], PAD["ramp_mm"]
    p["pad"] = build_strip(sw, PAD, "Landing_Pad",
                           [(0, -L), (0, L), (H, L - rp), (H, -L + rp)])
    L, H, c = SHOE["length_mm"] / 2, SHOE["height_mm"], SHOE["end_chamfer_mm"]
    p["shoe"] = build_strip(sw, SHOE, "Slide_Shoe",
                            [(0, -L), (0, L), (-H + c, L), (-H, L - c),
                             (-H, -L + c), (-H + c, -L)])
    return p


# ------------------------------------------------------------------ assembly
def build_assembly(sw, p, path, rails_dz, case_dz, lock):
    asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
    if asm.SaveAs3(path, 0, 1) != 0:
        raise RuntimeError("could not save " + path)
    shelf_l = os.path.join(PARTS_DIR, "Shelf_Rail_L.SLDPRT")
    shelf_r = os.path.join(PARTS_DIR, "Shelf_Rail_R.SLDPRT")
    for q in (shelf_l, shelf_r):
        sw.OpenDoc6(q, 1, 0, "", byref_int(), byref_int())
    comps = sr.place_shelf(sw, asm, shelf_l, shelf_r, rails_dz, case_dz, lock)
    sw.ActivateDoc3(os.path.basename(path), False, 0, byref_int())
    mid = K_LEN / 2
    for s in (-1, 1):
        out = bm.Y_TO_POS_X if s > 0 else bm.Y_TO_NEG_X
        for z in sr.SLIDE_Z:
            z += rails_dz
            comps.append(bm.place_axis(sw, asm, p["spacer"], out,
                                       (s * sr.OUTER_X, sr.SLIDE_Y, z),
                                       (s * sr.OUTER_X,
                                        s * (sr.OUTER_X + SPACER_H))))
            comps.append(bm.place_axis(sw, asm, p["roller"], out,
                                       (s * ROLLER_X0, sr.SLIDE_Y, z),
                                       (s * ROLLER_X0, s * ROLLER_X1)))
        comps.append(place(sw, asm, p["rail_l" if s < 0 else "rail_r"],
                           IDENT, (s * F_OUTER, HEEL_Y, F_REAR)))
        turn = IDENT if s > 0 else bm.TURN_Y180       # plain keeper: either
        for z0 in SEG_Z0[:-1]:
            comps.append(place(sw, asm, p["keeper"], turn,
                               (s * K_X, K_Y, z0 + mid)))
        comps.append(place(sw, asm, p["kfront_l" if s < 0 else "kfront_r"],
                           IDENT, (s * K_X, K_Y, SEG_Z0[-1] + mid)))
        comps.append(place(sw, asm, p["pad"], IDENT,
                           (s * PAD["centre_x_mm"], LEG_TOP,
                            PAD["centre_z_mm"])))
        comps.append(place(sw, asm, p["shoe"], IDENT,
                           (s * SHOE["centre_x_mm"], -sr.T,
                            SHOE["centre_z_mm"] + rails_dz)))
    fix_all(asm, comps)
    call(asm, "EditRebuild3")
    ignore = set(sr.SCREW_IGNORE)
    if rails_dz == 0:                 # shoe on the pad: the 0.5 mm lift
        ignore.add(("Landing_Pad", "Slide_Shoe"))
    hits = interferences(asm, ignore_pairs=ignore)
    for names, vol in hits:
        print("  INTERFERENCE", names, "%.3f mm3" % vol)
    print("  %s: %d interferences (excluding screw threads%s)"
          % (os.path.basename(path), len(hits),
             ", shoe on pad" if rails_dz == 0 else ""))
    try:                              # cosmetic; the dispatch may not
        asm.ShowNamedView2("*Isometric", 7)       # expose it
        call(asm, "ViewZoomtofit2")
    except AttributeError:
        pass
    asm.Save3(1, byref_int(), byref_int())
    return hits


# ---------------------------------------------------------------------- main
ASM_SHUT = os.path.join(HERE, "Dincase_Slide.SLDASM")
ASM_OPEN = os.path.join(HERE, "Dincase_Slide_Open.SLDASM")
PRINTED = ["Slide_Roller", "Slide_Spacer", "Slide_Keeper",
           "Slide_Keeper_Front_L", "Slide_Keeper_Front_R", "Landing_Pad",
           "Slide_Shoe"]


def main():
    print("Fixed rail %.0f long, upright at |x| %.1f-%.1f, leg top Y %.1f; "
          "keeper Y %.1f-%.1f, |x| %.1f-%.1f"
          % (F_LEN, F_INNER, F_OUTER, LEG_TOP, K_BOTTOM, K_BOTTOM + K_H,
             K_INNER, F_INNER))
    print("Slide travel %.1f + case travel %.1f = %.1f; case back from %.1f "
          "to %.1f (shelf coordinates)"
          % (SLIDE_TRAVEL, CASE_TRAVEL, SLIDE_TRAVEL + CASE_TRAVEL,
             CASE_BACK_SHUT, CASE_BACK_SHUT + SLIDE_TRAVEL + CASE_TRAVEL))
    sw = connect()
    for path in (ASM_SHUT, ASM_OPEN):
        sw.CloseDoc(os.path.basename(path))
        if os.path.exists(path):
            raise SystemExit("%s exists - delete it to rebuild." % path)
    for n in PRINTED + ["Slide_Rail_L", "Slide_Rail_R"]:
        sw.CloseDoc(n + ".SLDPRT")
    was = sw.GetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE)
    sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, False)
    try:
        p = build_parts(sw)
    finally:
        sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, was)
    stl = {n: br.export_stl(sw, n) for n in PRINTED}
    build_assembly(sw, p, ASM_SHUT, 0.0, 0.0, True)
    build_assembly(sw, p, ASM_OPEN, SLIDE_TRAVEL, CASE_TRAVEL, False)
    for req, outs in ((ROLLER, [p["roller"], stl["Slide_Roller"]]),
                      (SPACER, [p["spacer"], stl["Slide_Spacer"]]),
                      (RAIL_L, [p["rail_l"]]), (RAIL_R, [p["rail_r"]]),
                      (KEEPER, [p["keeper"], stl["Slide_Keeper"]]),
                      (KFRONT_L, [p["kfront_l"],
                                  stl["Slide_Keeper_Front_L"]]),
                      (KFRONT_R, [p["kfront_r"],
                                  stl["Slide_Keeper_Front_R"]]),
                      (PAD, [p["pad"], stl["Landing_Pad"]]),
                      (SHOE, [p["shoe"], stl["Slide_Shoe"]])):
        print("  build record", write_build_record(req, outs).name)
    print("Done.")


if __name__ == "__main__":
    main()
