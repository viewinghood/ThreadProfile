# How the BSW / Whitworth profile data were generated

**Repo:** viewinghood/ThreadProfile (fork of mwganson/ThreadProfile)  
**Feature:** BSW (British Standard Whitworth) 55° rounded thread profiles  
**Related upstream discussion:** [PR #72](https://github.com/mwganson/ThreadProfile/pull/72) (DrJPK)  

Supporting plots and FreeCAD files: `_bsw_validation_plots/`  
Generator: `Resources/assets/generate_bsw_profile_data.py` (`--check` must match embedded arrays)

---

ThreadProfile stores each thread form as radial offsets for one pitch (minor at zero, pitch normalized to 1). For BSW we followed the same pattern as PG: a **dedicated command**, a **reproducible generator**, **BSW presets**, and checks — not “UNC presets + Variant 55”.

In `makePoints()` the table is used as:

```text
radius = MinorDiameter/2 + table[i] * Pitch
```

---

## 1. Method

### 1.1 Whitworth geometry (pitch = 1)

| Quantity | Value / formula | Notes |
| -------- | --------------- | ----- |
| Included angle | 55° (flank 27.5°) | BS Whitworth form |
| Sharp height \(H\) | \(1/(2\tan 27.5°) \approx 0.960491\) | Reference triangle |
| Working depth \(h\) | \((2/3)H \approx 0.640327\) | Basic minor \(D-2h\) |
| Crest & root radius \(r\) | \(\approx 0.137329\) | Rounded form |
| Samples | 719 (`k = 1..719` of 720) | Same convention as PG / `thread_builder` |

Internal table: root fillet → straight flank → crest fillet.  
External table: same shape; root remapped to \(-0.018\) (print-friendly dip, as on PG).

### 1.2 Presets

Format: `[name, pitch_mm, external_minor_mm, internal_minor_mm]`

- Internal minor = basic Whitworth \(D - 2h\)
- External minor = internal − 0.15 mm print clearance (same idea as PG / Bottle)
- Sizes: 1/16 in … 6 in BSW (standard TPI list)
- Default: **1/4 in - 20 BSW** (basic minor ≈ 4.72 mm)

**1/4-20 check:** formula minor 4.724 mm vs chart ≈ 4.72 mm.  
Truncated-55 V using metric-style \(5/8\,H\) gives ≈ 4.825 mm — the confusion Mark noted on PR #72.

### 1.3 UX

| Item | Choice |
| ---- | ------ |
| Command | `ThreadProfileCreateBSWObject` — *Create BSW Whitworth thread profile* |
| Icon | `Resources/icons/CreateBSWObject.svg` (copper, distinct from V / PG) |
| Not used | Mixing UNC presets with a “55” variant |
| Calculator menu | Link to BSW chart ([Machining Doctor](https://www.machiningdoctor.com/charts/bsw/)) |

---

## 2. Validation artifacts

| Artifact | Role |
| -------- | ---- |
| `generate_bsw_profile_data.py --check` | Geometry + exact match to embedded tables |
| `_bsw_validate.py` + plots `01`–`05` | Table / polar / residual checks |
| `BSW_1_4_20_XZ_compare.FCStd` | Formula wires vs truncated-55 V |
| `BSW_smoke_profile.FCStd` | Workbench object smoke test |
| `BSW_1095K104_clean_overlay.FCStd` | **Two-colour** Mark-style section: orange = McMaster BSF CAD band, green = WB Whitworth |
| `07_whitworth_vs_mcmaster_form.png` | One-pitch form compare |
| McMaster notes | `ThreadDefinitions/BSW_McMaster/MCMMASTER_BSF_OVERLAY_REPORT.md` |

### McMaster STEPs (limitation)

McMaster does not stock BSW bolts/nuts with CAD. Closest Whitworth-family STEPs are **BSF grease fittings** (e.g. 1095K104, 1/4"-26 BSF). Majors match the chart; CAD depth is \(\approx 0.72\,P = (3/4)H\) (simplified truncated V), not true Whitworth \(h = (2/3)H\). That is a catalog CAD simplification — **do not retune** ThreadProfile tables to match it.

---

## 3. Regenerating checks

```text
python Resources/assets/generate_bsw_profile_data.py --check
python _bsw_validation_plots/_bsw_validate.py
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" _bsw_validation_plots\_bsw_smoke_wb.py
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" C:\Users\ritchie\ThreadDefinitions\BSW_McMaster\rebuild_clean_overlay.py
```

---

## 4. Scope note vs PR #72

PR #72 adds a “55” V-thread variant. This work instead adds a **BSW command** with rounded Whitworth form, correct minors, generator, and validation — addressing Mark’s review points (presets, auto form, data provenance, naming). BSPP/BSPT pipe threads are **out of scope** here (different series).
