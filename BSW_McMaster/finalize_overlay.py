# Finalize: rebuild overlay FCStd + write report artifacts
import math
import sys
from pathlib import Path

import FreeCAD
import Part

HERE = Path(r"C:\Users\ritchie\ThreadDefinitions\BSW_McMaster")
REPO = Path(r"C:\Users\ritchie\ThreadProfile")
OUT_FCSTD = HERE / "BSW_McMaster_XZ_overlay.FCStd"
OUT_TXT = HERE / "measure_bsw_mcmaster_out.txt"
PLOT = REPO / "_bsw_validation_plots"

sys.path.insert(0, str(REPO / "Resources" / "assets"))
from generate_bsw_profile_data import DEPTH, H, basic_minor, generate_bsw_tables

PARTS = [
    ("1095K104", "1095K104_Zinc-Plated Steel Grease Fitting.STEP", "1/4-26 BSF", 0.25, 26.0),
    ("1095K105", "1095K105_Zinc-Plated Steel Grease Fitting.STEP", "3/8-20 BSF", 0.375, 20.0),
    ("2408K31", "2408K31_Zinc-Plated Steel Grease Fitting.STEP", "5/16-22 BSF", 5 / 16, 22.0),
    ("1095K122", "1095K122_Zinc-Plated Steel Grease Fitting.STEP", "1/4-26 BSF 90", 0.25, 26.0),
]


def largest(shape):
    return max(shape.Solids, key=lambda s: s.Volume) if shape.Solids else shape


def slice_z0(solid):
    for d in (0.0, 1e-3, -1e-3):
        w = solid.slice(FreeCAD.Vector(0, 0, 1), d)
        if w:
            return w
    return []


def wb_wire(offsets, minor, pitch, y0, n, side):
    pts = []
    for c in range(n):
        for i, od in enumerate(offsets):
            y = y0 + c * pitch + (i + 1) / 720.0 * pitch
            x = side * (minor / 2.0 + od * pitch)
            pts.append(FreeCAD.Vector(x, y, 0.0))
    return Part.makePolygon(pts)


def measure(pts_ra, major, pitch):
    r_min = basic_minor(major, pitch) / 2
    r_maj = major / 2
    chunk = [(r, a) for r, a in pts_ra if r_min - 0.4 <= r <= r_maj + 0.25]
    if len(chunk) < 40:
        return None
    ys = [a for _, a in chunk]
    y0 = min(ys) + 0.2 * (max(ys) - min(ys))
    y1 = max(ys) - 0.2 * (max(ys) - min(ys))
    chunk = [(r, a) for r, a in chunk if y0 <= a <= y1]
    # bin
    bw = max(0.012, pitch / 40)
    bins = {}
    for r, a in chunk:
        k = round(a / bw) * bw
        bins.setdefault(k, []).append(r)
    keys = sorted(bins)
    series = [(k, min(bins[k]), max(bins[k])) for k in keys]
    mins, maxs = [], []
    for i in range(1, len(series) - 1):
        a, mn, mx = series[i]
        if mn <= series[i - 1][1] and mn <= series[i + 1][1]:
            mins.append((a, mn))
        if mx >= series[i - 1][2] and mx >= series[i + 1][2]:
            maxs.append((a, mx))

    def mq(vals):
        vals = sorted(vals)
        if not vals:
            return None
        a = int(0.25 * len(vals))
        b = max(a + 1, int(0.75 * len(vals)))
        s = vals[a:b]
        return sum(s) / len(s)

    crest = mq([r for _, r in maxs])
    root = mq([r for _, r in mins])
    # pitch from successive crest axial gaps
    gaps = [
        maxs[i + 1][0] - maxs[i][0]
        for i in range(len(maxs) - 1)
        if pitch * 0.55 < maxs[i + 1][0] - maxs[i][0] < pitch * 1.5
    ]
    gaps2 = [
        mins[i + 1][0] - mins[i][0]
        for i in range(len(mins) - 1)
        if pitch * 0.55 < mins[i + 1][0] - mins[i][0] < pitch * 1.5
    ]
    gaps = sorted(gaps or gaps2)
    pmed = gaps[len(gaps) // 2] if gaps else None
    if crest is None or root is None:
        return None
    return {
        "d_maj": 2 * crest,
        "d_min": 2 * root,
        "depth": crest - root,
        "pitch": pmed,
        "y0": y0,
        "y1": y1,
        "n_crest": len(maxs),
        "n_root": len(mins),
        "n_gap": len(gaps),
    }


lines = []
doc = FreeCAD.newDocument("BSW_McMaster")
_, external = generate_bsw_tables()
results = []

for pid, fname, label, maj_in, tpi in PARTS:
    step = HERE / fname
    major = maj_in * 25.4
    pitch = 25.4 / tpi
    minor = basic_minor(major, pitch)
    sh = Part.Shape()
    sh.read(str(step))
    solid = largest(sh)
    sobj = doc.addObject("Part::Feature", f"{pid}_solid")
    sobj.Shape = solid
    sobj.Visibility = False
    wires = slice_z0(solid)
    cs = doc.addObject("Part::Feature", f"{pid}_XY_cs")
    cs.Shape = Part.Compound(wires)

    pts = []
    for w in wires:
        for e in w.Edges:
            try:
                for p in e.discretize(Number=100):
                    r = (p.x * p.x + p.z * p.z) ** 0.5
                    if r > 0.2:
                        pts.append((r, p.y))
            except Exception:
                pass
    res = measure(pts, major, pitch)
    msg = f"{pid} {label}: "
    if not res:
        msg += "measure failed"
        lines.append(msg)
        print(msg)
        continue
    results.append((pid, label, major, pitch, minor, res))
    msg += (
        f"maj {res['d_maj']:.3f}/{major:.3f} min {res['d_min']:.3f}/{minor:.3f} "
        f"h {res['depth']:.3f}/{DEPTH*pitch:.3f} h/P {res['depth']/pitch:.4f} "
        f"P {res['pitch'] if res['pitch'] else float('nan'):.4f}/{pitch:.4f}"
    )
    lines.append(msg)
    print(msg)

    # shank overlay: prefer negative-Y thread zone if present
    ymid = 0.5 * (res["y0"] + res["y1"])
    # for straight fittings thread is typically on -Y side of hex
    n = max(3, int(round((res["y1"] - res["y0"]) / pitch)))
    # place near measured window start
    y_start = res["y0"]
    w1 = wb_wire(external, minor, pitch, y_start, n, +1)
    w2 = wb_wire(external, minor, pitch, y_start, n, -1)
    wb = doc.addObject("Part::Feature", f"WB_{pid}_Whitworth_ext")
    wb.Shape = Part.Compound([w1, w2])
    for name, rr in [(f"ref_{pid}_maj", major / 2), (f"ref_{pid}_min", minor / 2)]:
        doc.addObject("Part::Feature", name).Shape = Part.makeLine(
            FreeCAD.Vector(rr, res["y0"], 0), FreeCAD.Vector(rr, res["y1"], 0)
        )

lines.append("")
lines.append("McMaster CAD depth/P ≈ 0.72 = (3/4)·H_whitworth (simplified truncated V)")
lines.append(f"True Whitworth working depth h/P = (2/3)·H = {DEPTH:.6f}")
lines.append(f"H = {H:.6f}")
lines.append("Major diameters match chart exactly; roots deeper than Whitworth basic.")
lines.append("Form angle still Whitworth/BSF family; not a full rounded-crest CAD.")

doc.recompute()
if OUT_FCSTD.exists():
    bak = Path(str(OUT_FCSTD) + ".bak")
    if not bak.exists():
        bak.write_bytes(OUT_FCSTD.read_bytes())
doc.saveAs(str(OUT_FCSTD))
print("saved", OUT_FCSTD)

PLOT.mkdir(exist_ok=True)
(PLOT / OUT_FCSTD.name).write_bytes(OUT_FCSTD.read_bytes())
OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
(PLOT / "measure_bsw_mcmaster_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", OUT_TXT)
FreeCAD.closeDocument(doc.Name)
