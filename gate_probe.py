#!/usr/bin/env python3
"""Measure the image gates on REAL renders, without publishing anything.

    python3 gate_probe.py [n]        # n renders, default 4

This exists because of what 2026-10-06 turned up. The clearance gate was calibrated on PUBLISHED
frames — cover-cropped, re-rendered by Veo, h264-encoded — and then applied to the RAW render,
which is sharper and bigger. The number never matched, the gate rejected every render it ever saw
for a fortnight, and every post shipped a frame the gate had REJECTED. Nobody noticed, because the
only way to see a gate number was to publish a post and read the log afterwards.

So: generate what the gate actually sees, print what it actually measures, publish nothing. Any
future threshold gets calibrated against this output rather than against the finished reel.

Rule 0-2 applies — this reports numbers, it never decides anything. And rule E-0: each render is
billed, so the default is small.
"""
import os
import sys

import fetch_higgsfield as hf


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    start = int(os.environ.get("PROBE_SCENE", "0"))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out, exist_ok=True)
    dest = os.path.join(out, "_probe.png")

    print(f"{'scene':>4s} {'family':18s} {'size':>11s} {'clear':>7s} {'ruled':>7s} "
          f"{'seam':>7s} {'ratio':>7s}  verdict")
    rows = []
    for i in range(n):
        idx = (start + i) % len(hf.SCENES)
        try:
            hf.generate_background(dest, idx, placement=("center", "top"), aspect="9:16")
        except Exception as e:
            print(f"{idx:4d} {hf.SCENE_CATS[idx]:18s} render failed: {e}")
            continue
        from PIL import Image
        w, h = Image.open(dest).size
        clear = hf.clearance_below(dest)
        frac, _fy = hf.ruled_line(dest)
        jump, ratio, _sy = hf.seam_score(dest)
        bad = []
        if clear < hf.CLEARANCE_MIN:
            bad.append("cramped")
        if frac >= hf.RULED_FRAC:
            bad.append("ruled")
        if jump >= hf.SEAM_JUMP and ratio >= hf.SEAM_RATIO:
            bad.append("stacked")
        rows.append((clear, frac, not bad))
        print(f"{idx:4d} {hf.SCENE_CATS[idx]:18s} {w:5d}x{h:<5d} {clear * 100:6.1f}% "
              f"{frac:7.3f} {jump:7.1f} {ratio:7.0f}  "
              f"{'PASS' if not bad else 'reject: ' + ', '.join(bad)}")

    if not rows:
        print("\nno render succeeded — nothing measured")
        return 1
    # The fortnight-long bug showed itself as a constant. Say so loudly if it comes back.
    clears = [r[0] for r in rows]
    print(f"\nclearance: min {min(clears) * 100:.1f}%  max {max(clears) * 100:.1f}%  "
          f"(limit {hf.CLEARANCE_MIN * 100:.0f}%)")
    if len(rows) > 1 and max(clears) - min(clears) < 1e-6:
        print("WARNING: every render measured the SAME clearance. A number that cannot vary is "
              "not a measurement — this is exactly how the 09-22 gate failed.")
    print(f"passed all gates: {sum(1 for r in rows if r[2])}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
