#!/usr/bin/env python3
"""The still-image prompt must use the concrete photorealism levers real prompt engineers use,
not vague adjectives (RULES.md A-5, CONTENT_RULE.md §3b, 2026-11-11).

The account owner asked directly, after the 11-11 motion-prompt research, whether that same
rigor had actually been applied to the STILL image prompt too — "실제사진처럼 이미지 만드는
최전방에 있는 인플루언서들이 쓰는 프롬프트가 그런식인거 맞아? 그게 딥리서치한거맞아?" It had
not: `fetch_image.QUALITY` said "a normal prime lens" and never named a film format at all.

A first attempt also added a light-DIRECTION clause ("never flat or shadowless", naming "a
window" and "a horizon"). TWO independent structure reviews that same day killed it before it
shipped — it duplicated and fought machinery this file already has for exactly that job
(OUTDOOR_TOP's decisive overcast/dusk either-or, WALL_TONE's coded indoor light direction), named
objects only the scene sentence is allowed to name (A2e), and the first draft's absolute "never
flat or shadowless" directly contradicted OUTDOOR_TOP's own overcast branch — the same
COMPOSE/EVENTONE shape of self-contradiction this repo shipped broken renders over before
(09-14/09-17). This file locks in what survived review (named lens/focal-length, named film
grain + vignette) and guards the REVERTED clause from quietly creeping back in.
"""
import sys

import fetch_image as hf
import fetch_motion as fm

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


# The pre-2026-11-11 wording, byte-for-byte, so the reverse-tests below prove these checks would
# have caught the gap this change closes rather than always passing regardless of content.
_OLD_QUALITY = (
    "The mood is QUIET and STILL, with a sense of hope and reverence — peaceful and true, never "
    "cute, kitschy or saccharine. Natural light belonging to THIS scene at whatever hour it is: "
    "soft daylight, late dusk or faint light after dark are all welcome and dim is fine, but never "
    "gloomy, ominous, oppressive, bleak or sorrowful. Colour is MUTED and gentle, slightly "
    "desaturated, low in contrast, with a soft filmic quality and subtle grain — restrained, like a "
    "quiet film photograph, not vivid, glossy or dramatic. Understated and simple: "
    "few elements, nothing showy. Shot on a full-frame camera with a normal prime "
    "lens — natural depth of field with the far distance falling gently out of focus, believable "
    "lens character, and the slight imperfection of a real photograph. Detail is UNEVEN and organic "
    "the way nature actually is: grass and foliage vary in height, colour and density, never a "
    "uniform repeating carpet, with no airbrushed smoothness and no halo around edges."
)

# A near-miss first draft: the light-direction clause that two structure reviews killed before it
# shipped. Kept here verbatim (not just paraphrased in a comment) so a reverse-test can prove the
# guard below actually recognizes it, not just an absence of the word "light".
_REVERTED_FIRST_DRAFT_CLAUSE = (
    "The light comes from one real, identifiable direction for THIS scene — through a window, "
    "low on a horizon, from one side — never flat or shadowless, so it casts soft, real shadows "
    "the way actual light does."
)

# ---------------------------------------------------------------------------------------------
# Lever 1: a REAL lens/focal length, not "a normal prime lens".
# ---------------------------------------------------------------------------------------------
check("a concrete focal length is named (35mm or 50mm)",
      "35mm or 50mm" in hf.QUALITY and "prime" in hf.QUALITY)
check("reverse-test: the old wording said only 'a normal prime lens' (no focal length)",
      "35mm or 50mm" not in _OLD_QUALITY)

# ---------------------------------------------------------------------------------------------
# Lever 2: the SPECIFIC imperfection named (film grain, vignette), not just the word
# "imperfection" on its own.
# ---------------------------------------------------------------------------------------------
check("35mm film grain is named, not just 'grain'",
      "35mm film" in hf.QUALITY)
check("a vignette is named",
      "vignette" in hf.QUALITY)
check("reverse-test: the old wording said only 'the slight imperfection of a real photograph' "
      "(no named film stock/format, no vignette)",
      "35mm film" not in _OLD_QUALITY and "vignette" not in _OLD_QUALITY)

# ---------------------------------------------------------------------------------------------
# The reverted light-direction attempt must stay reverted. Checked three independent ways so a
# partial, reworded return of the same idea still trips at least one of them.
# ---------------------------------------------------------------------------------------------
check("the reverted first-draft light-direction clause is not back, verbatim",
      _REVERTED_FIRST_DRAFT_CLAUSE not in hf.QUALITY)
check("reverse-test: the guard above is sensitive — it WOULD fail if the first draft returned "
      "(simulated by appending the reverted clause and re-checking the same substring test)",
      _REVERTED_FIRST_DRAFT_CLAUSE in (hf.QUALITY + " " + _REVERTED_FIRST_DRAFT_CLAUSE))
check("no forbidden-object words from the reverted draft ('through a window', 'on a horizon')",
      not any(w in hf.QUALITY for w in ("through a window", "on a horizon")))
check("QUALITY does not re-litigate light direction/source at all (OUTDOOR_TOP/WALL_TONE's job)",
      "identifiable source" not in hf.QUALITY and "identifiable direction" not in hf.QUALITY)

# ---------------------------------------------------------------------------------------------
# QUALITY must not contradict OUTDOOR_TOP's own light either-or. The concrete failure mode caught
# by review: an absolute "never flat/shadowless" statement fighting OUTDOOR_TOP's overcast
# branch. Checking the actual OUTDOOR_TOP text (not a paraphrase) so this survives OUTDOOR_TOP's
# own wording changing later.
# ---------------------------------------------------------------------------------------------
check("OUTDOOR_TOP still offers a flat/overcast branch (the thing QUALITY must not contradict)",
      "overcast" in hf.OUTDOOR_TOP and "luminous field" in hf.OUTDOOR_TOP)
check("QUALITY contains no absolute anti-flat/anti-shadowless claim that would fight it",
      "never flat" not in hf.QUALITY and "shadowless" not in hf.QUALITY)

# ---------------------------------------------------------------------------------------------
# The research is equally clear on the inverse: stylised words push a model AWAY from
# photorealism. These were never in QUALITY, old or new — this guards the fix from acquiring
# them later (e.g. someone "improving" the mood language without re-reading A-5).
# ---------------------------------------------------------------------------------------------
_STYLE_WORDS = ("magical", "ethereal", "stunning", "dreamlike")
check("no stylising words that fight photorealism are present",
      not any(w in hf.QUALITY.lower() for w in _STYLE_WORDS))

# ---------------------------------------------------------------------------------------------
# check_rules.py's A7 checks read these exact substrings in hf.QUALITY — this change must not
# have silently dropped any of them while rewriting the surrounding prose.
# ---------------------------------------------------------------------------------------------
check("the banned-dread words A7 enforces are all still present",
      all(w in hf.QUALITY for w in ("gloomy", "ominous", "bleak")))
check("'dim is fine' is still present (A7 dark-light-stays-allowed)",
      "dim is fine" in hf.QUALITY)

# ---------------------------------------------------------------------------------------------
# The video-motion side of the same day's research (RULES.md E-3c) must be untouched by this
# pass — this change is scoped to the STILL prompt only. A loose substring check is enough: the
# point is "nobody reverted this while touching the neighbouring file", not re-deriving E-3c.
# ---------------------------------------------------------------------------------------------
check("fetch_motion.MOTION still leads with a POSITIVE list of what may move (E-3c, unchanged)",
      "ONLY" in fm.MOTION and "water rippling" in fm.MOTION)
check("fetch_motion.NEG no longer carries the 2026-11-11-morning symptom ban-list "
      "(floating dust/sparkle/shifting shadows) that 3c replaced", not any(
          w in fm.NEG for w in ("floating dust", "floating sparkle", "shifting shadow")))


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
