# McMaster BSF STEP overlay notes

**Purpose:** Cross-check ThreadProfile Whitworth form against vendor CAD (Mark-style section compare).  
**Parts:** McMaster BSF grease fittings (Whitworth-family 55°). McMaster does not offer BSW bolt/nut STEPs.

| Part | Size | Role |
| ---- | ---- | ---- |
| [1095K104](https://www.mcmaster.com/1095K104/) | 1/4"-26 BSF straight | Primary overlay |
| [1095K105](https://www.mcmaster.com/1095K105/) | 3/8"-20 BSF | Extra size |
| [2408K31](https://www.mcmaster.com/2408K31/) | 5/16"-22 BSF | Extra size |
| [1095K122](https://www.mcmaster.com/1095K122/) | 1/4"-26 BSF 90° | Optional |

**Canonical FreeCAD file:** `BSW_1095K104_clean_overlay.FCStd`  
- Orange: McMaster thread-band section  
- Green: ThreadProfile Whitworth external outline (\(h=(2/3)H\), rounded)  
- Full body CS hidden (avoid scribble at hex→shank)

| Check | Result |
| ----- | ------ |
| Major vs chart | Exact match on all four |
| CAD depth / pitch | ≈ 0.72 (= (3/4)·H) |
| Whitworth depth / pitch | ≈ 0.640 (= (2/3)·H) |
| Conclusion | Vendor CAD is simplified; keep true Whitworth tables |

Scripts: `rebuild_clean_overlay.py`, `finalize_overlay.py`, `plot_mcmaster_compare.py`  
STEPs live under `ThreadDefinitions/BSW_McMaster/` (local; not required in the git PR).
