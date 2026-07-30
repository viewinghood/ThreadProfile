# How the PG `internal_data` / `external_data` were generated

**Repo:** viewinghood/ThreadProfile (fork of mwganson/ThreadProfile)  
**Feature:** PG (Panzergewinde / DIN 40430) thread profiles  
**Date:** 2026-07-30  

Supporting plots: `_pg_validation_plots/`  
Validation script: `_pg_validation_plots/_pg_validate_tmp.py`

---

ThreadProfile already stores each thread form as a list of radial offsets for one pitch (minor at zero, pitch normalized to 1). For PG we followed that same pattern and filled `internal_pg_data` / `external_pg_data` from DIN 40430 geometry plus published size charts — not by eyeballing individual samples. A few practical offsets (print clearance, small external root dip) are called out below so it is clear what is formula and what is a deliberate fit choice.

In `makePoints()` the table is used as:

```text
radius = MinorDiameter/2 + table[i] * Pitch
```

---

## 1. Full method (step by step)

### 1.1 Same data model as existing ThreadProfile tables

As documented in `makeThreadProfile()`:

| Item   | Meaning                                                   |
| ------ | --------------------------------------------------------- |
| Length | ~720 samples over one pitch (`z/P` from 0 → 1)            |
| Value  | radial offset from the **minor** radius, divided by pitch |
| Scale  | `Pitch` and `MinorDiameter` applied at runtime            |
| Use    | closed planar face, swept along a helix                   |

So PG data is a **new profile family**, not a new geometry engine.

### 1.2 What is strictly mathematical

| Quantity                     | Formula / source                  | Guessed?         |
| ---------------------------- | --------------------------------- | ---------------- |
| Flank angle                  | DIN 40430 → **80°** included      | No               |
| Flank slope                  | `dx/dz = cot(40°)`                | No               |
| Sharp-V height (reference)   | `H = 0.5 / tan(40°) ≈ 0.5959 · P` | No               |
| Working height used in table | `h = 0.48 · P`                    | No — from charts |
| Chart depth check            | `(D_major − D_minor) / (2P)`      | No               |
| Pitch                        | `P = 25.4 / TPI` (20 / 18 / 16)   | No               |
| Sample spacing on flanks     | `Δx ≈ cot(40°) / 720` per step    | No               |

**Derivation of `h = 0.48`:**  
For every published size, the radial thread depth is `(Major − Minor) / 2`. Dividing by pitch gives ~0.48 (e.g. PG7: `(12.50 − 11.28) / (2 × 1.27) ≈ 0.480`). The table therefore uses a **single normalized height 0.48**, which then scales correctly with each preset’s pitch.

### 1.3 What is an engineering choice (documented)

These are **conscious design choices**, parallel to existing ThreadProfile practice — not “mystery numbers”:

| Choice                        | Value                            | Why                                                                        |
| ----------------------------- | -------------------------------- | -------------------------------------------------------------------------- |
| Flat crest / flat root        | trapezoid instead of sharp point | Stable FreeCAD sweep; matches chart major/minor; DIN form is shallow 80° V |
| External root offset in table | `−0.018` (pitch units)           | Small root clearance; stock V60 external also dips below 0                 |
| External preset clearance     | `−0.15 mm` on minor              | FDM / print fit (same idea as Bottle); **not** claimed as DIN tolerance    |
| Default size                  | PG 13.5                          | Common cable-gland / sensor size                                           |

So: **flanks and height are formula-driven; clearance offsets are explicit practical knobs.**

### 1.4 How internal vs external differ

```text
Internal:  root = 0.000  …  crest = 0.480
External:  root = −0.018 …  crest = 0.480   (same flank slope)
```

Presets then set:

```text
internal_minor = chart minor
external_minor = chart minor − 0.15   # print clearance
pitch          = 25.4 / TPI
```

Major diameter is **not hard-coded** from the chart into the table; it falls out as:

```text
Major ≈ Minor + 2 · max(table) · Pitch
      = Minor + 0.96 · Pitch
```

That recomputed major matches British Metrics / Sealcon within ~0.015 mm (see plot 04).

---

## 2. Evidence from the validation drawings

### Figure 01 — Profile tables compared

`_pg_validation_plots/01_profile_tables_compare.png`

- V60 / V45 / PG overlaid in the same normalized space.  
- PG internal (green) flanks coincide with the **ideal `cot(40°)`** reference (black dotted).  
- That is the geometric proof of the **80°** flank, not a freehand curve.

### Figure 02 — Unfolded XZ profiles

`_pg_validation_plots/02_pg_xz_unfolded.png`

- Internal: trapezoid, root at 0, crest at 0.48.  
- External: same shape, root slightly below 0 (`−0.018`).  
- Easy visual check of symmetry and truncation.

### Figure 03 — Polar faces (PG 13.5)

`_pg_validation_plots/03_pg13_5_polar_faces.png`

- Shows what FreeCAD actually sweeps: `radius = Minor/2 + od·Pitch`.  
- Confirms the table is used exactly like the other thread types.

### Figure 04 — Major residuals vs chart

`_pg_validation_plots/04_major_residuals.png`

- `Minor + 2·0.48·P − chart Major` stays within about **±0.015 mm**.  
- Proves presets + table height are consistent with the published majors.

### Figure 05 — Chart depth / pitch

`_pg_validation_plots/05_depth_over_pitch.png`

- Chart `(Major−Minor)/(2P)` sits on / next to the **0.48** line used in the table.

---

## 3. Sources used for numbers

1. **DIN 40430** — PG / Panzergewinde: straight thread, **80°** flank angle, shallow form for thin-wall conduit.  
2. **British Metrics PG thread chart** — size, TPI, major (ext), minor (int).  
3. **Sealcon “Thread Specifications & Pitch” catalog page** — major diameters and pitches in mm (cross-check).  
4. **Existing ThreadProfile convention** — 720-point normalized tables + optional print clearance (Bottle precedent).

---

## 4. Limitations

1. Tables have **719** samples in the shipped arrays (same off-by-one pattern as several stock tables), generated with **1/720** flank stepping. Harmless at typical `Quality` settings.  
2. The form is a **truncated / trapezoidal** approximation suitable for CAD sweep and FDM, not a claim of full DIN 40431 gauge geometry (pointed crest details, tolerance classes).  
3. The **0.15 mm** external print clearance is intentional for printing; disable or set to 0 for “chart nominal” mating studies.  
4. `major_ext` passed into the local preset helper is unused; major comes from the profile height, by design of ThreadProfile.
