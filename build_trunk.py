"""
Enclosure reference: the stacking trunk the dincase shelf fits into, in
its natural orientation (550 x 550 footprint, 440 high, front door in a
550 x 440 face), plus a measurement drawing to check it.

Run with SolidWorks open:
    python build_trunk.py

Inputs: specs/trunk-550.yaml. Makes:
    parts/Trunk_550.SLDPRT
    drawings/Trunk_Measure.SLDDRW/.PDF - lettered dimensions with the
        model value, and a table to write the measured values in

It is blow-moulded: one wall, 3-4 mm thick, so whatever is pressed into
the outside stands into the inside by the same amount. Modelled as the
outside form, then shelled:
  - the body, drafted both ways from the mould seam (about 100 mm below
    the top), with vertical strap channels in the side walls;
  - three long studs on top, front to back, sides and ends sloped so they
    release from the mould and seat without jamming; matching sloped
    sockets underneath, which stand up inside as ridges in the floor;
  - a handle pocket in each side wall;
  - shelled to the wall thickness, then the door opening cut through the
    front and the frame header added behind its top edge.
The door itself (a separate double-wall panel) is not modelled.

Axes: X across the door, Y up, Z out of the door (front +).
"""
import math
import os
import time

from partnum import load_requirements, write_build_record

import build_mount as bm
from swkit import (HERE, NUL, Kit, byref_int, call, colour, connect, m,
                   new_part, save_and_keep)

REQ = load_requirements(os.path.join(HERE, "specs", "trunk-550.yaml"))
OW, OH, OD = REQ["outer_w_mm"], REQ["outer_h_mm"], REQ["outer_d_mm"]
WALL = REQ["wall_mm"]
SEAM = OH - REQ["seam_from_top_mm"]          # height of the mould seam
DRAFT = REQ["draft_deg"]
GW, GH = REQ["opening_w_mm"], REQ["opening_h_mm"]
C_TOP, C_BASE = REQ["clear_top_mm"], REQ["clear_base_mm"]
HDR_D = REQ["header_d_mm"]
STUD_W, STUD_L, STUD_H = (REQ["stud_w_mm"], REQ["stud_len_mm"],
                          REQ["stud_h_mm"])
PITCH = REQ["stud_pitch_mm"]
SLOPE = REQ["stud_slope_deg"]
SOCK_C, SOCK_D = REQ["socket_clear_mm"], REQ["socket_depth_mm"]
STRAP_IN, STRAP_W, STRAP_D = (REQ["strap_from_corner_mm"],
                              REQ["strap_w_mm"], REQ["strap_depth_mm"])
HW, HH, HD = REQ["handle_w_mm"], REQ["handle_h_mm"], REQ["handle_depth_mm"]
H_FROM_TOP = REQ["handle_from_top_mm"]
STUD_X = (-PITCH, 0.0, PITCH)
BLUE = tuple(REQ.get("appearance", {}).get("colour", (0.35, 0.45, 0.65)))
DRW_DIR = os.path.join(HERE, "drawings")

TAN = math.tan(math.radians(DRAFT))
ZF = OD / 2                          # front face, at the seam
RIDGE = SOCK_D + WALL                # inside floor on the socket ridges
Y_OPEN = RIDGE + C_BASE              # door opening, bottom edge
Y_HDR = Y_OPEN + GH + C_TOP          # underside of the frame header
CEIL = OH - WALL                     # inside of the top skin
YC_H = OH - H_FROM_TOP               # handle pocket centre height


def inset(y):
    """How far the drafted outside is in from the seam outline at y."""
    return abs(y - SEAM) * TAN


def inside():
    """Clear inside box over the full depth (W, H, D), and the height
    behind the frame header."""
    side = min(OW / 2 - inset(0) - STRAP_D,             # channels, bottom
               OW / 2 - HD) - WALL                      # handle pockets
    depth = OD - 2 * (inset(0) + WALL)
    return 2 * side, min(Y_HDR, CEIL) - RIDGE, depth, CEIL - RIDGE


def check():
    """Refuse inputs that don't make a buildable, stackable trunk."""
    bad = []
    if STRAP_IN - STRAP_W / 2 < 20:
        bad.append("strap channel too close to the corner")
    if HW / 2 > OD / 2 - STRAP_IN - STRAP_W / 2 - 10:
        bad.append("handle pocket runs into the strap channels")
    if STUD_W - 2 * STUD_H * math.tan(math.radians(SLOPE)) < 10:
        bad.append("studs slope to nothing")
    if SOCK_D <= STUD_H:
        bad.append("sockets shallower than the studs")
    if PITCH + STUD_W / 2 + SOCK_C > OW / 2 - inset(0) - 10:
        bad.append("outer sockets run off the drafted base")
    if STUD_L / 2 + SOCK_C > OD / 2 - inset(0) - 10:
        bad.append("sockets too long for the drafted base")
    if Y_OPEN + GH > CEIL or C_BASE < 0 or C_TOP < 0:
        bad.append("opening doesn't fit the height")
    if GW / 2 > OW / 2 - inset(0) - WALL - 5:
        bad.append("opening wider than the front")
    if YC_H + HH / 2 > OH - 10 or YC_H - HH / 2 < RIDGE + 10:
        bad.append("handle pocket runs off the side wall")
    if HD > STRAP_D + 15:
        bad.append("handle pocket deeper than the wall can take")
    if bad:
        raise ValueError("specs/trunk-550.yaml: " + "; ".join(bad))


check()


# Letter for each lettered model dimension, by dimension and feature name.
LETTER = {"D1@Sketch3": "S", "D2@Sketch3": "U", "D1@Sketch5": "Q",
          "D2@Sketch5": "P", "D3@Sketch5": "C", "D1@Sketch7": "G",
          "D2@Sketch7": "H", "D3@Sketch7": "A", "D4@Sketch7": "B"}
LETTER_VALUE = {"A": OW, "B": OH, "C": OD, "S": STUD_W, "U": STUD_L,
                "Q": HH, "P": HW, "G": GW, "H": GH}


def dim_rect(model, segs):
    """Dimension a rectangle's first (D1) and last (D2) edges."""
    for seg in (segs[0], segs[3]):
        model.ClearSelection2(True)
        seg.Select4(False, NUL)
        a, b = seg.GetStartPoint2, seg.GetEndPoint2
        model.AddDimension2((a.X + b.X) / 2 - 0.02, (a.Y + b.Y) / 2 - 0.02,
                            0)
    model.ClearSelection2(True)


def plan_pts():
    """Outline at the seam, seen from above: the footprint with the strap
    channels notched into the side walls, as (x, z) pairs."""
    w, d = OW / 2, OD / 2
    c, s, n = d - STRAP_IN, STRAP_W / 2, STRAP_D
    right = [(w, -c - s), (w - n, -c - s), (w - n, -c + s), (w, -c + s),
             (w, c - s), (w - n, c - s), (w - n, c + s), (w, c + s)]
    left = [(-x, -z) for x, z in right]
    return [(-w, -d), (w, -d)] + right + [(w, d), (-w, d)] + left


def _extrude_draft(model, depth, rev, out, angle_deg, cut):
    """One-way drafted boss or cut of the open sketch."""
    model.SketchManager.InsertSketch(True)
    sk = model.FeatureByPositionReverse(0)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    fm = model.FeatureManager
    a = math.radians(angle_deg)
    if cut:
        f = fm.FeatureCut4(True, False, rev, 0, 0, m(depth), 0, True, False,
                           out, False, a, 0, False, False, False, False,
                           False, True, True, True, True, False, 0, 0,
                           False, False)
    else:
        f = fm.FeatureExtrusion2(True, False, rev, 0, 0, m(depth), 0, True,
                                 False, out, False, a, 0, False, False,
                                 False, False, True, True, True, 0, 0, False)
    model.ClearSelection2(True)
    return f is not None


def probe_flags(sw):
    """The 'reverse' / 'draft outward' flags for drafted extrusions of a
    Top-parallel sketch, each narrowing away from the sketch: boss up,
    boss down, and cut up into the part. Learned on throwaway blocks."""
    ang, d, a = 10.0, 20.0, 60.0
    a2 = a - 2 * d * math.tan(math.radians(ang))
    frustum = d / 3 * (a * a + a2 * a2 + a * a2)

    def vol(model):
        return model.Extension.CreateMassProperty.Volume * 1e9

    found = {}
    for rev in (False, True):
        for out in (False, True):
            model = new_part(sw)
            k = Kit(sw, model)
            k.sketch(k.top)
            k.box("y", -a / 2, a / 2, -a / 2, a / 2, 0)
            if _extrude_draft(model, d, rev, out, ang, cut=False) and abs(
                    vol(model) - frustum) < 0.01 * frustum:
                up = model.GetPartBox(True)[4] * 1000 > d / 2
                found["up" if up else "down"] = (rev, out)
            sw.CloseDoc(model.GetTitle)
            model = new_part(sw)
            k = Kit(sw, model)
            k.sketch(k.yplane(50))
            k.box("y", -50, 50, -50, 50, 50)
            k.boss(100)                                   # y 0..100
            v0 = vol(model)
            k.sketch(k.top)
            k.box("y", -a / 2, a / 2, -a / 2, a / 2, 0)
            if _extrude_draft(model, d, rev, out, ang, cut=True) and abs(
                    v0 - vol(model) - frustum) < 0.01 * frustum:
                found["cut_up"] = (rev, out)
            sw.CloseDoc(model.GetTitle)
    if set(found) != {"up", "down", "cut_up"}:
        raise RuntimeError("could not find drafted-extrusion flags: %s"
                           % found)
    return found


def construction(segs):
    """Make sketch lines construction-only (they carry a dimension)."""
    for s in segs:
        s.ConstructionGeometry = True
    return segs


def build(sw, fl):
    model = new_part(sw)
    k = Kit(sw, model)
    # Body: the seam outline drafted up to the top and down to the base.
    seam = k.yplane(SEAM)
    for depth, way in ((OH - SEAM, "up"), (SEAM, "down")):
        k.sketch(seam)
        k.poly([(x, SEAM, z) for x, z in plan_pts()])
        if not _extrude_draft(model, depth, *fl[way], DRAFT, cut=False):
            raise RuntimeError("body (%s) failed" % way)
    box = [v * 1000 for v in model.GetPartBox(True)]
    if abs(box[1]) > 0.1 or abs(box[4] - OH) > 0.1:
        raise RuntimeError("body went the wrong way: Y %.1f..%.1f"
                           % (box[1], box[4]))
    # Studs on top, sloped sides and ends.
    k.sketch(k.yplane(OH))
    for i, x in enumerate(STUD_X):
        segs = k.box("y", x - STUD_W / 2, x + STUD_W / 2, -STUD_L / 2,
                     STUD_L / 2, OH)
        if i == 0:
            dim_rect(model, segs)                                   # S, U
    if not _extrude_draft(model, STUD_H, *fl["up"], SLOPE, cut=False):
        raise RuntimeError("studs failed")                          # V, W
    # Matching sockets underneath, same slope, clear all round.
    k.sketch(k.top)
    for x in STUD_X:
        k.box("y", x - STUD_W / 2 - SOCK_C, x + STUD_W / 2 + SOCK_C,
              -STUD_L / 2 - SOCK_C, STUD_L / 2 + SOCK_C, 0)
    if not _extrude_draft(model, SOCK_D, *fl["cut_up"], SLOPE, cut=True):
        raise RuntimeError("sockets failed")                        # Y
    # Handle pocket in each side wall.
    for i, sd in enumerate((1, -1)):
        k.sketch(k.xplane(sd * OW / 2))
        segs = k.box("x", YC_H - HH / 2, YC_H + HH / 2, -HW / 2, HW / 2,
                     sd * OW / 2)
        if i == 0:
            dim_rect(model, segs)                                   # Q, P
            out = construction(k.box("x", 0, OH, -OD / 2, OD / 2, OW / 2))
            model.ClearSelection2(True)
            out[3].Select4(False, NUL)
            a, b = out[3].GetStartPoint2, out[3].GetEndPoint2
            model.AddDimension2((a.X + b.X) / 2, (a.Y + b.Y) / 2 - 0.02, 0)
            model.ClearSelection2(True)                             # C
        k.cut(2 * HD)                                               # R
    # One wall: shell the whole form inwards.
    model.ClearSelection2(True)
    model.InsertFeatureShell(m(WALL), False)
    if model.FeatureByPositionReverse(0).GetTypeName2 != "Shell":
        raise RuntimeError("shell failed")
    # Door opening through the front wall.
    k.sketch(k.zplane(ZF))
    dim_rect(model, k.box("z", -GW / 2, GW / 2, Y_OPEN, Y_OPEN + GH,
                          ZF))                                      # G, H
    dim_rect(model, construction(k.box("z", -OW / 2, OW / 2, 0, OH,
                                       ZF)))                        # A, B
    k.cut(2 * (inset(0) + WALL + 5))
    # Frame header behind the top of the opening, merged into the front,
    # side and top walls.
    if Y_HDR < CEIL - 0.5:
        z1 = ZF - inset(CEIL) - 0.5          # inside the front wall
        x1 = OW / 2 - inset(CEIL) - 0.5      # inside the side walls
        z0 = ZF - HDR_D
        k.sketch(k.zplane((z0 + z1) / 2))
        k.box("z", -x1, x1, Y_HDR, CEIL + 1, (z0 + z1) / 2)
        k.boss(z1 - z0)
    # Every lettered dimension must be the one it claims to be.
    for name, letter in LETTER.items():
        d = model.Parameter(name)
        if d is None or abs(d.SystemValue * 1000 - LETTER_VALUE[letter]) > .01:
            raise RuntimeError("dimension %s is not %s" % (name, letter))
    # Hide the construction planes the sketches were drawn on.
    f = model.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "RefPlane" and f.Name not in (
                "Front Plane", "Top Plane", "Right Plane"):
            model.ClearSelection2(True)
            f.Select2(False, 0)
            model.BlankRefGeom()
        f = f.GetNextFeature
    model.ClearSelection2(True)
    colour(model, BLUE)
    props = model.Extension.CustomPropertyManager("")
    for key, val in (("Description", "Enclosure ref."),
                     ("Material", "Polyethylene (bought)")):
        props.Add3(key, 30, val, 2)
    return model, save_and_keep(sw, model, "Trunk_550")


# --------------------------------------------------------------- drawing
def letter_for(full_name):
    return LETTER.get("@".join(full_name.split("@")[:2]))


PUB, OWN, MEAS, EST = "published", "owner", "measured", "estimate"

# (letter, what to measure, model value or None, where the value came from)
MEASURE = [
    ("A", "Outside width across the door face, at the seam", OW, PUB),
    ("B", "Outside height, underside to top skin", OH, PUB),
    ("C", "Outside depth, front to back, at the seam", OD, PUB),
    ("D", "Wall thickness (at the opening edge)", WALL, OWN),
    ("E", "Top down to the mould seam line", OH - SEAM, OWN),
    ("F", "Outside width at the very bottom (draft)",
     "%.0f" % (OW - 2 * inset(0)), EST),
    ("G", "Opening width", GW, MEAS),
    ("H", "Opening height", GH, MEAS),
    ("K", "Gap behind lip: top / base (to floor ridges)",
     "%g / %g" % (C_TOP, C_BASE), MEAS),
    ("J", "Frame header behind the opening, front to back", HDR_D, EST),
    ("I", "Underside to inside floor: flat / on the ridges",
     "%g / %g" % (WALL, RIDGE), EST),
    ("L", "Door: which way it comes off, latch positions", None, None),
    ("M", "Gap behind lip at each side; anything else inside", None, None),
]

# Pressed in from outside - single wall, so they stand in as far inside.
MEASURE_OUT = [
    ("N", "Strap channels: inset / wide / deep",
     "%g / %g / %g" % (STRAP_IN, STRAP_W, STRAP_D), EST),
    ("P", "Handle pocket width, front to back", HW, EST),
    ("Q", "Handle pocket height", HH, EST),
    ("R", "Handle pocket depth", HD, EST),
    ("T", "Top to the handle pocket centre", H_FROM_TOP, EST),
    ("S", "Studs (3 off): width at the base", STUD_W, EST),
    ("U", "Stud length at the base", STUD_L, EST),
    ("V", "Stud height", STUD_H, EST),
    ("W", "Stud side and end slope, degrees", SLOPE, EST),
    ("X", "Stud spacing, centre to centre", PITCH, EST),
    ("Y", "Sockets underneath: clear all round / deep",
     "%g / %g" % (SOCK_C, SOCK_D), EST),
    ("Z", "Biggest box that fits inside, W x H x D", None, None),
]

NOTES_TOP = [
    "MEASUREMENT SHEET - write the measured value next to each letter.",
    "Blow-moulded single-wall stacking trunk, natural orientation.",
    "Values: published, owner, measured, or ESTIMATED.",
]


def measure_line(letter, text, val, src, short=False):
    if val is None:
        tag = ""
    else:
        tag = " (%s %s)" % (src[:3] if short else src,
                            val if isinstance(val, str) else "%g" % val)
    return "%s   %s%s  -  %s" % (letter, text, tag, "meas: ____" if short
                                 else "measured: ________")


def sheet_columns():
    """Note lines for the left and right columns of the drawing."""
    w, h, d, h_back = inside()
    left = NOTES_TOP + [""] + [measure_line(*r) for r in MEASURE] + [
        "",
        "MODEL INSIDE, clear over the full depth: %.0f W x %.0f H x %.0f D"
        % (w, h, d),
        "  W at the channels/pockets; H floor ridges to header (%.0f behind)"
        % h_back,
        "  in one piece through the opening: %g W x %g H at most" % (GW, GH),
        "Overall height over the studs: %g" % (OH + STUD_H),
    ]
    right = ["PRESSED IN FROM OUTSIDE (stand in as far inside):"] + [
        measure_line(*r, short=True) for r in MEASURE_OUT]
    return left, right


NEED = set("ABCGH")                  # letters the views must carry
VIEW_SCALE, VIEW_Y = 0.2, 0.215
VIEWS = (("*Front", 0.090, VIEW_Y, VIEW_SCALE),
         ("*Right", 0.215, VIEW_Y, VIEW_SCALE),
         ("*Isometric", 0.345, 0.230, 0.1))
# Where each letter's text goes: (view index, model mm across the view
# from its centre, model mm up from the underside).
SPOT = {"A": (0, 0, -60), "B": (0, -OW / 2 - 60, OH / 2),
        "G": (0, 0, Y_OPEN + 40), "H": (0, -GW / 2 + 45, Y_OPEN + GH / 2),
        "S": (0, -PITCH, OH + STUD_H + 40),
        "C": (1, 0, -60), "U": (1, 0, OH + STUD_H + 40),
        "Q": (1, HW / 2 + 55, YC_H),
        "P": (1, 0, YC_H - HH / 2 - 40)}


def spot(letter, view_index):
    """Sheet position for a letter's text, or None if it isn't placed in
    this view (a duplicate)."""
    if letter not in SPOT or SPOT[letter][0] != view_index:
        return None
    _, x0, y0, s = VIEWS[view_index]
    _, u, y = SPOT[letter]
    return x0 + u * s / 1000, y0 + (y - (OH + STUD_H) / 2) * s / 1000


def make_drawing(sw, part_path):
    os.makedirs(DRW_DIR, exist_ok=True)
    for _ in range(3):
        drw, found = _sheet(sw, part_path)
        if NEED <= found:
            break
        # Straight after a build SolidWorks sometimes inserts only the
        # plane offsets; reload the part and try again.
        sw.CloseDoc(drw.GetTitle)
        sw.CloseDoc(os.path.basename(part_path))
        time.sleep(3)
    else:
        raise RuntimeError("drawing is missing dimensions %s"
                           % "".join(sorted(NEED - found)))
    left, right = sheet_columns()
    for x, lines in ((0.025, left), (0.240, right)):
        for i, text in enumerate(lines):
            note = drw.InsertNote(text)
            if note is not None:
                note.GetAnnotation.SetPosition2(x, 0.138 - i * 0.0052, 0)
    call(drw, "EditRebuild3")
    call(drw, "ViewZoomtofit2")
    path = os.path.join(DRW_DIR, "Trunk_Measure.SLDDRW")
    if drw.SaveAs3(path, 0, 1) != 0:
        raise RuntimeError("could not save " + path)
    pdf = os.path.join(DRW_DIR, "Trunk_Measure.PDF")
    if drw.SaveAs3(pdf, 0, 1) != 0:
        raise RuntimeError("PDF export failed")
    bm.scrub_pdf(pdf)
    return path, pdf


def _sheet(sw, part_path):
    """Views with the lettered model dimensions; returns the drawing and
    the letters it carries."""
    sw.OpenDoc6(part_path, 1, 1, "", byref_int(), byref_int())
    d = sw.GetFirstDocument
    while d is not None:
        nxt = d.GetNext
        if d.GetType == 3 and "Trunk_" in d.GetTitle:
            sw.CloseDoc(d.GetTitle)
        d = nxt
    drw = sw.NewDocument(sw.GetUserPreferenceStringValue(10), 8, 0.42, 0.297)
    drw.SetupSheet5(drw.GetCurrentSheet.GetName, 8, 12, 1, 5, False,
                    bm.SHEET_FORMAT, 0.42, 0.297, "Default", True)
    for name, x, y, scale in VIEWS:
        v = drw.CreateDrawViewFromModelView3(part_path, name, x, y, 0)
        if v is None:
            raise RuntimeError("view failed: " + name)
        v.UseSheetScale = False
        v.ScaleDecimal = scale
        if name != "*Isometric":
            v.SetDisplayMode3(False, 1, False, True)   # hidden lines grey
    drw.InsertModelAnnotations3(0, 32768, True, False, False, True)
    # Prefix each dimension with its letter and move it to its spot; drop
    # anything unlettered, and repeats of a letter in a second view.
    found = set()
    v = drw.GetFirstView.GetNextView
    i = 0
    while v is not None:
        dd = v.GetFirstDisplayDimension5
        doomed = []
        while dd is not None:
            dim = dd.GetDimension2(0)
            letter = letter_for(dim.FullName)
            at = spot(letter, i) if letter else None
            if at:
                dd.SetText(1, letter + " = ")              # prefix
                dd.SetPrecision3(0, 0, 0, 0)               # whole mm
                dd.GetAnnotation.SetPosition2(at[0], at[1], 0)
                found.add(letter)
            else:
                doomed.append(dd)
            dd = dd.GetNext5
        for dd in doomed:
            drw.ClearSelection2(True)
            dd.GetAnnotation.Select3(False, drw.SelectionManager
                                     .CreateSelectData)
            drw.EditDelete()
        v = v.GetNextView
        i += 1
    drw.ClearSelection2(True)
    return drw, found


def main():
    w, h, d, h_back = inside()
    print("Stacking trunk reference %s: outer %gx%gx%g at the seam (+%g studs), "
          "wall %g; inside clear %.0f W x %.0f H (%.0f behind the header) "
          "x %.0f D (published 495 x 410 x 500); opening %gx%g"
          % (REQ.id, OW, OH, OD, STUD_H, WALL, w, h, h_back, d, GW, GH))
    sw = connect()
    d = sw.GetFirstDocument                  # close the old part / drawing
    while d is not None:
        nxt = d.GetNext
        if "Trunk_" in d.GetTitle:
            sw.CloseDoc(d.GetTitle)
        d = nxt
    was = sw.GetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE)
    sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, False)
    try:
        flags = probe_flags(sw)
        _, part = build(sw, flags)
    finally:
        sw.SetUserPreferenceToggle(bm.SW_INPUT_DIM_ON_CREATE, was)
    # Reload from disk before drawing it.
    sw.CloseDoc(os.path.basename(part))
    drw, pdf = make_drawing(sw, part)
    print("  build record", write_build_record(REQ, [part, drw, pdf]).name)


if __name__ == "__main__":
    main()
