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


# ---------------------------------------------------------------------------------------------
# The fortnight this gate spent rejecting everything.
#
# From 2026-09-22 to 2026-10-06 the threshold was an absolute edge-energy value (4.0) read off
# PUBLISHED frames and then applied to the RAW render, which is sharper and bigger. Every CI log
# that still exists shows the same impossible line for every scene:
#
#     clearance below the verse: -0.0% (need 18%)
#
# so nothing ever passed, generate_checked always ran out its budget, and every post shipped the
# render the gate had REJECTED — 26 of the last 30 carry gate_passed=false. The ruled line in
# 디모데전서 2:4 reached the account that way: forest_path was not chosen, it was simply the sixth
# scene in rotation when the clock stopped.
#
# What follows pins the property that was missing, not the number that was wrong. If the measure
# ever again depends on how sharp the file happens to be, these fail.
print("\nthe measure must not move with sharpness or scale")

from PIL import ImageEnhance                                     # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata")
GROUND = [
    # frame                             recorded in RULES F-2c, judged by the account owner
    ("clearance_cramped_20260922.png", 0.122, "골로새서 2:7 — 여백이 너무 없어"),
    ("clearance_roomy_20260921.png", 0.257, "유다서 1:21 — the account owner called this right"),
]

for name, recorded, why in GROUND:
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        # Rule 0-2: "could not check" is never "it is fine".
        check(f"fixture {name} is present", False)
        continue
    got = F.clearance_below(p)
    check(f"{why}: {got * 100:.1f}% vs {recorded * 100:.1f}% recorded",
          abs(got - recorded) < 0.025)

    base = Image.open(p).convert("L")
    variants = {
        "upscaled x2": base.resize((base.width * 2, base.height * 2), Image.LANCZOS),
        "sharpened x3": ImageEnhance.Sharpness(base).enhance(3.0),
        "contrast x1.6": ImageEnhance.Contrast(base).enhance(1.6),
    }
    for vname, im in variants.items():
        q = os.path.join(D, f"{name}.{vname}.png")
        im.save(q)
        moved = abs(F.clearance_below(q) - got)
        check(f"  {vname} moves it less than 3%p (moved {moved * 100:.1f})", moved < 0.03)

# And the two must still land on OPPOSITE sides of the limit — the whole point of the number.
cramped = F.clearance_below(os.path.join(DATA, GROUND[0][0]))
roomy = F.clearance_below(os.path.join(DATA, GROUND[1][0]))
check(f"the limit still separates them ({cramped * 100:.1f}% < {F.CLEARANCE_MIN * 100:.0f}% "
      f"< {roomy * 100:.1f}%)", cramped < F.CLEARANCE_MIN < roomy)

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
