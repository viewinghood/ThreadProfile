#!/usr/bin/env python3
"""Plot McMaster BSF measured depth vs Whitworth / truncated-V expectations."""
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parent if HERE.name != "_bsw_validation_plots" else HERE.parent
# script lives in ThreadDefinitions/BSW_McMaster OR we copy to validation
OUT = Path(r"C:\Users\ritchie\ThreadProfile\_bsw_validation_plots")

# From measurement (mm)
rows = [
    # name, major, P, d_maj_m, d_min_m
    ("1095K104\n1/4-26 BSF", 6.350, 0.9769, 6.350, 4.941),
    ("1095K105\n3/8-20 BSF", 9.525, 1.2700, 9.525, 7.695),
    ("2408K31\n5/16-22 BSF", 7.9375, 1.1545, 7.937, 6.274),
    ("1095K122\n1/4-26 90°", 6.350, 0.9769, 6.350, 4.943),
]

H = 0.960491
h_whit = (2.0 / 3.0) * H  # 0.640327
h_34 = 0.75 * H  # 0.720368 — matches McMaster CAD depth/P

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

# depth/P
names = [r[0] for r in rows]
hP = [((r[3] - r[4]) / 2) / r[2] for r in rows]
ax = axes[0]
ax.bar(range(len(names)), hP, color="#c87941", label="McMaster CAD")
ax.axhline(h_whit, color="#2c5f7c", linewidth=2, label=f"Whitworth h/P={h_whit:.3f}")
ax.axhline(h_34, color="#666666", linestyle="--", linewidth=1.5, label=f"(3/4)·H={h_34:.3f}")
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("thread depth / pitch")
ax.set_title("Depth form factor")
ax.legend(loc="lower right", fontsize=8)
ax.grid(True, axis="y", alpha=0.3)

# major residual
ax = axes[1]
dmaj = [r[3] - r[1] for r in rows]
dmin_w = [r[4] - (r[1] - 2 * h_whit * r[2]) for r in rows]
x = range(len(names))
ax.bar([i - 0.18 for i in x], dmaj, width=0.36, color="#2c5f7c", label="Δ major (CAD−chart)")
ax.bar([i + 0.18 for i in x], dmin_w, width=0.36, color="#c87941", label="Δ minor (CAD−Whitworth basic)")
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(list(x))
ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("mm")
ax.set_title("Diameter residuals")
ax.legend(fontsize=8)
ax.grid(True, axis="y", alpha=0.3)

fig.suptitle("McMaster BSF grease-fitting STEPs vs Whitworth form (ThreadProfile BSW tables)")
fig.tight_layout()
OUT.mkdir(exist_ok=True)
fig.savefig(OUT / "06_mcmaster_bsf_vs_whitworth.png", dpi=140)
fig.savefig(Path(r"C:\Users\ritchie\ThreadDefinitions\BSW_McMaster") / "06_mcmaster_bsf_vs_whitworth.png", dpi=140)
print("wrote plots")
