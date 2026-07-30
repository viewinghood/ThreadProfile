# PG profile validation — run from repo root or this folder:
#   python _pg_validation_plots/_pg_validate_tmp.py
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
src = (ROOT / "ThreadProfileCmd.py").read_text(encoding="utf-8")


def extract(name: str):
    m = re.search(rf"{name}\s*=\s*\[([^\]]+)\]", src)
    return [float(x) for x in m.group(1).split(",") if x.strip()]


def extract_default(prop: str):
    # first assignment obj.<prop> = [ ... ] with long list
    m = re.search(rf"obj\.{prop}\s*=\s*\[([^\]]+)\]", src)
    return [float(x) for x in m.group(1).split(",") if x.strip()]


internal = extract("internal_pg_data")
external = extract("external_pg_data")
v60_int = extract_default("internal_data")
v60_ext = extract_default("external_data")
v45_int = extract_default("internal45_data")

print("lengths:", {k: len(v) for k, v in {
    "pg_int": internal, "pg_ext": external,
    "v60_int": v60_int, "v60_ext": v60_ext, "v45_int": v45_int,
}.items()})


def analyze(label, arr):
    n = len(arr)
    mn, mx = min(arr), max(arr)
    # ascent: first leave near-min to first hit near-max
    i0 = next(i for i, v in enumerate(arr) if abs(v - mn) > 1e-6)
    i1 = next(i for i, v in enumerate(arr) if abs(v - mx) < 1e-8)
    i_leave = i1
    while i_leave < n and abs(arr[i_leave] - mx) < 1e-8:
        i_leave += 1
    zs = [i / n for i in range(i0, i1)]
    xs = arr[i0:i1]
    zmean = sum(zs) / len(zs)
    xmean = sum(xs) / len(xs)
    num = sum((z - zmean) * (x - xmean) for z, x in zip(zs, xs))
    den = sum((z - zmean) ** 2 for z in zs)
    slope = num / den
    half = math.degrees(math.atan(slope))
    rms = math.sqrt(sum((x - (slope * z + (xmean - slope * zmean))) ** 2 for z, x in zip(zs, xs)) / len(xs))
    print(f"\n{label}: n={n} min={mn:.6f} max={mx:.6f}")
    print(f"  root flat pts={i0} ({i0/n*360:.1f} deg / {i0/n:.4f}P)")
    print(f"  crest flat pts={i_leave-i1} ({(i_leave-i1)/n*360:.1f} deg / {(i_leave-i1)/n:.4f}P)")
    print(f"  flank ascent pts={i1-i0} slope={slope:.6f} half-angle={half:.3f} incl={2*half:.3f} RMS={rms:.2e}")
    return dict(i0=i0, i1=i1, i_leave=i_leave, slope=slope, half=half, mn=mn, mx=mx)


a_pg_i = analyze("PG internal", internal)
a_pg_e = analyze("PG external", external)
a_v60_i = analyze("V60 internal", v60_int)
a_v45_i = analyze("V45 internal", v45_int)

tan40 = math.tan(math.radians(40))
tan30 = math.tan(math.radians(30))
print(f"\nExpected tan(40°)={tan40:.6f}  tan(30°)={tan30:.6f}")
print(f"PG slope error vs tan40: {a_pg_i['slope']-tan40:+.6e}")
print(f"Sharp H(80°)={0.5/tan40:.6f}P; trunc height used={a_pg_i['mx']:.6f}P")

chart = [
    ("PG 7", 12.50, 11.28, 20),
    ("PG 9", 15.20, 13.86, 18),
    ("PG 11", 18.60, 17.26, 18),
    ("PG 13.5", 20.40, 19.06, 18),
    ("PG 16", 22.50, 21.16, 18),
    ("PG 21", 28.30, 26.78, 16),
    ("PG 29", 37.00, 35.48, 16),
    ("PG 36", 47.00, 45.48, 16),
    ("PG 42", 54.00, 52.48, 16),
    ("PG 48", 59.30, 57.78, 16),
]
print("\nPreset check (internal major from profile max*2*P + minor):")
print(f"{'name':8} {'P':>7} {'depth/P':>8} {'maj_calc':>9} {'maj_cht':>8} {'err':>8}")
for name, maj, minor, tpi in chart:
    P = 25.4 / tpi
    depth_over_p = (maj - minor) / 2 / P
    maj_calc = minor + 2 * a_pg_i["mx"] * P
    print(f"{name:8} {P:7.4f} {depth_over_p:8.4f} {maj_calc:9.4f} {maj:8.2f} {maj_calc-maj:+8.4f}")

# Plots
out = HERE
out.mkdir(exist_ok=True)

z = [i / 720 for i in range(720)]

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(z, v60_int, label="V60 internal (default)", linewidth=1.2)
ax.plot(z, v45_int, label="V45 internal", linewidth=1.0, alpha=0.85)
ax.plot(z, internal, label="PG internal (80°, h=0.48)", linewidth=1.6)
ax.plot(z, external, label="PG external", linewidth=1.2, linestyle="--")
ax.axhline(0.48, color="gray", linestyle=":", linewidth=0.8)
ax.axhline(0, color="gray", linestyle=":", linewidth=0.8)
# ideal 80° flank overlay on PG ascent region
i0, i1 = a_pg_i["i0"], a_pg_i["i1"]
z_fl = [i / 720 for i in range(i0, i1)]
x_ideal = [tan40 * (zi - z_fl[0]) for zi in z_fl]
ax.plot(z_fl, x_ideal, "k:", linewidth=1.5, label="ideal tan(40°) flank")
ax.set_xlabel("normalized pitch position z/P  (index/720)")
ax.set_ylabel("radial offset / pitch  (x with minor at 0)")
ax.set_title("ThreadProfile 720-point tables: V60 / V45 / PG")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig(out / "01_profile_tables_compare.png", dpi=140)
plt.close(fig)

# Axial sketch style: unfold as XZ profile
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, arr, title in [
    (axes[0], internal, "PG internal"),
    (axes[1], external, "PG external"),
]:
    ax.fill_between(z, 0, arr, alpha=0.15)
    ax.plot(z, arr, linewidth=1.5)
    ax.set_title(title)
    ax.set_xlabel("z / P")
    ax.set_ylabel("x / P (from minor)")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="box")
fig.suptitle("PG profile unfolded (pitch=1) — visual flank / truncation check")
fig.tight_layout()
fig.savefig(out / "02_pg_xz_unfolded.png", dpi=140)
plt.close(fig)

# Polar face used by makePoints (radius = minor/2 + od*P), PG13.5 example
P = 25.4 / 18
minor_int = 19.06
minor_ext = 19.06 - 0.15
fig, axes = plt.subplots(1, 2, figsize=(10, 5), subplot_kw=dict(projection="polar"))
for ax, arr, minor, title in [
    (axes[0], internal, minor_int, "PG 13.5 Internal face"),
    (axes[1], external, minor_ext, "PG 13.5 External face (−0.15 clr)"),
]:
    theta = [2 * math.pi * i / 720 for i in range(720)]
    r = [minor / 2 + od * P for od in arr]
    ax.plot(theta + [theta[0]], r + [r[0]], linewidth=1.2)
    ax.set_title(title)
    ax.set_rticks([minor / 2, minor / 2 + 0.48 * P])
fig.tight_layout()
fig.savefig(out / "03_pg13_5_polar_faces.png", dpi=140)
plt.close(fig)

# Major diameter residual bar chart
fig, ax = plt.subplots(figsize=(9, 4))
names = [c[0] for c in chart]
errs = []
depths = []
for name, maj, minor, tpi in chart:
    P = 25.4 / tpi
    errs.append(minor + 2 * a_pg_i["mx"] * P - maj)
    depths.append((maj - minor) / 2 / P)
ax.bar(names, errs, color="#2c5f7c")
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("calc major − chart major [mm]")
ax.set_title("Preset consistency: chart major vs profile (h=0.48·P)")
ax.tick_params(axis="x", rotation=30)
fig.tight_layout()
fig.savefig(out / "04_major_residuals.png", dpi=140)
plt.close(fig)

print(f"\nPlots written to {out}")
print("depth/P from chart:", [round(d, 5) for d in depths])
