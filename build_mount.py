"""
Angle mount for the RolaCase: two 50x50x2 steel angles, legs under the
case. Each angle carries two 3D-printed rollers, one in each pocket of
that side's lock track, plus an M5 locking screw. M5x12 button heads
thread into the angles throughout.

Run with SolidWorks open (after build_case_assembly.py and build_roller.py):
    python build_mount.py

Makes:
    parts/Mount_Angle.SLDPRT      - 50x50x2 angle, 4 x M5 tapped holes
    parts/M5x12_Button.SLDPRT     - ISO 7380 style button head, simplified
    RolaCase_AngleMount.SLDASM    - case assembly + both angle sets
    drawings/Mount_Angle.SLDDRW   - fabrication drawing (+ PDF)
    (STLs of the roller and spacer come from build_roller.py)

Each side track (from Sketch6 in RC001_Case_v2) has two pockets:
    front pocket  Z -71.5 -> +46: closed front end, lip from -51.5, and a
                  lip-free entry slot -71.5 -> -51.5 open to the bottom
    rib           Z -74 -> -71.5 (2.5 thick)
    rear pocket   Z -184 -> -74: open at the back end, lip full length
    channel       8 -> 26.5 up from the case bottom

Fitting the case:
  1. Lower it so each front roller comes up through its entry slot (the
     rear rollers are then just behind the case).
  2. Slide the case back ~98 mm. The rear rollers run into the open back
     ends of the rear pockets; the front rollers stop at the closed ends
     of the front pockets. Both lips now hold the case down.
  3. Thread the M5 locking screw in from outside, through the hole nearest
     the rear roller. Its thread lands against the front face of the rib,
     so the case can't slide forward to the entry slots again.
To remove: back out the locking screws, slide forward, lift.

The two angles are identical: the lock hole is drilled near both ends so
either angle fits either side. Use the one nearest the rear roller.

Axes: X across the case, Y up (case bottom at 0), Z front (+, handle).
"""
import math
import os

from swkit import (
    HERE, PARTS_DIR, IDENT, Kit, call, connect, new_part, colour,
    save_and_keep, place, transform, fix_all, interferences, byref_int, m,
    NUL,
)
from partnum import load_requirements, write_build_record

import build_roller
from build_roller import ROLLER_D, ROLLER_H, SPACER_H

# ------------------------------------------------------------ requirements
# All build inputs live in the requirement files; their hash is the part
# number (see the partnum package).
ANGLE_REQ = load_requirements(os.path.join(HERE, "specs", "mount-angle.yaml"))
SCREW_REQ = ANGLE_REQ.use("screw")
for _name, _built in (("roller", build_roller.ROLLER_REQ),
                      ("spacer", build_roller.SPACER_REQ),
                      ("screw", build_roller.SCREW_REQ)):
    if ANGLE_REQ.use(_name).id != _built.id:
        raise SystemExit("mount-angle.yaml uses a different %s than "
                         "build_roller.py builds" % _name)

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

STEEL = tuple(ANGLE_REQ.get("appearance", {}).get("colour", (0.62, 0.64, 0.66)))
ZINC = tuple(SCREW_REQ.get("appearance", {}).get("colour", (0.8, 0.8, 0.82)))

ASM_PATH = os.path.join(HERE, "RolaCase_AngleMount.SLDASM")
CASE_ASM = os.path.join(HERE, "RolaCase_Assembly.SLDASM")
DRW_DIR = os.path.join(HERE, "drawings")

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
assert _drop_front - ROLLER_SPACING + ROLLER_D / 2 < -CASE_W / 2,     "rear roller can't start behind the case - increase roller_spacing_mm"
assert REAR_Z + ROLLER_D / 2 < RIB_FRONT_Z - RIB_T, "rear roller hits the rib"

SW_INPUT_DIM_ON_CREATE = 10


# ---------------------------------------------------------------------- parts
def build_angle(sw):
    """Heel on the origin, upright leg up +Y, base leg out +X, length from
    Z=0 (one end) to +ANGLE_LEN. Real sketch dimensions, measured from that
    end, so the drawing can import them."""
    model = new_part(sw)
    k = Kit(sw, model)
    md = model
    L, T = ANGLE_LEG, ANGLE_T
    k.sketch(k.front)
    segs = k.poly([(0, 0, 0), (L, 0, 0), (L, T, 0), (T, T, 0), (T, L, 0),
                   (0, L, 0)])
    for seg, at in ((segs[0], (L / 2, -8)), (segs[5], (-8, L / 2)),
                    (segs[1], (L + 6, T)), (segs[4], (T / 2, L + 6))):
        md.ClearSelection2(True)
        seg.Select4(False, NUL)
        md.AddDimension2(m(at[0]), m(at[1]), 0)
    md.ClearSelection2(True)
    k.boss(ANGLE_LEN, midplane=False)          # Z 0 -> ANGLE_LEN

    # Tapped holes through the upright (sketch on its outside face, X=0).
    k.sketch(k.right)
    circles = [k.circle((0, HOLE_Y, z), TAP_DRILL) for z in HOLES_FROM_END]

    def pick(*items):
        md.ClearSelection2(True)
        for it in items:
            if it == "origin":
                md.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT",
                                         0, 0, 0, True, 0, NUL, 0)
            else:
                it.Select4(True, NUL)

    pick(circles[0])
    md.AddDimension2(0, m(HOLE_Y + 10), m(HOLES_FROM_END[0]))   # diameter
    for c in circles[1:]:                       # all the same size and height
        pick(circles[0], c)
        md.SketchAddConstraints("sgSAMELENGTH")
        pick(circles[0].GetCenterPoint2, c.GetCenterPoint2)
        md.SketchAddConstraints("sgHORIZONTALPOINTS2D")
    pick(circles[0].GetCenterPoint2, "origin")
    md.AddVerticalDimension2(0, m(HOLE_Y / 2), m(-8))           # height
    for i, c in enumerate(circles):                              # from end
        pick(c.GetCenterPoint2, "origin")
        md.AddHorizontalDimension2(0, m(-6 - 7 * i), m(HOLES_FROM_END[i] / 2))
    md.ClearSelection2(True)
    k.cut(10)

    colour(model, STEEL)
    return model, save_and_keep(sw, model, "Mount_Angle")


def build_screw(sw):
    """Head bearing face on the origin, shank up +Y, head down -Y."""
    model = new_part(sw)
    k = Kit(sw, model)
    k.sketch(k.yplane(-HEAD_H / 2))
    k.circle((0, -HEAD_H / 2, 0), HEAD_D)
    k.boss(HEAD_H)
    shank = SCREW_L - TIP_CHAMFER
    k.sketch(k.yplane(shank / 2))
    k.circle((0, shank / 2, 0), SCREW_D)
    k.boss(shank)
    # Chamfered end (as on real screws), modelled as a short smaller step.
    k.sketch(k.yplane(shank + TIP_CHAMFER / 2))
    k.circle((0, shank + TIP_CHAMFER / 2, 0), SCREW_D - 1.5 * TIP_CHAMFER)
    k.boss(TIP_CHAMFER)
    r = HEX_AF / 3 ** 0.5
    k.sketch(k.yplane(-HEAD_H + 1.25))
    k.poly([(r * math.cos(math.radians(a)), 0, r * math.sin(math.radians(a)))
            for a in range(0, 360, 60)])
    k.cut(2.5)
    colour(model, ZINC)
    return model, save_and_keep(sw, model, "M5x12_Button")


# ------------------------------------------------------------------ assembly
# Row-major rotations (rows = where part X, Y, Z go).
Y_TO_NEG_X = (0, 1, 0, -1, 0, 0, 0, 0, 1)
Y_TO_POS_X = (0, -1, 0, 1, 0, 0, 0, 0, 1)
TURN_Y180 = (-1, 0, 0, 0, 1, 0, 0, 0, -1)


def transpose(r):
    return (r[0], r[3], r[6], r[1], r[4], r[7], r[2], r[5], r[8])


def place_axis(sw, asm, path, rot, at, x_range):
    """Place a part whose axis is part +Y; check the X extent and fall back
    to the transposed rotation if SolidWorks uses the other convention."""
    c = place(sw, asm, path, rot, at)
    b = [v * 1000 for v in c.GetBox(False, False)]
    if abs(min(b[0], b[3]) - min(x_range)) > 0.2 or \
       abs(max(b[0], b[3]) - max(x_range)) > 0.2:
        c.Transform2 = transform(sw, transpose(rot), *at)
    return c


# ------------------------------------------------------------------- drawing
DRW_NOTES = [
    "MATERIAL: 50 x 50 x 2 mm EQUAL ANGLE, MILD STEEL",
    "QTY: 2, IDENTICAL. FIT ONE EACH SIDE, UPRIGHT OUTSIDE THE CASE.",
    "HOLES: 4 x M5 x 0.8 TAPPED THRU, TAP DRILL %.1f" % TAP_DRILL,
    "  OUTER 2 = ROLLERS. INNER 2 = LOCKING SCREW (USE THE ONE NEAREST",
    "  THE REAR ROLLER - THE OTHER LETS ONE PART FIT EITHER SIDE).",
    "CUT LENGTH %.0f +/-0.5. DEBURR ALL EDGES." % ANGLE_LEN,
    "FINISH: ZINC PLATE OR PAINT AFTER TAPPING",
]

SHEET_FORMAT = os.path.join(
    r"C:\ProgramData\SolidWorks\SOLIDWORKS 2023\lang\english\sheetformat",
    "a3 - iso.slddrt")


def tidy_dimensions(drw):
    """Profile dims only in the profile view; length and hole dims only in
    the upright view, laid out clear of each other. Sheet metres."""
    views = []
    v = drw.GetFirstView.GetNextView          # first "view" is the sheet
    while v is not None:
        views.append(v)
        v = v.GetNextView
    profile, upright = views[0], views[1]
    ux0, uy0, ux1, uy1 = upright.GetOutline
    for view in (profile, upright):
        dd = view.GetFirstDisplayDimension5
        doomed, moves = [], []
        while dd is not None:
            dim = dd.GetDimension2(0)
            name, val = dim.FullName, dim.SystemValue * 1000
            in_profile = "Sketch1" in name
            if (view is upright) == in_profile or round(val) == 48:
                doomed.append(dd)
            elif view is upright:
                x, _, _ = dd.GetAnnotation.GetPosition
                if "Boss-Extrude1" in name:                 # overall length
                    moves.append((dd, x, uy0 - 0.030))
                elif abs(val - TAP_DRILL) < 1e-6:        # hole size
                    moves.append((dd, x + 0.015, uy1 + 0.008))
                elif abs(val - HOLE_Y) < 1e-6:              # hole height
                    moves.append((dd, ux1 + 0.008, uy0 + 0.012))
                else:                                       # hole from end
                    k = HOLES_FROM_END.index(min(
                        HOLES_FROM_END, key=lambda h: abs(h - val)))
                    moves.append((dd, x, uy0 - 0.004 - 0.0065 * k))
            dd = dd.GetNext5
        for dd, x, y in moves:
            dd.GetAnnotation.SetPosition2(x, y, 0)
        for dd in doomed:
            drw.ClearSelection2(True)
            sd = drw.SelectionManager.CreateSelectData
            dd.GetAnnotation.Select3(False, sd)
            drw.EditDelete()
    drw.ClearSelection2(True)


def scrub_pdf(path):
    """SolidWorks writes the Windows account and PC name into the PDF's
    Author / dc:creator metadata, as "pc-name, backslash, user (PC-NAME)".
    Overwrite them in place with text of the same length, so the file's
    byte offsets stay valid."""
    import getpass
    import platform
    user, host = getpass.getuser(), platform.node()
    who = "%s\\%s (%s)" % (host.lower(), user, host.upper())
    data = open(path, "rb").read()
    escaped = (who.replace("\\", "\\\\").replace("(", "\\(")
               .replace(")", "\\)"))
    for raw in (who.encode(), escaped.encode()):     # XMP, then Info dict
        data = data.replace(raw, b"dincase".ljust(len(raw)))
    open(path, "wb").write(data)
    if user.encode() in data:
        raise RuntimeError("PDF still contains the account name")


def make_drawing(sw, angle_path):
    """A3 ISO sheet, third angle, 1:1: profile (front) view, the upright
    seen from outside (left view, shows the holes), and a 1:2 isometric.
    Model dimensions are imported, plus fabrication notes. Saves SLDDRW+PDF."""
    os.makedirs(DRW_DIR, exist_ok=True)
    e, w = byref_int(), byref_int()
    part = sw.OpenDoc6(angle_path, 1, 0, "", e, w)
    props = part.Extension.CustomPropertyManager("")
    for name, val in (("Description", "RolaCase mount angle"),
                      ("Material", "Mild steel"),
                      ("PartNo", "RC-MNT-01")):
        props.Add3(name, 30, val, 2)          # text, replace if present
    part.Save3(1, e, w)

    # Close any previous copy of the drawing so it can be rewritten.
    d = sw.GetFirstDocument
    while d is not None:
        nxt = d.GetNext
        if d.GetType == 3 and "Mount_Angle" in d.GetTitle:
            sw.CloseDoc(d.GetTitle)
        d = nxt

    template = sw.GetUserPreferenceStringValue(10)  # default drawing
    drw = sw.NewDocument(template, 8, 0.42, 0.297)  # A3 landscape
    if drw is None:
        raise RuntimeError("could not create drawing from " + template)
    views = [("*Front", 0.285, 0.185, None),       # angle profile
             ("*Left", 0.135, 0.185, None),        # upright, with the holes
             ("*Isometric", 0.355, 0.245, 0.5)]
    for name, x, y, scale in views:
        v = drw.CreateDrawViewFromModelView3(angle_path, name, x, y, 0)
        if v is None:
            raise RuntimeError("view failed: " + name)
        if scale:
            v.UseSheetScale = False
            v.ScaleDecimal = scale
    drw.InsertModelAnnotations3(0, 32768, True, False, False, True)
    tidy_dimensions(drw)
    if not drw.SetupSheet5(drw.GetCurrentSheet.GetName, 8, 12, 1, 1, False,
                           SHEET_FORMAT, 0.42, 0.297, "Default", True):
        print("  (sheet format not applied: %s)" % SHEET_FORMAT)
    for i, text in enumerate(DRW_NOTES):
        note = drw.InsertNote(text)
        if note is not None:
            note.GetAnnotation.SetPosition2(0.025, 0.098 - i * 0.0065, 0)
    call(drw, "EditRebuild3")
    call(drw, "ViewZoomtofit2")
    path = os.path.join(DRW_DIR, "Mount_Angle.SLDDRW")
    if drw.SaveAs3(path, 0, 1) != 0:
        raise RuntimeError("could not save " + path)
    pdf = os.path.join(DRW_DIR, "Mount_Angle.PDF")
    if drw.SaveAs3(pdf, 0, 1) != 0:
        raise RuntimeError("PDF export failed: " + pdf)
    scrub_pdf(pdf)
    print("  drawing", path, "| pdf ok (metadata scrubbed)")
    return drw, path, pdf


# ---------------------------------------------------------------------- main
def main():
    sw = connect()
    for title in ("RolaCase_AngleMount.SLDASM", "Mount_Angle.SLDPRT",
                  "M5x12_Button.SLDPRT", "M6x12_Button.SLDPRT"):
        sw.CloseDoc(title)                    # free them to be rebuilt
    if os.path.exists(ASM_PATH):
        raise SystemExit("%s exists - delete it to rebuild." % ASM_PATH)
    print("Angle %s  Screw %s" % (ANGLE_REQ.id, SCREW_REQ.id))
    print("Rollers at Z %.2f (rear) and %.2f (front), lock screw at %.2f; "
          "axis Y %.2f; angle %.0f long, holes from end %s"
          % (REAR_Z, FRONT_Z, LOCK_Z, AXIS_Y, ANGLE_LEN,
             ", ".join("%.2f" % h for h in HOLES_FROM_END)))
    was = sw.GetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE)
    sw.SetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE, False)
    try:
        angle, angle_path = build_angle(sw)
        screw, screw_path = build_screw(sw)
    finally:
        sw.SetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE, was)

    roller_path = os.path.join(PARTS_DIR, "Track_Roller.SLDPRT")
    spacer_path = os.path.join(PARTS_DIR, "Roller_Spacer.SLDPRT")
    for p in (roller_path, spacer_path):      # must be loaded to insert
        e, w = byref_int(), byref_int()
        sw.OpenDoc6(p, 1, 0, "", e, w)

    asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
    if asm.SaveAs3(ASM_PATH, 0, 1) != 0:
        raise RuntimeError("could not save " + ASM_PATH)
    e, w = byref_int(), byref_int()
    sw.OpenDoc6(CASE_ASM, 2, 0, "", e, w)
    sw.ActivateDoc3(os.path.basename(ASM_PATH), False, 0, e)
    comps = [place(sw, asm, CASE_ASM)]

    head_face = UPRIGHT_X - SPACER_H        # roller screw head face (|x|)
    outer_face = UPRIGHT_X + ANGLE_T        # lock screw head face (|x|)
    for s in (1, -1):
        x0 = s * UPRIGHT_X
        # Left angle as modelled; right one turned end for end, so both
        # have their part Z=0 end at the back.
        comps.append(place(sw, asm, angle_path,
                           TURN_Y180 if s > 0 else IDENT,
                           (s * outer_face, -ANGLE_T,
                            ANGLE_Z0 + ANGLE_LEN if s > 0 else ANGLE_Z0)))
        inward = Y_TO_NEG_X if s > 0 else Y_TO_POS_X
        outward = Y_TO_POS_X if s > 0 else Y_TO_NEG_X
        for z in (REAR_Z, FRONT_Z):
            comps.append(place_axis(sw, asm, roller_path, inward,
                                    (x0, AXIS_Y, z),
                                    (x0, x0 - s * ROLLER_H)))
            comps.append(place_axis(sw, asm, spacer_path, inward,
                                    (x0, AXIS_Y, z),
                                    (x0, x0 - s * SPACER_H)))
            comps.append(place_axis(sw, asm, screw_path, outward,
                                    (s * head_face, AXIS_Y, z),
                                    (s * (head_face - HEAD_H),
                                     s * (head_face + SCREW_L))))
        # Locking screw: in from outside, thread against the rib.
        comps.append(place_axis(sw, asm, screw_path, inward,
                                (s * outer_face, AXIS_Y, LOCK_Z),
                                (s * (outer_face - SCREW_L),
                                 s * (outer_face + HEAD_H))))
    fix_all(asm, comps)
    call(asm, "EditRebuild3")

    for c in comps:
        b = [round(v * 1000, 2) for v in c.GetBox(False, False)]
        print("  %-26s X[%.2f, %.2f] Y[%.2f, %.2f] Z[%.2f, %.2f]"
              % (c.Name2, b[0], b[3], b[1], b[4], b[2], b[5]))
    # Screws thread into the angle's and the spacer's tap-drill holes by
    # design (the overlap is the thread engagement).
    hits = interferences(asm, ignore_pairs={("M5x12_Button", "Mount_Angle"),
                                            ("M5x12_Button", "Roller_Spacer")})
    for names, vol in hits:
        print("  INTERFERENCE", names, "%.3f mm3" % vol)
    print("Interferences (excluding screw threads in the angles):", len(hits))

    asm.ShowNamedView2("*Isometric", 7)
    call(asm, "ViewZoomtofit2")
    asm.Save3(1, byref_int(), byref_int())
    for model in (angle, screw):
        sw.CloseDoc(model.GetTitle)

    _, drw_path, pdf_path = make_drawing(sw, angle_path)
    for req, outs in ((SCREW_REQ, [screw_path]),
                      (ANGLE_REQ, [angle_path, drw_path, pdf_path])):
        print("  build record", write_build_record(req, outs).name)
    print("Done:", ASM_PATH)


if __name__ == "__main__":
    main()
