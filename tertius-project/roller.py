"""
3D-printed track roller and journal spacer for hanging a RolaCase on a
50x50x2 angle. Build123D port of build_roller.py.

    Track_Roller  - spins in the case's side track
    Roller_Spacer - sleeve the M5 screw clamps; the roller turns on it

Stack, from the angle up:
    angle leg (2) -> spacer (SPACER_H) -> M5 button head (4, dia 9.4)
The head sits in the roller's counterbore, below the roller top, and its
edge overhangs the roller bore slightly so the roller can't lift off.
The spacer is 0.3 mm taller than the roller's bore so the screw clamps the
spacer, not the roller - otherwise the roller couldn't turn.

Holes are modelled at standard drill sizes (they print slightly small and
get drilled out); outside diameters carry the fit and have a small bed
chamfer against elephant's foot. Print flat, bottom face down.

Both parts: axis +Y, bottom face on Y = 0.
"""
from kit import Kit, chamfer_circle, finish
from spec import spec

ROLLER_REQ = spec("track-roller")
SPACER_REQ = spec("roller-spacer")
SCREW_REQ = ROLLER_REQ.use("screw")
if SPACER_REQ.use("roller").id != ROLLER_REQ.id:
    raise ValueError("roller-spacer.yaml uses a different roller")

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


def counterbored_roller(d, h, bore, cbore, bore_len, chamfer):
    """Ring d x h on bore, with a counterbore down from the top to
    bore_len, and a bed chamfer on the bottom outside edge."""
    k = Kit()
    k.sketch("y", 0)
    k.circle((0, 0, 0), d)
    k.circle((0, 0, 0), bore)
    k.boss(h, midplane=False)
    k.sketch("y", h)
    k.circle((0, h, 0), cbore)
    k.cut(2 * (h - bore_len))
    return chamfer_circle(k.part, 0, d, chamfer)


def build_roller():
    part = counterbored_roller(ROLLER_D, ROLLER_H, BORE_D, CBORE_D,
                               BORE_LEN, BED_CHAMFER)
    return finish(part, "Track_Roller " + ROLLER_REQ.id, ROLLER_REQ.colour)


def build_spacer():
    k = Kit()
    k.sketch("y", 0)
    k.circle((0, 0, 0), SPACER_OD)
    k.circle((0, 0, 0), SCREW_CLEAR_D)
    k.boss(SPACER_H, midplane=False)
    part = chamfer_circle(k.part, 0, SPACER_OD, SPACER_CHAMFER)
    return finish(part, "Roller_Spacer " + SPACER_REQ.id, SPACER_REQ.colour)
