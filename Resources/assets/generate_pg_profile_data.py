#!/usr/bin/env python3
"""Generate PG (DIN 40430) internal_pg_data / external_pg_data tables.

These arrays are consumed by ThreadProfileCmd.py (Create PG Object) in the same
normalized form as the existing V-thread tables:

    radius = MinorDiameter/2 + table[i] * Pitch

Geometry (pitch normalized to 1):
  - Included flank angle 80 deg  ->  flank step dx = cot(40 deg) / 720
  - Working height h = 0.48  (from chart (Major-Minor)/(2P) ~= 0.48)
  - Internal: flat root at 0, straight flanks, flat crest at 0.48
  - External: same crest/flanks, root offset -0.018 (pitch units)
  - Sample count 719 = range(1, 720), matching Resources/assets/thread_builder.FCMacro

External presets then apply an extra -0.15 mm print clearance on MinorDiameter
in ThreadProfileCmd.py (not in these tables).

Usage (from repo root or this folder):
    python Resources/assets/generate_pg_profile_data.py
    python Resources/assets/generate_pg_profile_data.py --check

--check compares generated tables to the arrays currently embedded in
ThreadProfileCmd.py (must match exactly).
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

# --- PG profile parameters (documented engineering choices) ---
RES = 720
H = 0.48
ROOT_EXTERNAL = -0.018
N_ROOT = 70
N_RISE = 289
N_CREST = 71
N_FALL = 289

assert N_ROOT + N_RISE + N_CREST + N_FALL == RES - 1


def generate_pg_tables():
    """Return (internal_pg_data, external_pg_data) as lists of floats."""
    dx_i = (1.0 / math.tan(math.radians(40.0))) / RES

    internal = []
    for _ in range(N_ROOT):
        internal.append(0.0)
    for j in range(1, N_RISE + 1):
        internal.append(round(H - (N_RISE + 1 - j) * dx_i, 12))
    for _ in range(N_CREST):
        internal.append(H)
    for j in range(N_FALL, 0, -1):
        internal.append(round(j * dx_i, 12))

    # External uses the same sample layout; flank step scaled so the rise
    # spans from ROOT_EXTERNAL to H with the same number of samples.
    first_i = H - N_RISE * dx_i
    first_e = ROOT_EXTERNAL + first_i * (H - ROOT_EXTERNAL) / H
    dx_e = (H - first_e) / N_RISE

    external = []
    for _ in range(N_ROOT):
        external.append(ROOT_EXTERNAL)
    for j in range(1, N_RISE + 1):
        external.append(round(H - (N_RISE + 1 - j) * dx_e, 12))
    for _ in range(N_CREST):
        external.append(H)
    for j in range(N_FALL, 0, -1):
        external.append(round(ROOT_EXTERNAL + j * dx_e, 12))

    return internal, external


def format_array(name: str, values) -> str:
    body = ",".join(str(v) for v in values)
    return f"{name} = [{body}]"


def extract_from_cmd(src: str, name: str):
    m = re.search(rf"{name}\s*=\s*\[([^\]]+)\]", src)
    if not m:
        raise SystemExit(f"{name} not found in ThreadProfileCmd.py")
    return [float(x) for x in m.group(1).split(",") if x.strip()]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--check",
        action="store_true",
        help="verify against ThreadProfileCmd.py arrays",
    )
    p.add_argument(
        "--cmd",
        type=Path,
        default=None,
        help="path to ThreadProfileCmd.py (for --check)",
    )
    args = p.parse_args(argv)

    internal, external = generate_pg_tables()

    if args.check:
        here = Path(__file__).resolve()
        cmd = args.cmd or here.parents[2] / "ThreadProfileCmd.py"
        text = cmd.read_text(encoding="utf-8")
        ref_i = extract_from_cmd(text, "internal_pg_data")
        ref_e = extract_from_cmd(text, "external_pg_data")
        di = max(abs(a - b) for a, b in zip(internal, ref_i))
        de = max(abs(a - b) for a, b in zip(external, ref_e))
        ok = (
            len(internal) == len(ref_i)
            and len(external) == len(ref_e)
            and di == 0.0
            and de == 0.0
        )
        print(f"internal: n={len(internal)} maxdiff={di}")
        print(f"external: n={len(external)} maxdiff={de}")
        print("OK" if ok else "MISMATCH")
        return 0 if ok else 1

    print(format_array("internal_pg_data", internal))
    print(format_array("external_pg_data", external))
    print(
        f"# n={len(internal)}  h={H}  root_ext={ROOT_EXTERNAL}  "
        f"dx_i=cot(40)/{RES}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
