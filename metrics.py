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
    except FileNotFoundError:
        return {}
    except Exception as e:
        # A MISSING ledger is normal — first run, fresh clone. A ledger that exists and
        # cannot be read is a different thing entirely, and treating both as "empty" means
        # every no-repeat guarantee silently disappears with nothing in the log to say so.
        print(f"WARNING: {FILE} exists but could not be read ({e}) — every reader of this "
              f"file (oldest-verse-first selection, the drop watcher) now sees an account that "
              f"has never posted.")
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


def published_kst(entry):
    """`published` as an aware KST datetime, or None.

    Two writers fill this field and they disagree on zone: record() below stamps local KST
    (`+09:00`) while the insights.py backfill copies Instagram's own timestamp (`+0000`).
    Both are unambiguous, so nothing is lost — but anything that reads the raw string and
    assumes one zone is silently 9 hours out, which made an early read of this ledger put
    the 19:00 KST posts in the small hours. Always go through here."""
    raw = (entry.get("published") or "").strip()
    if not raw:
        return None
    try:                                  # fromisoformat only learned "+0000" in 3.11
        t = datetime.fromisoformat(raw.replace("+0000", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:                  # legacy naive rows were written in KST
        t = t.replace(tzinfo=KST)
    return t.astimezone(KST)


def prune_deleted(token=None, limit=50):
    """Drop entries for posts Instagram no longer has. Returns the refs removed.

    ledger_merge is a union — by design, so two bots writing at once never lose each other's
    additions — but that also means a DELETION cannot survive it: remove an entry here, and the
    next workflow merges its older copy back in. A post deleted from the account would keep
    occupying its verse for a year (RULES.md C4 keeps the account as the record, and this is the
    same rule applied to removals).

    Only the window the API actually returned is considered. Anything older than the oldest post
    it listed is outside that window and is left alone — absence there means "not asked about",
    not "deleted".
    """
    import post_instagram
    try:
        live = post_instagram.recent_media(limit=limit, token=token)
    except Exception as e:
        print(f"prune skipped ({e}) — not removing anything on a failed lookup")
        return []
    if not live:
        return []
    ids = {m.get("id") for m in live}
    oldest = min((m.get("timestamp") or "")[:19] for m in live)
    data = load()
    gone = []
    for media_id, entry in list(data.items()):
        pub = published_kst(entry)
        if not pub or media_id in ids:
            continue
        # Compare in UTC, the form the API reports.
        stamp = (pub - timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S")
        if stamp >= oldest:
            gone.append(entry.get("ref") or media_id)
            del data[media_id]
    if gone:
        save(data)
        print(f"pruned {len(gone)} post(s) no longer on the account: {gone}")
    return gone


def refresh(token=None, days=MATURE_DAYS):
    """Re-pull insights for every post younger than `days`. Never raises: a metrics failure
    must not be able to break a posting run."""
    import post_instagram
    data = load()
    now = datetime.now(KST)
    touched = 0
    for media_id, entry in data.items():
        pub = published_kst(entry) or now
        if (now - pub).days > days:
            continue                      # numbers have settled; stop spending calls on it
        got = post_instagram.insights(media_id, token)
        if got:
            # MERGE, never replace. likes/comments arrive from the plain media fields (and
            # from the insights.py backfill for the ~100 pre-ledger posts), while reach and
            # views arrive from the insights endpoint, which may answer with only a subset.
            # Assigning the subset used to delete the engagement numbers we already had.
            merged = dict(entry.get("insights") or {})
            merged.update({k: v for k, v in got.items() if v is not None})
            # A real answer supersedes a hand-entered one, and the marker has to go with it —
            # otherwise the ledger keeps saying "typed in by hand" about an API number.
            if got.get("views") is not None:
                merged.pop("views_manual", None)
            entry["insights"] = merged
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
        when = published_kst(e)
        rows.append((when.isoformat() if when else "", when.hour if when else None,
                     e.get("theme") or "?",
                     likes + (cmts if isinstance(cmts, (int, float)) else 0)))
    if not rows:
        return
    rows.sort()
    total = sum(r[3] for r in rows)
    print(f"\n{len(rows)} post(s) with likes/comments — avg {total / len(rows):.1f} per post")
    recent = rows[-THEME_WINDOW:]
    by = {}
    for _, _, theme, eng in recent:
        b = by.setdefault(theme, [0, 0])
        b[0] += eng
        b[1] += 1
    ranked = sorted(by.items(), key=lambda kv: -kv[1][0] / kv[1][1])
    print(f"by theme (likes+comments per post, last {len(recent)} posts): "
          + "  ".join(f"{t}={e / n:.1f}(n={n})" for t, (e, n) in ranked))

    # Which slot earns its place. The two daily slots are a real cost — twice the Veo spend,
    # twice the chance of tripping a duplicate — so they have to be compared, in KST, on the
    # same window the theme table uses.
    slots = {}
    for _, hour, _, eng in recent:
        if hour is None:
            continue
        name = "아침 04-11" if 4 <= hour < 12 else ("낮 12-16" if 12 <= hour < 17 else "저녁 17-24")
        s = slots.setdefault(name, [0, 0])
        s[0] += eng
        s[1] += 1
    if slots:
        print(f"by slot KST (last {len(recent)} posts): "
              + "  ".join(f"{k}={e / n:.1f}(n={n})" for k, (e, n) in sorted(slots.items())))

    # The account's own trend. A theme table cannot show a decline that hits every theme.
    months = {}
    for iso, _, _, eng in rows:
        if iso:
            m = months.setdefault(iso[:7], [0, 0])
            m[0] += eng
            m[1] += 1
    print("by month: " + "  ".join(f"{k}={e / n:.1f}(n={n})" for k, (e, n) in sorted(months.items())))


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


def note_views(which, count):
    """Record a view count read off the app by hand → True if it landed.

    The API cannot give us this: the publishing token's app lacks
    instagram_manage_insights (`(#10) Application does not have permission`), so all 166 posts
    carry likes and comments only while every post visibly shows a view count in the app. That
    gap is not cosmetic — 2026-08-27's reach restriction is a DISTRIBUTION event, and likes are
    a lagging, noisy proxy for distribution. Until IG_INSIGHTS_TOKEN exists (see ig_login.py),
    a number typed in by hand beats no number at all.

    Marked `views_manual` so nothing later mistakes it for something the API returned, and so
    `refresh()` overwriting it with a real value is an improvement rather than a conflict."""
    data = load()
    for media_id, entry in data.items():
        if which in (media_id, entry.get("permalink", ""), entry.get("ref", "")) or \
           which in entry.get("permalink", ""):
            ins = entry.setdefault("insights", {})
            ins["views"] = int(count)
            ins["views_manual"] = True
            save(data)
            print(f"{entry.get('ref', media_id)}: views={count} (hand-entered)")
            return True
    print(f"no post matching {which!r} — pass a ref (\"신명기 1:29\"), a permalink or a media id")
    return False


def note_flag(refs, flagged=True, basis=None):
    """Record which posts Instagram lists under 퍼온 콘텐츠 → count of rows that landed.

    Instagram exposes this list ONLY in the app (계정 상태 → 도달 → 퍼온 콘텐츠); no API field
    carries it. So it reaches us as screenshots, and a screenshot is not a ledger — the
    2026-09-14 restriction has already been re-diagnosed three times because each new picture
    replaced the last one in memory instead of accumulating next to it.

    This is the FASTEST signal the account has. Likes need ~36h to mature and a week to
    separate from noise; the flag is attached within hours of publishing (2026-09-17: a post
    13 hours old was already listed). That turns "did the change work?" from a weekly
    argument into a per-post reading.

    `flagged=False` is not the absence of a record — it is the positive statement "this post
    was looked for in the list and was not there", which is the only way a negative ever
    becomes evidence."""
    data = load()
    today = datetime.now(KST).date().isoformat()
    hit = 0
    for which in refs:
        for media_id, entry in data.items():
            if which in (media_id, entry.get("ref", "")) or which in entry.get("permalink", ""):
                rec = {"flagged": bool(flagged), "checked": today}
                # HOW we know, when it wasn't simply read off the screen. An inference is
                # allowed in this ledger — 시편 4:8 is only known to be absent because both of
                # its neighbours in a newest-first list were present and it was not — but an
                # inference that gets stored looking like an observation is how a guess becomes
                # a fact three sessions later.
                if basis:
                    rec["basis"] = basis
                entry["reposted_flag"] = rec
                hit += 1
                print(f"  {entry.get('ref', media_id):<16} "
                      f"{'FLAGGED 퍼온 콘텐츠' if flagged else 'not in the list'} (checked {today})")
                break
        else:
            print(f"  no post matching {which!r} — pass a ref (\"신명기 1:29\"), permalink or media id")
    if hit:
        save(data)
    return hit


# When the one original sentence started shipping in captions (RULES B-5, commit efec853
# 2026-09-15 00:05 KST; first post carrying it was 09-15 05:19). Posts either side of this
# line are the only before/after the account has for that change.
REFLECTION_SINCE = datetime(2026, 9, 15, 0, 5, tzinfo=KST)


def flag_report(since="2026-09-10"):
    """Line up each post's inputs against whether Instagram flagged it — the table that says
    which axis (caption text, format, length) actually moves the classifier."""
    data = load()
    cut = datetime.fromisoformat(since).replace(tzinfo=KST)
    rows = []
    for media_id, entry in data.items():
        pub = published_kst(entry)
        if not pub or pub < cut:
            continue
        rows.append((pub, entry))
    rows.sort()
    print(f"{'published':<17} {'kind':<6} {'ref':<18} {'views':>6}  flagged?")
    for pub, entry in rows:
        f = entry.get("reposted_flag")
        state = "?" if not f else ("YES" if f["flagged"] else "no")
        v = (entry.get("insights") or {}).get("views")
        print(f"{pub.strftime('%m-%d %H:%M KST'):<17} {(entry.get('kind') or '?')[:5]:<6} "
              f"{str(entry.get('ref'))[:18]:<18} {('-' if v is None else v):>6}  {state}")
    known = [(t, e) for t, e in rows if e.get("reposted_flag")]
    if known:
        print()
        on = [e for t, e in known if t >= REFLECTION_SINCE]
        off = [e for t, e in known if t < REFLECTION_SINCE]
        for label, group in (("caption line ON ", on), ("caption line OFF", off)):
            if group:
                n = sum(1 for e in group if e["reposted_flag"]["flagged"])
                print(f"{label}: {n}/{len(group)} flagged")
        # The axis the caption experiment cannot see. Every flagged post so far is a reel, and
        # reels are ~87% of everything the account posts — so this split is only worth reading
        # once a FEED post has actually been looked for in the list and recorded either way.
        # The comparison the whole restriction hangs on. Views are lifetime totals at different
        # ages, so read the medians as a direction and nothing more — one flagged post (고린도전서
        # 15:55, 2026-09-20) had 199 views at nine hours, which on its own says the flag does not
        # simply switch reach off.
        for label, want in (("flagged   ", True), ("not flagged", False)):
            vs = sorted(v for v in ((e.get("insights") or {}).get("views")
                                    for _, e in known if e["reposted_flag"]["flagged"] is want)
                        if v is not None)
            if vs:
                print(f"{label} views: n={len(vs)} median {vs[len(vs) // 2]}  {vs}")
        for kind in ("REELS", "FEED"):
            g = [e for _, e in known if (e.get("kind") or "") == kind]
            if g:
                n = sum(1 for e in g if e["reposted_flag"]["flagged"])
                print(f"{kind:<16}: {n}/{len(g)} flagged")
        for _, e in known:
            if e["reposted_flag"].get("basis"):
                print(f"  ! {e.get('ref')}: {e['reposted_flag']['basis']}")
    else:
        print("\nno post has been checked against the app list yet — "
              'python3 metrics.py flagged "<ref>" …')


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "record":
        record()
    elif cmd == "refresh":
        refresh()
    elif cmd == "views":
        # python3 metrics.py views "신명기 1:29" 59
        if len(sys.argv) < 4:
            raise SystemExit('usage: metrics.py views "<ref|permalink|media id>" <count>')
        sys.exit(0 if note_views(sys.argv[2], sys.argv[3]) else 1)
    elif cmd in ("flagged", "notflagged"):
        # python3 metrics.py flagged "데살로니가후서 3:3" "고린도전서 2:16" …
        # python3 metrics.py notflagged "시편 4:8"      ← looked for it, it was NOT listed
        if len(sys.argv) < 3:
            raise SystemExit(f'usage: metrics.py {cmd} "<ref|permalink|media id>" [more refs…]')
        sys.exit(0 if note_flag(sys.argv[2:], flagged=(cmd == "flagged")) else 1)
    elif cmd == "flagreport":
        flag_report(*sys.argv[2:3])
    else:
        report()
