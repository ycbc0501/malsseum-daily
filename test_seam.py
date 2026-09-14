#!/usr/bin/env python3
"""
The stacked-composite gate (RULES A-6).

Calibrated on four reels that actually shipped, measured 2026-09-14:

    post-34776617567  jump 16.5  363x   STACKED   ← 신명기 1:29, one of the flagged ten
    post-34684776461  jump  9.5   80x   STACKED
    post-34731122707  jump  5.1   20x   ok
    post-34638366339  jump  4.5    8x   ok

Those frames are not in the repo (they live on the media release), so the cases here are
synthetic — a gradient wall with a hard paste line, versus the same wall without one. The
thresholds are the ones that separated the four real frames 4/4.

    python3 test_seam.py
"""

import os
import sys
import tempfile

from PIL import Image

import fetch_higgsfield as hf

W, H = 540, 960


def wall(paste_at=None, step=40, noise=True):
    """A dark wall that drifts in brightness, optionally with a scene pasted in below `paste_at`."""
    im = Image.new("L", (W, H))
    px = im.load()
    for y in range(H):
        base = 28 + (y / H) * 18                  # gentle vertical drift, like real falloff
        if paste_at is not None and y >= paste_at:
            base += step                          # the pasted half is lit differently
        for x in range(W):
            v = base + ((x * 7 + y * 13) % 3 if noise else 0)
            px[x, y] = max(0, min(255, int(v)))
    return im


def main():
    fails = []
    with tempfile.TemporaryDirectory() as d:
        cases = [
            ("clean wall", wall(None), False),
            ("paste at 67%", wall(int(H * 0.67)), True),
            ("paste at 55%", wall(int(H * 0.55)), True),
            ("faint paste (2 levels)", wall(int(H * 0.67), step=2), False),
            # The verse band is excluded on purpose: white text on a dark wall is a real
            # brightness cliff and is not a defect.
            ("edge in the text band", wall(int(H * 0.30)), False),
            # Frame edges are excluded too — the last row of a video is often darker.
            ("edge at the very bottom", wall(H - 3), False),
        ]
        for name, im, want in cases:
            p = os.path.join(d, f"{name}.png")
            im.save(p)
            got = hf.has_seam(p)
            if got != want:
                fails.append(f"{name}: got {got}, expected {want}")

        # A gate that cannot run must never stop a post (rule 0-3).
        if hf.has_seam(os.path.join(d, "does-not-exist.png")):
            fails.append("a missing file was reported as a seam")

    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{7 - len(fails)}/7 checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
