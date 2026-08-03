#!/usr/bin/env python3
"""Build a FreeCAD document with BSW XZ cross-section overlays (Mark-style).

Creates:
  - BSW 1/4-20 Internal / External profiles as Part::Feature polylines in XZ
  - Fake truncated-55 V (5/8 H) for comparison
  - Optional McMaster STEP import if a path is given

Usage (FreeCAD cmd):
  "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" _bsw_validation_plots/_bsw_freecad_xz.py
  freecadcmd _bsw_validation_plots/_bsw_freecad_xz.py --step path\\to\\mcmaster.step
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

# FreeCAD injects its own path; when run via freecadcmd, FreeCAD is available.
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "BSW_1_4_20_XZ_compare.FCStd"

sys.path.insert(0, str(ROOT / "Resources" / "assets"))
from generate_bsw_profile_data import (  # noqa: E402
    DEPTH,
    basic_minor,
    generate_bsw_tables,
)


def profile_wire(offsets, minor, pitch, z0=0.0, label="profile"):
    """Build open wire in XZ: z along pitch, x = radius (one pitch)."""
    n = len(offsets)
    pts = []
    for i, od in enumerate(offsets):
        z = z0 + (i + 1) / 720.0 * pitch  # match generator k=1..719
        x = minor / 2.0 + od * pitch
        pts.append(App.Vector(x, 0.0, z))
    # close with verticals at ends down to axis for a filled-looking section? Keep open.
    edge = Part.makePolygon(pts)
    return edge


def truncated55_offsets(n=719):
    """Old wrong approach: 55° V with metric-style 5/8 truncation (flat crest/root)."""
    H = 1.0 / (2.0 * math.tan(math.radians(27.5)))
    h_trunc = (5.0 / 8.0) * H
    slope = 1.0 / math.tan(math.radians(27.5))
    # flat root, rise, flat crest, fall — approximate like PG layout scaled
    # Use same sampling as whitworth but clipped flats
    out = []
    for k in range(1, n + 1):
        z = k / 720.0
        if z > 0.5:
            z = 1.0 - z
        # sharp V from 0 then clip
        x = slope * z
        # root truncation: move origin so crest at h_trunc with flats
        # simpler: clip to [0, h_trunc]
        x = max(0.0, min(h_trunc, x - (H - h_trunc) / 2.0))
        # Actually classic truncated V: remove H/8 from tip and H/4 from root of sharp H
        # height of flank usable = 5/8 H; root flat starts after H/4 from sharp tip...
        # For comparison plot use: x = clamp(slope*z - root_cut, 0, h_trunc)
        root_cut = (H - h_trunc) / 2.0  # symmetric truncation approximation
        x = slope * z - root_cut
        if x < 0:
            x = 0.0
        if x > h_trunc:
            x = h_trunc
        out.append(x)
    return out


def main():
    step_path = None
    if "--step" in sys.argv:
        i = sys.argv.index("--step")
        step_path = sys.argv[i + 1] if i + 1 < len(sys.argv) else None

    doc = App.newDocument("BSW_XZ_Compare")
    internal, external = generate_bsw_tables()

    major = 0.25 * 25.4
    pitch = 25.4 / 20.0
    minor_i = basic_minor(major, pitch)
    minor_e = minor_i - 0.15

    # True BSW internal (one pitch XZ)
    w_i = profile_wire(internal, minor_i, pitch)
    o_i = doc.addObject("Part::Feature", "BSW_1_4_20_internal_XZ")
    o_i.Shape = w_i
    o_i.ViewObject.LineColor = (0.78, 0.47, 0.25) if hasattr(o_i, "ViewObject") and o_i.ViewObject else None

    w_e = profile_wire(external, minor_e, pitch)
    o_e = doc.addObject("Part::Feature", "BSW_1_4_20_external_XZ")
    o_e.Shape = w_e

    # Fake truncated-55 for contrast (same minor as wrong V-preset)
    H55 = pitch / (2 * math.tan(math.radians(27.5)))
    fake_minor = major - 2 * (5.0 / 8.0) * H55
    fake = truncated55_offsets()
    w_f = profile_wire(fake, fake_minor, pitch)
    o_f = doc.addObject("Part::Feature", "Fake_truncated55_V_XZ")
    o_f.Shape = w_f

    # Reference lines: major / minor radii as vertical segments
    for name, r in [
        ("ref_major_r", major / 2),
        ("ref_minor_basic_r", minor_i / 2),
        ("ref_minor_fake_r", fake_minor / 2),
    ]:
        line = Part.makeLine(App.Vector(r, 0, 0), App.Vector(r, 0, pitch))
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = line

    if step_path and os.path.isfile(step_path):
        Part.insert(step_path, doc.Name)
        print(f"Imported STEP: {step_path}")
        print("Tip: Part -> Cross-sections… on XZ, or SectionCut, then compare wires.")

    doc.recompute()
    OUT.parent.mkdir(exist_ok=True)
    doc.saveAs(str(OUT))
    print(f"Saved {OUT}")
    print(f"1/4-20 major={major:.4f} P={pitch:.4f}")
    print(f"  BSW basic minor={minor_i:.4f}  fake5/8H minor={fake_minor:.4f}")
    print(f"  depth h={DEPTH * pitch:.4f} mm  (h/P={DEPTH:.6f})")
    App.closeDocument(doc.Name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
