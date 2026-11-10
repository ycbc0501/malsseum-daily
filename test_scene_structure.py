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


# ---------------------------------------------------------------------------------------------
# 2026-11-10: `room` and `still_life` used to be SEPARATE buckets even though 23 of 25
# `still_life` categories are also in INTERIOR_CATS and get the identical INDOOR_TOP "wall"
# composition as the 5 `room` categories. avoid_structure could therefore hand back bedroom
# right after tea_cup — different category, different bucket, same "object against a plain
# wall" picture — exactly what the account owner flagged after studying references: "하얀 방이
# 벽인 이미지가 이렇게 계속 나오는건가". Every INTERIOR_CATS category must now share ONE bucket.
# ---------------------------------------------------------------------------------------------
check("every INTERIOR_CATS category is in the SAME structural bucket ('room') as the others — "
      "this is the actual fix, not just a renumbering",
      {hf.SCENE_STRUCTURE[c] for c in hf.INTERIOR_CATS} == {"room"})
check("the merged 'room' bucket is EXACTLY INTERIOR_CATS — no interior category left outside it, "
      "no outdoor category pulled in",
      {c for c, s in hf.SCENE_STRUCTURE.items() if s == "room"} == hf.INTERIOR_CATS)


def walk_with_structure(structure_map, avoid_structure=4, n=60):
    """Like walk() above, but lets a reverse-test substitute the OLD (pre-fix) bucket map."""
    scene_i, cats, interior_adjacent = 0, [], 0
    prev_was_interior = False
    for _ in range(n):
        scene_i, cat = hf.pick_scene(scene_i, cats, avoid_structure=avoid_structure)
        is_interior = cat in hf.INTERIOR_CATS
        if is_interior and prev_was_interior:
            interior_adjacent += 1
        prev_was_interior = is_interior
        cats.append(cat)
        del cats[:-4]
        scene_i += 1
    return interior_adjacent


# Reverse-test: pick_scene's avoid_structure logic is unchanged — it only ever looks at
# SCENE_STRUCTURE. So to prove the OLD split (room vs still_life as separate buckets) really
# could seat two interior scenes back-to-back, simulate it by temporarily splitting the merged
# bucket back apart (first 5 INTERIOR_CATS alphabetically → "room", the rest → "still_life_old"),
# the same shape the dict had before this fix.
_old_interior_split = sorted(hf.INTERIOR_CATS)
_OLD_STRUCTURE = dict(hf.SCENE_STRUCTURE)
for _n, _c in enumerate(_old_interior_split):
    _OLD_STRUCTURE[_c] = "room" if _n < 5 else "still_life_old"

_real_structure = hf.SCENE_STRUCTURE
hf.SCENE_STRUCTURE = _OLD_STRUCTURE
try:
    old_interior_adjacent = walk_with_structure(_OLD_STRUCTURE, n=200)
finally:
    hf.SCENE_STRUCTURE = _real_structure

check("reverse-test: splitting INTERIOR_CATS into two buckets (the pre-fix shape) lets two "
      "interior scenes land back-to-back at least once in 200 picks — proves the next check is "
      "exercising a real fix, not a pool that never clusters",
      old_interior_adjacent > 0)

new_interior_adjacent = walk_with_structure(hf.SCENE_STRUCTURE, n=200)
check("fixed SCENE_STRUCTURE: two INTERIOR_CATS scenes never land back-to-back in 200 picks",
      new_interior_adjacent == 0)


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
