#!/usr/bin/env python3
"""
The ruled-line gate (RULES A-4, F-2) — a straight line must not cut across the top of the frame.

WHY THIS EXISTS SEPARATELY FROM test_seam.py
--------------------------------------------
has_seam() skips the rows between 18% and 45% of the height. 2026-10-06 디모데전서 2:4 shipped a
forest guillotined by a dead-straight line at 32.1% — inside that skipped band — and the gate
reported `ok` nine times running. The first case below pins exactly that: the old gate passes the
real frame, the new one rejects it. If anyone ever deletes has_ruled_line, this test says what
breaks and names the post that broke it.

REAL FIXTURES
-------------
`testdata/` holds three frames lifted from reels that actually published, downscaled to 540x960
grey (the gate reads shape, not colour). Unlike test_seam.py, which had to be synthetic because
the frames lived only on the media release, these are the real thing:

    ruled_forest_20261006.png      디모데전서 2:4   REJECT   the reported defect
    clean_snowfall_20260929.png    신명기 26:9      pass     worst-scoring CLEAN frame of 29
    clean_wheatfield_20261003.png  이사야 42:12     pass     a true low horizon — allowed

CALIBRATION, measured over all 29 reels on the media release (2026-10-06):

    worst row in the upper 45%     defect 0.900   worst clean 0.347   median 0.000
    limit 0.55                     → 1.6x headroom on BOTH sides

The window was swept rather than guessed: 0.34-0.40 separates 3.1x and 0.42-0.50 separates 2.6x.
0.45 was kept, because wider coverage is worth more than the prettier ratio while the limit still
sits 1.6x clear either way.

The measure is resolution-sensitive — downscaling SHARPENS it (snowfall 0.347 at 1080px, 0.473 at
540px). The gate always runs on full-size renders, so the full-size numbers are the real ones; the
fixtures are half-size and therefore a HARSHER test than production.

RE-SWEPT 2026-10-07 over 46 reels — every one the account still carried, back to 09-10, each one
downloaded and measured rather than sampled. The calibration above was built on 29; widening it
changed nothing and settled two questions:

    ruled  1 of 46         디모데전서 2:4 only. There is nothing else to take down.
    97%    the defect      next worst 42% (신명기 26:9), then 29%, 25%, 18%, 18%; median 0%
    0/45   false positives on real published frames

So the 55% limit sits in an EMPTY band, 42%…97%, measured on published posts rather than chosen.
Moving it anywhere inside that band changes no verdict; moving it below 42% starts rejecting the
snowfall frame, which the account owner never objected to.

(The same sweep's clearance column is NOT comparable to CLEARANCE_MIN: it reads published frames,
and reading a published number and applying it to the raw render is precisely the mistake that
blinded this gate for a fortnight. It is recorded in notes/deleted/ruled_line_sweep_20261007.json
and deliberately not acted on.)

    python3 test_ruled_line.py
"""

import os
import sys
import tempfile

from PIL import Image

import fetch_higgsfield as hf

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "testdata")
W, H = 540, 960


def scene(cut_at=None, step=40, ragged=0):
    """A textured scene under a plain sky. `cut_at` rules a line across it; `ragged` lets the
    boundary wander by that many pixels per column, the way a real tree line does."""
    im = Image.new("L", (W, H))
    px = im.load()
    for x in range(W):
        # a deterministic but irregular wobble — no RNG, so the test cannot flake
        wob = 0 if not ragged else int(ragged * (((x * 37) % 23) / 22.0 - 0.5) * 2)
        for y in range(H):
            v = 210 + (y / H) * 8                     # the sky, drifting gently
            if cut_at is not None and y >= cut_at + wob:
                v = 210 - step + ((x * 7 + y * 13) % 9)   # the scene below, textured
            px[x, y] = max(0, min(255, int(v)))
    return im


def main():
    fails = []

    # 1. The real frames. These are the whole point.
    real = [
        ("ruled_forest_20261006.png", True,
         "디모데전서 2:4 — the reported forest cut off by a ruled line at 32%"),
        ("clean_snowfall_20260929.png", False,
         "신명기 26:9 — the worst-scoring clean frame of the 29"),
        ("clean_wheatfield_20261003.png", False,
         "이사야 42:12 — a true low horizon, which is allowed"),
    ]
    for name, want, why in real:
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            # Rule 0-2: "could not check" is never "it is fine".
            fails.append(f"missing fixture {name} — this test cannot verify anything without it")
            continue
        frac, y = hf.ruled_line(p)
        got = hf.has_ruled_line(p)
        if got != want:
            fails.append(f"{why}: got {got}, expected {want} (frac {frac:.3f} at y={y})")

    # 2. The regression itself: the OLD gate passes the real defect, the NEW one catches it.
    #    If this ever flips, has_seam was widened and has_ruled_line may be redundant — but say so
    #    on purpose, do not discover it by a reel shipping.
    p = os.path.join(DATA, "ruled_forest_20261006.png")
    if os.path.exists(p):
        if not hf.has_seam(p):
            pass                       # expected: the blind band is why this file exists
        else:
            fails.append("has_seam now catches 디모데전서 2:4 — re-check whether both gates are needed")
        if not hf.has_ruled_line(p):
            fails.append("has_ruled_line missed the very frame it was written for")

    # 3. Synthetic cases, for the shapes no published frame happens to show.
    with tempfile.TemporaryDirectory() as d:
        cases = [
            ("no line at all", scene(None), False),
            # 30% of the height: the band has_seam cannot see. This is the defect's shape.
            ("ruled line at 30%", scene(int(H * 0.30)), True),
            ("ruled line at 20%", scene(int(H * 0.20)), True),
            # A real canopy or roofline meets the sky at a different height in every column.
            ("ragged tree line at 30%", scene(int(H * 0.30), ragged=14), False),
            # A true horizon sits low in these compositions and is outside the window.
            ("line at 70% (a real low horizon)", scene(int(H * 0.70)), False),
            # Gentle enough that no eye reads it as a join.
            ("faint step (6 levels)", scene(int(H * 0.30), step=6), False),
        ]
        for name, im, want in cases:
            p = os.path.join(d, f"{name}.png")
            im.save(p)
            got = hf.has_ruled_line(p)
            if got != want:
                frac, y = hf.ruled_line(p)
                fails.append(f"{name}: got {got}, expected {want} (frac {frac:.3f} at y={y})")

        # 4. A gate that cannot run must never stop a post (rule 0-3).
        if hf.has_ruled_line(os.path.join(d, "does-not-exist.png")):
            fails.append("a missing file was reported as a ruled line")

    total = len(real) + 2 + 6 + 1
    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{total - len(fails)}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
