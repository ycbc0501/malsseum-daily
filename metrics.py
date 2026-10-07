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


# Veo's published rate, derived from the September invoice: 1,400 billed seconds for ₩193,659.
# Update it if the SKU price changes; it is only used to turn recorded seconds into won.
VEO_WON_PER_SECOND = 193659 / 1400


def spend(days=30):
    """What the recorded Veo seconds actually cost over the last `days`.

    The bill was being reconstructed from logs and guessed at from call counts. Posts now record
    veo_seconds, so this is arithmetic on measured numbers instead — and it is the line that
    matters, at ~80% of the project's spend.
    """
    now = datetime.now(KST)
    rows = []
    for entry in load().values():
        pub = published_kst(entry)
        secs = entry.get("veo_seconds")
        if pub and secs and (now - pub).days < days:
            rows.append((pub, secs, entry.get("ref")))
    if not rows:
        print("no post has recorded veo_seconds yet — the next one will")
        return None
    total = sum(r[1] for r in rows)
    span = max(1, (now - min(r[0] for r in rows)).days + 1)
    won = total * VEO_WON_PER_SECOND
    per_day = won / span
    print(f"veo: {len(rows)} post(s) over {span} day(s), {total:.0f}s = ₩{won:,.0f}")
    print(f"     ₩{per_day:,.0f}/day → ₩{per_day * 30:,.0f}/month at this rate")
    worst = max(rows, key=lambda r: r[1])
    print(f"     most expensive: {worst[2]} at {worst[1]:.0f}s")
    return per_day * 30


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
            # otherwise the ledger keeps saying "typed in by hand" about an API number. Every
            # app field can now be hand-entered (see note()), so every marker has to be cleared,
            # not just views': a stale `shares_manual` next to an API `shares` would make the
            # one number Instagram ranks on look untrustworthy exactly when it became real.
            for _f in APP_FIELDS:
                if got.get(_stored(_f)) is not None:
                    merged.pop(f"{_stored(_f)}_manual", None)
            entry["insights"] = merged
            entry["fetched"] = now.isoformat(timespec="seconds")
            touched += 1
            print(f"  {media_id} {entry.get('ref', '?'):<14} "
                  + " ".join(f"{k}={v}" for k, v in sorted(got.items()) if v is not None))
    save(data)
    print(f"metrics: refreshed {touched} post(s)")
    return touched


def distribution(entry):
    """How many people this post reached, or the closest number we actually have.

    `reach` (unique accounts) never arrives from the insights endpoint, which answers `(#10)`
    for this token. It is not unobtainable, though — that was a second-order version of the
    same error: 「릴스 인사이트 → 조회한 사람」 is reach, on screen, free, and went unread
    until 2026-10-07. `views` is the weaker stand-in for the posts nobody has opened yet. They are not the same measurement (views
    counts plays, reach counts people) but one of them exists and the other does not, and
    report() used to require `reach` and therefore showed "0 with insights" while fourteen
    distribution numbers sat in the file unread. That is the same mistake as reading the API's
    silence as "no data": the number was there and nothing looked at it.

    Returns (value, is_exact). `is_exact` is False when this is views standing in for reach, so
    callers can say which one they are printing instead of quietly implying reach.
    """
    ins = entry.get("insights") or {}
    r = ins.get("reach")
    if isinstance(r, (int, float)) and r:
        return r, True
    v = ins.get("views")
    if isinstance(v, (int, float)) and v:
        return v, False
    return None, True


def _rate(entry, num, den="reach"):
    ins = entry.get("insights") or {}
    a = ins.get(num)
    b = distribution(entry)[0] if den == "reach" else ins.get(den)
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
    scored = [e for e in data.values() if distribution(e)[0]]
    exact = sum(1 for e in scored if distribution(e)[1])
    # Reach can now arrive two ways — the API, or 「조회한 사람」 typed off the 릴스 인사이트
    # screen. Both are reach and both are exact, but saying "from the API" about a number a
    # human read off a phone is the kind of small untruth that later gets built on.
    byhand = sum(1 for e in scored if distribution(e)[1]
                 and (e.get("insights") or {}).get("reach_manual"))
    print(f"{len(data)} post(s) recorded, {len(scored)} with a distribution number "
          f"({exact - byhand} reach from the API, {byhand} reach read off 릴스 인사이트, "
          f"{len(scored) - exact} views standing in for reach)\n")
    if not scored:
        print("No reach/views at all — the token lacks instagram_manage_insights "
              "(`python3 metrics.py refresh` once it has it), and nothing has been entered by "
              "hand either (`python3 metrics.py observe \"<ref>\" views=… shares=…`).")
        _engagement_only(data)
        return
    if exact < len(scored):
        # Not `exact == 0`: once ONE post carries real reach, a test for zero goes quiet while
        # the other fourteen posts keep using views as the denominator unannounced. The note
        # has to survive the good news.
        print(f"NOTE: {len(scored) - exact} of {len(scored)} rows below use VIEWS as the "
              "denominator, not reach — views count plays, reach counts people, so those rates "
              "are conservative. The API has never returned `reach` on this token; where reach "
              "is present a human read 「조회한 사람」 off the app (RULES.md G-2).\n")

    def group(key, label):
        buckets = {}
        for e in scored:
            buckets.setdefault(e.get(key, "?"), []).append(e)
        print(f"— by {label} —")
        for k in sorted(buckets, key=str):
            g = buckets[k]
            def vals_of(m):
                vals = [(e["insights"] or {}).get(m) for e in g]
                return [v for v in vals if isinstance(v, (int, float))]

            def avg(m):
                vals = vals_of(m)
                return sum(vals) / len(vals) if vals else 0

            def avg_n(m, scale=1.0, unit=""):
                """Mean plus the count it stands on. A column averaged over 1 post under a
                header saying n=13 reads as thirteen posts agreeing; it is one post."""
                vals = vals_of(m)
                if not vals:
                    return f"{'—':>7}{unit}      "
                return f"{sum(vals) / len(vals) * scale:7.1f}{unit}(n={len(vals)})"

            shares = [r for r in (_rate(e, "shares") for e in g) if r is not None]
            likes = [r for r in (_rate(e, "likes") for e in g) if r is not None]
            dists = [d for d in (distribution(e)[0] for e in g) if d]
            print(f"  {str(k):<12} n={len(g):<3} "
                  f"seen={(sum(dists) / len(dists) if dists else 0):7.1f}  "
                  # `shares` is averaged over the posts that HAVE it, which is not n — printing
                  # a mean over 3 posts under a header saying n=13 is the same quiet overclaim
                  # this whole section exists to stop. Say how many it is standing on.
                  f"saved={avg_n('saved')}  "
                  f"shares={avg_n('shares')}  "
                  # The signal Instagram says it ranks reels on. Printed next to like rate so the
                  # proxy and the real thing are never confused for each other again.
                  f"send/seen={(sum(shares) / len(shares) * 100 if shares else 0):5.2f}%  "
                  f"like/seen={(sum(likes) / len(likes) * 100 if likes else 0):5.2f}%  "
                  f"follows={avg('follows'):5.1f}  "
                  # Watch time and skip rate are the two columns that say whether anyone stayed
                  # long enough to read the verse. Everything to their left measures people who
                  # already did. 2026-10-07: the first post ever measured came back at 2.0s on a
                  # 30s asset with an 85.2% skip rate (STRATEGY.md §15).
                  f"watch={avg_n('ig_reels_avg_watch_time', 1 / 1000, 's')}  "
                  f"skip={avg_n('reels_skip_rate', 1.0, '%')}")
        print()

    group("segments", "Veo segments (reel length)")
    # Does the caption shape matter? `follows` is the column that answers it — the follow CTA moved
    # out of the caption on 2026-08-01, and this is where that shows up or doesn't.
    group("cta_in_caption", "follow CTA in caption")
    group("theme", "verse theme")


# What the Instagram app shows on a post, under the icons, that the API refuses us. The names
# on the right are the ledger's, so a hand-entered number lands in the same field a working
# IG_INSIGHTS_TOKEN would later fill — the whole point of `*_manual` is that a real answer can
# supersede it without a migration.
#
#   ♡  likes      Q  comments      🔁 reposts      ✈️ shares (보내기)      🔖 saves
#
# `shares` is the one that matters most and the one this project went two months without:
# Instagram's own public statement of what ranks a reel is SENDS PER REACH, and until
# 2026-10-07 the strategy note recorded sends as "not designed for" — inferred, never read.
# They were on screen the entire time, next to the paper-plane icon.
#
# 「릴스 인사이트」 — one tap deeper than the post, and the層 that was never opened until
# 2026-10-07 evening. It carries the three things this ledger could not previously hold:
#
#   조회한 사람    → reach     THE unique-accounts number. "reach has never been available on
#                             this token" was true of the API and false of the screen.
#   평균 조회 시간  → watch     seconds in, stored as ms in the API's own field, so a working
#                             token later overwrites it instead of sitting beside it.
#   주요 조회 출처  → src_*     릴스 탭 / 탐색 탭 / 피드, in percent. Reels+Explore are surfaces
#                             shown to people who do NOT follow us, so this is the direct
#                             read on distribution that follower-ratio arithmetic only inferred.
#   건너뛰기 비율  → skip_rate  share of viewers who swiped past. No API equivalent at all.
APP_FIELDS = ("views", "reach", "likes", "comments", "shares", "reposts", "saves",
              "follows", "watch", "skip_rate", "src_reels", "src_explore", "src_feed")

# Percentages off the insights screen: these are not counts and must not be int()ed — 85.2
# becoming 85 is a silent edit to a measurement.
_PCT_FIELDS = ("skip_rate", "src_reels", "src_explore", "src_feed")

# Where a hand-entered field is actually stored. The name a human types is the one on the
# screen; the name on disk is the API's, so a hand-entered number and a future refresh() land
# in the SAME field instead of two fields that silently disagree.
#
#   watch  → the app prints "평균 조회 시간 2초", the API returns milliseconds
#   saves  → the icon is 🔖 and the app says 저장, but the API metric is spelled `saved`,
#            which report() already reads. Entered as `saves` and stored as `saves`, the
#            number would have sat in the file unread — the exact failure this module just
#            fixed one level up (see report()).
#   skip_rate → the API calls it `reels_skip_rate` ("the percentage of views from people who
#            skipped during the first 3 seconds", marked estimated/in development in the
#            reference). Caught by the rule above the moment it was written down: on
#            2026-10-07 this was stored as plain `skip_rate` while the API answers to
#            `reels_skip_rate`, so the hand-entered 85.2% and the first API answer would have
#            sat in two fields that silently disagreed. Whether the API returns 85.2 or 0.852
#            is NOT yet known — no call has ever succeeded. The first real answer must be
#            compared against a hand-entered one before any rate is trusted.
_FIELD_STORE = {"watch": "ig_reels_avg_watch_time", "saves": "saved",
                "skip_rate": "reels_skip_rate"}


def _stored(field):
    return _FIELD_STORE.get(field, field)


def note(which, **vals):
    """Record numbers read off the app by hand → True if they landed.

    The API cannot give us most of these: the publishing token's app lacks
    instagram_manage_insights (`(#10) Application does not have permission`), so every post in
    the ledger carries likes and comments only — while the app shows views, sends and reposts
    right there on the post. That gap is not cosmetic. Reach is a DISTRIBUTION number and likes
    are a lagging, noisy proxy for it; sends are the ranking signal Instagram names out loud.
    Until IG_INSIGHTS_TOKEN exists (see ig_login.py), a number typed in by hand beats no number.

    Each field is marked `<field>_manual` so nothing later mistakes it for something the API
    returned, and so `refresh()` overwriting it with a real value is an improvement rather than
    a conflict. Zero is a VALUE, not a missing number: a post with no sends is the observation
    that makes the posts with sends mean something, so `shares=0` is recorded, not skipped."""
    vals = {k: v for k, v in vals.items() if v is not None}
    unknown = [k for k in vals if k not in APP_FIELDS]
    if unknown:
        print(f"not a field this ledger keeps: {', '.join(unknown)} "
              f"(known: {', '.join(APP_FIELDS)})")
        return False
    if not vals:
        print("nothing to record — pass at least one of " + ", ".join(APP_FIELDS))
        return False
    data = load()
    for media_id, entry in data.items():
        if which in (media_id, entry.get("permalink", ""), entry.get("ref", "")) or \
           which in entry.get("permalink", ""):
            ins = entry.setdefault("insights", {})
            for k, v in vals.items():
                if k in _PCT_FIELDS:
                    val = float(v)
                elif k == "watch":
                    val = round(float(v) * 1000)       # 초 → ms, the API's unit
                else:
                    val = int(v)
                ins[_stored(k)] = val
                ins[f"{_stored(k)}_manual"] = True
            save(data)
            print(f"{entry.get('ref', media_id)}: "
                  + " ".join(f"{k}={v}" for k, v in sorted(vals.items())) + " (hand-entered)")
            return True
    print(f"no post matching {which!r} — pass a ref (\"신명기 1:29\"), a permalink or a media id")
    return False


def note_views(which, count):
    """Back-compat: the old views-only entry point (notes/reach-recovery-2026-09-14.md §409)."""
    return note(which, views=count)


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
    elif cmd == "observe":
        # Everything the app shows on a post, in one line, read straight off the screen:
        #   python3 metrics.py observe "요한삼서 1:2" views=465 likes=40 comments=3 shares=5 reposts=1
        # `shares` is the paper-plane (보내기) count. Record 0 explicitly when there are none.
        if len(sys.argv) < 4 or "=" not in "".join(sys.argv[3:]):
            raise SystemExit('usage: metrics.py observe "<ref|permalink|media id>" '
                             'views=465 likes=40 shares=5 …  (fields: '
                             + ", ".join(APP_FIELDS) + ")")
        kv = {}
        for arg in sys.argv[3:]:
            if "=" not in arg:
                raise SystemExit(f"not a field=value pair: {arg!r}")
            k, v = arg.split("=", 1)
            kv[k.strip()] = v.strip()
        sys.exit(0 if note(sys.argv[2], **kv) else 1)
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
