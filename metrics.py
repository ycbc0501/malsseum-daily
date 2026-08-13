#!/usr/bin/env python3
"""Performance ledger — what each post actually did.

Every no-repeat ledger in `state.json` answers "what have we used?". None of them answers
"did it work?", so every format decision so far has been an argument from taste. This file
records the numbers instead: one entry per published post, carrying both the *inputs* we
chose (verse, theme, reel duration, how many Veo segments) and the *outcome* Instagram
reports (reach, plays, shares, saves, watch time).

Recording the inputs alongside the outcome is the whole point — it makes changes measurable
after the fact without building an A/B harness. The 8s→16s reel change is the first one it
answers: `python3 metrics.py report` groups by duration.

Kept OUT of state.json deliberately. state.json is a no-repeat ledger — bounded, rewritten
every run, and only ever read to avoid repeats. This is append-only history that must grow,
and mixing the two would mean either truncating history or bloating the hot file.

    python3 metrics.py record          # after publishing (reads output/_meta.json + _media_id.txt)
    python3 metrics.py refresh         # re-pull insights for recent posts (numbers mature for days)
    python3 metrics.py report          # what's working
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "metrics.json")
OUT = os.path.join(HERE, "output")
KST = timezone(timedelta(hours=9))

# How long a post's numbers keep moving. Reels accumulate views for well over a week, so a
# single fetch right after publishing would record a near-zero and freeze it. `refresh` re-pulls
# anything younger than this on every run.
MATURE_DAYS = 14


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)


def record(media_id=None, meta=None):
    """Log a freshly published post. Inputs only — insights come later via refresh(),
    because at publish time every counter is still zero."""
    if media_id is None:
        p = os.path.join(OUT, "_media_id.txt")
        media_id = open(p).read().strip() if os.path.exists(p) else ""
    if not media_id:
        print("metrics: no media id → nothing to record")
        return None
    if meta is None:
        p = os.path.join(OUT, "_meta.json")
        meta = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    data = load()
    entry = data.setdefault(media_id, {})
    entry.update(meta)
    entry.setdefault("published", datetime.now(KST).isoformat(timespec="seconds"))
    entry.setdefault("insights", {})
    save(data)
    print(f"metrics: recorded {media_id} ({meta.get('ref', '?')}, "
          f"{meta.get('duration', '?')}s, {meta.get('segments', '?')} segment(s))")
    return media_id


def refresh(token=None, days=MATURE_DAYS):
    """Re-pull insights for every post younger than `days`. Never raises: a metrics failure
    must not be able to break a posting run."""
    import post_instagram
    data = load()
    now = datetime.now(KST)
    touched = 0
    for media_id, entry in data.items():
        try:
            pub = datetime.fromisoformat(entry.get("published", ""))
        except Exception:
            pub = now
        if (now - pub).days > days:
            continue                      # numbers have settled; stop spending calls on it
        got = post_instagram.insights(media_id, token)
        if got:
            entry["insights"] = got
            entry["fetched"] = now.isoformat(timespec="seconds")
            touched += 1
            print(f"  {media_id} {entry.get('ref', '?'):<14} "
                  + " ".join(f"{k}={v}" for k, v in sorted(got.items()) if v is not None))
    save(data)
    print(f"metrics: refreshed {touched} post(s)")
    return touched


def _rate(entry, num, den="reach"):
    ins = entry.get("insights") or {}
    a, b = ins.get(num), ins.get(den)
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not b:
        return None
    return a / b


THEME_WINDOW = 40        # posts back the degraded theme table looks (see _engagement_only)


def _engagement_only(data):
    """Fallback table when reach is unavailable: likes + comments, which are plain media
    fields needing no insights scope. It ranks posts against each other, which is most of
    what the ledger is for, and it is labelled so nobody mistakes it for reach.

    Windowed on purpose. Engagement tracks how many followers existed at the time, so over
    all time a theme that ran during launch week looks terrible forever: 위로 averaged 5.4
    across 12 posts from 2026-06-29..07-04 and 22 on the one posted since. Comparing across
    account sizes measures age, not content."""
    rows = []
    for e in data.values():
        ins = e.get("insights") or {}
        likes, cmts = ins.get("likes"), ins.get("comments")
        if not isinstance(likes, (int, float)):
            continue
        rows.append((e.get("published", "")[:10], e.get("theme") or "?",
                     likes + (cmts if isinstance(cmts, (int, float)) else 0)))
    if not rows:
        return
    rows.sort()
    total = sum(r[2] for r in rows)
    print(f"\n{len(rows)} post(s) with likes/comments — avg {total / len(rows):.1f} per post")
    recent = rows[-THEME_WINDOW:]
    by = {}
    for _, theme, eng in recent:
        b = by.setdefault(theme, [0, 0])
        b[0] += eng
        b[1] += 1
    ranked = sorted(by.items(), key=lambda kv: -kv[1][0] / kv[1][1])
    print(f"by theme (likes+comments per post, last {len(recent)} posts): "
          + "  ".join(f"{t}={e / n:.1f}(n={n})" for t, (e, n) in ranked))


def report():
    """Group posts by the choices we made, so a format change shows up as a number.

    Reach is the denominator throughout: the open question is 'why do so few people see
    this?', and a share rate computed against a tiny reach says nothing about reach itself."""
    data = load()
    if not data:
        print("metrics.json is empty — nothing published has been recorded yet.")
        return
    scored = [e for e in data.values() if (e.get("insights") or {}).get("reach")]
    print(f"{len(data)} post(s) recorded, {len(scored)} with insights\n")
    if not scored:
        print("No reach/shares — the token lacks instagram_manage_insights "
              "(`python3 metrics.py refresh` once it has it).")
        _engagement_only(data)
        return

    def group(key, label):
        buckets = {}
        for e in scored:
            buckets.setdefault(e.get(key, "?"), []).append(e)
        print(f"— by {label} —")
        for k in sorted(buckets, key=str):
            g = buckets[k]
            def avg(m):
                vals = [(e["insights"] or {}).get(m) for e in g]
                vals = [v for v in vals if isinstance(v, (int, float))]
                return sum(vals) / len(vals) if vals else 0
            shares = [r for r in (_rate(e, "shares") for e in g) if r is not None]
            print(f"  {str(k):<12} n={len(g):<3} reach={avg('reach'):7.1f}  "
                  f"plays={avg('plays') or avg('views'):7.1f}  saved={avg('saved'):5.1f}  "
                  f"shares={avg('shares'):5.1f}  "
                  f"share/reach={(sum(shares) / len(shares) * 100 if shares else 0):5.2f}%  "
                  f"follows={avg('follows'):5.1f}  "
                  f"watch={avg('ig_reels_avg_watch_time') / 1000 if avg('ig_reels_avg_watch_time') else 0:5.1f}s")
        print()

    group("segments", "Veo segments (reel length)")
    # Does the caption shape matter? `follows` is the column that answers it — the follow CTA moved
    # out of the caption on 2026-08-01, and this is where that shows up or doesn't.
    group("cta_in_caption", "follow CTA in caption")
    group("theme", "verse theme")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "record":
        record()
    elif cmd == "refresh":
        refresh()
    else:
        report()
