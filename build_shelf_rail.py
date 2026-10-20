"""
Shelf rails (draft): the dincase mounting angle, lengthened to run past the
back of the case so the two rails can be tied together by a rear cross
brace and carried on slides as a pull-out shelf.

Run with SolidWorks open:
    python build_shelf_rail.py

Inputs: specs/shelf-rail-left.yaml and specs/shelf-rail-right.yaml (mirror
images: same parameters apart from `hand`). Makes:
    parts/Shelf_Rail_L.SLDPRT, parts/Shelf_Rail_R.SLDPRT
    Dincase_Shelf.SLDASM          - case + both rails, rollers and screws
    drawings/Shelf_Rail.SLDDRW/.PDF - LH as drawn, RH opposite hand

Per rail: 50x50x2 angle, upright outside the case. Four M5 tapped holes in
the upright on the track line: rear roller, lock screw and front roller at
the same positions relative to the case as the mounting angle, plus a stop
screw. Two more, lower down, carry the drawer-slide rollers on the outside
(see build_slide.py). Two M5 clearance holes in the base leg where it runs
past the case, for the rear cross brace.

Two-stage pull-out: with the lock screw left out, the case rolls forward on
its own track rollers until the stop screw meets the rib between the
pockets (stop_travel_mm, short of the rear roller leaving its lip). Then the
rail itself runs out on the slide. The lock screw hole stays, as a transit
lock.

Axes: X across the case, Y up (case bottom at 0), Z front (+, handle).
"""
import os

import pythoncom
from win32com.client import VARIANT

from partnum import load_requirements, write_build_record

import build_mount as bm
import build_roller
from build_roller import ROLLER_D, ROLLER_H, SPACER_H
from swkit import (HERE, PARTS_DIR, IDENT, NUL, Kit, byref_int, call, colour,
                   connect, fix_all, interferences, m, new_part, place,
                   save_and_keep)

# ------------------------------------------------------------ requirements
LEFT = load_requirements(os.path.join(HERE, "specs", "shelf-rail-left.yaml"))
RIGHT = load_requirements(os.path.join(HERE, "specs", "shelf-rail-right.yaml"))
_l, _r = LEFT.params, RIGHT.params
if (_l.pop("hand"), _r.pop("hand")) != ("left", "right") or _l != _r:
    raise SystemExit("shelf-rail-left/right must differ only in `hand`")
for _name, _built in (("roller", build_roller.ROLLER_REQ),
                      ("spacer", build_roller.SPACER_REQ),
                      ("screw", build_roller.SCREW_REQ)):
    for _req in (LEFT, RIGHT):
        if _req.use(_name).id != _built.id:
            raise SystemExit("%s uses a different %s than build_roller.py "
                             "builds" % (_req.path.name, _name))
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
STEEL = tuple(P.get("appearance", {}).get("colour", (0.62, 0.64, 0.66)))

ASM_PATH = os.path.join(HERE, "Dincase_Shelf.SLDASM")
CASE_ASM = os.path.join(HERE, "RolaCase_Assembly.SLDASM")
DRW_DIR = os.path.join(HERE, "drawings")

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
def build_rail(sw, req, sign):
    """sign +1: left rail (base leg runs +X from the heel); -1: right.
    Heel on the origin, upright outer face at X=0, rear end at Z=0."""
    model = new_part(sw)
    k = Kit(sw, model)
    md = model

    def pick(*items):
        md.ClearSelection2(True)
        for it in items:
            if it == "origin":
                md.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT",
                                         0, 0, 0, True, 0, NUL, 0)
            else:
                it.Select4(True, NUL)

    s = sign
    k.sketch(k.front)
    segs = k.poly([(0, 0, 0), (s * LEG, 0, 0), (s * LEG, T, 0), (s * T, T, 0),
                   (s * T, LEG, 0), (0, LEG, 0)])
    for seg, at in ((segs[0], (s * LEG / 2, -8)), (segs[5], (-s * 8, LEG / 2)),
                    (segs[1], (s * (LEG + 6), T)), (segs[4], (s * T / 2, LEG + 6))):
        pick(seg)
        md.AddDimension2(m(at[0]), m(at[1]), 0)
    md.ClearSelection2(True)
    k.boss(RAIL_LEN, midplane=False)                  # Z 0 -> RAIL_LEN

    # Upright: rear roller, lock screw, front roller (M5 tapped).
    k.sketch(k.right)
    holes = [k.circle((0, HOLE_Y, z), TAP_DRILL) for z in HOLES_FROM_REAR]
    pick(holes[0])
    md.AddDimension2(0, m(HOLE_Y + 10), m(HOLES_FROM_REAR[0]))
    for c in holes[1:]:
        pick(holes[0], c)
        md.SketchAddConstraints("sgSAMELENGTH")
        pick(holes[0].GetCenterPoint2, c.GetCenterPoint2)
        md.SketchAddConstraints("sgHORIZONTALPOINTS2D")
    pick(holes[0].GetCenterPoint2, "origin")
    md.AddVerticalDimension2(0, m(HOLE_Y / 2), m(-8))
    for i, c in enumerate(holes):
        pick(c.GetCenterPoint2, "origin")
        md.AddHorizontalDimension2(0, m(-6 - 7 * i), m(HOLES_FROM_REAR[i] / 2))
    md.ClearSelection2(True)
    k.cut(10)

    # Upright, low down: slide roller holes (M5 tapped).
    k.sketch(k.right)
    slide = [k.circle((0, SLIDE_HOLE_Y, z), TAP_DRILL)
             for z in SLIDE_FROM_REAR_ALL]
    pick(slide[0])
    md.AddDimension2(0, m(SLIDE_HOLE_Y - 10), m(SLIDE_FROM_REAR_ALL[0]))
    pick(slide[0], slide[1])
    md.SketchAddConstraints("sgSAMELENGTH")
    pick(slide[0].GetCenterPoint2, slide[1].GetCenterPoint2)
    md.SketchAddConstraints("sgHORIZONTALPOINTS2D")
    pick(slide[0].GetCenterPoint2, "origin")
    md.AddVerticalDimension2(0, m(SLIDE_HOLE_Y / 2), m(-30))
    for i, c in enumerate(slide):
        pick(c.GetCenterPoint2, "origin")
        md.AddHorizontalDimension2(0, m(LEG + 6 + 7 * i),
                                   m(SLIDE_FROM_REAR_ALL[i] / 2))
    md.ClearSelection2(True)
    k.cut(10)

    # Base leg, behind the case: rear cross brace bolts (M5 clearance).
    k.sketch(k.top)
    braces = [k.circle((s * BRACE_FROM_HEEL, 0, z), BRACE_D)
              for z in BRACE_FROM_REAR]
    pick(braces[0])
    md.AddDimension2(m(s * (BRACE_FROM_HEEL + 10)), 0, m(BRACE_FROM_REAR[0]))
    for c in braces[1:]:
        pick(braces[0], c)
        md.SketchAddConstraints("sgSAMELENGTH")
    pick(braces[0].GetCenterPoint2, braces[1].GetCenterPoint2)
    md.SketchAddConstraints("sgVERTICALPOINTS2D")
    pick(braces[0].GetCenterPoint2, "origin")
    md.AddHorizontalDimension2(m(s * BRACE_FROM_HEEL / 2), 0, m(-8))
    for i, c in enumerate(braces):
        pick(c.GetCenterPoint2, "origin")
        md.AddVerticalDimension2(m(-s * (8 + 7 * i)), 0, 0)
    md.ClearSelection2(True)
    k.cut(10)

    colour(model, STEEL)
    name = "Shelf_Rail_" + ("L" if sign > 0 else "R")
    props = model.Extension.CustomPropertyManager("")
    for key, val in (("Description", "dincase shelf rail %s"
                      % ("LH" if sign > 0 else "RH")),
                     ("Material", "Mild steel"), ("PartNo", req.id)):
        props.Add3(key, 30, val, 2)
    return model, save_and_keep(sw, model, name)


# ------------------------------------------------------------------ assembly
SCREW_IGNORE = {("M5x12_Button", "Shelf_Rail_L"),
                ("M5x12_Button", "Shelf_Rail_R"),
                ("M5x12_Button", "Roller_Spacer")}


def place_shelf(sw, asm, left_path, right_path, rails_dz=0.0, case_dz=0.0,
                lock=True):
    """Case, both rails, track rollers, spacers and screws. rails_dz moves
    the rails (slide travel); case_dz moves the case further along the
    rails (case travel, up to STOP_TRAVEL). The stop screw is always fitted;
    the lock screw only if `lock` (it would stop the case travelling)."""
    roller_path = os.path.join(PARTS_DIR, "Track_Roller.SLDPRT")
    spacer_path = os.path.join(PARTS_DIR, "Roller_Spacer.SLDPRT")
    screw_path = os.path.join(PARTS_DIR, "M5x12_Button.SLDPRT")
    for p, kind in ((roller_path, 1), (spacer_path, 1), (screw_path, 1),
                    (CASE_ASM, 2)):
        sw.OpenDoc6(p, kind, 0, "", byref_int(), byref_int())
    sw.ActivateDoc3(os.path.basename(asm.GetPathName), False, 0, byref_int())
    dz = rails_dz
    comps = [place(sw, asm, CASE_ASM, IDENT, (0, 0, rails_dz + case_dz))]
    head_face = UPRIGHT_X - SPACER_H
    for s, path in ((-1, left_path), (1, right_path)):
        x0 = s * UPRIGHT_X
        comps.append(place(sw, asm, path, IDENT,
                           (s * OUTER_X, -T, RAIL_Z0 + dz)))
        inward = bm.Y_TO_NEG_X if s > 0 else bm.Y_TO_POS_X
        outward = bm.Y_TO_POS_X if s > 0 else bm.Y_TO_NEG_X
        for z in (REAR_Z + dz, FRONT_Z + dz):
            comps.append(bm.place_axis(sw, asm, roller_path, inward,
                                       (x0, AXIS_Y, z),
                                       (x0, x0 - s * ROLLER_H)))
            comps.append(bm.place_axis(sw, asm, spacer_path, inward,
                                       (x0, AXIS_Y, z),
                                       (x0, x0 - s * SPACER_H)))
            comps.append(bm.place_axis(sw, asm, screw_path, outward,
                                       (s * head_face, AXIS_Y, z),
                                       (s * (head_face - HEAD_H),
                                        s * (head_face + SCREW_L))))
        for z in ((LOCK_Z, STOP_Z) if lock else (STOP_Z,)):
            comps.append(bm.place_axis(sw, asm, screw_path, inward,
                                       (s * OUTER_X, AXIS_Y, z + dz),
                                       (s * (OUTER_X - SCREW_L),
                                        s * (OUTER_X + HEAD_H))))
    return comps


def build_assembly(sw, left_path, right_path):
    asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
    if asm.SaveAs3(ASM_PATH, 0, 1) != 0:
        raise RuntimeError("could not save " + ASM_PATH)
    comps = place_shelf(sw, asm, left_path, right_path)
    fix_all(asm, comps)
    call(asm, "EditRebuild3")
    hits = interferences(asm, ignore_pairs=SCREW_IGNORE)
    for names, vol in hits:
        print("  INTERFERENCE", names, "%.3f mm3" % vol)
    print("Interferences (excluding screw threads):", len(hits))
    try:                              # cosmetic; the dispatch may not
        asm.ShowNamedView2("*Isometric", 7)       # expose it
        call(asm, "ViewZoomtofit2")
    except AttributeError:
        pass
    asm.Save3(1, byref_int(), byref_int())
    return asm


# ------------------------------------------------------------------- drawing
DRW_NOTES = [
    "DRAFT - NOT RELEASED",
    "MATERIAL: 50 x 50 x 2 mm EQUAL ANGLE, MILD STEEL",
    "QTY: 1 LEFT HAND AS DRAWN + 1 RIGHT HAND (MIRROR IMAGE)",
    "UPRIGHT: 6 x M5 x 0.8 TAPPED THRU, TAP DRILL %.1f" % TAP_DRILL,
    "  UPPER ROW: REAR ROLLER, LOCK, STOP, FRONT ROLLER (FROM REAR END)",
    "  LOWER ROW: SLIDE ROLLERS",
    "BASE LEG: 2 x %.1f THRU (M5 CLEARANCE) FOR REAR CROSS BRACE" % BRACE_D,
    "CUT LENGTH %.2f +/-0.5. DEBURR ALL EDGES." % RAIL_LEN,
    "FINISH: ZINC PLATE OR PAINT AFTER TAPPING",
]


# Sheet layout (metres, A3 landscape). Views are 1:1, so each view's box
# follows from the part size; SolidWorks' own view outlines are too loose.
UPRIGHT_AT = (0.195, 0.150)       # rail upright, seen from outside
PLAN_AT = (0.195, 0.240)          # base leg, seen from above (rotated)
PROFILE_AT = (0.388, 0.150)
ISO_AT = (0.385, 0.255)


def _box(centre, w, h):
    cx, cy = centre
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def tidy_dimensions(drw):
    """Each sketch's dimensions only in the view that shows them, laid out
    clear of each other and of the notes."""
    views = []
    v = drw.GetFirstView.GetNextView
    while v is not None:
        views.append(v)
        v = v.GetNextView
    upright, plan, profile = views[0], views[1], views[2]
    L, H = m(RAIL_LEN), m(LEG)
    boxes = {id(upright): _box(UPRIGHT_AT, L, H),
             id(plan): _box(PLAN_AT, L, H),
             id(profile): _box(PROFILE_AT, H, H)}
    home = {"Sketch1": [profile], "Sketch2": [upright], "Sketch3": [upright],
            "Sketch4": [plan], "Boss-Extrude1": [upright, plan]}
    length_kept = False
    for view in (upright, plan, profile):
        x0, y0, x1, y1 = boxes[id(view)]
        dd = view.GetFirstDisplayDimension5
        doomed, moves = [], []
        while dd is not None:
            dim = dd.GetDimension2(0)
            name, val = dim.FullName, dim.SystemValue * 1000
            feat = name.split("@")[1]
            x, _, _ = dd.GetAnnotation.GetPosition
            if view not in home.get(feat, []) or round(val) == 48 or                     (feat == "Boss-Extrude1" and length_kept):
                doomed.append(dd)
            elif feat == "Boss-Extrude1":               # overall length
                length_kept = True
                moves.append((dd, (x0 + x1) / 2,
                              (y0 - 0.031) if view is upright else
                              (y1 + 0.012)))
            elif view is upright and feat == "Sketch3":   # slide rollers
                if abs(val - TAP_DRILL) < 1e-6:
                    moves.append((dd, x - 0.012, y0 - 0.040))
                elif abs(val - SLIDE_HOLE_Y) < 1e-6:
                    moves.append((dd, x0 - 0.010, y0 + 0.006))
                else:
                    k = SLIDE_FROM_REAR_ALL.index(min(
                        SLIDE_FROM_REAR_ALL, key=lambda h: abs(h - val)))
                    moves.append((dd, x, y1 + 0.010 + 0.0072 * k))
            elif view is upright:
                if abs(val - TAP_DRILL) < 1e-6:
                    moves.append((dd, x + 0.012, y1 + 0.010))
                elif abs(val - HOLE_Y) < 1e-6:
                    moves.append((dd, x1 + 0.010, y0 + 0.010))
                else:
                    k = min(range(len(HOLES_FROM_REAR)),
                            key=lambda i: abs(HOLES_FROM_REAR[i]
                                                        - val))
                    moves.append((dd, x, y0 - 0.009 - 0.0072 * k))
            elif view is plan:
                if abs(val - BRACE_D) < 1e-6:
                    moves.append((dd, x0 + 0.06, y1 + 0.010))
                elif abs(val - BRACE_FROM_HEEL) < 1e-6:
                    moves.append((dd, x0 - 0.010, (y0 + y1) / 2))
                else:
                    k = BRACE_FROM_REAR.index(min(
                        BRACE_FROM_REAR, key=lambda b: abs(b - val)))
                    moves.append((dd, x, y0 - 0.008 - 0.0072 * k))
            dd = dd.GetNext5
        for dd, x, y in moves:
            dd.GetAnnotation.SetPosition2(x, y, 0)
        for dd in doomed:
            drw.ClearSelection2(True)
            dd.GetAnnotation.Select3(False, drw.SelectionManager
                                     .CreateSelectData)
            drw.EditDelete()
    drw.ClearSelection2(True)


def make_drawing(sw, left_path):
    os.makedirs(DRW_DIR, exist_ok=True)
    sw.OpenDoc6(left_path, 1, 0, "", byref_int(), byref_int())
    d = sw.GetFirstDocument
    while d is not None:                      # free an old copy
        nxt = d.GetNext
        if d.GetType == 3 and "Shelf_Rail" in d.GetTitle:
            sw.CloseDoc(d.GetTitle)
        d = nxt
    drw = sw.NewDocument(sw.GetUserPreferenceStringValue(10), 8, 0.42, 0.297)
    # Sheet format and 1:1 scale FIRST: changing the sheet scale later
    # rescales everything already placed on it.
    drw.SetupSheet5(drw.GetCurrentSheet.GetName, 8, 12, 1, 1, False,
                    bm.SHEET_FORMAT, 0.42, 0.297, "Default", True)
    import math
    for name, (x, y), scale, turn in (
            ("*Left", UPRIGHT_AT, None, 0),           # upright
            ("*Top", PLAN_AT, None, math.pi / 2),     # base leg, lengthways
            ("*Front", PROFILE_AT, None, 0),          # profile
            ("*Isometric", ISO_AT, 0.3, 0)):
        v = drw.CreateDrawViewFromModelView3(left_path, name, x, y, 0)
        if v is None:
            raise RuntimeError("view failed: " + name)
        v.UseSheetScale = False           # fixed scale: SolidWorks would
        v.ScaleDecimal = scale or 1.0     # otherwise auto-pick 1:5 here
        if turn:
            v.Angle = turn
            v.Position = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y])
    drw.InsertModelAnnotations3(0, 32768, True, False, False, True)
    tidy_dimensions(drw)
    drw.SetupSheet5(drw.GetCurrentSheet.GetName, 8, 12, 1, 1, False,
                    bm.SHEET_FORMAT, 0.42, 0.297, "Default", True)
    for i, text in enumerate(DRW_NOTES):
        note = drw.InsertNote(text)
        if note is not None:
            note.GetAnnotation.SetPosition2(0.025, 0.085 - i * 0.0058, 0)
    call(drw, "EditRebuild3")
    call(drw, "ViewZoomtofit2")
    path = os.path.join(DRW_DIR, "Shelf_Rail.SLDDRW")
    if drw.SaveAs3(path, 0, 1) != 0:
        raise RuntimeError("could not save " + path)
    pdf = os.path.join(DRW_DIR, "Shelf_Rail.PDF")
    if drw.SaveAs3(pdf, 0, 1) != 0:
        raise RuntimeError("PDF export failed")
    bm.scrub_pdf(pdf)
    return path, pdf


# ---------------------------------------------------------------------- main
def main():
    print("Left %s  Right %s" % (LEFT.id, RIGHT.id))
    print("Rail %.2f long: rear end Z %.2f (%.0f past the case), front end "
          "Z %.2f" % (RAIL_LEN, RAIL_Z0, REAR_OVERHANG, RAIL_Z1))
    print("Upright holes from rear end: %s; brace holes %s from rear, %.0f "
          "from heel" % (", ".join("%.2f" % h for h in HOLES_FROM_REAR),
                         BRACE_FROM_REAR, BRACE_FROM_HEEL))
    sw = connect()
    for t in ("Dincase_Shelf.SLDASM", "Shelf_Rail_L.SLDPRT",
              "Shelf_Rail_R.SLDPRT"):
        sw.CloseDoc(t)
    if os.path.exists(ASM_PATH):
        raise SystemExit("%s exists - delete it to rebuild." % ASM_PATH)
    was = sw.GetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE)
    sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, False)
    try:
        _, left_path = build_rail(sw, LEFT, +1)
        _, right_path = build_rail(sw, RIGHT, -1)
    finally:
        sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, was)
    build_assembly(sw, left_path, right_path)
    drw_path, pdf_path = make_drawing(sw, left_path)
    for req, outs in ((LEFT, [left_path, drw_path, pdf_path]),
                      (RIGHT, [right_path])):
        print("  build record", write_build_record(req, outs).name)
    print("Done:", ASM_PATH)


if __name__ == "__main__":
    main()
