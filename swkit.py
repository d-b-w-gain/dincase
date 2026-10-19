"""
Shared SolidWorks API helpers for the RolaCase build scripts.

Talks to a running SolidWorks over COM (pywin32). All sizes in mm; the API
works in metres, so m() converts.
"""
import os
import types
import pythoncom
import win32com.client
from win32com.client import VARIANT

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_DIR = os.path.join(HERE, "parts")

END_BLIND = 0
END_MIDPLANE = 6
NUL = VARIANT(pythoncom.VT_DISPATCH, None)


def m(v):
    """mm -> metres (SolidWorks API units)."""
    return v / 1000.0


def call(obj, name):
    """Run a no-argument API call. pywin32 exposes some of these as methods
    and others as properties (already evaluated), depending on SW typeinfo."""
    r = getattr(obj, name)
    return r() if isinstance(r, types.MethodType) else r


def byref_int():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def connect():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    sw.Visible = True
    return sw


def base_planes(model):
    """Front, Top, Right planes in feature-tree order (language independent)."""
    planes = []
    f = model.FirstFeature
    while f is not None and len(planes) < 3:
        if f.GetTypeName2 == "RefPlane":
            planes.append(f)
        f = f.GetNextFeature
    return planes


def new_part(sw):
    template = sw.GetUserPreferenceStringValue(8)  # swDefaultTemplatePart
    model = sw.NewDocument(template, 0, 0, 0)
    if model is None:
        raise RuntimeError("Could not create a new part from " + template)
    model.SketchManager.AddToDB = True       # no snapping/inference
    model.SketchManager.DisplayWhenAdded = False
    return model


def start_sketch(model, plane):
    model.ClearSelection2(True)
    plane.Select2(False, 0)
    model.SketchManager.InsertSketch(True)


def extrude(model, depth, midplane=False):
    """Extrude the active sketch. Returns the feature."""
    model.SketchManager.InsertSketch(True)   # close sketch -> stays selected
    feat = model.FeatureManager.FeatureExtrusion2(
        True, False, False,
        END_MIDPLANE if midplane else END_BLIND, 0,
        m(depth), 0,
        False, False, False, False, 0, 0,
        False, False, False, False,
        True, True, True,
        0, 0, False)
    if feat is None:
        raise RuntimeError("Extrusion failed")
    model.ClearSelection2(True)
    return feat


def offset_plane(model, plane, dist):
    """Reference plane parallel to `plane`, `dist` mm along its +normal."""
    model.ClearSelection2(True)
    plane.Select2(False, 0)
    p = model.FeatureManager.InsertRefPlane(8, m(dist), 0, 0, 0, 0)  # distance
    if p is None:
        raise RuntimeError("Could not create offset plane")
    model.ClearSelection2(True)
    return p


def colour(model, rgb):
    r, g, b = rgb
    vals = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                   [r, g, b, 0.6, 0.8, 0.4, 0.3, 0.0, 0.0])
    model.MaterialPropertyValues = vals


def save_and_keep(sw, model, name):
    path = os.path.join(PARTS_DIR, name + ".SLDPRT")
    os.makedirs(PARTS_DIR, exist_ok=True)
    # Hand snapping/inference back for anyone sketching in this part later.
    model.SketchManager.AddToDB = False
    model.SketchManager.DisplayWhenAdded = True
    call(model, "ViewZoomtofit2")
    model.ShowNamedView2("*Isometric", 7)
    call(model, "ViewZoomtofit2")
    err = model.SaveAs3(path, 0, 1)          # swSaveAsOptions_Silent
    if err != 0:
        raise RuntimeError("Save failed (%s) for %s" % (err, path))
    box = model.GetPartBox(True)
    print("  saved %s  bbox mm X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]" % (
        name, box[0] * 1000, box[3] * 1000, box[1] * 1000, box[4] * 1000,
        box[2] * 1000, box[5] * 1000))
    return path


# ----------------------------------------------------------------- assembly
IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)


def transform(sw, rot, x, y, z):
    """MathTransform from a 3x3 rotation (row-major) and a mm translation."""
    data = list(rot) + [m(x), m(y), m(z), 1.0, 0.0, 0.0, 0.0]
    mu = call(sw, "GetMathUtility")
    mu._FlagAsMethod("CreateTransform")
    return mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                      data))


def place(sw, asm, path, rot=IDENT, at=(0, 0, 0)):
    """Insert a component with its origin exactly at `at`. (AddComponent5
    alone centres the bounding box on the point, not the origin.)"""
    comp = asm.AddComponent5(path, 0, "", False, "", 0, 0, 0)
    if comp is None:
        raise RuntimeError("Could not insert " + path)
    comp.Transform2 = transform(sw, rot, *at)
    return comp


def fix_all(asm, comps):
    asm.ClearSelection2(True)
    for c in comps:
        c.Select4(True, NUL, False)
    call(asm, "FixComponent")
    asm.ClearSelection2(True)


def unloaded(asm):
    """Components SolidWorks couldn't load (e.g. the file's internal ID no
    longer matches what the assembly recorded)."""
    return [c.Name2 for c in asm.GetComponents(False)
            if c.GetSuppression2 != 0 and c.GetModelDoc2 is None]


def relink(sw, asm_path, names):
    """Re-attach an assembly to parts/sub-assemblies that were rebuilt.

    A rebuilt document is a NEW file with a new internal ID, even when it is
    saved over the old name, so assemblies that used the old one can no
    longer load it (greyed out with a warning). For every instance whose file
    name (no extension) is in `names`, record its exact transform, delete it,
    insert the current file in the same place, and fix it. Saves the
    assembly. Does nothing if the assembly doesn't exist."""
    if not os.path.exists(asm_path):
        return 0
    e = byref_int()
    asm = sw.OpenDoc6(asm_path, 2, 0, "", e, byref_int())
    title = os.path.basename(asm_path)
    targets = [c for c in asm.GetComponents(True)
               if os.path.splitext(os.path.basename(c.GetPathName))[0]
               in names]
    if not targets:
        return 0
    keep = []
    for c in targets:
        d = list(c.Transform2.ArrayData)
        keep.append((c.GetPathName, d[0:9], [v * 1000 for v in d[9:12]]))
    for path in {p for p, _, _ in keep}:          # must be loaded to insert
        sw.OpenDoc6(path, 2 if path.upper().endswith("ASM") else 1, 0, "",
                    e, byref_int())
    sw.ActivateDoc3(title, False, 0, e)
    asm.ClearSelection2(True)
    for c in targets:
        c.Select4(True, NUL, False)
    asm.Extension.DeleteSelection2(0)
    new = [place(sw, asm, p, rot, at) for p, rot, at in keep]
    fix_all(asm, new)
    asm.ForceRebuild3(False)
    bad = unloaded(asm)
    if bad:
        raise RuntimeError("%s still has unloaded components: %s"
                           % (title, bad))
    asm.Save3(1, e, byref_int())
    print("  relinked %d component(s) in %s" % (len(new), title))
    return len(new)


def interferences(asm, ignore_pairs=()):
    """Run interference detection; returns [(names, mm3)] not in ignore.
    Refuses to run if any component isn't loaded - unloaded parts can't
    clash, so the check would pass for the wrong reason."""
    bad = unloaded(asm)
    if bad:
        raise RuntimeError("components not loaded, interference check would "
                           "be meaningless: %s" % bad)
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    hits = call(idm, "GetInterferences") or []
    out = []
    for i in hits:
        names = sorted(c.Name2.rsplit("-", 1)[0] for c in i.Components)
        if tuple(names) not in ignore_pairs:
            out.append((names, i.Volume * 1e9))
    call(idm, "Done")
    return out


# --------------------------------------------------------------- geometry kit
class Kit:
    """Sketch/feature helpers that take MODEL coordinates (mm), so plane
    orientation and sketch-axis signs never matter. Extrudes and cuts are
    midplane, centred on the sketch plane."""

    def __init__(self, sw, model):
        self.sw, self.model = sw, model
        self.front, self.top, self.right = base_planes(model)
        self.mu = call(sw, "GetMathUtility")
        self.mu._FlagAsMethod("CreatePoint")

    def plane(self, base, dist):
        """Plane parallel to base at signed distance along its normal."""
        if abs(dist) < 1e-9:
            return base
        md = self.model
        md.ClearSelection2(True)
        base.Select2(False, 0)
        opt = 8 | (256 if dist < 0 else 0)        # distance (+ flip)
        p = md.FeatureManager.InsertRefPlane(opt, m(abs(dist)), 0, 0, 0, 0)
        md.ClearSelection2(True)
        if p is None:
            raise RuntimeError("plane failed")
        return p

    def xplane(self, x):
        return self.plane(self.right, x)

    def yplane(self, y):
        return self.plane(self.top, y)

    def zplane(self, z):
        return self.plane(self.front, z)

    def sketch(self, plane):
        start_sketch(self.model, plane)
        sk = self.model.SketchManager.ActiveSketch
        self._t = sk.ModelToSketchTransform

    def _uv(self, p):
        pt = self.mu.CreatePoint(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                         [m(v) for v in p]))
        pt._FlagAsMethod("MultiplyTransform")
        a = pt.MultiplyTransform(self._t).ArrayData
        return a[0], a[1]

    def poly(self, pts):
        sk = self.model.SketchManager
        uv = [self._uv(p) for p in pts]
        segs = []
        for (u1, v1), (u2, v2) in zip(uv, uv[1:] + uv[:1]):
            segs.append(sk.CreateLine(u1, v1, 0, u2, v2, 0))
        return segs

    def box(self, axis, a0, a1, b0, b1, at):
        """Rectangle on an X/Y/Z plane given the two in-plane ranges."""
        if axis == "x":      # (y, z)
            pts = [(at, a0, b0), (at, a1, b0), (at, a1, b1), (at, a0, b1)]
        elif axis == "y":    # (x, z)
            pts = [(a0, at, b0), (a1, at, b0), (a1, at, b1), (a0, at, b1)]
        else:                # (x, y)
            pts = [(a0, b0, at), (a1, b0, at), (a1, b1, at), (a0, b1, at)]
        return self.poly(pts)

    def circle(self, centre, d):
        u, v = self._uv(centre)
        return self.model.SketchManager.CreateCircleByRadius(u, v, 0,
                                                             m(d / 2))

    def _feature(self, depth, cut, midplane=True):
        md = self.model
        md.SketchManager.InsertSketch(True)
        sk = md.FeatureByPositionReverse(0)
        md.ClearSelection2(True)
        sk.Select2(False, 0)
        fm = md.FeatureManager
        t1 = END_MIDPLANE if midplane else END_BLIND
        if cut:
            f = fm.FeatureCut4(True, False, False, t1, 0, m(depth), 0,
                               False, False, False, False, 0, 0,
                               False, False, False, False, False, True, True,
                               True, True, False, 0, 0, False, False)
        else:
            f = fm.FeatureExtrusion2(True, False, False, t1, 0, m(depth), 0,
                                     False, False, False, False, 0, 0,
                                     False, False, False, False, True, True,
                                     True, 0, 0, False)
        md.ClearSelection2(True)
        if f is None:
            raise RuntimeError(("cut" if cut else "boss") + " failed")
        return f

    def boss(self, depth, midplane=True):
        return self._feature(depth, False, midplane)

    def cut(self, depth, midplane=True):
        return self._feature(depth, True, midplane)
