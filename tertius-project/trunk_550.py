"""
Enclosure reference: the stacking trunk the dincase shelf fits into, in
its natural orientation (550 x 550 footprint, 440 high, front door in a
550 x 440 face). Build123D port of build_trunk.py.

It is blow-moulded: one wall, 3-4 mm thick, so whatever is pressed into
the outside stands into the inside by the same amount. Modelled as the
outside form, then shelled:
  - the body, drafted both ways from the mould seam (about 100 mm below
    the top), with vertical strap channels in the side walls;
  - three long studs on top, front to back, sides and ends sloped so they
    release from the mould and seat without jamming; matching sloped
    sockets underneath, which stand up inside as ridges in the floor;
  - a handle pocket in each side wall;
  - hollowed to the wall thickness, then the door opening cut through the
    front and the frame header added behind its top edge.
The door itself (a separate double-wall panel) is not modelled.

Axes (Build123D, Z up): X across the door, Y front to back (front -Y),
Z up. build_trunk.py had Y up and Z out of the door: SW (x, y, z) is
(x, -z, y) here. All sizes in mm.
"""
import math

import build123d as bd

from kit import finish
from spec import spec

# Inputs: specs/trunk-550.yaml (letters as on the measurement drawing).
REQ = spec("trunk-550")
OW, OH, OD = REQ["outer_w_mm"], REQ["outer_h_mm"], REQ["outer_d_mm"]  # A B C
WALL = REQ["wall_mm"]                                    # D
SEAM = OH - REQ["seam_from_top_mm"]                      # E  mould seam
DRAFT = REQ["draft_deg"]                                 # F
GW, GH = REQ["opening_w_mm"], REQ["opening_h_mm"]        # G, H  door
C_TOP, C_BASE = REQ["clear_top_mm"], REQ["clear_base_mm"]  # K
HDR_D = REQ["header_d_mm"]                               # J
STUD_W, STUD_L, STUD_H = (REQ["stud_w_mm"], REQ["stud_len_mm"],
                          REQ["stud_h_mm"])              # S, U, V
PITCH = REQ["stud_pitch_mm"]                             # X
SLOPE = REQ["stud_slope_deg"]                            # W
SOCK_C, SOCK_D = REQ["socket_clear_mm"], REQ["socket_depth_mm"]  # Y
STRAP_IN, STRAP_W, STRAP_D = (REQ["strap_from_corner_mm"],
                              REQ["strap_w_mm"], REQ["strap_depth_mm"])  # N
HW, HH, HD = (REQ["handle_w_mm"], REQ["handle_h_mm"],
              REQ["handle_depth_mm"])                    # P, Q, R
H_FROM_TOP = REQ["handle_from_top_mm"]                   # T

STUD_X = (-PITCH, 0.0, PITCH)
TAN = math.tan(math.radians(DRAFT))
YF = -OD / 2                         # front face, at the seam
RIDGE = SOCK_D + WALL                # inside floor on the socket ridges
Z_OPEN = RIDGE + C_BASE              # door opening, bottom edge
Z_HDR = Z_OPEN + GH + C_TOP          # underside of the frame header
CEIL = OH - WALL                     # inside of the top skin
ZC_H = OH - H_FROM_TOP               # handle pocket centre height


def inset(z):
    """How far the drafted outside is in from the seam outline at z."""
    return abs(z - SEAM) * TAN


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
    if Z_OPEN + GH > CEIL or C_BASE < 0 or C_TOP < 0:
        bad.append("opening doesn't fit the height")
    if GW / 2 > OW / 2 - inset(0) - WALL - 5:
        bad.append("opening wider than the front")
    if ZC_H + HH / 2 > OH - 10 or ZC_H - HH / 2 < RIDGE + 10:
        bad.append("handle pocket runs off the side wall")
    if HD > STRAP_D + 15:
        bad.append("handle pocket deeper than the wall can take")
    if bad:
        raise ValueError("trunk_550: " + "; ".join(bad))


def plan_pts():
    """Outline at the seam, seen from above: the footprint with the strap
    channels notched into the side walls, as (x, y) pairs."""
    w, d = OW / 2, OD / 2
    c, s, n = d - STRAP_IN, STRAP_W / 2, STRAP_D
    right = [(w, -c - s), (w - n, -c - s), (w - n, -c + s), (w, -c + s),
             (w, c - s), (w - n, c - s), (w - n, c + s), (w, c + s)]
    left = [(-x, -y) for x, y in right]
    return [(-w, -d), (w, -d)] + right + [(w, d), (-w, d)] + left


def tapered(face, height, angle):
    """Extrude a face on the XY plane up by height, narrowing at angle."""
    return bd.extrude(face, amount=height, taper=angle)


def body(outline, up_h, down_h):
    """A seam outline drafted up by up_h and down by down_h."""
    up = tapered(outline, up_h, DRAFT).translate((0, 0, SEAM))
    # Draft down: the same narrowing extrusion, mirrored under the seam.
    down = tapered(outline, down_h, DRAFT).mirror(bd.Plane.XY)
    return up + down.translate((0, 0, SEAM))


def stud_row(w, l, height, z):
    """Three sloped studs (or socket cutters) on the stud pitch at z."""
    return [tapered(bd.Pos(x, 0) * bd.Rectangle(w, l), height,
                    SLOPE).translate((0, 0, z)) for x in STUD_X]


def form(grow, top, base):
    """The trunk form with every face moved out by grow (negative: in):
    body, studs on top, sockets and handle pockets cut in. top and base
    are the heights of the top skin and underside."""
    outline = bd.Polygon(*plan_pts(), align=None)
    if grow:
        outline = bd.offset(outline, grow / math.cos(math.radians(DRAFT)),
                            kind=bd.Kind.INTERSECTION)
    shape = body(outline, top - SEAM, SEAM - base)
    # Sloped faces move sideways by grow / cos at a given height; start
    # each one 1 mm below where it meets the body so the fuse overlaps.
    # The studs also start grow lower, which takes back grow * tan.
    tan, sec = math.tan(math.radians(SLOPE)), 1 / math.cos(
        math.radians(SLOPE))
    g = 2 * (grow * (sec - tan) + tan)
    for stud in stud_row(STUD_W + g, STUD_L + g, STUD_H + 1, top - 1):
        shape += stud
    # Sockets: the underside cutter, moved in by grow (out of the cavity
    # when grow < 0), from 1 mm below the underside.
    g = 2 * (SOCK_C - grow * sec + tan)
    for socket in stud_row(STUD_W + g, STUD_L + g, SOCK_D - grow + 1, -1):
        shape -= socket
    # Handle pocket in each side wall, HD deep at the seam outline.
    for sd in (1, -1):
        shape -= bd.Pos(sd * OW / 2, 0, ZC_H) * bd.Box(
            2 * (HD - grow), HW - 2 * grow, HH - 2 * grow)
    return shape


def build():
    check()
    # One wall: the outside form less the same form moved in by the wall
    # (a 3D offset of the drafted, notched form doesn't solve in OCCT).
    trunk = form(0, OH, 0) - form(-WALL, OH - WALL, WALL)
    # Door opening through the front wall.
    cut_d = 2 * (inset(0) + WALL + 5)
    trunk -= bd.Pos(0, YF, Z_OPEN + GH / 2) * bd.Box(GW, cut_d, GH)
    # Frame header behind the top of the opening, merged into the front,
    # side and top walls.
    if Z_HDR < CEIL - 0.5:
        y0 = YF + inset(CEIL) + 0.5          # inside the front wall
        x1 = OW / 2 - inset(CEIL) - 0.5      # inside the side walls
        y1 = YF + HDR_D
        z1 = CEIL + 1
        trunk += bd.Pos(0, (y0 + y1) / 2, (Z_HDR + z1) / 2) * bd.Box(
            2 * x1, y1 - y0, z1 - Z_HDR)
    return finish(trunk, "Trunk_550 " + REQ.id, REQ.colour)
