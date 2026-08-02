# Maintainer feedback on PG21 — analysis report

**PR:** [mwganson/ThreadProfile#82](https://github.com/mwganson/ThreadProfile/pull/82)  
**Comment:** Mark Ganson, 2026-07-30  
**Updated:** 2026-08-02 (fair McMaster locknut compare + measurements)

Supporting artifacts in this repo:

| Artifact | Path |
|----------|------|
| Overlay screenshot (hand-aligned) | `_pg_validation_plots/2026_08_02_13_53_42_PG21_locknut_vs_WB_XZ_FreeCAD_1.1.3.png` |
| FreeCAD overlay (XZ sections) | `example/PG21_locknut_vs_WB_XZ.FCStd` |
| Diameter / fit log | `example/measure_3185K94_out.txt` |

---

## 1. What the maintainer did

Mark compared **ThreadProfile workbench (WB) threads** (black) against **commercial / community references** (red) by cutting XZ cross-sections in FreeCAD:

| Size | Reference source | Result (his words) |
|------|------------------|--------------------|
| PG7  | Thingiverse [thing:3663884](https://www.thingiverse.com/thing:3663884) | reasonably close |
| PG9  | same Thingiverse set | reasonably close |
| PG21 | McMaster [7805K45](https://www.mcmaster.com/7805K45/) (M32 ↔ PG21 adapter) | **significantly off** |
| PG48 | McMaster [3185K133](https://www.mcmaster.com/3185K133/) | reasonably close |

He also checked that the **M32** side of the adapter matches a WB M32 — so his FreeCAD / Mesh workflow itself looks trustworthy.

His broader worry: PG might **not be scalable** with one profile table (some thread families change formulation by size range).

---

## 2. Are *our* PG21 numbers wrong vs DIN / charts?

**No — against published DIN 40430-style charts, PG21 is consistent.**

| Quantity | Chart / DIN-style data | Our preset / profile |
|----------|------------------------|----------------------|
| Major | 28.30 mm | ≈ 28.30 (internal) / ≈ 28.15 (external with −0.15 clearance) |
| Minor (male) | 26.78 mm | internal uses 26.78; external 26.63 (−0.15) |
| Pitch | 1.588 mm (16 TPI) | `25.4/16 = 1.5875` |
| Thread height H1 | **0.76 mm** | `0.48 × P ≈ 0.762 mm` |

---

## 3. PG21 and PG48 share the same tooth

One pair of arrays (`internal_pg_data` / `external_pg_data`) is used for every PG size:

```text
radius = Minor/2 + table[i] * Pitch
```

| | PG21 | PG48 |
|--|------|------|
| Pitch | 1.5875 mm (16 TPI) | **same** |
| Profile table | same 80° / h=0.48 | **same** |
| Tooth shape in mm | identical | identical |
| Only difference | Minor ≈ 26.78 | Minor ≈ 57.78 |

If WB PG48 matches Mark’s PG48 reference, the **same** tooth is what WB draws for PG21. A “PG21-only formula bug” would also break PG48.

---

## 4. Scalability

Published H1/P from gage charts stays ≈ **0.48** from PG7 through PG48. DIN 40430 PG **does** scale with one formulation; our model matches that.

---

## 5. Root cause of the “significantly off” PG21 overlay

### 5.1 Wrong mating feature on the adapter

[7805K45](https://www.mcmaster.com/7805K45/) is an **M32 ↔ PG21 adapter**, not a PG21 nut.

From Mark’s `PG tests` file (object `Part__Feature001_cs` vs WB `Sweep_cs003`):

| Feature in the overlay | Measured (approx.) | Standard |
|------------------------|--------------------|----------|
| WB green male | major ≈ **28.15**, minor ≈ **26.57** | PG21 external (−0.15 clearance) ✓ |
| Orange female surrounding that male | tips ≈ **Ø30**, roots ≈ **Ø32**, pitch ≈ **1.5** | **M32×1.5 female**, not PG21 |

Equal left/right gap in the screenshot is therefore expected: **PG21 male inside an M32 female**. That is not evidence of a second PG norm or a broken WB PG21 formula.

Mark’s own note that WB **M32** matched the adapter supports this reading: he was looking at the M32 end of the part.

### 5.2 Fair reference (same series as his PG48)

Mark’s good large-size check used nylon locknut **[3185K133](https://www.mcmaster.com/3185K133/)** (PG48).  
The sibling PG21 part is **[3185K94](https://www.mcmaster.com/3185K94/)** (PG-21 nylon locknut).

McMaster CAD/STEP for that part needs a **McMaster account** (Product Detail → **3-D STEP**).

### 5.3 Measurements: 3185K94 vs WB PG21 External

XZ slice of the McMaster STEP vs WB section from Mark’s file:

| | McMaster 3185K94 (female) | WB PG21 Ext | DIN PG21 |
|--|---------------------------|-------------|----------|
| Major | **28.300** | 28.155 | 28.30 |
| Minor | **26.888** | 26.573 | 26.78 |
| H1 | ~0.71 | — | 0.76 |

Major–major clearance ≈ **0.07 mm/side** — tight, sensible engagement.

Hand-aligned overlay (same workflow as Mark): see screenshot above. Flanks nest; no large bilateral gap.

---

## 6. Verdict

| Question | Answer |
|----------|--------|
| Off vs British Metrics / Sealcon / DIN-style charts for PG21? | **No** |
| Is `h = 0.48·P` inconsistent for large sizes? | **No** — H1/P ~0.48 for PG7…PG48 |
| Did Mark’s PG21 screenshot prove WB PG21 is broken? | **No** — that view was **M32 female** on 7805K45 |
| Fair McMaster locknut compare (3185K94), like his PG48? | **Yes — close match** |

---

## 7. Suggested PR reply (done / for reference)

1. Thank him for the XZ checks and `PG tests.zip`.  
2. Explain 7805K45: PG21 male was compared to the **M32** female bore.  
3. Point to **3185K94** as the fair mate (same locknut family as 3185K133).  
4. Note McMaster login is required for the STEP download.  
5. Scalability concern is weak for PG: charts keep H1/P ≈ 0.48 across sizes; PG21 and PG48 share pitch + profile table.

---

## 8. One-line summary

**WB PG21 matches DIN charts and a McMaster PG21 locknut (3185K94); the earlier “significantly off” overlay was PG21 male vs M32 female on adapter 7805K45 — not a bad PG formula.**
