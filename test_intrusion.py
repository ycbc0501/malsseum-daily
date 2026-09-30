#!/usr/bin/env python3
"""The clip is scanned in full, and the moments something ENTERED get inspected.

Why this file exists: 예레미야 33:3 (2026-09-25) shipped with a sleeved arm swinging into frame
from 1.5s to 2.3s and a hand carrying a dish at 7.5s. The clip inspection sampled two frames —
the middle (4.0s) and the end (7.4s) — and the arm arrived after the first and left before the
second, so both saw an empty room. The vision gate was never at fault: shown the 2.17s frame
afterwards it answered "a person's arm and hand on the right side" immediately.

These tests build clips with ffmpeg rather than asserting on the real one, so they run in CI with
no network and no Instagram. The shape of the failure is what is pinned: a thing that appears for
a moment and leaves must be FOUND, and must land in the frames handed to the gate.
"""

import os
import subprocess
import sys
import tempfile

import make_video

FAILED = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def _make_clip(path, appears_from=None, appears_to=None, dur=8, moving=False):
    """A plain grey clip. `moving` adds noise everywhere (water/clouds); `appears_*` puts a bright
    box on screen only between those seconds — something that enters and then leaves."""
    src = f"color=c=gray:s=256x456:d={dur}:r=10"
    vf = []
    if moving:
        # Noise redrawn every frame: change that is everywhere, all the time — exactly what a
        # real water or cloud clip looks like to this measurement, and exactly what must NOT
        # read as an intrusion.
        vf.append("noise=alls=40:allf=t+u")
    if appears_from is not None:
        vf.append(f"drawbox=x=150:y=200:w=80:h=180:color=white:t=fill:"
                  f"enable='between(t,{appears_from},{appears_to})'")
    cmd = [make_video.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", src]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", path]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def main():
    if not make_video.FFMPEG or subprocess.run([make_video.FFMPEG, "-version"],
                                               capture_output=True).returncode != 0:
        print("CANNOT VERIFY  ffmpeg is missing — these tests cannot build their clips")
        print("               (that is not the same as the rule holding)")
        return 1

    d = tempfile.mkdtemp(prefix="test_intrusion_")

    # 1. The exact 예레미야 shape: present only between the two frames the old gate sampled.
    #    For an 8s clip those were 4.0s (middle) and 7.4s (end), so 1.5–2.3s is invisible to it.
    clip = _make_clip(os.path.join(d, "arm.mp4"), appears_from=1.5, appears_to=2.3)
    peaks = make_video.intrusion_times(clip)
    check("something that enters and leaves is found at all", bool(peaks),
          "intrusion_times returned nothing")
    if peaks:
        t, score = peaks[0]
        check("…and it is found WHEN it happened", 1.2 <= t <= 2.6, f"peak at {t:.2f}s")
        check("…and it scores above the floor", score >= make_video.NOVELTY_FLOOR,
              f"{score:.2f}% < {make_video.NOVELTY_FLOOR}%")

        # The old behaviour, written out: this is what the two fixed samples saw. If this ever
        # stops failing to see it, the bug is back.
        old_samples = [8 * 0.5, 8 - 0.6]
        check("the two old samples really did miss it",
              all(not (1.5 <= s <= 2.3) for s in old_samples),
              "the regression case no longer reproduces")

    # 2. A clip where nothing enters must not manufacture a suspect.
    calm = _make_clip(os.path.join(d, "calm.mp4"))
    check("a clip where nothing happens yields no suspect moment",
          make_video.intrusion_times(calm) == [], "found an intrusion in a static clip")

    # 3. Water and clouds move constantly and are SUPPOSED to. They must not read as an intruder.
    #    This is the whole reason the score counts only pixels that are normally still.
    waves = _make_clip(os.path.join(d, "waves.mp4"), moving=True)
    wave_peaks = make_video.intrusion_times(waves)
    check("constant motion everywhere is not an intrusion", wave_peaks == [],
          f"motion read as intrusion: {[(round(t, 2), round(s, 2)) for t, s in wave_peaks]}")

    # 4. The gate must actually LOOK at what the measurement found — finding it and not
    #    inspecting it would be the same failure in a new place.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_post.py")).read()
    body = src.split("def clip_survives_inspection")[1].split("\ndef ")[0]
    check("the gate inspects the moments the scan found",
          "make_video.intrusion_times(clip)" in body and "samples.append" in body,
          "clip_survives_inspection does not use the scan")
    check("the scan never rejects on its own",
          "return False" not in body.split("for when, where in samples:")[0].split("peaks =")[1],
          "a novelty score can kill a post — populations overlap, it may only choose frames")

    print()
    if FAILED:
        print("FAIL  " + ", ".join(FAILED))
        return 1
    print("intrusion scan holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
