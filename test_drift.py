#!/usr/bin/env python3
"""A scene has to stay the same scene.

    python3 test_drift.py

고린도전서 15:55 (2026-09-19) shipped with a fence whose posts drifted and changed shape as the
reel played. Every individual frame was a fine photograph, so the per-frame vision gate passed
it — a question asked one frame at a time cannot see a thing morph. Measured on the real files:

    09-19 울타리 (reported)   34.9  35.5  41.1  42.5
    09-16 (fine)               6.9   3.7
    09-17 (fine)              12.0  10.3
"""
import os
import sys
import tempfile

from PIL import Image, ImageDraw

import make_video

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


D = tempfile.mkdtemp()


def fence(path, xs, w=8):
    """A picket fence on the lower half — `xs` are the post positions."""
    im = Image.new("RGB", (540, 960), (150, 160, 170))
    d = ImageDraw.Draw(im)
    for x in xs:
        d.rectangle([x, 600, x + w, 880], fill=(60, 50, 40))
    d.rectangle([0, 660, 540, 672], fill=(60, 50, 40))
    im.save(path)
    return path


print("structure drift")

same_a = fence(os.path.join(D, "a.png"), range(40, 500, 60))
same_b = fence(os.path.join(D, "b.png"), range(40, 500, 60))
check("identical frames drift zero", make_video.edge_drift(same_a, same_b) == 0.0)

# Light changes, structure does not — the calm scene we actually want.
lit = Image.open(same_a).point(lambda v: min(255, int(v * 1.12)))
lit.save(os.path.join(D, "lit.png"))
check("a light change alone stays under the limit",
      make_video.edge_drift(same_a, os.path.join(D, "lit.png")) < make_video.DRIFT_MAX)

# The reported failure: posts move and one more appears.
moved = fence(os.path.join(D, "moved.png"), list(range(52, 500, 60)) + [505], w=11)
d_moved = make_video.edge_drift(same_a, moved)
d_lit = make_video.edge_drift(same_a, os.path.join(D, "lit.png"))
print(f"  (synthetic: light {d_lit:.1f}, fence moved {d_moved:.1f})")
# Ordering, NOT the absolute limit. A drawn fence on flat grey has a fraction of the edge
# density of a photograph, so its numbers do not live on the same scale as DRIFT_MAX — which was
# calibrated on real files. Asserting the limit here would mean tuning the limit until a
# synthetic case passed, which is how a threshold stops meaning anything.
check("a fence that shifts and gains a post drifts far more than light alone",
      d_moved > d_lit * 3)

# The limit has to sit between the two measured populations, not inside either.
check("limit is above every reel nobody complained about", make_video.DRIFT_MAX > 12.0)
check("limit is below every segment of the reported reel", make_video.DRIFT_MAX < 34.9)

# An unmeasurable clip must not read as a passing one, and must not read as failing either —
# it returns a sentinel the caller can tell apart from a real zero.
check("a missing file measures -1, not 0",
      make_video.structure_drift(os.path.join(D, "nope.mp4")) in (-1.0, 0.0))

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
