"""
RolaCase as an assembly: base, lid, steel hinge rod, folding handle and two
side latches - all driven by the master case part.

Run with SolidWorks open and the master saved:
    python build_case_assembly.py

Master: parts/RC001_Case_v2.SLDPRT (your outer shape + side tracks).
Base and lid are DERIVED parts of the master (Insert > Part), so if you
change the master's size or tracks and rebuild, both follow.

Builds into ./parts:
    RC_Base        - lower tray: tracks, hinge knuckles, handle bosses,
                     latch recesses + pivot holes
    RC_Lid         - upper tray: hinge knuckles, latch catch slots
    RC_HingeRod    - steel rod through the interleaved knuckles
    RC_Handle      - black folding U handle, pivots in the base bosses
    RC_Latch_R/_L  - black side latches, pivot on the base, hook into lid
and assembles them in RolaCase_Assembly.SLDASM (all parts are modelled in
the master's coordinates, so they go in at the origin).

Read from photos (product shots + your IMG_4727-4731), ESTIMATED:
lid depth, wall thickness, hinge knuckle size/count, handle and latch
sizes. All in the PARAMETERS block.

Master axes: X across (left/right), Y up from the base bottom, Z
front (+, handle) / back (-, hinge).
"""
import os
import pythoncom
from win32com.client import VARIANT

from swkit import (
    PARTS_DIR, HERE, NUL, Kit, call, connect, new_part, colour,
    save_and_keep, place, fix_all, interferences, relink,
)

# ----------------------------------------------------------------- PARAMETERS
MASTER = os.path.join(PARTS_DIR, "RC001_Case_v2.SLDPRT")
ASM_PATH = os.path.join(HERE, "RolaCase_Assembly.SLDASM")
# Assemblies that use this one - re-linked after a rebuild.
USED_IN = [os.path.join(HERE, "RolaCase_AngleMount.SLDASM"),
           os.path.join(HERE, "Dincase_Shelf.SLDASM")]

LID_H = 25.0            # lid tray depth (photos: 23-27 of 85)
WALL = 2.5              # moulded wall / floor thickness

# Moulding draft (estimated from IMG_4732 / IMG_4736 - measure to confirm:
# width across the lid, across the base just under the seam, and across the
# base bottom edge). The lid is the widest part (the master's W x D); the
# base is set in by LID_STEP at the seam and tapers in towards its bottom;
# the lid tapers in towards its top. Tracks and pockets keep their master
# positions, so roller and angle positions don't change.
BASE_DRAFT_DEG = 2.0
LID_DRAFT_DEG = 2.0
LID_STEP = 1.5          # lid outside beyond base outside at the seam, a side
TRACK_TOP = 30.0        # below this the side walls step in round the tracks
TRACK_DEPTH = 10.0      # side track depth (Cut-Extrude5)

# Hinge (back edge, on the seam)
KNUCKLE_R = 5.0
KNUCKLE_COUNT = 5       # odd: base gets the two ends + middle
KNUCKLE_MARGIN = 14.0   # from each side face to the end knuckles
KNUCKLE_GAP = 0.5
ROD_D = 3.0
ROD_HOLE_BASE = 3.0     # press fit in the base knuckles
ROD_HOLE_LID = 3.3      # lid turns on the rod

# Handle (front face of the base, folds down flat)
HANDLE_INNER = 120.0    # between the legs
HANDLE_T = 10.0         # bar section
HANDLE_DROP = 45.0      # pivot centre to bottom of grip
HANDLE_GAP = 1.0        # folded handle to front face
BOSS_W = 14.0
BOSS_H = 16.0
PIN_D = 5.0
PIN_CLEAR = 0.4

# Latches (each side, near the front, straddling the seam)
LATCH_FROM_FRONT = 35.0  # front face to latch centre
LATCH_W = 30.0
LATCH_BELOW = 20.0      # latch plate below the seam
LATCH_ABOVE = 7.0       # latch plate above the seam (into the lid)
LATCH_T = 5.0
RECESS_DEPTH = 6.0
HOOK_DEPTH = 3.0        # hook tip reaches this far past the recess floor
LATCH_PIN_D = 4.0
LATCH_PIN_DROP = 14.0   # seam to pivot

ORANGE = (0.95, 0.40, 0.10)
BLACK = (0.08, 0.08, 0.08)
STEEL = (0.70, 0.70, 0.72)

def master_size(sw):
    errs = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warns = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.OpenDoc6(MASTER, 1, 1, "", errs, warns)
    if doc.GetSaveFlag:
        raise SystemExit("Save RC001_Case_v2 first - the base and lid are "
                         "derived from the file on disk.")
    b = [v * 1000 for v in doc.GetPartBox(True)]
    w, h, d = round(b[3] - b[0]), round(b[4] - b[1]), round(b[5] - b[2])
    return w, h, d


def derived(sw):
    """New part holding the master body, trimmed to the lid or base half."""
    model = new_part(sw)
    model.SketchManager.AddToDB = True
    feat = model.InsertPart3(MASTER, 1, "")   # 1 = import solid bodies
    if feat is None:
        raise RuntimeError("Insert Part (derived master) failed")
    return model, Kit(sw, model)


# ---------------------------------------------------------------- the parts
def knuckle_ranges(W):
    span = W - 2 * KNUCKLE_MARGIN
    seg = span / KNUCKLE_COUNT
    x0 = -span / 2
    return [(x0 + i * seg, x0 + (i + 1) * seg) for i in range(KNUCKLE_COUNT)]


def hinge(k, W, D, seam, mine, hole_d):
    """Knuckles along the back edge. mine = indices this part keeps."""
    axis = (0, seam, -D / 2 + KNUCKLE_R)
    k.sketch(k.right)
    k.circle(axis, 2 * KNUCKLE_R)
    k.boss(W - 2 * KNUCKLE_MARGIN)
    # Clear out the other part's knuckle zones (plus running gap).
    k.sketch(k.yplane(seam))
    zb = (-D / 2 - 1, -D / 2 + 2 * KNUCKLE_R + 1)
    for i, (a, b) in enumerate(knuckle_ranges(W)):
        if i not in mine:
            k.box("y", a - KNUCKLE_GAP, b + KNUCKLE_GAP, zb[0], zb[1], seam)
    k.cut(2 * KNUCKLE_R + 2)
    k.sketch(k.right)
    k.circle(axis, hole_d)
    k.cut(W + 20)


def latch_zone(W, D):
    xs = W / 2
    zc = D / 2 - LATCH_FROM_FRONT
    return xs, zc


def draft_walls(k, W, D, y_lo, y_hi, inset_at, angle_deg):
    """Trim all four outside walls between y_lo and y_hi so they slope:
    the wall sits `inset_at(y)` in from the master envelope, linear in y.
    Done as wedge cuts through the part, so features cut by the master
    (tracks, pockets) stay exactly where they are."""
    import math
    t = math.tan(math.radians(angle_deg))
    a, b = inset_at(y_lo, t), inset_at(y_hi, t)
    k.sketch(k.front)                                   # +/-X walls
    for s in (-1, 1):
        k.poly([(s * (W / 2 - a), y_lo, 0), (s * (W / 2 + 2), y_lo, 0),
                (s * (W / 2 + 2), y_hi, 0), (s * (W / 2 - b), y_hi, 0)])
    k.cut(D + 40)
    k.sketch(k.right)                                   # +/-Z walls
    for s in (-1, 1):
        k.poly([(0, y_lo, s * (D / 2 - a)), (0, y_lo, s * (D / 2 + 2)),
                (0, y_hi, s * (D / 2 + 2)), (0, y_hi, s * (D / 2 - b))])
    k.cut(W + 40)


def build_base(sw, W, H, D):
    seam = H - LID_H
    model, k = derived(sw)
    xs, zc = latch_zone(W, D)

    # Keep only below the seam.
    k.sketch(k.yplane(seam + 50))
    k.box("y", -W, W, -D, D, seam + 50)
    k.cut(100)

    # Draft: set in by LID_STEP at the seam, more towards the bottom.
    draft_walls(k, W, D, -1, seam,
                lambda y, t: LID_STEP + (seam - y) * t, BASE_DRAFT_DEG)

    # Hollow: narrow round the tracks, wider above them.
    k.sketch(k.yplane((WALL + TRACK_TOP) / 2))
    i = W / 2 - TRACK_DEPTH - WALL
    k.box("y", -i, i, -D / 2 + WALL, D / 2 - WALL, 0)
    k.cut(TRACK_TOP - WALL)
    k.sketch(k.yplane((TRACK_TOP + seam) / 2 + 1))
    k.box("y", -W / 2 + WALL, W / 2 - WALL, -D / 2 + WALL, D / 2 - WALL, 0)
    k.cut(seam - TRACK_TOP + 2)

    # Backing blocks behind the latch recesses.
    k.sketch(k.yplane((TRACK_TOP + seam) / 2))
    for s in (-1, 1):
        k.box("y", s * (xs - WALL - 10.5), s * (xs - WALL), zc - 20, zc + 20,
              0)
    k.boss(seam - TRACK_TOP)

    # Latch recesses + pivot holes.
    k.sketch(k.yplane(seam - (LATCH_BELOW + 2) / 2))
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH), s * (xs + 1),
              zc - LATCH_W / 2 - 2, zc + LATCH_W / 2 + 2, 0)
    k.cut(LATCH_BELOW + 2)
    k.sketch(k.right)
    k.circle((0, seam - LATCH_PIN_DROP, zc), LATCH_PIN_D + 0.2)
    k.cut(W + 20)

    # Handle bosses on the front face, with the pivot hole.
    py, pz = handle_pivot(H, D)
    k.sketch(k.zplane(pz))
    for s in (-1, 1):
        a = HANDLE_INNER / 2 + HANDLE_T + 0.5
        k.box("z", s * a, s * (a + BOSS_W), py - BOSS_H / 2, py + BOSS_H / 2,
              0)
    k.boss(2 * (pz - D / 2))
    # Fill the gap the draft leaves between the bosses and the front wall.
    k.sketch(k.zplane(D / 2 - 3))
    for s in (-1, 1):
        a = HANDLE_INNER / 2 + HANDLE_T + 0.5
        k.box("z", s * a, s * (a + BOSS_W), py - BOSS_H / 2, py + BOSS_H / 2,
              0)
    k.boss(6)
    k.sketch(k.right)
    k.circle((0, py, pz), PIN_D + PIN_CLEAR)
    k.cut(W + 20)

    hinge(k, W, D, seam, mine={0, 2, 4}, hole_d=ROD_HOLE_BASE)
    colour(model, ORANGE)
    return model, save_and_keep(sw, model, "RC_Base")


def build_lid(sw, W, H, D):
    seam = H - LID_H
    model, k = derived(sw)
    xs, zc = latch_zone(W, D)

    k.sketch(k.yplane(seam - 50))
    k.box("y", -W, W, -D, D, seam - 50)
    k.cut(100)

    # Draft: full size at the seam, tapering in towards the top.
    draft_walls(k, W, D, seam, H + 1,
                lambda y, t: (y - seam) * t, LID_DRAFT_DEG)

    # Hollow, open to the seam.
    top = H - WALL
    k.sketch(k.yplane((seam + top) / 2 - 1))
    k.box("y", -W / 2 + WALL, W / 2 - WALL, -D / 2 + WALL, D / 2 - WALL, 0)
    k.cut(top - seam + 2)

    # Backing blocks, then the catch recess and the hook slot.
    k.sketch(k.yplane(seam + 6))
    for s in (-1, 1):
        k.box("y", s * (xs - WALL - 10.5), s * (xs - WALL), zc - 20, zc + 20,
              0)
    k.boss(12)
    k.sketch(k.yplane(seam + (LATCH_ABOVE + 1) / 2))
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH), s * (xs + 1),
              zc - LATCH_W / 2 - 2, zc + LATCH_W / 2 + 2, 0)
    k.cut(LATCH_ABOVE + 1)
    k.sketch(k.yplane(seam + 5.5))
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH - HOOK_DEPTH),
              s * (xs - RECESS_DEPTH + 0.5),
              zc - LATCH_W / 2 + 1, zc + LATCH_W / 2 - 1, 0)
    k.cut(3)

    hinge(k, W, D, seam, mine={1, 3}, hole_d=ROD_HOLE_LID)
    colour(model, ORANGE)
    return model, save_and_keep(sw, model, "RC_Lid")


def build_rod(sw, W, H, D):
    seam = H - LID_H
    model = new_part(sw)
    k = Kit(sw, model)
    k.sketch(k.right)
    k.circle((0, seam, -D / 2 + KNUCKLE_R), ROD_D)
    k.boss(W - 1)
    colour(model, STEEL)
    return model, save_and_keep(sw, model, "RC_HingeRod")


def handle_pivot(H, D):
    py = H - LID_H - 10
    pz = D / 2 + HANDLE_GAP + HANDLE_T / 2
    return py, pz


def build_handle(sw, W, H, D):
    model = new_part(sw)
    k = Kit(sw, model)
    py, pz = handle_pivot(H, D)
    a, b = HANDLE_INNER / 2, HANDLE_INNER / 2 + HANDLE_T
    bot = py - HANDLE_DROP
    top = py + HANDLE_T / 2
    k.sketch(k.zplane(pz))
    k.poly([(-b, bot, pz), (b, bot, pz), (b, top, pz), (a, top, pz),
            (a, bot + HANDLE_T, pz), (-a, bot + HANDLE_T, pz),
            (-a, top, pz), (-b, top, pz)])
    k.boss(HANDLE_T)
    for s in (-1, 1):            # pivot pins into the bosses
        k.sketch(k.xplane(s * (b + (BOSS_W + 0.5) / 2)))
        k.circle((s * (b + BOSS_W / 2), py, pz), PIN_D)
        k.boss(BOSS_W + 0.5)
    colour(model, BLACK)
    return model, save_and_keep(sw, model, "RC_Handle")


def build_latch(sw, W, H, D, side):
    seam = H - LID_H
    xs, zc = latch_zone(W, D)
    s = side
    model = new_part(sw)
    k = Kit(sw, model)
    floor = xs - RECESS_DEPTH                 # recess floor (|x|)
    # Plate in the recess.
    k.sketch(k.xplane(s * (floor + 0.5 + LATCH_T / 2)))
    k.box("x", seam - LATCH_BELOW, seam + LATCH_ABOVE - 0.5,
          zc - LATCH_W / 2, zc + LATCH_W / 2, 0)
    k.boss(LATCH_T)
    # Grip ribs (two raised bars on the outside face).
    k.sketch(k.xplane(s * (floor + 0.5 + LATCH_T)))
    for y in (seam - LATCH_BELOW + 3, seam - LATCH_BELOW + 7):
        k.box("x", y, y + 2, zc - LATCH_W / 2 + 4, zc + LATCH_W / 2 - 4, 0)
    k.boss(1.0)
    # Hook tip into the lid slot.
    k.sketch(k.xplane(s * (floor + 0.5 - HOOK_DEPTH / 2)))
    k.box("x", seam + 4.5, seam + 6.5, zc - LATCH_W / 2 + 2,
          zc + LATCH_W / 2 - 2, 0)
    k.boss(HOOK_DEPTH)
    # Pivot pin into the base.
    k.sketch(k.xplane(s * (floor + 0.5 - 2.5)))
    k.circle((s * floor, seam - LATCH_PIN_DROP, zc), LATCH_PIN_D)
    k.boss(5.0)
    colour(model, BLACK)
    return model, save_and_keep(sw, model,
                                "RC_Latch_" + ("R" if side > 0 else "L"))


# ------------------------------------------------------------------ assembly
def main():
    sw = connect()
    for a in USED_IN:                     # free the files to be rewritten
        sw.CloseDoc(os.path.basename(a))
    if os.path.exists(ASM_PATH):
        raise SystemExit("%s exists - delete it to rebuild."
                         % os.path.basename(ASM_PATH))
    W, H, D = master_size(sw)
    print("Master %d W x %d H x %d D, seam at %.1f" % (W, H, D, H - LID_H))

    built = []
    for name, fn in [("base", build_base), ("lid", build_lid),
                     ("rod", build_rod), ("handle", build_handle)]:
        print("Building", name)
        built.append(fn(sw, W, H, D))
    for side in (1, -1):
        print("Building latch", side)
        built.append(build_latch(sw, W, H, D, side))

    asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
    if asm.SaveAs3(ASM_PATH, 0, 1) != 0:
        raise RuntimeError("could not save assembly")
    comps = [place(sw, asm, path) for _, path in built]
    fix_all(asm, comps)
    call(asm, "EditRebuild3")
    hits = interferences(asm)
    for names, vol in hits:
        print("  INTERFERENCE", names, "%.2f mm3" % vol)
    print("Interferences:", len(hits))

    asm.ShowNamedView2("*Isometric", 7)
    call(asm, "ViewZoomtofit2")
    e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    asm.Save3(1, e, VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0))
    for model, _ in built:
        sw.CloseDoc(model.GetTitle)
    sw.ActivateDoc3(os.path.basename(ASM_PATH), False, 0, e)
    for a in USED_IN:
        relink(sw, a, {"RolaCase_Assembly"})
    print("Done:", ASM_PATH)


if __name__ == "__main__":
    main()
