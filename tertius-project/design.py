"""dincase: DIN-rail style mounts for carry parts cases.

Tertius project, ported from the SolidWorks builders (build_*.py). Each
part family is a module beside this file; build inputs come from the
partnum requirement files via specs.json (tools/sync_specs.py). All
dimensions are millimetres.

The SolidWorks assemblies, side by side along X:
    RolaCase_Assembly      the case model (base, lid, hinge, handle,
                           latches) - interface geometry only
    RolaCase_AngleMount    case on the two mounting angles, locked
    Dincase_Shelf          case on the shelf rails (draft)
    Dincase_Slide          shelf on its drawer slides, shut (draft)
    Dincase_Slide_Open     slides out, case rolled forward (draft)
    Trunk_550              the stacking trunk the shelf fits into
Set SHOW to one of those names to see it on its own. CHECK runs the
interference checks the SolidWorks builds ran (slower).

Parts are modelled in the builders' axes (Y up, Z front) and turned here
to Z up, front towards -Y.
"""
import build123d as bd

import case
import mount
import roller
import shelf_rail
import slide
import trunk_550
from kit import group, interferences

SHOW = "all"
CHECK = False
PITCH = 700                 # assembly spacing along X when SHOW = "all"

parts = {"roller": roller.build_roller(), "spacer": roller.build_spacer(),
         "screw": mount.build_screw(), "angle": mount.build_angle()}
parts.update(shelf_rail.build())
parts.update(slide.build())
case_parts = case.build()

assemblies = {
    "RolaCase_Assembly": (case_parts, ()),
    "RolaCase_AngleMount": (case_parts + mount.assembly(parts),
                            mount.SCREW_IGNORE),
    "Dincase_Shelf": (shelf_rail.place_shelf(parts, case_parts),
                      shelf_rail.SCREW_IGNORE),
    "Dincase_Slide": slide.assembly(parts, case_parts, 0.0, 0.0, True),
    "Dincase_Slide_Open": slide.assembly(parts, case_parts,
                                         slide.SLIDE_TRAVEL,
                                         slide.CASE_TRAVEL, False),
}

if CHECK:
    found = {name: interferences(placed, ignore)
             for name, (placed, ignore) in assemblies.items()
             if SHOW in ("all", name)}
    found = {name: hits for name, hits in found.items() if hits}
    if found:
        raise RuntimeError("interferences: %r" % found)

# Turn the builders' Y-up frame to Z up (front to -Y).
UP = bd.Rot(90, 0, 0)
nodes = [UP * group(name, placed) for name, (placed, _) in assemblies.items()]
nodes.append(trunk_550.build())          # already Z up
nodes = [n for n in nodes if SHOW in ("all", n.label.split(" ")[0])]
if not nodes:
    raise ValueError("SHOW = %r is not an assembly" % SHOW)
if SHOW == "all":
    nodes = [bd.Pos(i * PITCH, 0, 0) * n for i, n in enumerate(nodes)]
model = nodes[0] if len(nodes) == 1 else group("dincase", nodes)
