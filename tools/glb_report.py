"""
Summarise a GLB from Tertius: the node tree with each node's world
bounding box (mm), and every mesh's volume and colour. Standard library
only.

    python3 tools/glb_report.py model.glb [--depth 2] [--meshes]
"""
import argparse
import json
import struct

COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
FORMATS = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}


def load(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + n])
    rest = data[20 + n:]
    blen = struct.unpack("<I", rest[0:4])[0]
    return gltf, rest[8:8 + blen]


def accessor(gltf, binary, i):
    acc = gltf["accessors"][i]
    view = gltf["bufferViews"][acc["bufferView"]]
    k, fmt = COMPONENTS[acc["type"]], FORMATS[acc["componentType"]]
    size = struct.calcsize("<" + fmt)
    stride = view.get("byteStride") or k * size
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for j in range(acc["count"]):
        o = start + j * stride
        v = struct.unpack_from("<%d%s" % (k, fmt), binary, o)
        out.append(v if k > 1 else v[0])
    return out


def mat_mul(a, b):
    return [sum(a[r + 4 * k] * b[k + 4 * c] for k in range(4))
            for c in range(4) for r in range(4)]      # column-major


def local_matrix(node):
    if "matrix" in node:
        return list(node["matrix"])
    t = node.get("translation", [0, 0, 0])
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
         t[0], t[1], t[2], 1]
    for c in range(3):
        for rr in range(3):
            r[4 * c + rr] *= s[c]
    return r


def apply(m, p):
    return tuple(m[r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r]
                 for r in range(3))


def mesh_info(gltf, binary, mi):
    pts, vol = [], 0.0
    for prim in gltf["meshes"][mi]["primitives"]:
        pos = accessor(gltf, binary, prim["attributes"]["POSITION"])
        idx = accessor(gltf, binary, prim["indices"]) if "indices" in prim \
            else list(range(len(pos)))
        pts.extend(pos)
        for a, b, c in zip(idx[0::3], idx[1::3], idx[2::3]):
            p, q, r = pos[a], pos[b], pos[c]
            vol += (p[0] * (q[1] * r[2] - q[2] * r[1]) -
                    p[1] * (q[0] * r[2] - q[2] * r[0]) +
                    p[2] * (q[0] * r[1] - q[1] * r[0])) / 6
    return pts, vol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--meshes", action="store_true")
    a = ap.parse_args()
    gltf, binary = load(a.glb)
    unit = 1000.0 if gltf.get("extras", {}).get("tertiusModelGeometry") \
        else 1.0                                  # Tertius GLBs are metres
    cache = {}

    def walk(i, parent, depth):
        node = gltf["nodes"][i]
        m = mat_mul(parent, local_matrix(node))
        pts = []
        if "mesh" in node:
            if node["mesh"] not in cache:
                cache[node["mesh"]] = mesh_info(gltf, binary, node["mesh"])
            pts = [apply(m, p) for p in cache[node["mesh"]][0]]
        for c in node.get("children", []):
            pts += walk(c, m, depth + 1)
        if depth <= a.depth and pts:
            lo = [min(p[k] for p in pts) * unit for k in range(3)]
            hi = [max(p[k] for p in pts) * unit for k in range(3)]
            print("%s%-40s X[%8.2f,%8.2f] Y[%8.2f,%8.2f] Z[%8.2f,%8.2f]"
                  % ("  " * depth, node.get("name", "?")[:40], lo[0], hi[0],
                     lo[1], hi[1], lo[2], hi[2]))
        return pts

    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    scene = gltf["scenes"][gltf.get("scene", 0)]
    for r in scene["nodes"]:
        walk(r, ident, 0)
    if a.meshes:
        names = {}
        for n in gltf["nodes"]:
            if "mesh" in n:
                names.setdefault(n["mesh"], n.get("name"))
        for mi in sorted(cache):
            pts, vol = cache[mi]
            mat = gltf["meshes"][mi]["primitives"][0].get("material")
            col = gltf["materials"][mat]["pbrMetallicRoughness"].get(
                "baseColorFactor") if mat is not None else None
            print("mesh %-3d %-38s vol %10.2f mm3  colour %s"
                  % (mi, (names.get(mi) or "?")[:38], vol * unit ** 3,
                     [round(c, 3) for c in col] if col else None))


if __name__ == "__main__":
    main()
