# dincase

Mount carry-style parts cases the way gear clips onto DIN rail: drop the
case on, slide it back, and it locks. Built for tradies, especially
sparkies, who keep dozens of small components in cases in a van, ute or
workshop.

Compatible with RolaCase and other frames' cases that use the same
side lock track (370 x 370 mm footprint).

> Independent project. Not affiliated with or endorsed by RolaCase /
> Thomas Moloney Pty Ltd. RolaCase is their trade mark, used here only to
> describe compatibility.

## The mount

Two 50 x 50 x 2 mm steel angles sit under the case, one each side. Each
angle carries two 3D-printed rollers, one in each pocket of the case's
side lock track, and an M5 locking screw.

1. Lower the case so each front roller comes up through the lip-free entry
   slot of the front pocket.
2. Slide the case back about 98 mm. The rear rollers run into the open
   back ends of the rear pockets, and the front rollers stop at the closed
   ends of the front pockets. The track lips hold the case down.
3. Thread the M5 locking screw in from outside, through the hole nearest
   the rear roller. Its thread bears on the rib between the pockets, so
   the case can't slide back to the entry slots.

To remove it, back out the locking screws, slide the case forward and lift.

## Parts

Every part number is a hash of the part's build inputs (see
[partnum](https://github.com/d-b-w-gain/partnum)). Releases are git tags:
`<part number>/<revision>`.

| Part number | Nickname | Part | Make |
|---|---|---|---|
| `YYY-V00T-MDAXM` | Yoked Yawless Yo-yo | Track roller | 3D print, 4 off |
| `PVQ-AHQ6-SPD1G` | Pivot, Very Quiet | Roller journal spacer | 3D print, 4 off |
| `NGZ-D4Y4-CH3ZG` | Nesting Guide Z-rail | Mounting angle | Steel, 2 off ([drawing](drawings/Mount_Angle.PDF)) |
| `YAQ-Q2SV-WQ8B5` | Yaw-Arresting Quoin | M5 x 12 button head screw | Buy, 6 off |

### In progress: pull-out shelf (draft, not released)

Handed side rails that run 50 mm past the back of the case, so a rear
cross brace can bolt through their base legs and the pair can ride on
slides as a pull-out shelf. Same rollers, lock screw and case interface as
the mounting angle.

| Part number | Part | Make |
|---|---|---|
| `ZKM-91RV-KHZYH` | Shelf rail, left hand | Steel ([drawing](drawings/Shelf_Rail.PDF)) |
| `KMP-CSMQ-45K0W` | Shelf rail, right hand | Steel, mirror image |

Built by `build_shelf_rail.py`; fit check in `Dincase_Shelf.SLDASM`.

### Printing the rollers and spacers

[stl/Track_Roller.STL](stl/Track_Roller.STL) and
[stl/Roller_Spacer.STL](stl/Roller_Spacer.STL), in millimetres. Print them
flat on their bottom face, with no supports. PETG wears better than PLA.

The holes are modelled at standard drill sizes. They print slightly small,
so drill them out to size:

| Hole | Drill | Notes |
|---|---|---|
| Roller bore | 8.0 | runs on the 7.6 spacer (0.4 mm running fit) |
| Spacer bore | 4.2 | M5 tap drill: tap it M5, or drill 5.0-5.5 for clearance |
| Roller counterbore | 11.0 | only if the screw head doesn't drop in |

## Repository

```
specs/        requirement files: the build inputs that set each part number,
              and a build record per part
build_roller.py   roller + spacer (SolidWorks), exports the STLs
build_mount.py    mounting angle, screw, assembly and drawing
build_case_assembly.py   simplified case model (base, lid, hinge, handle,
              latches) for checking fits - interface geometry only
swkit.py      SolidWorks API helpers
parts/        SolidWorks parts       stl/  printable parts
drawings/     fabrication drawing    *.SLDASM  assemblies
```

The case model is a simplified envelope with the side track geometry,
modelled from measurements for designing mounts. It is not a copy of the
manufacturer's design.

## Building

Needs Windows, SolidWorks (2023 tested) running, and Python 3.9+:

```
pip install -r requirements.txt
python build_roller.py
python build_mount.py
```

### In Tertius

`tertius-project/` is the same design in Build123D for
[Tertius](https://tertius.gainengineering.com.au), ported module by module
from the `build_*.py` scripts (fabrication drawings not ported yet). It
reads the same `specs/` files: run `tools/sync_specs.py` after changing
one. Push and compile it with:

```
python3 tools/sync_specs.py
python3 tools/tertius_client.py compile dincase tertius-project
```

`TERTIUS_USER` / `TERTIUS_PASSWORD` select the account (default demo).
In `design.py`, `SHOW` picks one assembly and `CHECK = True` runs the
interference checks.

Change a part by editing its file in `specs/`; that gives it a new part
number. Release a revision with:

```
python -m partnum release specs/track-roller.yaml A
python -m partnum verify
```
