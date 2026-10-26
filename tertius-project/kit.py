"""
Build123D stand-in for swkit.Kit, so the parts read like the SolidWorks
builders they were ported from: sketch on an X/Y/Z plane in MODEL
coordinates (mm), then boss or cut. Extrudes and cuts are midplane,
centred on the sketch plane, unless midplane=False (then along +axis).
Loops in one sketch combine like a SolidWorks sketch: a loop inside
another is a hole.

Parts are modelled in the builders' axes: X across, Y up, Z front (+).
design.py turns the finished model to Tertius' Z up.
"""
import build123d as bd

AXES = {"x": 0, "y": 1, "z": 2}
UNIT = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


class Kit:
    def __init__(self, part=None):
        self.part = part

    def sketch(self, axis, at=0.0):
        self.axis, self.at, self.loops = axis, at, []

    def _on_plane(self, p):
        p = list(p)
        p[AXES[self.axis]] = self.at          # project, as SolidWorks does
        return bd.Vector(*p)

    def poly(self, pts):
        wire = bd.Wire.make_polygon([self._on_plane(p) for p in pts],
                                    close=True)
        face = bd.Face(wire)
        # Mirrored (handed) outlines wind the other way: face them along
        # +axis so every extrusion is a solid the right way out.
        if face.normal_at().dot(bd.Vector(*UNIT[self.axis])) < 0:
            face = -face
        self.loops.append(face)

    def box(self, axis, a0, a1, b0, b1, at):
        """Rectangle on an X/Y/Z plane given the two in-plane ranges."""
        if axis == "x":      # (y, z)
            pts = [(at, a0, b0), (at, a1, b0), (at, a1, b1), (at, a0, b1)]
        elif axis == "y":    # (x, z)
            pts = [(a0, at, b0), (a1, at, b0), (a1, at, b1), (a0, at, b1)]
        else:                # (x, y)
            pts = [(a0, b0, at), (a1, b0, at), (a1, b1, at), (a0, b1, at)]
        self.poly(pts)

    def circle(self, centre, d):
        plane = bd.Plane(origin=self._on_plane(centre), z_dir=UNIT[self.axis])
        self.loops.append(bd.Face(bd.Wire.make_circle(d / 2, plane)))

    def _solid(self, depth, midplane):
        n = bd.Vector(*UNIT[self.axis])
        shift = n * (-depth / 2) if midplane else bd.Vector(0, 0, 0)
        solid = None
        for face in self.loops:               # even-odd, like a sketch
            s = bd.extrude(face.translate(shift), amount=depth, dir=n)
            solid = s if solid is None else (solid - s) + (s - solid)
        return solid

    def boss(self, depth, midplane=True):
        s = self._solid(depth, midplane)
        self.part = s if self.part is None else self.part + s

    def cut(self, depth, midplane=True):
        self.part = self.part - self._solid(depth, midplane)


def tapered(face, height, angle):
    """Extrude a face on the XY plane up +Z by height, narrowing at angle
    (degrees) on every wall."""
    return bd.extrude(face, amount=height, taper=angle)


# Turn a +Z extrusion to run along a builder axis.
TO_AXIS = {"+y": bd.Rot(-90, 0, 0), "-y": bd.Rot(90, 0, 0),
           "+z": bd.Location(), "-z": bd.Rot(180, 0, 0),
           "+x": bd.Rot(0, 90, 0), "-x": bd.Rot(0, -90, 0)}


def drafted_rect(half_u, half_v, depth, direction, angle, origin):
    """Rectangle 2*half_u by 2*half_v centred at origin, extruded `depth`
    along direction ('+y', '-y', ...), narrowing at `angle` degrees.
    For +/-y, u is X and v is Z."""
    solid = tapered(bd.Rectangle(2 * half_u, 2 * half_v), depth, angle)
    return bd.Pos(*origin) * (TO_AXIS[direction] * solid)


def chamfer_circle(part, y, d, size):
    """45 deg chamfer on the circular edge of diameter d at Y = y."""
    edges = [e for e in part.edges().filter_by(bd.GeomType.CIRCLE)
             if abs(e.radius - d / 2) < 1e-3 and abs(e.arc_center.Y - y) < 1e-3]
    if len(edges) != 1:
        raise RuntimeError("edge d%.2f at y=%g not found (%d)"
                           % (d, y, len(edges)))
    return bd.chamfer(edges[0], size)


# ---------------------------------------------------------------- placing
# Row-major rotations, rows = where part X, Y, Z go (as swkit).
IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)
Y_TO_NEG_X = (0, 1, 0, -1, 0, 0, 0, 0, 1)
Y_TO_POS_X = (0, -1, 0, 1, 0, 0, 0, 0, 1)
TURN_Y180 = (-1, 0, 0, 0, 1, 0, 0, 0, -1)


def place(shape, rot=IDENT, at=(0, 0, 0), label=None):
    """A copy of shape turned by rot and moved to at. Keeps label and
    colour."""
    frame = bd.Plane(origin=at, x_dir=rot[0:3], z_dir=rot[6:9])
    out = shape.moved(bd.Location(frame))
    out.label = label or shape.label
    out.color = shape.color
    return out


def place_axis(shape, rot, at, x_range, label=None):
    """Place a part whose axis is part +Y, and check its X extent lands on
    x_range (what swkit's place_axis checked after placing)."""
    out = place(shape, rot, at, label)
    bb = out.bounding_box()
    if abs(bb.min.X - min(x_range)) > 0.2 or \
            abs(bb.max.X - max(x_range)) > 0.2:
        raise RuntimeError("%s: X %.2f..%.2f, expected %.2f..%.2f"
                           % (out.label, bb.min.X, bb.max.X, min(x_range),
                              max(x_range)))
    return out


def finish(shape, label, rgb):
    """A part as a labelled, coloured single solid."""
    solids = shape.solids()
    if len(solids) != 1:
        raise RuntimeError("%s: %d solids, expected 1" % (label,
                                                          len(solids)))
    solid = solids[0]
    solid.label = label
    solid.color = bd.Color(*rgb)
    return solid


def group(label, children):
    """An assembly node: a labelled compound of placed parts."""
    return bd.Compound(children=list(children), label=label)


def interferences(children, ignore_pairs=(), tol=1e-3):
    """Pairs of placed parts (by label) that overlap by more than tol mm3,
    skipping pairs whose label stems are in ignore_pairs."""
    flat = []

    def walk(node):
        if node.children:
            for c in node.children:
                walk(c)
        else:
            flat.append(node)
    for c in children:
        walk(c)

    def stem(s):
        return s.label.split(" ")[0]

    ignore = {tuple(sorted(p)) for p in ignore_pairs}
    hits = []
    for i, a in enumerate(flat):
        ba = a.bounding_box()
        for b in flat[i + 1:]:
            if tuple(sorted((stem(a), stem(b)))) in ignore:
                continue
            bb = b.bounding_box()
            if (ba.min.X > bb.max.X or bb.min.X > ba.max.X or
                    ba.min.Y > bb.max.Y or bb.min.Y > ba.max.Y or
                    ba.min.Z > bb.max.Z or bb.min.Z > ba.max.Z):
                continue
            common = a.intersect(b)
            if common is None:
                continue
            if not isinstance(common, bd.Shape):      # a ShapeList
                common = bd.Compound(list(common))
            vol = common.volume
            if vol > tol:
                hits.append(((a.label, b.label), vol))
    return hits

