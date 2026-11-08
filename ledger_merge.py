#!/usr/bin/env python3
"""Merge two versions of a machine-written ledger (state.json / metrics.json).

Why this exists: the posting workflow saved the ledger with `git pull --rebase`, which is a
TEXTUAL merge. state.json and metrics.json are single-line JSON written by several bots at once
(the two daily posts, the metrics backfill), so a concurrent push makes git see two rewrites of
the same line and stop with a conflict. `|| true` then swallowed it, the repo was left mid-rebase,
`git push` failed — and the run had ALREADY published. The ledger was lost, the next run read a
stale one and re-posted the same verse with the same scene (잠언 18:10 on 08-26 and 08-28,
잠언 27:17 twice on 08-29). Duplicate posts get the whole account demoted.

A DELETION CANNOT BE EXPRESSED HERE. The merge cannot tell "ours removed this key" from
"ours never had it", so a union always restores a key the remote still carries. Every ledger
in this repo is append-only (used_verses, used_clips, metrics rows, counters) with ONE
exception: `pending_replies` in comments.json is a work queue, and removing a finished item
is the whole point. That deletion was silently undone on every run, so comment_reply.py kept
replying to the same comment every few hours for days (2026-09-17). The fix lives there —
`replied_publicly` is the authority and a resurrected queue entry is dropped on sight.
BEFORE ADDING A LEDGER THAT DELETES, read that code: this file will not honour it.

The second ledger that deletes is metrics.json (`prune_deleted`, 2026-09-22), and it did NOT
honour this warning for two weeks: the pruned row came back from origin/main on the very next
save and the deleted post went on holding its verse. Same fix, same shape — `metrics_deleted.json`
is additive, therefore merge-safe, and `metrics.load()` drops anything it lists on sight
(RULES C4d). The verse release is recomputed from it every run for the same reason.

These files are dicts, not prose, so the correct resolution is semantic, not textual:
  · dict  → union of keys; OURS wins a shared key (we just wrote it, so it is fresher)
  · list  → theirs first, then anything of ours they lack — order kept, no duplicates
  · int   → max(), because every counter here only ever advances

THAT LAST LINE IS A LIE FOR A COUNTER THAT WRAPS. state.json["scene_i"] is not a counter that
only advances — pick_scene() walks it modulo len(SCENES), so the very next pick after the
rotation completes a lap is a SMALLER number than before. max() then keeps the old, larger
number forever: the first time scene_i ever reached len(SCENES) (its wrap ceiling), it got stuck
there, because every later real pick is by definition <= that ceiling. Confirmed stuck at
exactly 140 (== len(SCENES)) in production from at least 2026-10-13 through 2026-11-08 — nearly
four weeks where the no-repeat rotation D-1 depends on never actually moved, while posts kept
going out and state["used_scene_cats"] (see below) hid the symptom. RULES.md D-3.

state.json["used_scene_cats"] has the same disease from the other direction. daily_post.py
deliberately trims it to the last 4 picks (`del scene_cats[:-4]`) so pick_scene() only ever
weighs genuinely recent history — the comment at the top of this file already names the general
shape of this hazard ("A DELETION CANNOT BE EXPRESSED HERE... every ledger in this repo is
append-only... with ONE exception"), but nobody recognised this ledger as a second exception when
D-1 built it. List-union dedups BY VALUE: once a category has appeared anywhere in the ledger's
whole history, every later re-pick of that same category is silently dropped as "already seen"
instead of being appended, because `theirs` (the fat historical copy) already contains it. The
tail state.json actually carries in production is "the first time each of ~47 categories ever
appeared," frozen the moment they have all appeared once — not the last 4 posts.

Both are therefore WHOLE-VALUE OURS-WINS keys, not max()/union candidates: the fresher local
write is correct regardless of whether it looks numerically smaller or value-wise a subset of the
remote copy. Keep this set to fields that are read ONLY as "the current rotation position / the
current short window", never as a historical record something else depends on being complete —
that is exactly the line C4c/C4d/the pending_replies fix already drew for deletions, just applied
to two keys that are not deletions but have the identical "merge silently undoes the fresh write"
shape.
Usage: ledger_merge.py OURS THEIRS OUT
"""
import json
import os
import sys

# state.json keys where OURS always replaces THEIRS wholesale — see the docstring above.
OURS_REPLACES_KEYS = {"scene_i", "used_scene_cats"}


def merge(ours, theirs):
    if isinstance(ours, dict) and isinstance(theirs, dict):
        out = dict(theirs)
        for k, v in ours.items():
            if k in OURS_REPLACES_KEYS:
                out[k] = v
            else:
                out[k] = merge(v, theirs[k]) if k in theirs else v
        return out
    if isinstance(ours, list) and isinstance(theirs, list):
        out = list(theirs)
        seen = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in theirs}
        for x in ours:
            key = json.dumps(x, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out
    if isinstance(ours, bool) or isinstance(theirs, bool):
        return ours
    if isinstance(ours, int) and isinstance(theirs, int):
        return max(ours, theirs)          # counters only advance
    return ours                            # ours is the fresher write


def _style(path):
    """The json.dump keywords the file's OWN writer uses.

    Each ledger already has one writer that shapes it: metrics.json comes from
    `metrics.save()` (indent=1, sorted keys), state.json from `daily_post.save_state()`
    (compact, one line). Merging with a different shape rewrites every byte of the file, so
    the next ledger commit is a 2,400-line diff and ANY concurrent push conflicts on the
    whole file instead of on the one entry that actually changed — which is exactly the
    whole-file conflict this script exists to prevent (2026-09-17).

    Unknown ledgers keep the historical compact form."""
    # account.json and api_support.json are written the same way metrics.json is
    # (insights.account(), ig_probe._write()). Leaving them out of this list would make every
    # merge rewrite the whole file compactly, which is precisely the whole-file conflict this
    # function exists to prevent — and account.json is appended to by the same daily workflow
    # that writes metrics.json, so it would hit it immediately.
    # metrics_deleted.json is written by metrics.prune_deleted() with metrics.save()'s shape.
    if os.path.basename(path) in ("metrics.json", "metrics_deleted.json",
                                  "account.json", "api_support.json"):
        return {"indent": 1, "sort_keys": True}
    return {}


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main(ours_p, theirs_p, out_p):
    ours, theirs = load(ours_p), load(theirs_p)
    if ours is None and theirs is None:
        print(f"{out_p}: neither side readable — leaving it alone")
        return 0
    result = ours if theirs is None else theirs if ours is None else merge(ours, theirs)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, **_style(out_p))
    print(f"{out_p}: merged")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
