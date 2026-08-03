# Measure & overlay McMaster BSF grease fittings (axis = Y) vs WB Whitworth tables.
# "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" ...\measure_bsw_mcmaster.py

from __future__ import annotations

import math
import sys
from pathlib import Path

import FreeCAD
import Part

HERE = Path(r"C:\Users\ritchie\ThreadDefinitions\BSW_McMaster")
REPO = Path(r"C:\Users\ritchie\ThreadProfile")
OUT_TXT = HERE / "measure_bsw_mcmaster_out.txt"
OUT_FCSTD = HERE / "BSW_McMaster_XZ_overlay.FCStd"
PLOT_DIR = REPO / "_bsw_validation_plots"

sys.path.insert(0, str(REPO / "Resources" / "assets"))
from generate_bsw_profile_data import DEPTH, ROOT_EXTERNAL, basic_minor, generate_bsw_tables

PARTS = [
    {
        "id": "1095K104",
        "file": "1095K104_Zinc-Plated Steel Grease Fitting.STEP",
        "label": "1/4-26 BSF",
        "major_in": 0.25,
        "tpi": 26.0,
    },
    {
        "id": "1095K105",
        "file": "1095K105_Zinc-Plated Steel Grease Fitting.STEP",
        "label": "3/8-20 BSF",
        "major_in": 0.375,
        "tpi": 20.0,
    },
    {
        "id": "2408K31",
        "file": "2408K31_Zinc-Plated Steel Grease Fitting.STEP",
        "label": "5/16-22 BSF",
        "major_in": 5.0 / 16.0,
        "tpi": 22.0,
    },
    {
        "id": "1095K122",
        "file": "1095K122_Zinc-Plated Steel Grease Fitting.STEP",
        "label": "1/4-26 BSF 90deg",
        "major_in": 0.25,
        "tpi": 26.0,
        "elbow": True,
    },
]


def log(lines, msg):
    print(msg)
    lines.append(msg)


def mid_quantile(vals, lo=0.25, hi=0.75):
    vals = sorted(vals)
    if not vals:
        return None
    a = int(len(vals) * lo)
    b = max(a + 1, int(len(vals) * hi))
    sel = vals[a:b]
    return sum(sel) / len(sel)


def local_extrema(pts, bin_w):
    bins = {}
    for r, a in pts:
        key = round(a / bin_w) * bin_w
        bins.setdefault(key, []).append(r)
    keys = sorted(bins)
    series = [(k, min(bins[k]), max(bins[k])) for k in keys if bins[k]]
    mins, maxs = [], []
    for i in range(1, len(series) - 1):
        a, mn, mx = series[i]
        if mn <= series[i - 1][1] and mn <= series[i + 1][1]:
            mins.append((a, mn))
        if mx >= series[i - 1][2] and mx >= series[i + 1][2]:
            maxs.append((a, mx))
    return mins, maxs


def pitch_median(extrema, lo, hi):
    gaps = [extrema[i + 1][0] - extrema[i][0] for i in range(len(extrema) - 1)]
    gaps = sorted(g for g in gaps if lo < g < hi)
    if not gaps:
        return None, 0
    return gaps[len(gaps) // 2], len(gaps)


def largest_solid(shape):
    if not shape.Solids:
        return shape
    return max(shape.Solids, key=lambda s: s.Volume)


def slice_axis_plane(solid, plane="Z"):
    """Plane through Y-axis: Z=0 -> XY section; X=0 -> ZY section."""
    normal = FreeCAD.Vector(0, 0, 1) if plane == "Z" else FreeCAD.Vector(1, 0, 0)
    for d in (0.0, 1e-3, -1e-3, 0.01, -0.01):
        wires = solid.slice(normal, d)
        if wires:
            return wires, d
    return [], None


def sample_radial_axial(wires, plane="Z", n=80):
    """Return (r, axial_y, signed_radial_for_plot) samples.
    For Z=0 plane: radial from X, axial=Y. Keep +X side for overlay.
    """
    pts = []
    for w in wires:
        for e in w.Edges:
            try:
                for p in e.discretize(Number=n):
                    if plane == "Z":
                        r = abs(p.x)  # in Z=0, radial ≈ |x| if near plane
                        # more accurate: hypot(x,z) but z~0
                        r = (p.x * p.x + p.z * p.z) ** 0.5
                        pts.append((r, p.y, p.x))
                    else:
                        r = (p.y * p.y + p.z * p.z) ** 0.5
                        # wait axis is Y: radial = hypot(x,z), axial=y
                        r = (p.x * p.x + p.z * p.z) ** 0.5
                        pts.append((r, p.y, p.z))
            except Exception:
                pass
    return pts


def profile_polyline(offsets, minor, pitch, y0, n_copies, side=+1):
    """Profile in XY plane (Z=0): x = side*(minor/2 + od*P), y along axis."""
    pts = []
    for c in range(n_copies):
        for i, od in enumerate(offsets):
            y = y0 + c * pitch + (i + 1) / 720.0 * pitch
            x = side * (minor / 2.0 + od * pitch)
            pts.append(FreeCAD.Vector(x, y, 0.0))
    return Part.makePolygon(pts)


def analyze(lines, pts, major, pitch, label):
    r_maj = major / 2.0
    r_min = basic_minor(major, pitch) / 2.0
    lo, hi = r_min - 0.40, r_maj + 0.25
    chunk = [(r, a) for r, a, *_ in pts if lo <= r <= hi]
    log(lines, f"\n=== {label} band r={lo:.3f}..{hi:.3f} n={len(chunk)} ===")
    log(lines, f"chart major={major:.4f} minor={2*r_min:.4f} P={pitch:.4f} h={DEPTH*pitch:.4f}")
    if len(chunk) < 50:
        log(lines, "too few points")
        return None

    # restrict to shank Y region: prefer lower half of axial span in band
    ax = [a for _, a in chunk]
    a_lo, a_hi = min(ax), max(ax)
    # use middle 60% of axial span in band
    a0 = a_lo + 0.15 * (a_hi - a_lo)
    a1 = a_hi - 0.15 * (a_hi - a_lo)
    chunk2 = [(r, a) for r, a in chunk if a0 <= a <= a1]
    if len(chunk2) >= 40:
        chunk = chunk2
    log(lines, f"axial window y={a0:.3f}..{a1:.3f} n={len(chunk)}")

    bin_w = max(0.010, pitch / 50.0)
    mins, maxs = local_extrema(chunk, bin_w)
    crest = mid_quantile([r for _, r in maxs]) if maxs else None
    root = mid_quantile([r for _, r in mins]) if mins else None
    rs = sorted(r for r, _ in chunk)
    r_hi = mid_quantile(rs[int(0.80 * len(rs)) :], 0, 1)
    r_lo = mid_quantile(rs[: max(1, int(0.20 * len(rs)))], 0, 1)

    p_lo, p_hi = pitch * 0.65, pitch * 1.40
    pc, nc = pitch_median(maxs, p_lo, p_hi)
    pr, nr = pitch_median(mins, p_lo, p_hi)

    if crest is not None:
        log(lines, f"crest extrema: d={2*crest:.4f} (n={len(maxs)})")
    if root is not None:
        log(lines, f"root  extrema: d={2*root:.4f} (n={len(mins)})")
    log(lines, f"quant hi/lo: d_hi={2*r_hi:.4f} d_lo={2*r_lo:.4f}")
    if pc:
        log(lines, f"pitch crests={pc:.4f} (n={nc}) expect {pitch:.4f}")
    if pr:
        log(lines, f"pitch roots ={pr:.4f} (n={nr})")

    d_maj = 2 * (crest if crest is not None else r_hi)
    d_min = 2 * (root if root is not None else r_lo)
    depth = (d_maj - d_min) / 2.0
    log(lines, f"depth h~{depth:.4f} expect {DEPTH*pitch:.4f}  h/P~{depth/pitch:.4f} expect {DEPTH:.4f}")
    log(lines, f"err major {d_maj-major:+.4f}  minor {d_min-2*r_min:+.4f}")
    return {
        "d_maj": d_maj,
        "d_min": d_min,
        "depth": depth,
        "pitch": pc or pr,
        "ymin": a0,
        "ymax": a1,
        "crest": crest or r_hi,
        "root": root or r_lo,
    }


def main():
    lines = []
    for p in (OUT_TXT, OUT_FCSTD):
        if p.exists():
            bak = Path(str(p) + ".bak")
            if not bak.exists():
                bak.write_bytes(p.read_bytes())

    _, external = generate_bsw_tables()
    doc = FreeCAD.newDocument("BSW_McMaster")

    log(lines, "=== McMaster BSF grease fittings vs WB Whitworth form ===")
    log(lines, f"h/P={DEPTH:.6f}  ext_root={ROOT_EXTERNAL}")
    log(lines, "CAD axis = Y; section Z=0 (XY). Same 55° form as BSW; BSF = fine pitch.")

    results = []
    for spec in PARTS:
        step = HERE / spec["file"]
        log(lines, f"\n######## {spec['id']} {spec['label']} ########")
        if not step.is_file():
            log(lines, "MISSING file")
            continue

        major = spec["major_in"] * 25.4
        pitch = 25.4 / spec["tpi"]
        minor = basic_minor(major, pitch)

        sh = Part.Shape()
        sh.read(str(step))
        solid = largest_solid(sh)
        bb = solid.BoundBox
        log(
            lines,
            f"main solid BB {bb.XLength:.2f}x{bb.YLength:.2f}x{bb.ZLength:.2f} "
            f"Y {bb.YMin:.2f}..{bb.YMax:.2f} vol={solid.Volume:.1f}",
        )

        sobj = doc.addObject("Part::Feature", f"{spec['id']}_solid")
        sobj.Shape = solid
        sobj.Visibility = False

        wires, d = slice_axis_plane(solid, "Z")
        log(lines, f"slice Z={d} wires={len(wires) if wires else 0}")
        if not wires:
            log(lines, "no section")
            continue

        cs = doc.addObject("Part::Feature", f"{spec['id']}_XY_cs")
        cs.Shape = Part.Compound(wires)

        pts = sample_radial_axial(wires, "Z")
        rs = [r for r, *_ in pts]
        ys = [y for _, y, *_ in pts]
        log(lines, f"samples={len(pts)} r={min(rs):.3f}..{max(rs):.3f} y={min(ys):.3f}..{max(ys):.3f}")

        bins = {}
        for r, *_ in pts:
            k = round(r * 5) / 5.0
            bins[k] = bins.get(k, 0) + 1
        log(lines, "radius hist d:")
        for r in sorted(bins):
            if bins[r] < 15:
                continue
            log(lines, f"  d={2*r:6.2f} n={bins[r]:4d} {'#'*min(40, bins[r]//3)}")

        res = analyze(lines, pts, major, pitch, spec["label"])
        if not res:
            continue
        results.append((spec, major, pitch, minor, res))

        # Overlay WB external profile (±X) along Y in thread window
        ymid = 0.5 * (res["ymin"] + res["ymax"])
        span = res["ymax"] - res["ymin"]
        n_turns = max(2, int(round(span / pitch)) + 1)
        y0 = ymid - 0.5 * n_turns * pitch
        w_pos = profile_polyline(external, minor, pitch, y0, n_turns, +1)
        w_neg = profile_polyline(external, minor, pitch, y0, n_turns, -1)
        wb = doc.addObject("Part::Feature", f"WB_{spec['id']}_ext_XY")
        wb.Shape = Part.Compound([w_pos, w_neg])

        for name, rr in [
            (f"ref_{spec['id']}_maj", major / 2),
            (f"ref_{spec['id']}_min", minor / 2),
        ]:
            doc.addObject("Part::Feature", name).Shape = Part.makeLine(
                FreeCAD.Vector(rr, res["ymin"], 0),
                FreeCAD.Vector(rr, res["ymax"], 0),
            )
        log(lines, f"overlay WB {n_turns} pitches at y0={y0:.3f}")

    log(lines, "\n=== SUMMARY ===")
    log(
        lines,
        f"{'part':10} {'size':14} {'maj_m':>7} {'maj_c':>7} {'eMaj':>7} "
        f"{'min_m':>7} {'min_c':>7} {'eMin':>7} {'h_m':>6} {'h_c':>6} {'P':>6} flag",
    )
    ok_n = 0
    for spec, major, pitch, minor, res in results:
        eMaj = res["d_maj"] - major
        eMin = res["d_min"] - minor
        h_c = DEPTH * pitch
        maj_ok = abs(eMaj) < 0.30
        min_ok = abs(eMin) < 0.40
        h_ok = abs(res["depth"] - h_c) < 0.25
        p_ok = res["pitch"] is None or abs(res["pitch"] - pitch) < 0.10
        # McMaster CAD often uses simplified / truncated thread — accept form if depth & pitch ok
        flag = "OK" if ((maj_ok or h_ok) and (min_ok or h_ok) and p_ok) else "CHECK"
        if flag == "OK":
            ok_n += 1
        log(
            lines,
            f"{spec['id']:10} {spec['label']:14} {res['d_maj']:7.3f} {major:7.3f} {eMaj:+7.3f} "
            f"{res['d_min']:7.3f} {minor:7.3f} {eMin:+7.3f} "
            f"{res['depth']:6.3f} {h_c:6.3f} {(res['pitch'] or 0):6.3f} {flag}",
        )

    log(lines, f"\nmeasured {len(results)}  OK-ish {ok_n}")
    log(
        lines,
        "Note: grease-fitting STEPs may simplify crest/root; still validate 55° Whitworth "
        "depth≈0.64P and pitch. Not a substitute for a real BSW bolt STEP.",
    )

    doc.recompute()
    doc.saveAs(str(OUT_FCSTD))
    log(lines, f"saved {OUT_FCSTD}")
    PLOT_DIR.mkdir(exist_ok=True)
    dest = PLOT_DIR / OUT_FCSTD.name
    dest.write_bytes(OUT_FCSTD.read_bytes())
    log(lines, f"copied {dest}")

    FreeCAD.closeDocument(doc.Name)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT_TXT)


main()
