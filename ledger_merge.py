#!/usr/bin/env python3
"""Merge two versions of a machine-written ledger (state.json / metrics.json).

Why this exists: the posting workflow saved the ledger with `git pull --rebase`, which is a
TEXTUAL merge. state.json and metrics.json are single-line JSON written by several bots at once
(the two daily posts, the metrics backfill), so a concurrent push makes git see two rewrites of
the same line and stop with a conflict. `|| true` then swallowed it, the repo was left mid-rebase,
`git push` failed — and the run had ALREADY published. The ledger was lost, the next run read a
stale one and re-posted the same verse with the same scene (잠언 18:10 on 08-26 and 08-28,
잠언 27:17 twice on 08-29). Duplicate posts get the whole account demoted.

These files are dicts, not prose, so the correct resolution is semantic, not textual:
  · dict  → union of keys; OURS wins a shared key (we just wrote it, so it is fresher)
  · list  → theirs first, then anything of ours they lack — order kept, no duplicates
  · int   → max(), because every counter here only ever advances
Usage: ledger_merge.py OURS THEIRS OUT
"""
import json
import sys


def merge(ours, theirs):
    if isinstance(ours, dict) and isinstance(theirs, dict):
        out = dict(theirs)
        for k, v in ours.items():
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
        json.dump(result, f, ensure_ascii=False)
    print(f"{out_p}: merged")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
