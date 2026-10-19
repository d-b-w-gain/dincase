"""
3D-printed track roller for hanging a RolaCase on a 50x50x2 angle.

Run with SolidWorks open:
    python build_roller.py

Builds two printed parts into ./parts, with real driving dimensions so you
can double-click and change them in SolidWorks afterwards:
    Track_Roller  - spins in the case's side track
    Roller_Spacer - sleeve the M5 screw clamps; the roller turns on it

Stack, from the angle up:
    angle leg (2) -> spacer (SPACER_H) -> M5 button head (4, Ø9.4)
The head sits in the roller's counterbore, below the roller top, and its
edge overhangs the roller bore slightly so the roller can't lift off.
The spacer is 0.3 mm taller than the roller's bore so the screw clamps the
spacer, not the roller - otherwise the roller couldn't turn.

Track sizes come from Cut-Extrude5 in RC001_Case_v2: channel 18.5 wide
(8 -> 26.5 mm from the base face), 10 deep.

Printing (FDM, e.g. Anycubic i3 Mega): outside diameters carry the fit, so
they are modelled at their working size, with a small chamfer on the bed
edge so first-layer squish ("elephant's foot") doesn't make them oversize.
Holes are modelled at standard drill sizes: they print slightly small, then
get drilled out to size, so their final size doesn't depend on the printer.
    roller bore   8.0 drill  -> runs on the 7.6 spacer (0.4 printed running fit)
    spacer bore   4.2 drill  -> M5 tap drill: tap it M5 (the spacer then
                                screws onto the bolt), or drill 5.0-5.5 for
                                a clearance fit
    counterbore  11.0 drill  -> screw head
The 8.0 bore leaves the Ø9.4 screw head 0.7 mm a side of roller to sit over,
so the roller can't come off past the head.
Print both parts flat, bottom face down, no supports.
"""
import pythoncom
from win32com.client import VARIANT

import os

from partnum import load_requirements, write_build_record

from swkit import (
    HERE, m, call, connect, new_part, base_planes, start_sketch, extrude,
    offset_plane, colour, save_and_keep, relink,
)

# Assemblies that use these parts - re-linked after a rebuild.
USED_IN = [os.path.join(HERE, "RolaCase_AngleMount.SLDASM")]

# ------------------------------------------------------------ requirements
# All build inputs live in the requirement files; their hash is the part
# number (see the partnum package). Nothing below is a free choice.
ROLLER_REQ = load_requirements(os.path.join(HERE, "specs", "track-roller.yaml"))
SPACER_REQ = load_requirements(os.path.join(HERE, "specs", "roller-spacer.yaml"))
SCREW_REQ = ROLLER_REQ.use("screw")
if SPACER_REQ.use("roller").id != ROLLER_REQ.id:
    raise SystemExit("roller-spacer.yaml uses a different roller")

TRACK_W = ROLLER_REQ["track_w_mm"]
TRACK_DEPTH = ROLLER_REQ["track_depth_mm"]
SIDE_CLEAR = ROLLER_REQ["side_clear_mm"]
TOP_CLEAR = ROLLER_REQ["top_clear_mm"]
BORE_D = ROLLER_REQ["bore_d_mm"]
CBORE_D = ROLLER_REQ["cbore_d_mm"]
SPIN_GAP = ROLLER_REQ["spin_gap_mm"]
HEAD_BELOW_TOP = ROLLER_REQ["head_below_top_mm"]
BED_CHAMFER = ROLLER_REQ["bed_chamfer_mm"]
HEAD_D = SCREW_REQ["head_d_mm"]
HEAD_H = SCREW_REQ["head_h_mm"]
THREAD_D = SCREW_REQ["thread_d_mm"]
RUNNING_FIT = SPACER_REQ["running_fit_mm"]
SCREW_CLEAR_D = SPACER_REQ["bore_d_mm"]
SPACER_CHAMFER = SPACER_REQ["bed_chamfer_mm"]

ORANGE = tuple(ROLLER_REQ.get("appearance", {}).get("colour", (0.95, 0.55, 0.1)))
GREY = tuple(SPACER_REQ.get("appearance", {}).get("colour", (0.6, 0.6, 0.6)))

STL_DIR = os.path.join(HERE, "stl")

# ------------------------------------------------------------------- derived
ROLLER_D = TRACK_W - 2 * SIDE_CLEAR
ROLLER_H = TRACK_DEPTH - TOP_CLEAR
SPACER_OD = BORE_D - RUNNING_FIT
# Screw head sits in the counterbore, just below the roller top.
BORE_LEN = ROLLER_H - HEAD_H - SPIN_GAP - HEAD_BELOW_TOP
SPACER_H = BORE_LEN + SPIN_GAP
CBORE_DEPTH = ROLLER_H - BORE_LEN

assert (HEAD_D - BORE_D) / 2 >= 0.6, "screw head barely overlaps the roller"
assert (SPACER_OD - THREAD_D) / 2 >= 1.2, "spacer wall too thin round the thread"
assert CBORE_D < ROLLER_D - 3, "roller wall too thin round the counterbore"
assert SPACER_H + HEAD_H < ROLLER_H, "screw head sticks out of the roller"

SW_INPUT_DIM_ON_CREATE = 10


# ------------------------------------------------------------------- helpers
NUL = VARIANT(pythoncom.VT_DISPATCH, None)


def circle(model, d, label_x):
    """Circle on the origin with a driving diameter dimension."""
    seg = model.SketchManager.CreateCircleByRadius(0, 0, 0, m(d / 2))
    # Fix the centre to the origin.
    model.ClearSelection2(True)
    seg.GetCenterPoint2.Select4(False, NUL)
    model.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT",
                                0, 0, 0, True, 0, NUL, 0)
    model.SketchAddConstraints("sgCOINCIDENT")
    # Diameter dimension.
    model.ClearSelection2(True)
    seg.Select4(False, NUL)
    model.AddDimension2(m(label_x), m(label_x), 0)
    model.ClearSelection2(True)
    return seg


def cut_mid(model, depth):
    model.SketchManager.InsertSketch(True)
    sk = model.FeatureByPositionReverse(0)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    f = model.FeatureManager.FeatureCut4(
        True, False, False, 6, 0, m(depth), 0,
        False, False, False, False, 0, 0, False, False, False, False,
        False, True, True, True, True, False, 0, 0, False, False)
    if f is None:
        raise RuntimeError("Cut failed")
    model.ClearSelection2(True)


def chamfer_bottom_edge(model, d, size=None):
    """45 deg chamfer on the circular edge of diameter d at Y = 0."""
    body = model.GetBodies2(0, False)[0]
    ge = body.GetEdges
    picked = 0
    model.ClearSelection2(True)
    for e in (ge() if callable(ge) else ge):
        c = e.GetCurve
        if not c.IsCircle:
            continue
        cp = c.CircleParams            # centre xyz, axis xyz, radius
        if abs(cp[1]) < 1e-6 and abs(cp[6] * 2000 - d) < 1e-3:
            e.Select4(True, NUL)
            picked += 1
    if picked != 1:
        raise RuntimeError("bottom edge not found (%d)" % picked)
    f = model.FeatureManager.InsertFeatureChamfer(
        4, 1, m(size or BED_CHAMFER), 0.785398, 0, 0, 0, 0)  # angle-distance
    model.ClearSelection2(True)
    if f is None:
        raise RuntimeError("chamfer failed")


def sketch_status(model):
    sk = model.SketchManager.ActiveSketch
    return {1: "under defined", 2: "under defined", 3: "fully defined",
            4: "over defined"}.get(sk.GetConstrainedStatus, "?")


# ---------------------------------------------------------------------- parts
def build_roller(sw):
    model = new_part(sw)
    model.SketchManager.AddToDB = False   # keep relations usable
    front, top, right = base_planes(model)

    start_sketch(model, top)
    circle(model, ROLLER_D, ROLLER_D * 0.7)
    circle(model, BORE_D, BORE_D * 0.4)
    print("  roller sketch:", sketch_status(model))
    extrude(model, ROLLER_H)

    # Counterbore for the screw head, down from the top face (midplane cut
    # centred on the top face so the direction can't go wrong).
    start_sketch(model, offset_plane(model, top, ROLLER_H))
    circle(model, CBORE_D, CBORE_D * 0.5)
    cut_mid(model, 2 * CBORE_DEPTH)
    chamfer_bottom_edge(model, ROLLER_D)

    colour(model, ORANGE)
    return model, save_and_keep(sw, model, "Track_Roller")


def build_spacer(sw):
    model = new_part(sw)
    model.SketchManager.AddToDB = False
    front, top, right = base_planes(model)
    start_sketch(model, top)
    circle(model, SPACER_OD, SPACER_OD * 0.7)
    circle(model, SCREW_CLEAR_D, SCREW_CLEAR_D * 0.4)
    print("  spacer sketch:", sketch_status(model))
    extrude(model, SPACER_H)
    chamfer_bottom_edge(model, SPACER_OD, SPACER_CHAMFER)
    colour(model, GREY)
    return model, save_and_keep(sw, model, "Roller_Spacer")


def export_stl(sw, name):
    """Binary STL in mm. The part is brought to the front first: saving
    through a document that isn't active can export whatever is."""
    os.makedirs(STL_DIR, exist_ok=True)
    e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.ActivateDoc3(name + ".SLDPRT", False, 0, e)
    if doc is None or doc.GetTitle != name + ".SLDPRT":
        raise RuntimeError("could not activate " + name)
    path = os.path.join(STL_DIR, name + ".STL")
    if doc.SaveAs3(path, 0, 1) != 0:
        raise RuntimeError("STL export failed: " + path)
    return path


def main():
    print("Roller %s  Spacer %s  (screw %s)"
          % (ROLLER_REQ.id, SPACER_REQ.id, SCREW_REQ.id))
    sw = connect()
    for a in USED_IN:                     # free the files to be rewritten
        sw.CloseDoc(os.path.basename(a))
    for t in ("Track_Roller.SLDPRT", "Roller_Spacer.SLDPRT"):
        sw.CloseDoc(t)
    was = sw.GetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE)
    sw.SetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE, False)
    try:
        print("Roller  Ø%.1f x %.1f, bore Ø%.1f x %.1f, counterbore Ø%.1f x %.1f"
              % (ROLLER_D, ROLLER_H, BORE_D, BORE_LEN, CBORE_D, CBORE_DEPTH))
        print("Spacer  Ø%.1f / Ø%.1f x %.1f" % (SPACER_OD, SCREW_CLEAR_D,
                                               SPACER_H))
        print("Head top at %.1f, roller top at %.1f, channel depth %.1f"
              % (SPACER_H + HEAD_H, ROLLER_H, TRACK_DEPTH))
        (_, roller_part), (_, spacer_part) = built =             [build_roller(sw), build_spacer(sw)]
    finally:
        sw.SetUserPreferenceToggle(SW_INPUT_DIM_ON_CREATE, was)
    roller_stl = export_stl(sw, "Track_Roller")
    spacer_stl = export_stl(sw, "Roller_Spacer")
    for req, outs in ((ROLLER_REQ, [roller_part, roller_stl]),
                      (SPACER_REQ, [spacer_part, spacer_stl])):
        print("  build record", write_build_record(req, outs).name)
    for a in USED_IN:
        relink(sw, a, {"Track_Roller", "Roller_Spacer"})
    return sw, built


if __name__ == "__main__":
    main()
