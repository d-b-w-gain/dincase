"""
Requirement files, as partnum loads them, from specs.json (written from
specs/*.yaml by tools/sync_specs.py - edit the YAML, not the JSON).

    req = spec("track-roller")
    req["track_w_mm"]           # a parameter
    req.use("screw")            # the part this one is built from
    req.id, req.colour
"""
import json
import os

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "specs.json"), encoding="utf-8") as _f:
    _SPECS = json.load(_f)


class Spec:
    def __init__(self, name):
        self.name = name
        self.data = _SPECS[name]
        self.id = self.data["id"]

    def __getitem__(self, key):
        try:
            return self.data["parameters"][key]
        except KeyError:
            raise KeyError("%s has no parameter %r" % (self.name, key)) \
                from None

    @property
    def params(self):
        return dict(self.data["parameters"])

    @property
    def colour(self):
        return tuple(self.data["appearance"].get("colour", (0.7, 0.7, 0.7)))

    def use(self, key):
        """The part named in `uses:`, which must still have that number."""
        ref = self.data["uses"].get(key)
        if not ref:
            raise KeyError("%s does not use %r" % (self.name, key))
        for name, data in _SPECS.items():
            if data["id"] == ref:
                return Spec(name)
        raise KeyError("%s uses %s = %s, but no spec has that number any "
                       "more" % (self.name, key, ref))


def spec(name):
    return Spec(name)


def handed(left, right):
    """Left/right specs, checked to differ only in `hand`."""
    a, b = spec(left), spec(right)
    pa, pb = a.params, b.params
    if (pa.pop("hand"), pb.pop("hand")) != ("left", "right") or pa != pb:
        raise ValueError("%s / %s must differ only in `hand`" % (left, right))
    return a, b
