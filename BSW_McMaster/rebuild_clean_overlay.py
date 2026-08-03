# Clean Mark-style overlay: one part, colors, shank-only thread zone.
# Green issues in the first overlay were mostly McMaster full-section CS
# (hex + glitchy wire compound). This rebuild separates layers clearly.
#
# freecadcmd.exe ...\rebuild_clean_overlay.py

from __future__ import annotations

import math
import sys
from pathlib import Path

import FreeCAD
import Part

HERE = Path(r"C:\Users\ritchie\ThreadDefinitions\BSW_McMaster")
REPO = Path(r"C:\Users\ritchie\ThreadProfile")
STEP = HERE / "1095K104_Zinc-Plated Steel Grease Fitting.STEP"
OUT = HERE / "BSW_1095K104_clean_overlay.FCStd"
PLOT = REPO / "_bsw_validation_plots"

sys.path.insert(0, str(REPO / "Resources" / "assets"))
from generate_bsw_profile_data import DEPTH, basic_minor, generate_bsw_tables, whitworth_offset


def largest(shape):
    return max(shape.Solids, key=lambda s: s.Volume)


def set_color(obj, rgb, width=2.0):
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        try:
            obj.ViewObject.LineColor = rgb
            obj.ViewObject.PointColor = rgb
            obj.ViewObject.LineWidth = width
        except Exception:
            pass


def wb_profile_wire(minor, pitch, y0, n_pitches, side, use_external=True):
    """True Whitworth axial section — rounded crest/root via continuous function."""
    _, external = generate_bsw_tables()
    internal, _ = generate_bsw_tables()
    table = external if use_external else internal
    # denser sample for visible rounds
    pts = []
    n = 360  # points per pitch
    for c in range(n_pitches):
        for i in range(n):
            z_norm = (i + 0.5) / n
            # use analytic Whitworth, then map like external table
            v = whitworth_offset(z_norm)
            if use_external:
                # same remapping as generator
                # approximate with table lookup
                idx = min(len(table) - 1, max(0, int(round(z_norm * 719)) - 1))
                od = table[idx]
            else:
                od = v
            y = y0 + c * pitch + z_norm * pitch
            x = side * (minor / 2.0 + od * pitch)
            pts.append(FreeCAD.Vector(x, y, 0.0))
    return Part.makePolygon(pts)


def extract_thread_outline(wires, r_lo, r_hi, y_lo, y_hi, side_sign):
    """Keep only section edges in the male-thread band on +X or -X."""
    edges_out = []
    for w in wires:
        for e in w.Edges:
            try:
                ps = e.discretize(Number=40)
            except Exception:
                continue
            keep = []
            for p in ps:
                r = (p.x * p.x + p.z * p.z) ** 0.5
                if r_lo <= r <= r_hi and y_lo <= p.y <= y_hi:
                    if side_sign > 0 and p.x > 0.05:
                        keep.append(p)
                    elif side_sign < 0 and p.x < -0.05:
                        keep.append(p)
            if len(keep) >= 2:
                # rebuild as polyline in Z=0 using (signed x ≈ ±r, y)
                pts = []
                for p in keep:
                    r = (p.x * p.x + p.z * p.z) ** 0.5
                    pts.append(FreeCAD.Vector(side_sign * r, p.y, 0.0))
                # sort by y to avoid scribble
                pts.sort(key=lambda v: v.y)
                # drop huge jumps
                cleaned = [pts[0]]
                for v in pts[1:]:
                    if abs(v.y - cleaned[-1].y) < 0.35 and abs(v.x - cleaned[-1].x) < 1.2:
                        cleaned.append(v)
                    else:
                        if len(cleaned) >= 2:
                            edges_out.append(Part.makePolygon(cleaned))
                        cleaned = [v]
                if len(cleaned) >= 2:
                    edges_out.append(Part.makePolygon(cleaned))
    return edges_out


def main():
    if OUT.exists():
        bak = Path(str(OUT) + ".bak")
        if not bak.exists():
            bak.write_bytes(OUT.read_bytes())

    major = 0.25 * 25.4
    pitch = 25.4 / 26.0
    minor = basic_minor(major, pitch)
    h = DEPTH * pitch

    doc = FreeCAD.newDocument("BSW_clean")
    sh = Part.Shape()
    sh.read(str(STEP))
    solid = largest(sh)

    sobj = doc.addObject("Part::Feature", "McMaster_1095K104_solid")
    sobj.Shape = solid
    sobj.Visibility = False

    wires = None
    for d in (0.0, 1e-3, -1e-3):
        wires = solid.slice(FreeCAD.Vector(0, 0, 1), d)
        if wires:
            break

    # Full CS (hidden by default) — this is what looked "broken" as one green scribble
    full = doc.addObject("Part::Feature", "McMaster_full_XY_cs_HIDDEN")
    full.Shape = Part.Compound(wires)
    full.Visibility = False
    set_color(full, (0.4, 0.4, 0.4), 1.0)

    # Thread band: major 6.35 → r=3.175; minor ~5.1 → r=2.55; CAD root deeper ~2.47
    # Shank on this part is roughly Y negative (from earlier inspect)
    bb = solid.BoundBox
    # use lower half for straight fitting thread
    y_lo = bb.YMin + 0.5
    y_hi = min(-1.0, bb.YMin + 0.45 * bb.YLength)  # prefer -Y shank
    # fallback if window empty
    r_lo = minor / 2 - 0.35
    r_hi = major / 2 + 0.20

    # probe which Y side has thread points
    def count_band(ylo, yhi):
        n = 0
        for w in wires:
            for e in w.Edges:
                try:
                    for p in e.discretize(Number=20):
                        r = (p.x * p.x + p.z * p.z) ** 0.5
                        if r_lo <= r <= r_hi and ylo <= p.y <= yhi and abs(p.x) > 0.2:
                            n += 1
                except Exception:
                    pass
        return n

    c_neg = count_band(bb.YMin, 0.0)
    c_pos = count_band(0.0, bb.YMax)
    print(f"thread samples -Y:{c_neg} +Y:{c_pos}")
    if c_neg >= c_pos:
        y_lo, y_hi = bb.YMin + 0.3, min(-0.5, -0.5)
        # better: from YMin up to hex start — hex is wider
        y_lo, y_hi = bb.YMin + 0.2, -1.5
    else:
        y_lo, y_hi = 1.5, bb.YMax - 0.2

    # refine: find Y where r in thread band exists
    ys = []
    for w in wires:
        for e in w.Edges:
            try:
                for p in e.discretize(Number=60):
                    r = (p.x * p.x + p.z * p.z) ** 0.5
                    if (minor / 2 - 0.2) <= r <= (major / 2 + 0.05) and abs(p.x) > 1.0:
                        ys.append(p.y)
            except Exception:
                pass
    if ys:
        ys.sort()
        # take densest quartile near end of fitting
        y_lo = ys[int(0.05 * len(ys))]
        y_hi = ys[int(0.55 * len(ys))]
        if y_hi - y_lo < 2 * pitch:
            y_hi = y_lo + 4 * pitch
        print(f"auto thread Y window {y_lo:.3f}..{y_hi:.3f} (n={len(ys)})")

    mcm_edges = []
    for side in (+1, -1):
        mcm_edges.extend(extract_thread_outline(wires, r_lo, r_hi, y_lo, y_hi, side))
    if mcm_edges:
        mcm = doc.addObject("Part::Feature", "McMaster_thread_band_ONLY")
        mcm.Shape = Part.Compound(mcm_edges)
        set_color(mcm, (0.85, 0.35, 0.10), 2.5)  # orange = McMaster
        print(f"McMaster thread edges: {len(mcm_edges)}")
    else:
        print("WARNING: no McMaster thread edges extracted")

    # WB Whitworth overlay — copper
    n_pitches = max(3, int((y_hi - y_lo) / pitch))
    y0 = y_lo
    wb_parts = []
    for side in (+1, -1):
        wb_parts.append(wb_profile_wire(minor, pitch, y0, n_pitches, side, True))
    wb = doc.addObject("Part::Feature", "WB_Whitworth_rounded_ext")
    wb.Shape = Part.Compound(wb_parts)
    set_color(wb, (0.20, 0.75, 0.35), 2.8)  # green = our true Whitworth
    print(f"WB overlay {n_pitches} pitches from y0={y0:.3f}")

    # Reference radii
    for name, r, rgb in [
        ("ref_major_r", major / 2, (0.9, 0.9, 0.2)),
        ("ref_minor_whitworth_r", minor / 2, (0.2, 0.6, 0.9)),
        ("ref_minor_mcm_approx_r", (major / 2) - 0.72 * pitch, (0.7, 0.7, 0.7)),
    ]:
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = Part.makeLine(FreeCAD.Vector(r, y_lo, 0), FreeCAD.Vector(r, y_hi, 0))
        set_color(obj, rgb, 1.2)

    # Annotation notes as document string
    doc.Label = "Orange=McMaster CAD (simplified V); Green=WB Whitworth rounded h=0.64P"

    doc.recompute()
    doc.saveAs(str(OUT))
    PLOT.mkdir(exist_ok=True)
    (PLOT / OUT.name).write_bytes(OUT.read_bytes())
    print("saved", OUT)
    print(
        f"chart major={major:.3f} whitworth minor={minor:.3f} P={pitch:.4f} h={h:.4f}"
    )
    print("Open in FreeCAD, view along +Z. Hide full CS. Compare orange vs green.")
    FreeCAD.closeDocument(doc.Name)


main()
