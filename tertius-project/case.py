"""
RolaCase as an assembly: base, lid, steel hinge rod, folding handle and two
side latches. Build123D port of build_case_assembly.py.

    RC_Base        - lower tray: tracks, hinge knuckles, handle bosses,
                     latch recesses + pivot holes
    RC_Lid         - upper tray: hinge knuckles, latch catch slots
    RC_HingeRod    - steel rod through the interleaved knuckles
    RC_Handle      - black folding U handle, pivots in the base bosses
    RC_Latch_R/_L  - black side latches, pivot on the base, hook into lid

The SolidWorks base and lid were derived from a hand-modelled master,
parts/RC001_Case_v2.SLDPRT. Its outside is taken here as a plain
W x H x D box (sizes below); its side tracks don't matter, as the base
fills them and re-cuts them from the drafted wall.

Read from photos (product shots + IMG_4727-4731), ESTIMATED: lid depth,
wall thickness, hinge knuckle size/count, handle and latch sizes.

A simplified envelope with the side track geometry, modelled from
measurements for designing mounts - not the manufacturer's design.

Axes: X across (left/right), Y up from the base bottom, Z front (+,
handle) / back (-, hinge).
"""
import math

import build123d as bd

from kit import Kit, drafted_rect, finish

# ----------------------------------------------------------------- PARAMETERS
# Master envelope. W and D are the mounts' case_w_mm and the track
# positions (rear pocket from -184); H from the photos (lid 23-27 of 85).
W, H, D = 368, 85, 368

LID_H = 25.0            # lid tray depth (photos: 23-27 of 85)
WALL = 2.5              # moulded wall / floor thickness

# Moulding draft (estimated from IMG_4732 / IMG_4736 - measure to confirm).
# The lid is the widest part (the master's W x D); the base is set in by
# LID_STEP at the seam and tapers in towards its bottom; the lid tapers in
# towards its top. Tracks and pockets keep their master positions.
BASE_DRAFT_DEG = 2.0
LID_DRAFT_DEG = 2.0
LID_STEP = 1.5          # lid outside beyond base outside at the seam, a side
TRACK_TOP = 30.0        # below this the side walls step in round the tracks
TRACK_DEPTH = 10.0      # side track depth, from the local wall
TRACK_MID_Y = 17.25     # track depth is set from the wall at this height
# Side lock track regions (y up from the case bottom, z measured forward
# from the case's back face), cut into the drafted wall so the depth and
# the full 2.5 mm lips are kept. The master's small R1 edge fillets are
# not reproduced.
TRACK_OUTLINES = [
    # Recess under the lips, the front pocket and its lip-free entry slot,
    # as one outline: the front pocket's lip (y 5.5-8, z 132.5-230) is the
    # notch it goes round.
    [(0.0, 2.5), (0.0, 230.0), (5.5, 230.0), (5.5, 132.5), (8.0, 132.5),
     (8.0, 230.0), (26.5, 230.0), (26.5, 112.5), (5.5, 112.5), (5.5, 2.5)],
    # Rear pocket, open at the back of the case.
    [(8.0, -1.0), (8.0, 110.0), (26.5, 110.0), (26.5, -1.0)],
]
SEAM = H - LID_H

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


def master():
    """The master's outside: W x H x D, base bottom on Y = 0."""
    return bd.Pos(0, H / 2, 0) * bd.Box(W, H, D)


# ---------------------------------------------------------------- the parts
def knuckle_ranges():
    span = W - 2 * KNUCKLE_MARGIN
    seg = span / KNUCKLE_COUNT
    x0 = -span / 2
    return [(x0 + i * seg, x0 + (i + 1) * seg) for i in range(KNUCKLE_COUNT)]


def hinge(k, mine, hole_d):
    """Knuckles along the back edge. mine = indices this part keeps."""
    axis = (0, SEAM, -D / 2 + KNUCKLE_R)
    k.sketch("x", 0)
    k.circle(axis, 2 * KNUCKLE_R)
    k.boss(W - 2 * KNUCKLE_MARGIN)
    # Clear out the other part's knuckle zones (plus running gap).
    k.sketch("y", SEAM)
    zb = (-D / 2 - 1, -D / 2 + 2 * KNUCKLE_R + 1)
    for i, (a, b) in enumerate(knuckle_ranges()):
        if i not in mine:
            k.box("y", a - KNUCKLE_GAP, b + KNUCKLE_GAP, zb[0], zb[1], SEAM)
    k.cut(2 * KNUCKLE_R + 2)
    k.sketch("x", 0)
    k.circle(axis, hole_d)
    k.cut(W + 20)


def base_inset(y):
    """How far the drafted base's outside wall sits in from the master
    envelope (the lid's size) at height y."""
    return LID_STEP + (SEAM - y) * math.tan(math.radians(BASE_DRAFT_DEG))


def latch_zone():
    """Latch centre z, and xs: the local outside wall at the latch, which
    the recesses and the latch are seated relative to."""
    xs = W / 2 - base_inset(SEAM - LATCH_BELOW / 2)
    zc = D / 2 - LATCH_FROM_FRONT
    return xs, zc


def drafted_pocket(k, y, half_x, half_z, depth, way, angle_deg):
    """Moulded cavity: rectangle at height y, cut `depth` down or up,
    getting narrower with depth by `angle_deg` on every wall."""
    k.part -= drafted_rect(half_x, half_z, depth,
                           "-y" if way == "down" else "+y", angle_deg,
                           (0, y, 0))


def draft_walls(k, y_lo, y_hi, inset_at, angle_deg):
    """Trim all four outside walls between y_lo and y_hi so they slope:
    the wall sits `inset_at(y)` in from the master envelope, linear in y.
    Done as wedge cuts through the part, so features cut by the master
    (tracks, pockets) stay exactly where they are."""
    t = math.tan(math.radians(angle_deg))
    a, b = inset_at(y_lo, t), inset_at(y_hi, t)
    k.sketch("z", 0)                                    # +/-X walls
    for s in (-1, 1):
        k.poly([(s * (W / 2 - a), y_lo, 0), (s * (W / 2 + 2), y_lo, 0),
                (s * (W / 2 + 2), y_hi, 0), (s * (W / 2 - b), y_hi, 0)])
    k.cut(D + 40)
    k.sketch("x", 0)                                    # +/-Z walls
    for s in (-1, 1):
        k.poly([(0, y_lo, s * (D / 2 - a)), (0, y_lo, s * (D / 2 + 2)),
                (0, y_hi, s * (D / 2 + 2)), (0, y_hi, s * (D / 2 - b))])
    k.cut(W + 40)


def handle_pivot():
    py = H - LID_H - 10
    pz = D / 2 + HANDLE_GAP + HANDLE_T / 2
    return py, pz


def build_base():
    k = Kit(master())
    xs, zc = latch_zone()

    # Keep only below the seam.
    k.sketch("y", SEAM + 50)
    k.box("y", -W, W, -D, D, SEAM + 50)
    k.cut(100)

    # Draft: set in by LID_STEP at the seam, more towards the bottom.
    draft_walls(k, -1, SEAM, lambda y, t: LID_STEP + (SEAM - y) * t,
                BASE_DRAFT_DEG)

    # Side lock tracks, TRACK_DEPTH into the drafted wall.
    floor = W / 2 - base_inset(TRACK_MID_Y) - TRACK_DEPTH
    for sd in (-1, 1):
        k.sketch("x", sd * (floor + W / 2 + 2) / 2)
        for outline in TRACK_OUTLINES:
            k.poly([(0, y, -D / 2 + z) for y, z in outline])
        k.cut(W / 2 + 2 - floor)

    # Hollow, moulded: walls drafted parallel to the outside. Below
    # TRACK_TOP the sides step in behind the tracks.
    drafted_pocket(k, SEAM, W / 2 - LID_STEP - WALL, D / 2 - LID_STEP - WALL,
                   SEAM - TRACK_TOP, "down", BASE_DRAFT_DEG)
    k.sketch("y", (WALL + TRACK_TOP) / 2)
    zi = D / 2 - base_inset(TRACK_TOP) - WALL
    k.box("y", -(floor - WALL), floor - WALL, -zi, zi, 0)
    k.cut(TRACK_TOP - WALL)

    # Backing blocks behind the latch recesses (reach into the wall).
    k.sketch("y", (TRACK_TOP + SEAM) / 2)
    for s in (-1, 1):
        k.box("y", s * (xs - WALL - 10.5), s * xs, zc - 20, zc + 20, 0)
    k.boss(SEAM - TRACK_TOP)

    # Latch recesses, seated into the drafted wall, + pivot holes.
    k.sketch("y", SEAM - (LATCH_BELOW + 2) / 2)
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH), s * (W / 2 + 1),
              zc - LATCH_W / 2 - 2, zc + LATCH_W / 2 + 2, 0)
    k.cut(LATCH_BELOW + 2)
    k.sketch("x", 0)
    k.circle((0, SEAM - LATCH_PIN_DROP, zc), LATCH_PIN_D + 0.2)
    k.cut(W + 20)

    # Handle bosses on the front face, with the pivot hole.
    py, pz = handle_pivot()
    a = HANDLE_INNER / 2 + HANDLE_T + 0.5
    k.sketch("z", pz)
    for s in (-1, 1):
        k.box("z", s * a, s * (a + BOSS_W), py - BOSS_H / 2, py + BOSS_H / 2,
              0)
    k.boss(2 * (pz - D / 2))
    # Fill the gap the draft leaves between the bosses and the front wall.
    k.sketch("z", D / 2 - 3)
    for s in (-1, 1):
        k.box("z", s * a, s * (a + BOSS_W), py - BOSS_H / 2, py + BOSS_H / 2,
              0)
    k.boss(6)
    k.sketch("x", 0)
    k.circle((0, py, pz), PIN_D + PIN_CLEAR)
    k.cut(W + 20)

    hinge(k, mine={0, 2, 4}, hole_d=ROD_HOLE_BASE)
    return finish(k.part, "RC_Base", ORANGE)


def build_lid():
    k = Kit(master())
    xs, zc = latch_zone()

    k.sketch("y", SEAM - 50)
    k.box("y", -W, W, -D, D, SEAM - 50)
    k.cut(100)

    # Draft: full size at the seam, tapering in towards the top.
    draft_walls(k, SEAM, H + 1, lambda y, t: (y - SEAM) * t, LID_DRAFT_DEG)

    # Hollow, moulded: open to the seam, walls drafted parallel outside.
    drafted_pocket(k, SEAM, W / 2 - WALL, D / 2 - WALL, H - WALL - SEAM,
                   "up", LID_DRAFT_DEG)

    # Backing blocks (reach into the wall), then the catch recess and slot.
    k.sketch("y", SEAM + 6)
    for s in (-1, 1):
        k.box("y", s * (xs - WALL - 10.5), s * W / 2, zc - 20, zc + 20, 0)
    k.boss(12)
    k.sketch("y", SEAM + (LATCH_ABOVE + 1) / 2)
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH), s * (W / 2 + 1),
              zc - LATCH_W / 2 - 2, zc + LATCH_W / 2 + 2, 0)
    k.cut(LATCH_ABOVE + 1)
    k.sketch("y", SEAM + 5.5)
    for s in (-1, 1):
        k.box("y", s * (xs - RECESS_DEPTH - HOOK_DEPTH),
              s * (xs - RECESS_DEPTH + 0.5),
              zc - LATCH_W / 2 + 1, zc + LATCH_W / 2 - 1, 0)
    k.cut(3)

    hinge(k, mine={1, 3}, hole_d=ROD_HOLE_LID)
    return finish(k.part, "RC_Lid", ORANGE)


def build_rod():
    k = Kit()
    k.sketch("x", 0)
    k.circle((0, SEAM, -D / 2 + KNUCKLE_R), ROD_D)
    k.boss(W - 1)
    return finish(k.part, "RC_HingeRod", STEEL)


def build_handle():
    k = Kit()
    py, pz = handle_pivot()
    a, b = HANDLE_INNER / 2, HANDLE_INNER / 2 + HANDLE_T
    bot = py - HANDLE_DROP
    top = py + HANDLE_T / 2
    k.sketch("z", pz)
    k.poly([(-b, bot, pz), (b, bot, pz), (b, top, pz), (a, top, pz),
            (a, bot + HANDLE_T, pz), (-a, bot + HANDLE_T, pz),
            (-a, top, pz), (-b, top, pz)])
    k.boss(HANDLE_T)
    for s in (-1, 1):            # pivot pins into the bosses
        k.sketch("x", s * (b + (BOSS_W + 0.5) / 2))
        k.circle((s * (b + BOSS_W / 2), py, pz), PIN_D)
        k.boss(BOSS_W + 0.5)
    return finish(k.part, "RC_Handle", BLACK)


def build_latch(side):
    xs, zc = latch_zone()
    s = side
    k = Kit()
    floor = xs - RECESS_DEPTH                 # recess floor (|x|)
    # Plate in the recess.
    k.sketch("x", s * (floor + 0.5 + LATCH_T / 2))
    k.box("x", SEAM - LATCH_BELOW, SEAM + LATCH_ABOVE - 0.5,
          zc - LATCH_W / 2, zc + LATCH_W / 2, 0)
    k.boss(LATCH_T)
    # Grip ribs (two raised bars on the outside face).
    k.sketch("x", s * (floor + 0.5 + LATCH_T))
    for y in (SEAM - LATCH_BELOW + 3, SEAM - LATCH_BELOW + 7):
        k.box("x", y, y + 2, zc - LATCH_W / 2 + 4, zc + LATCH_W / 2 - 4, 0)
    k.boss(1.0)
    # Hook tip into the lid slot.
    k.sketch("x", s * (floor + 0.5 - HOOK_DEPTH / 2))
    k.box("x", SEAM + 4.5, SEAM + 6.5, zc - LATCH_W / 2 + 2,
          zc + LATCH_W / 2 - 2, 0)
    k.boss(HOOK_DEPTH)
    # Pivot pin into the base.
    k.sketch("x", s * (floor + 0.5 - 2.5))
    k.circle((s * floor, SEAM - LATCH_PIN_DROP, zc), LATCH_PIN_D)
    k.boss(5.0)
    return finish(k.part, "RC_Latch_" + ("R" if side > 0 else "L"), BLACK)


def build():
    """All the case parts, in the master's coordinates (they go in at the
    origin)."""
    return [build_base(), build_lid(), build_rod(), build_handle(),
            build_latch(1), build_latch(-1)]
