#!/usr/bin/env python3
"""The grid must not read as "same structure, different caption."

2026-11-04: the account owner looked at the live grid and flagged it directly —
"같은구조의 방 바다 들판 좀 따분한거같은데" (room/ocean/field, same structure, repeating). The
no-repeat ledger (`pick_scene`, `state["used_scene_cats"]`) was working exactly as designed the
whole time: it never picked the same CATEGORY key within the last 2 posts. The problem it never
addressed is that 70 category keys are not 70 different-looking pictures — `sea`, `shore`,
`harbor`, `reflection_lake`, `river`, `waterfall`, `rain_pond`, `still_water` are eight different
dict keys that all render as "a wide body of water under open sky", so the ledger let three of
them run back-to-back and it read as "ocean, ocean, ocean" regardless.

This file checks two things: that SCENE_STRUCTURE is a COMPLETE grouping (every SCENE_GROUPS key
has exactly one bucket, so a new scene family can't be added and silently fall outside the
clustering check), and that pick_scene() actually uses it to spread buckets apart — with a
reverse-test (avoid_structure=0) proving the check is sensitive, not just always-true.
"""
import sys
from collections import Counter

import fetch_image as hf

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


# ---------------------------------------------------------------------------------------------
# Completeness: SCENE_STRUCTURE must cover SCENE_GROUPS exactly, in both directions.
# ---------------------------------------------------------------------------------------------
groups_keys = set(hf.SCENE_GROUPS.keys())
struct_keys = set(hf.SCENE_STRUCTURE.keys())

check("every SCENE_GROUPS key has a structural bucket", groups_keys <= struct_keys)
check("every SCENE_STRUCTURE key is a real SCENE_GROUPS category", struct_keys <= groups_keys)
check("there is more than one bucket (a single bucket could never spread anything)",
      len(set(hf.SCENE_STRUCTURE.values())) > 1)
# Every SCENE_CATS entry (the woven, flattened list pick_scene actually walks) must resolve too —
# this is the one SCENE_STRUCTURE.get() in pick_scene would silently return None for otherwise,
# and None IS a valid "bucket" that would then itself start clustering.
check("every woven SCENE_CATS entry resolves to a non-None bucket",
      all(hf.SCENE_STRUCTURE.get(c) is not None for c in hf.SCENE_CATS))


# ---------------------------------------------------------------------------------------------
# Reverse-test base case: with avoid_structure=0 (the old behaviour), the SAME bucket CAN run
# back-to-back. If this were false, the next check wouldn't be proving anything — it would mean
# the scene pool happens not to cluster regardless of the setting, and the fix below would be
# untested air.
# ---------------------------------------------------------------------------------------------
def walk(avoid_structure, n=60):
    scene_i, cats, buckets = 0, [], []
    for _ in range(n):
        scene_i, cat = hf.pick_scene(scene_i, cats, avoid_structure=avoid_structure)
        cats.append(cat)
        del cats[:-4]   # keep only last 4, as daily_post.py does (`del scene_cats[:-4]`)
        scene_i += 1
        buckets.append(hf.SCENE_STRUCTURE[cat])
    return buckets


old_buckets = walk(avoid_structure=0)
old_adjacent_repeats = sum(1 for i in range(1, len(old_buckets)) if old_buckets[i] == old_buckets[i - 1])
check("reverse-test: avoid_structure=0 lets a bucket repeat back-to-back at least once in 60 picks "
      "(proves the next check is actually exercising the fix, not a scene pool that never clusters)",
      old_adjacent_repeats > 0)


# ---------------------------------------------------------------------------------------------
# The actual fix: default pick_scene() must not let a bucket repeat on the very next pick.
# ---------------------------------------------------------------------------------------------
new_buckets = walk(avoid_structure=4)
new_adjacent_repeats = sum(1 for i in range(1, len(new_buckets)) if new_buckets[i] == new_buckets[i - 1])
check("default pick_scene() never repeats a structural bucket on the next pick, over 60 picks",
      new_adjacent_repeats == 0)

# No single bucket should dominate a run either — spot-check the distribution is reasonably even,
# not just "never exactly adjacent" (e.g. water,room,water,room forever would also pass the above).
dist = Counter(new_buckets)
check("no structural bucket takes more than a third of 60 picks",
      max(dist.values()) <= 20)


# ---------------------------------------------------------------------------------------------
# pick_scene must still terminate and return something sane when the structural constraint and
# the exact-category constraint together would exclude every scene (degenerate recent_cats).
# ---------------------------------------------------------------------------------------------
all_cats_recent = list(hf.SCENE_CATS)   # every category "recently used" — nothing should satisfy
i, cat = hf.pick_scene(0, all_cats_recent, avoid=len(all_cats_recent), avoid_structure=len(all_cats_recent))
check("pick_scene relaxes rather than hanging when everything looks 'recent'",
      isinstance(i, int) and cat in hf.SCENE_CATS)


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
