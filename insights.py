#!/usr/bin/env python3
"""
Read the account's own numbers back — the loop that turns posting into learning.

The account published 67 posts before this existed and never looked at a single metric, so
every content decision was a guess. This collects per-post metrics into `insights.json`,
joined to what the pipeline knows about each post (verse, theme), and prints a ranked report.

Ranking is by **shares per reach**, not likes: Instagram's stated ranking signals are watch
time, sends per reach and likes per reach, and a send carries several times the weight of a
like in deciding whether to show a post to non-followers. For this account that is not a
growth hack — a 말씀 someone forwards to a friend having a hard day IS the point.

Metric availability differs by media type and changes with API versions, so the metric set is
PROBED once and the working set remembered — a metric Meta stops serving degrades the report
instead of crashing the job.

    python3 insights.py              # collect + append, then print the report
    python3 insights.py --report     # print the report from the stored ledger, fetch nothing
"""

import argparse
import json
import os
import re
import urllib.error
from datetime import datetime, timedelta, timezone

import post_instagram

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "insights.json")
KST = timezone(timedelta(hours=9))

# Superset per media type; whatever Meta rejects is dropped on the first probe and remembered.
WANTED = {
    "REELS": ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions",
              "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"],
    "FEED": ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions",
             "follows", "profile_visits"],
}
FRESH_DAYS = 21          # metrics keep accruing, so keep re-polling recent posts
_REF = re.compile(r"\[([^\[\]]+)\]")


def _themes():
    """verse ref → theme, so posts published long before any bookkeeping existed can still be
    grouped by theme (the ref is printed in every caption)."""
    try:
        with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
            return {v["ref"]: v.get("theme", "") for v in json.load(f)["verses"]}
    except Exception:
        return {}


def _why(e):
    """Meta puts the actual reason in the error body, so an HTTPError alone says nothing
    useful — 'usable metrics = NONE' without a reason sends you looking for the wrong bug."""
    try:
        return json.loads(e.read().decode()).get("error", {}).get("message", str(e))
    except Exception:
        return str(e)


def _insights(media_id, metrics, token):
    if not metrics:
        return {}
    got = post_instagram._get(f"{post_instagram.GRAPH}/{media_id}/insights"
                              f"?metric={','.join(metrics)}&access_token={token}")
    out = {}
    for row in got.get("data", []):
        vals = row.get("values") or [{}]
        out[row["name"]] = vals[0].get("value")
    return out


def fetch_media_insights(media_id, kind, ledger, token):
    """Metrics for one post, probing which ones this media type actually serves.

    Meta rejects the WHOLE request if any single metric is unsupported, so on failure each
    metric is tried alone and the survivors are cached per media type — the slow path runs
    once, not on every poll."""
    ok = ledger.setdefault("metrics_ok", {})
    if kind in ok:
        if not ok[kind]:
            # Probed to nothing already — usually a token missing instagram_manage_insights.
            # Re-probing per post would spend ~9 requests each against a 200/hour budget and
            # still learn nothing, so take the answer and move on until the token changes.
            return {}
        try:
            return _insights(media_id, ok[kind], token)
        except Exception as e:
            print(f"  cached metric set failed ({e}) — re-probing")
            del ok[kind]

    wanted = WANTED.get(kind, WANTED["FEED"])
    try:
        got = _insights(media_id, wanted, token)
        ok[kind] = wanted
        return got
    except urllib.error.HTTPError as e:
        print(f"  {kind}: full metric set rejected ({e.code}: {_why(e)}) — probing one at a time")
    except Exception as e:
        print(f"  {kind}: full metric set failed ({e}) — probing one at a time")

    good, out, last = [], {}, ""
    for m in wanted:
        try:
            out.update(_insights(media_id, [m], token))
            good.append(m)
        except urllib.error.HTTPError as e:
            last = _why(e)
        except Exception as e:
            last = str(e)
    ok[kind] = good
    print(f"  {kind}: usable metrics = {good or 'NONE'}" + (f" — last error: {last}" if not good else ""))
    return out


def collect(ledger, token=None, ig_user_id=None):
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    if not (token and ig_user_id):
        raise SystemExit("set IG_USER_ID and IG_ACCESS_TOKEN")

    themes = _themes()
    media_rows = ledger.setdefault("media", {})
    now = datetime.now(timezone.utc)

    for m in post_instagram.recent_media(limit=30, ig_user_id=ig_user_id, token=token):
        mid = m["id"]
        row = media_rows.setdefault(mid, {})
        row["timestamp"] = m.get("timestamp", "")
        row["permalink"] = m.get("permalink", "")
        kind = "REELS" if m.get("media_product_type") == "REELS" else "FEED"
        row["kind"] = kind
        cap = m.get("caption") or ""
        ref = _REF.search(cap)
        row["ref"] = ref.group(1) if ref else ""
        row["theme"] = themes.get(row["ref"], "")

        try:
            age = (now - datetime.strptime(row["timestamp"], "%Y-%m-%dT%H:%M:%S%z")).days
        except Exception:
            age = 0
        if age > FRESH_DAYS and row.get("metrics"):
            continue                       # settled — stop spending rate limit on it
        print(f"{row['timestamp'][:10]} {row['ref'] or mid}")
        row["metrics"] = fetch_media_insights(mid, kind, ledger, token)

    # The follower curve is the only number that answers "is any of this working at all", so it
    # is read TWICE over. The insights time-series needs instagram_manage_insights, but the plain
    # profile field needs only instagram_basic — so the curve keeps building one point per run
    # even while the insights scope is missing.
    daily = ledger.setdefault("daily_followers", {})
    try:
        prof = post_instagram._get(
            f"{post_instagram.GRAPH}/{ig_user_id}"
            f"?fields=username,followers_count,media_count&access_token={token}")
        daily[datetime.now(KST).strftime("%Y-%m-%d")] = prof.get("followers_count")
        ledger["media_count"] = prof.get("media_count")
        print(f"followers: {prof.get('followers_count')}  media: {prof.get('media_count')}")
    except Exception as e:
        print(f"profile unavailable ({e})")
    try:
        got = post_instagram._get(
            f"{post_instagram.GRAPH}/{ig_user_id}/insights"
            f"?metric=follower_count&period=day&access_token={token}")
        for row in got.get("data", []):          # backfills history the profile field can't give
            for v in row.get("values", []):
                daily[v.get("end_time", "")[:10]] = v.get("value")
    except urllib.error.HTTPError as e:
        print(f"follower time-series unavailable ({e.code}: {_why(e)})")
    except Exception as e:
        print(f"follower time-series unavailable ({e})")

    if any(not v for v in (ledger.get("metrics_ok") or {}).values()):
        print("\nNO METRICS AVAILABLE. Meta answers '(#10) Application does not have permission'\n"
              "for every insights call, which means IG_ACCESS_TOKEN is missing the\n"
              "instagram_manage_insights scope. Everything else here works — publishing,\n"
              "comments and captions only need the scopes the token already has.\n"
              "Fix: reissue the token with instagram_manage_insights added, update the\n"
              "IG_ACCESS_TOKEN repo secret, then run `python3 insights.py --reprobe` once\n"
              "(the empty result is cached deliberately, so it will not retry on its own).")
    ledger["updated"] = datetime.now(KST).isoformat(timespec="seconds")
    return ledger


def report(ledger, top=10):
    rows = []
    for mid, r in ledger.get("media", {}).items():
        met = r.get("metrics") or {}
        reach = met.get("reach") or met.get("views") or 0
        shares = met.get("shares") or 0
        saved = met.get("saved") or 0
        rows.append({
            "date": r.get("timestamp", "")[:10], "ref": r.get("ref") or mid[:8],
            "theme": r.get("theme", ""), "reach": reach, "views": met.get("views") or 0,
            "shares": shares, "saved": saved, "likes": met.get("likes") or 0,
            "spr": (shares / reach * 100) if reach else 0.0,
            "link": r.get("permalink", ""),
        })
    if not rows:
        print("no metrics collected yet")
        return rows

    rows.sort(key=lambda r: (r["spr"], r["shares"]), reverse=True)
    print(f"\n{'date':11}{'ref':16}{'theme':7}{'reach':>7}{'shares':>7}{'saved':>7}"
          f"{'likes':>7}{'send/reach':>12}")
    print("-" * 74)
    for r in rows[:top]:
        print(f"{r['date']:11}{r['ref']:16}{r['theme']:7}{r['reach']:>7}{r['shares']:>7}"
              f"{r['saved']:>7}{r['likes']:>7}{r['spr']:>11.2f}%")

    tot_reach = sum(r["reach"] for r in rows)
    tot_shares = sum(r["shares"] for r in rows)
    print(f"\naccount send/reach: {tot_shares}/{tot_reach} = "
          f"{(tot_shares / tot_reach * 100) if tot_reach else 0:.2f}%   "
          f"(2%+ is a strong signal; below ~0.5% means the post isn't being forwarded)")

    by_theme = {}
    for r in rows:
        t = by_theme.setdefault(r["theme"] or "?", [0, 0])
        t[0] += r["shares"]
        t[1] += r["reach"]
    ranked = sorted(by_theme.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))
    print("\nby theme (send/reach): " + "  ".join(
        f"{t}={(s / rc * 100) if rc else 0:.2f}%" for t, (s, rc) in ranked))

    days = {k: v for k, v in (ledger.get("daily_followers") or {}).items() if v is not None}
    if days:
        keys = sorted(days)[-14:]
        delta = days[keys[-1]] - days[keys[0]]
        print(f"\nfollowers {keys[0]}→{keys[-1]}: {days[keys[0]]} → {days[keys[-1]]} "
              f"({delta:+d})   media: {ledger.get('media_count', '?')}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print the stored ledger, fetch nothing")
    ap.add_argument("--reprobe", action="store_true",
                    help="forget which metrics are available and probe again "
                         "(run this after granting the token a new scope)")
    args = ap.parse_args()

    try:
        with open(LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception:
        ledger = {}
    if args.reprobe:
        ledger.pop("metrics_ok", None)
        print("metric availability forgotten — probing from scratch")
    if not args.report:
        collect(ledger)
        with open(LEDGER, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=1, sort_keys=True)
    report(ledger)


if __name__ == "__main__":
    main()
