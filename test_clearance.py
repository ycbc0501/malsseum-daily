#!/usr/bin/env python3
"""The picture must not start right under the verse.

    python3 test_clearance.py

The verse block is pinned at the same place on every post (top 25.6%, bottom 36.6%), so when the
account owner said 여백이 너무 없어서 글이 구석에 몰려있어 about 골로새서 2:7 (2026-09-22) it was
never the typography. It was the photograph: the hedgerow began 12% below the block where the
two posts he pointed to as right leave 21% and 26%.
"""
import os
import sys
import tempfile

from PIL import Image, ImageDraw

import fetch_higgsfield as F

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


D = tempfile.mkdtemp()


def frame(path, content_at):
    """A quiet sky down to `content_at`, then textured ground."""
    im = Image.new("RGB", (540, 960), (200, 205, 212))
    d = ImageDraw.Draw(im)
    y0 = int(960 * content_at)
    for y in range(y0, 960, 3):            # stripes = edges = "content"
        d.line([(0, y), (540, y)], fill=(70, 60, 50), width=1)
    im.save(path)
    return path


print("clearance below the verse")

roomy = frame(os.path.join(D, "roomy.png"), 0.62)
tight = frame(os.path.join(D, "tight.png"), 0.46)

check("a frame that stays open is not rejected", not F.too_cramped(roomy))
check("a frame whose content starts just under the verse is rejected", F.too_cramped(tight))
check("clearance is measured from the block bottom, not the top",
      abs(F.clearance_below(roomy) - (0.62 - F.BLOCK_BOTTOM)) < 0.04)

# An all-quiet frame must not be reported as zero clearance — that would reject empty skies,
# which are the thing the layout wants most.
plain = os.path.join(D, "plain.png")
Image.new("RGB", (540, 960), (200, 205, 212)).save(plain)
check("a wholly open frame gets the maximum clearance",
      F.clearance_below(plain) > F.CLEARANCE_MIN)

# The limit has to sit between the two real populations rather than at a round number.
check("limit is above the reported post's 12%", F.CLEARANCE_MIN > 0.12)
check("limit is below both posts the account owner approved", F.CLEARANCE_MIN < 0.199)

# A gate that cannot run must never stop a post (rule 0-3).
check("an unreadable file does not reject", not F.too_cramped(os.path.join(D, "nope.png")))

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
