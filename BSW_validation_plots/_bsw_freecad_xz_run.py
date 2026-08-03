# Build BSW XZ overlay FCStd via FreeCAD (no __file__ dependency).
# Run:
#   "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" _bsw_validation_plots\_bsw_freecad_xz_run.py

import math
import os
import sys

import FreeCAD as App
import Part

ROOT = r"C:\Users\ritchie\ThreadProfile"
HERE = os.path.join(ROOT, "_bsw_validation_plots")
OUT = os.path.join(HERE, "BSW_1_4_20_XZ_compare.FCStd")

sys.path.insert(0, os.path.join(ROOT, "Resources", "assets"))
from generate_bsw_profile_data import DEPTH, basic_minor, generate_bsw_tables


def profile_wire(offsets, minor, pitch):
    pts = []
    for i, od in enumerate(offsets):
        z = (i + 1) / 720.0 * pitch
        x = minor / 2.0 + od * pitch
        pts.append(App.Vector(x, 0.0, z))
    return Part.makePolygon(pts)


def truncated55_offsets(n=719):
    H = 1.0 / (2.0 * math.tan(math.radians(27.5)))
    h_trunc = (5.0 / 8.0) * H
    slope = 1.0 / math.tan(math.radians(27.5))
    root_cut = (H - h_trunc) / 2.0
    out = []
    for k in range(1, n + 1):
        z = k / 720.0
        if z > 0.5:
            z = 1.0 - z
        x = slope * z - root_cut
        if x < 0.0:
            x = 0.0
        if x > h_trunc:
            x = h_trunc
        out.append(x)
    return out


doc = App.newDocument("BSW_XZ_Compare")
internal, external = generate_bsw_tables()

major = 0.25 * 25.4
pitch = 25.4 / 20.0
minor_i = basic_minor(major, pitch)
minor_e = minor_i - 0.15

doc.addObject("Part::Feature", "BSW_1_4_20_internal_XZ").Shape = profile_wire(
    internal, minor_i, pitch
)
doc.addObject("Part::Feature", "BSW_1_4_20_external_XZ").Shape = profile_wire(
    external, minor_e, pitch
)

H55 = pitch / (2 * math.tan(math.radians(27.5)))
fake_minor = major - 2 * (5.0 / 8.0) * H55
doc.addObject("Part::Feature", "Fake_truncated55_V_XZ").Shape = profile_wire(
    truncated55_offsets(), fake_minor, pitch
)

for name, r in [
    ("ref_major_r", major / 2),
    ("ref_minor_basic_r", minor_i / 2),
    ("ref_minor_fake_r", fake_minor / 2),
]:
    line = Part.makeLine(App.Vector(r, 0, 0), App.Vector(r, 0, pitch))
    doc.addObject("Part::Feature", name).Shape = line

# Optional STEP path via env
step_path = os.environ.get("BSW_STEP", "").strip()
if step_path and os.path.isfile(step_path):
    Part.insert(step_path, doc.Name)
    print("Imported STEP:", step_path)

doc.recompute()
os.makedirs(HERE, exist_ok=True)
doc.saveAs(OUT)
print("Saved", OUT)
print(
    "1/4-20 major={:.4f} P={:.4f} BSW minor={:.4f} fake55={:.4f} h={:.4f}".format(
        major, pitch, minor_i, fake_minor, DEPTH * pitch
    )
)
App.closeDocument(doc.Name)
