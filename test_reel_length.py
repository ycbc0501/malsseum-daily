#!/usr/bin/env python3
"""Reel length + loop-seam contract (CONTENT_RULE 6, 7).

These assert the things that actually reached a viewer's ear and eye on 2026-08-21, when the
account owner reported "the music stops and repeats before I even read the line":

  * the reel is never longer than Lyria's 30s hymn, so the music never loops inside one play;
  * the audio fades are short, so Instagram's endless loop does not put a hole of silence in
    the middle of the verse;
  * a chain cut short by the motion gate or the clock still produces a valid, shorter reel.

ffmpeg is NOT required — subprocess.run is intercepted and the command line is inspected, which
is the actual contract between us and ffmpeg. Run: python3 test_reel_length.py
"""

import re
import sys
from unittest import mock

import daily_post
import make_video


def capture_native(video_dur, duration=None):
    """Return the ffmpeg argv build_reel_native would run, without running it."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return mock.Mock(returncode=0, stdout=b"", stderr=b"")

    with mock.patch.object(make_video.subprocess, "run", fake_run), \
         mock.patch.object(make_video, "_duration", lambda p: video_dur):
        make_video.build_reel_native("in.mp4", "ov.png", "hymn.wav", "out.mp4",
                                     duration=duration)
    return calls[0]


def arg_after(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def fails(msg):
    print(f"  FAIL {msg}")
    return 1


bad = 0

# --- 1. the cap ----------------------------------------------------------------------------
# Four good Veo segments join to ~31s, just past the hymn. daily_post passes min(joined, HYMN_S).
joined = 31.0
capped = min(joined, daily_post.HYMN_S) or None
cmd = capture_native(joined, duration=capped)
t = float(arg_after(cmd, "-t"))
print(f"1. joined {joined}s → reel {t}s (hymn is {daily_post.HYMN_S}s)")
if t > daily_post.HYMN_S:
    bad += fails(f"reel {t}s outlasts the {daily_post.HYMN_S}s hymn → music would loop (rule 7)")
if not (daily_post.HYMN_S - 1.0 <= t <= daily_post.HYMN_S):
    bad += fails(f"reel {t}s wastes hymn; expected to sit just under {daily_post.HYMN_S}s")

# --- 2. a short chain is not padded ---------------------------------------------------------
# The motion gate or CHAIN_DEADLINE_S can stop the chain early; that must shorten the reel,
# never stretch or loop it.
short = 15.65
cmd = capture_native(short, duration=min(short, daily_post.HYMN_S) or None)
t_short = float(arg_after(cmd, "-t"))
print(f"2. gate/clock cut the chain at {short}s → reel {t_short}s (not padded to the cap)")
if t_short > short:
    bad += fails(f"short chain padded to {t_short}s — that can only come from replayed frames")

# --- 3. the loop seam ------------------------------------------------------------------------
# Instagram loops reels forever, so the fade-out and the NEXT play's fade-in are heard back to
# back as one dip to silence. Before this change it was 1.8 + 1.2 = 3.0s, on a 15.33s reel.
af = arg_after(cmd, "-af")
fade_in = float(re.search(r"afade=t=in:st=0:d=([\d.]+)", af).group(1))
fade_out = float(re.search(r"afade=t=out:st=[\d.]+:d=([\d.]+)", af).group(1))
seam = fade_in + fade_out
print(f"3. loop seam = {fade_out}s out + {fade_in}s in = {seam}s of dipping music")
if seam > 1.5:
    bad += fails(f"{seam}s seam — audible as the music stopping and restarting mid-verse")

# --- 4. the fade-out lands at the end, not before it -----------------------------------------
st = float(re.search(r"afade=t=out:st=([\d.]+)", af).group(1))
print(f"4. fade-out starts at {st}s of a {t_short}s reel")
if not (0 < t_short - st <= 1.5):
    bad += fails(f"fade-out starts {t_short - st:.2f}s early — silence while the verse is still up")

# --- 5. still fallbacks are the same length as a full chain ----------------------------------
print(f"5. SEGMENTS={daily_post.SEGMENTS}, HYMN_S={daily_post.HYMN_S}, "
      f"CHAIN_DEADLINE_S={daily_post.CHAIN_DEADLINE_S}s")
src = open("daily_post.py", encoding="utf-8").read()
if "duration=24" in src:
    bad += fails("a still fallback still runs 24s — shorter than the chained reel it replaces")
if daily_post.SEGMENTS * 7.65 < daily_post.HYMN_S - 8:
    bad += fails(f"SEGMENTS={daily_post.SEGMENTS} cannot reach the hymn length; "
                 f"the reel will loop inside the music again")

# --- 6. the still fallback has the same seam discipline ---------------------------------------
# It is a reel too, so Instagram loops it identically. It used to fade 1.0 in / 1.5 out.
still_calls = []
with mock.patch.object(make_video.subprocess, "run",
                       lambda cmd, **kw: still_calls.append(cmd)):
    make_video.build_reel_still("bg.png", "ov.png", "hymn.wav", "out.mp4",
                                duration=daily_post.HYMN_S)
still_af = arg_after(still_calls[0], "-af")
s_in = float(re.search(r"afade=t=in:st=0:d=([\d.]+)", still_af).group(1))
s_out = float(re.search(r"afade=t=out:st=[\d.]+:d=([\d.]+)", still_af).group(1))
print(f"6. still fallback seam = {s_out}s out + {s_in}s in = {s_in + s_out}s")
if s_in + s_out > 1.5:
    bad += fails(f"still fallback still has a {s_in + s_out}s seam")
if float(arg_after(still_calls[0], "-t")) > daily_post.HYMN_S:
    bad += fails("still fallback outlasts the hymn")

print("\nFAILED" if bad else "\nall reel-length checks passed")
sys.exit(1 if bad else 0)
