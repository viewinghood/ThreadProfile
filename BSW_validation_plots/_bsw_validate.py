#!/usr/bin/env python3
"""BSW / Whitworth profile validation plots (mirrors _pg_validation_plots).

Run from repo root:
  python _bsw_validation_plots/_bsw_validate.py
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "Resources" / "assets"))
from generate_bsw_profile_data import (  # noqa: E402
    DEPTH,
    H,
    R,
    ROOT_EXTERNAL,
    SLOPE,
    basic_minor,
    generate_bsw_tables,
    whitworth_offset,
)

src = (ROOT / "ThreadProfileCmd.py").read_text(encoding="utf-8")


def extract(name: str):
    m = re.search(rf"{name}\s*=\s*\[([^\]]+)\]", src)
    return [float(x) for x in m.group(1).split(",") if x.strip()]


def extract_default(prop: str):
    m = re.search(rf"obj\.{prop}\s*=\s*\[([^\]]+)\]", src)
    return [float(x) for x in m.group(1).split(",") if x.strip()]


internal = extract("internal_bsw_data")
external = extract("external_bsw_data")
v60_int = extract_default("internal_data")
gen_i, gen_e = generate_bsw_tables()

assert internal == gen_i and external == gen_e
print("Embedded tables match generator exactly.")

print(
    f"lengths: bsw_int={len(internal)} bsw_ext={len(external)} v60_int={len(v60_int)}"
)
print(
    f"BSW internal [{min(internal):.6f} .. {max(internal):.6f}] "
    f"expect h={DEPTH:.6f}"
)
print(
    f"BSW external [{min(external):.6f} .. {max(external):.6f}] "
    f"expect root={ROOT_EXTERNAL}"
)

# Flank angle from mid-rise samples
zs = [i / 720 for i in range(1, 720)]
# sample on straight flank only (z ~ 0.15..0.25 folded)
samples = [(z, whitworth_offset(z)) for z in [0.12, 0.15, 0.18, 0.22]]
slope = (samples[-1][1] - samples[0][1]) / (samples[-1][0] - samples[0][0])
half = math.degrees(math.atan(1.0 / slope))  # atan(dz/dx) wait: slope=dx/dz = cot(theta)
# dx/dz = cot(27.5) => theta = atan(dz/dx) = atan(1/slope)
theta = math.degrees(math.atan(1.0 / slope))
print(f"flank dx/dz={slope:.6f} (expect {SLOPE:.6f})  half-angle={theta:.3f}° incl={2*theta:.3f}°")

# Chart / formula size check for a few BSW sizes
chart = [
    ("1/4-20", 0.25, 20, 4.72),  # published basic minor ~4.72 mm
    ("3/8-16", 0.375, 16, None),
    ("1/2-12", 0.5, 12, None),
    ("5/8-11", 0.625, 11, None),
    ("3/4-10", 0.75, 10, None),
    ("1-8", 1.0, 8, None),
]
print("\nPreset formula check:")
print(f"{'name':8} {'major':>7} {'P':>7} {'minor':>8} {'chart':>8} {'err':>8}")
for name, maj_in, tpi, chart_min in chart:
    maj = maj_in * 25.4
    P = 25.4 / tpi
    minor = basic_minor(maj, P)
    cref = chart_min if chart_min is not None else float("nan")
    err = minor - chart_min if chart_min is not None else float("nan")
    print(f"{name:8} {maj:7.3f} {P:7.4f} {minor:8.4f} {cref:8.4f} {err:+8.4f}")

# Fake truncated-55 V minor (what PR#72 / old V-preset did) vs true Whitworth
maj = 0.25 * 25.4
P = 25.4 / 20
H55 = P / (2 * math.tan(math.radians(55) / 2))
fake_int = maj - 2 * (5 / 8) * H55
true_int = basic_minor(maj, P)
print(f"\n1/4-20 comparison:")
print(f"  true Whitworth basic minor = {true_int:.4f} mm")
print(f"  truncated-55 V (5/8 H) minor = {fake_int:.4f} mm  (delta {fake_int-true_int:+.4f})")

HERE.mkdir(exist_ok=True)
out = HERE
z = [i / 720 for i in range(720)]

# Tables are 719 samples (k=1..719); pad index 0 for 720-point plots
def pad719(arr):
    return [arr[0]] + list(arr)


bsw_i = pad719(internal)
bsw_e = pad719(external)
v60_i = pad719(v60_int)

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(z, v60_i, label="V60 internal (sharp 60°)", linewidth=1.0, alpha=0.8)
ax.plot(z, bsw_i, label="BSW internal (55° + rounds)", linewidth=1.6)
ax.plot(z, bsw_e, label="BSW external (root −0.018)", linewidth=1.2, linestyle="--")
ax.axhline(DEPTH, color="gray", linestyle=":", linewidth=0.8, label=f"h={DEPTH:.4f}")
ax.axhline(0, color="gray", linestyle=":", linewidth=0.8)
# ideal flank overlay
z_fl = [zi for zi in z if 0.12 <= zi <= 0.35]
x_ideal = [whitworth_offset(0.12) + SLOPE * (zi - 0.12) for zi in z_fl]
ax.plot(z_fl, x_ideal, "k:", linewidth=1.3, label="ideal cot(27.5°) flank")
ax.set_xlabel("normalized pitch position z/P  (index/720)")
ax.set_ylabel("radial offset / pitch  (x with minor at 0)")
ax.set_title("ThreadProfile tables: V60 vs BSW Whitworth")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig(out / "01_profile_tables_compare.png", dpi=140)
plt.close(fig)

# XZ unfolded (Mark-style axial view)
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, arr, title in [
    (axes[0], bsw_i, "BSW internal"),
    (axes[1], bsw_e, "BSW external"),
]:
    ax.fill_between(z, 0, arr, alpha=0.15, color="#c87941")
    ax.plot(z, arr, linewidth=1.5, color="#c87941")
    ax.set_title(title)
    ax.set_xlabel("z / P")
    ax.set_ylabel("x / P (from minor)")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="box")
fig.suptitle("BSW profile unfolded (pitch=1) — rounded crest/root check")
fig.tight_layout()
fig.savefig(out / "02_bsw_xz_unfolded.png", dpi=140)
plt.close(fig)

# Polar face 1/4-20
P = 25.4 / 20
minor_int = basic_minor(0.25 * 25.4, P)
minor_ext = minor_int - 0.15
fig, axes = plt.subplots(1, 2, figsize=(10, 5), subplot_kw=dict(projection="polar"))
for ax, arr, minor, title in [
    (axes[0], bsw_i, minor_int, "1/4-20 BSW Internal"),
    (axes[1], bsw_e, minor_ext, "1/4-20 BSW External (−0.15 clr)"),
]:
    theta = [2 * math.pi * i / 720 for i in range(720)]
    r = [minor / 2 + od * P for od in arr]
    ax.plot(theta + [theta[0]], r + [r[0]], linewidth=1.2, color="#c87941")
    ax.set_title(title)
    ax.set_rticks([minor / 2, minor / 2 + DEPTH * P])
fig.tight_layout()
fig.savefig(out / "03_quarter20_polar_faces.png", dpi=140)
plt.close(fig)

# Major residual for common sizes (formula majors vs profile max)
fig, ax = plt.subplots(figsize=(9, 4))
labels = []
errs = []
for name, maj_in, tpi, _ in chart:
    maj = maj_in * 25.4
    P = 25.4 / tpi
    minor = basic_minor(maj, P)
    maj_calc = minor + 2 * max(internal) * P
    labels.append(name)
    errs.append(maj_calc - maj)
ax.bar(labels, errs, color="#c87941")
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("calc major − nominal major [mm]")
ax.set_title("Preset consistency: nominal major vs profile (h≈0.640327·P)")
ax.tick_params(axis="x", rotation=30)
fig.tight_layout()
fig.savefig(out / "04_major_residuals.png", dpi=140)
plt.close(fig)

# Geometry constants card
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.axis("off")
txt = (
    f"Whitworth form (P=1)\n"
    f"  included angle 55°  →  flank 27.5°\n"
    f"  H = 1/(2 tan 27.5°) = {H:.6f}\n"
    f"  h = (2/3) H         = {DEPTH:.6f}\n"
    f"  r (crest & root)    = {R:.6f}\n"
    f"  external root dip   = {ROOT_EXTERNAL}\n"
    f"  samples             = 719 (k=1..719 of 720)\n"
    f"\n1/4-20 basic minor = {true_int:.4f} mm (chart ~4.72)\n"
    f"truncated-55 V minor = {fake_int:.4f} mm  ← wrong for BSW"
)
ax.text(0.02, 0.95, txt, va="top", family="monospace", fontsize=11)
ax.set_title("BSW geometry constants")
fig.tight_layout()
fig.savefig(out / "05_geometry_constants.png", dpi=140)
plt.close(fig)

print(f"\nPlots written to {out}")
