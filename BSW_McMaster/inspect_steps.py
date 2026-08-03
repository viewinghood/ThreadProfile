# Inspect McMaster BSF STEP geometry (units, solids, possible thread zones)
import FreeCAD
import Part
from pathlib import Path

HERE = Path(r"C:\Users\ritchie\ThreadDefinitions\BSW_McMaster")
files = sorted(HERE.glob("*.STEP"))

for step in files:
    print("\n====", step.name, "====")
    sh = Part.Shape()
    sh.read(str(step))
    print("Solids", len(sh.Solids), "Faces", len(sh.Faces), "Edges", len(sh.Edges), "Shells", len(sh.Shells))
    bb = sh.BoundBox
    print(
        f"global BB: X {bb.XMin:.4f}..{bb.XMax:.4f} ({bb.XLength:.4f})  "
        f"Y {bb.YMin:.4f}..{bb.YMax:.4f} ({bb.YLength:.4f})  "
        f"Z {bb.ZMin:.4f}..{bb.ZMax:.4f} ({bb.ZLength:.4f})"
    )
    # Heuristic: if max extent < 5, might be inches
    mx = max(bb.XLength, bb.YLength, bb.ZLength)
    print(f"max extent {mx:.4f}  -> if inches, mm={mx*25.4:.2f}")

    for i, s in enumerate(sh.Solids):
        b = s.BoundBox
        print(
            f"  solid[{i}] vol={s.Volume:.4f} faces={len(s.Faces)} "
            f"BB {b.XLength:.3f}x{b.YLength:.3f}x{b.ZLength:.3f} "
            f"center ({b.Center.x:.3f},{b.Center.y:.3f},{b.Center.z:.3f})"
        )

    # Count cylindrical / helical-looking edges by radius of curvature samples
    # Simpler: face types
    types = {}
    for f in sh.Faces:
        t = f.Surface.__class__.__name__
        types[t] = types.get(t, 0) + 1
    print("face types:", types)

    # Sample outer radii along each principal axis by slicing
    for axis_name, normal in [
        ("Y=0", FreeCAD.Vector(0, 1, 0)),
        ("X=0", FreeCAD.Vector(1, 0, 0)),
        ("Z=0", FreeCAD.Vector(0, 0, 1)),
    ]:
        wires = sh.slice(normal, 0.0)
        if not wires:
            continue
        rs = []
        for w in wires:
            for e in w.Edges:
                try:
                    for p in e.discretize(Number=40):
                        if axis_name.startswith("Y"):
                            r = (p.x * p.x + p.z * p.z) ** 0.5
                            ax = p.y
                        elif axis_name.startswith("X"):
                            r = (p.y * p.y + p.z * p.z) ** 0.5
                            ax = p.x
                        else:
                            r = (p.x * p.x + p.y * p.y) ** 0.5
                            ax = p.z
                        if r > 0.05:
                            rs.append((r, ax, p.x, p.y, p.z))
                except Exception:
                    pass
        if not rs:
            continue
        rvals = [r for r, *_ in rs]
        print(
            f"  slice {axis_name}: n={len(rs)} r {min(rvals):.4f}..{max(rvals):.4f} "
            f"d {2*min(rvals):.4f}..{2*max(rvals):.4f}"
        )
