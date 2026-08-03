# Smoke-test: create BSW ThreadProfile via workbench command logic
import os
import sys

import FreeCAD as App

ROOT = r"C:\Users\ritchie\ThreadProfile"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import ThreadProfileCmd as TPC

doc = App.newDocument("BSW_smoke")
cmd = TPC.ThreadProfileCreateBSWObjectCommandClass()
obj = cmd.makeBSWThreadProfile()
doc.recompute()

assert obj is not None
print("Name", obj.Name)
print("Presets", obj.Presets)
print("Pitch", obj.Pitch)
print("MinorDiameter", float(obj.MinorDiameter))
print("InternalOrExternal", obj.InternalOrExternal)
print("Shape valid", obj.Shape.isValid(), "edges", len(obj.Shape.Edges))
bb = obj.Shape.BoundBox
print("BB X {:.3f}..{:.3f} Y {:.3f}..{:.3f}".format(bb.XMin, bb.XMax, bb.YMin, bb.YMax))
# External default: basic minor 4.7236 - 0.15 print clearance
expect = 4.723568465831219 - 0.15
assert abs(float(obj.MinorDiameter) - expect) < 1e-6, (obj.MinorDiameter, expect)
assert abs(float(obj.Pitch) - 1.27) < 1e-9
print("OK smoke")
out = os.path.join(ROOT, "_bsw_validation_plots", "BSW_smoke_profile.FCStd")
doc.saveAs(out)
print("Saved", out)
App.closeDocument(doc.Name)
