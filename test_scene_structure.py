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
import inspect
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


def walk_with_structure(start, avoid_structure=4, n=20):
    """Like walk() above, but starts from a given scene_i so a reverse-test can sweep every
    possible starting offset instead of trusting one fixed start=0 to land on a collision.
    (2026-11-13: start=0/n=200 alone stopped reproducing the old-split collision after an
    unrelated catalog edit — removing one category shifted every later index by one, which
    happened to move the walk off the lucky offset. A reverse-test that only works for
    TODAY's catalog size is not proving the fix; sweeping every start makes it catalog-size
    independent.)"""
    scene_i, cats, interior_adjacent = start, [], 0
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


def total_adjacent_over_all_starts():
    return sum(walk_with_structure(s) for s in range(len(hf.SCENES)))


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
    old_interior_adjacent = total_adjacent_over_all_starts()
finally:
    hf.SCENE_STRUCTURE = _real_structure

check("reverse-test: splitting INTERIOR_CATS into two buckets (the pre-fix shape) lets two "
      "interior scenes land back-to-back at least once, swept across every starting offset — "
      "proves the next check is exercising a real fix, not a pool that never clusters",
      old_interior_adjacent > 0)

new_interior_adjacent = total_adjacent_over_all_starts()
check("fixed SCENE_STRUCTURE: two INTERIOR_CATS scenes never land back-to-back, "
      "swept across every starting offset",
      new_interior_adjacent == 0)


# ---------------------------------------------------------------------------------------------
# 2026-11-11 (D-5): fixing clustering (above) is not the same as fixing FREQUENCY. The account
# owner flagged "또 흰 벽의 방" again after D-4 had already stopped interiors from running
# back-to-back — the reference study (notes/reference-study/2026-11-04.md) shows interiors are
# ~17% of the reference grid but were still 40% of OUR catalog share (56 of 140 scenes), because
# _weave() only ever changed spacing, never share. Reverse-test first: prove a target of 0 (i.e.
# "no dilution", the pre-fix shape) really does leave interiors at the raw ~40% catalog rate, so
# the next check is exercising something real.
# ---------------------------------------------------------------------------------------------
def _interior_share(target):
    old = hf.INDOOR_RATIO_TARGET
    hf.INDOOR_RATIO_TARGET = target
    try:
        scenes, cats = hf._weave()
    finally:
        hf.INDOOR_RATIO_TARGET = old
    return sum(1 for c in cats if c in hf.INTERIOR_CATS) / len(cats), scenes, cats


# target=1.0 degenerates reps to 0 outdoor replays (the ratio math has nothing to dilute with),
# which is the cleanest stand-in for "no dilution happened" without dividing by zero.
_raw_share, _, _ = _interior_share(0.999999)
check("reverse-test: with no dilution, interiors sit at their raw ~40% catalog share "
      "(proves the dilution below is doing real work, not reporting a pool that was already fine)",
      0.35 < _raw_share < 0.45)

_target_share, _target_scenes, _ = _interior_share(hf.INDOOR_RATIO_TARGET)
check(f"fixed _weave(): interiors settle near INDOOR_RATIO_TARGET ({hf.INDOOR_RATIO_TARGET}), "
      "not the raw catalog share",
      abs(_target_share - hf.INDOOR_RATIO_TARGET) < 0.05)
check("the diluted run never repeats the identical scene text back-to-back (replaying the "
      "outdoor pool must not seat the same scene next to itself)",
      all(_target_scenes[i] != _target_scenes[i + 1] for i in range(len(_target_scenes) - 1)))


# ---------------------------------------------------------------------------------------------
# 2026-11-11 (D-5, code review): _weave()'s replay-seam safety must not depend on today's
# SCENE_GROUPS happening to start and end on different categories — a future reordering could
# make out_q's first and last categories MATCH, which would seat that category adjacent to
# itself every time the outdoor pool wraps. Build a synthetic catalog that forces exactly that
# shape (first round-robin pass starts AND ends on "catX") and confirm _weave()'s swap-repair
# still produces zero adjacent same-category pairs, rather than trusting the ordering accident.
# ---------------------------------------------------------------------------------------------
_old_groups, _old_interior, _old_target = hf.SCENE_GROUPS, hf.INTERIOR_CATS, hf.INDOOR_RATIO_TARGET
hf.SCENE_GROUPS = {
    "catX": ["x1 scene", "x2 scene"],   # 2 items: round0 -> catX, round1 -> catX again
    "catY": ["y1 scene"],
    "catZ": ["z1 scene"],
    "room1": ["r1 scene"],
}
hf.INTERIOR_CATS = {"room1"}
hf.INDOOR_RATIO_TARGET = 0.10   # forces reps >= 2, so the replay seam is actually exercised
try:
    _syn_scenes, _syn_cats = hf._weave()
finally:
    hf.SCENE_GROUPS, hf.INTERIOR_CATS, hf.INDOOR_RATIO_TARGET = _old_groups, _old_interior, _old_target

# Independent oracle (not pulled from _weave()'s own internals): the synthetic catalog's
# round-robin is dict-order catX,catY,catZ for round 0 (all three have an item 0) and catX only
# for round 1 (the only category with a second item) -> single pass = [catX,catY,catZ,catX].
# Naively replaying that pass verbatim DOES seat catX next to itself at the seam (index 3 meets
# index 4 of the doubled list) — confirming this synthetic setup genuinely exercises the bug
# class, not a case that was already safe.
_naive_single_pass = ["catX", "catY", "catZ", "catX"]
_naive_doubled = _naive_single_pass * 2
check("sanity: naively replaying the synthetic catalog's single pass collides at the seam "
      "(proves the next check exercises a real repair, not an already-safe case)",
      _naive_doubled[3] == _naive_doubled[4])
check("_weave()'s swap-repair fixes an adjacent-category seam even when the catalog's own order "
      "would have produced one",
      all(_syn_cats[i] != _syn_cats[i + 1] for i in range(len(_syn_cats) - 1)))


# ---------------------------------------------------------------------------------------------
# 2026-11-11 (D-5): INDOOR_TOP used to leave the wall's tone ("pale and bright or deep in
# shadow") as an open either/or, paired with LIGHT[:INDOOR_LIGHT_CUTOFF] being entirely
# daylight-leaning — so the model had no actual reason to ever pick shadow, and never did.
# WALL_TONE moves that decision into code. Reverse-test: with only one tone phrase, every
# indoor render would ask for the same tone regardless of t (the pre-fix shape in effect).
# ---------------------------------------------------------------------------------------------
_old_tone = hf.WALL_TONE
hf.WALL_TONE = _old_tone[:1]
try:
    _same_tone = {hf.scene_variation(t, indoors=True) for t in range(6)}
finally:
    hf.WALL_TONE = _old_tone
check("reverse-test: a single WALL_TONE entry collapses every indoor render onto one tone "
      "phrase regardless of t (proves the next check is exercising a real axis, not a no-op)",
      len({s.rsplit(", ", 1)[-1] for s in _same_tone}) == 1)

check("WALL_TONE has more than one option to actually choose between",
      len(hf.WALL_TONE) >= 2)
_varied_tones = {hf.scene_variation(t, indoors=True).rsplit(", ", 1)[-1]
                 for t in range(len(hf.WALL_TONE) * 2)}
check("fixed scene_variation(): indoor renders actually cycle through more than one wall tone",
      len(_varied_tones) >= 2)
check("INDOOR_TOP no longer poses the unresolved pale-or-shadow either/or itself",
      "either" not in hf.INDOOR_TOP.lower())


# ---------------------------------------------------------------------------------------------
# 2026-11-13 (structural review of D-5b): WALL_TONE used to be picked via `t % len(WALL_TONE)`
# where t is the global post_i counter. A SPECIFIC scene recurs roughly every len(SCENES) posts
# (post_i advances by ~1 per post, same as scene_i), so whenever len(SCENES) became an exact
# multiple of len(WALL_TONE) — which D-5b's category removal that same morning actually did,
# 308 -> 306 -- every recurrence of every indoor scene landed on the identical t % 3, locking
# each scene onto ONE wall tone forever. Reverse-test: reconstruct the OLD naive-modulo
# selection and show it locks at a multiple-of-3 recurrence interval; then show the ACTUAL
# `_wall_tone_pick` (seeded random, not a direct modulo) does not, regardless of the interval.
# ---------------------------------------------------------------------------------------------
def _old_naive_pick(t):
    return t % len(hf.WALL_TONE)

_lock_interval = len(hf.WALL_TONE) * 7   # any multiple of len(WALL_TONE) reproduces the bug
_old_tones_seen = {_old_naive_pick(k * _lock_interval) for k in range(20)}
check("reverse-test: the old naive `t % len(WALL_TONE)` selection locks onto a single tone "
      "when the scene's recurrence interval is a multiple of len(WALL_TONE) (proves the next "
      "check is exercising a real fix, not a coincidence of today's catalog size)",
      len(_old_tones_seen) == 1)

_new_tones_seen = {hf._wall_tone_pick(k * _lock_interval) for k in range(20)}
check("fixed `_wall_tone_pick`: the same multiple-of-3 recurrence interval that locked the old "
      "selection does NOT lock the new one — all three tones still turn up",
      len(_new_tones_seen) == len(hf.WALL_TONE))

check("`_wall_tone_pick` is deterministic (same t always gives the same tone, so a render is "
      "reproducible/debuggable, not flaky)",
      all(hf._wall_tone_pick(t) == hf._wall_tone_pick(t) for t in range(10)))

check("scene_variation() actually calls _wall_tone_pick (not a reintroduced direct modulo)",
      "_wall_tone_pick" in inspect.getsource(hf.scene_variation)
      and "% len(WALL_TONE)" not in inspect.getsource(hf.scene_variation))


# ---------------------------------------------------------------------------------------------
# 2026-11-13 (structural review of D-5b): `curtain`'s own scene text ("a long sheer curtain ...
# at an open window") is a wall-and-window shot like `window_light`, but D-4 filed it under the
# no-wall `still_life` bucket, so it was getting OUTDOOR_TOP's "open sky fills most of the
# picture above it" — the 에베소서 2:8 sky-above-the-room composite. Moved into INTERIOR_CATS.
# ---------------------------------------------------------------------------------------------
check("curtain is INTERIOR (a window-against-a-wall shot, not a no-wall outdoor still life)",
      "curtain" in hf.INTERIOR_CATS)
check("curtain shares the 'room' structural bucket like every other INTERIOR_CATS category",
      hf.SCENE_STRUCTURE.get("curtain") == "room")


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
