"""
Copy the requirement files into the Tertius project as one JSON file, so
the Build123D modules read the same build inputs as partnum hashes.

    python3 tools/sync_specs.py

Writes tertius-project/specs.json: for each specs/<name>.yaml, its part
number (computed by partnum, not copied), name, uses, parameters and
appearance.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "partnum", "src"))
from partnum import load_requirements  # noqa: E402

OUT = os.path.join(HERE, "tertius-project", "specs.json")


def main():
    specs = {}
    folder = os.path.join(HERE, "specs")
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".yaml"):
            continue
        req = load_requirements(os.path.join(folder, f))
        specs[f[:-5]] = {
            "id": req.id,
            "name": req.get("name"),
            "uses": req.get("uses") or {},
            "parameters": req.params,
            "appearance": req.get("appearance") or {},
        }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(specs, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s (%d specs)" % (os.path.relpath(OUT, HERE), len(specs)))


if __name__ == "__main__":
    main()
