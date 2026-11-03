"""Fabrication drawings, the Tertius port of build_mount.make_drawing().

Declared with tertius.drawing while design.py runs; Tertius projects them in
its drafting build and serves each one as a PDF:

    tertius_client.py drawings dincase tertius-project --drawing Mount_Angle --pdf Mount_Angle.pdf

Each part is drawn in the design's Z-up frame (the builders' Y-up frame turned
by bd.Rot(90, 0, 0): builder (x, y, z) -> (x, -z, y)), so the standard views
match the SolidWorks sheet: front = the angle's end profile, left = the
upright seen from outside with its holes.
"""
import build123d as bd
from tertius.drawing import Drawing

import mount

UP = bd.Rot(90, 0, 0)


def _z_up(x, y, z):
    """A builder-frame point in the design's Z-up frame."""
    return (x, -z, y)


def mount_angle(angle):
    """A3, third angle, 1:1: profile (front), upright from outside (left),
    1:2 isometric, with the hole positions measured from one end."""
    part = UP * angle
    notes = [
        "MATERIAL: 50 x 50 x 2 mm EQUAL ANGLE, MILD STEEL",
        "QTY: 2, IDENTICAL. FIT ONE EACH SIDE, UPRIGHT OUTSIDE THE CASE.",
        "HOLES: 4 x M5 x 0.8 TAPPED THRU, TAP DRILL %.1f" % mount.TAP_DRILL,
        "  OUTER 2 = ROLLERS. INNER 2 = LOCKING SCREW (USE THE ONE NEAREST",
        "  THE REAR ROLLER - THE OTHER LETS ONE PART FIT EITHER SIDE).",
        "CUT LENGTH %.0f +/-0.5. DEBURR ALL EDGES." % mount.ANGLE_LEN,
        "FINISH: ZINC PLATE OR PAINT AFTER TAPPING",
    ]
    drw = Drawing(
        "Mount_Angle", part, sheet="A3", scale=1,
        title="RolaCase mount angle", number=mount.ANGLE_REQ.id,
        material="Mild steel", finish="Zinc plate or paint",
        revision="A", reference="dincase (Tertius port)", notes=notes,
        notes_at=(18, 95),
    )
    leg, t, length = mount.ANGLE_LEG, mount.ANGLE_T, mount.ANGLE_LEN
    hole_y = mount.HOLE_Y

    front = drw.view("front", at=(300, 185))          # the angle's end profile
    side = drw.view("left", aligned_to=front)         # upright from outside
    drw.view("iso", at=(355, 248), scale=0.5)

    # Profile: legs and thickness.
    front.horizontal(_z_up(0, 0, 0), _z_up(leg, 0, 0), offset=-10)
    front.vertical(_z_up(0, 0, 0), _z_up(0, leg, 0), offset=-10)
    front.horizontal(_z_up(0, leg, 0), _z_up(t, leg, 0), offset=6)
    front.vertical(_z_up(leg, 0, 0), _z_up(leg, t, 0), offset=6)

    # Upright: holes from the end, stacked under the view, then overall length.
    end = _z_up(0, 0, 0)
    for i, z in enumerate(mount.HOLES_FROM_END):
        side.horizontal(end, _z_up(0, hole_y, z), offset=-6 - 7 * i)
    side.horizontal(end, _z_up(0, 0, length), offset=-6 - 7 * len(mount.HOLES_FROM_END))
    side.vertical(end, _z_up(0, hole_y, mount.HOLES_FROM_END[-1]), offset=8)
    first_hole = _z_up(0, hole_y, mount.HOLES_FROM_END[0])
    side.diameter(center=first_hole, diameter=mount.TAP_DRILL, angle=60, leader=16)
    return drw


def declare(parts):
    """Declare every fabrication drawing for the built parts."""
    return [mount_angle(parts["angle"])]
