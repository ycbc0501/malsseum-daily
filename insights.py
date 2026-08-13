#!/usr/bin/env python3
"""
Backfill `metrics.json` for posts published before metrics.py existed, and track followers.

`metrics.py` is the performance ledger (rule 11b) and it records a post at publish time. That
leaves two gaps this file fills, and nothing else:

  1. The ~100 posts published before that ledger existed have no entry at all.
  2. Nothing records the follower count, which is the only number that answers "is any of this
     working?" — and unlike media insights it needs no special scope.

This deliberately does NOT re-implement metric fetching: `post_instagram.insights()` already
degrades tier by tier, and two collectors measuring one account is how you get two different
answers to one question (rule 11b).

    python3 insights.py            # backfill metrics.json + record today's follower count
"""

import json
import os
from datetime import datetime, timedelta, timezone

import metrics
import post_instagram

HERE = os.path.dirname(os.path.abspath(__file__))
FOLLOWERS = os.path.join(HERE, "followers.json")
KST = timezone(timedelta(hours=9))
import re
_REF = re.compile(r"\[([^\[\]]+)\]")


def api():
    """(base_url, account_path, token) — which door to read through.

    `IG_ACCESS_TOKEN` is the Facebook-login system-user token that publishes; it never expires
    but cannot be granted `instagram_manage_insights` without a Business-Manager action gated
    behind SMS 2FA that does not arrive. `IG_INSIGHTS_TOKEN` comes from Instagram Login
    (`ig_login.py`), needs no Facebook account, and is read-only. When present it wins for
    READING. Publishing never touches it."""
    tok = os.environ.get("IG_INSIGHTS_TOKEN")
    if tok:
        return "https://graph.instagram.com/v21.0", "me", tok
    return (post_instagram.GRAPH, os.environ.get("IG_USER_ID"),
            os.environ.get("IG_ACCESS_TOKEN"))


def _themes():
    """verse ref → theme, so posts predating any bookkeeping still resolve (the caption
    carries the reference)."""
    try:
        with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
            return {v["ref"]: v.get("theme", "") for v in json.load(f)["verses"]}
    except Exception:
        return {}


def backfill(limit=90):
    """Give every recent post an entry in metrics.json, filling what we can actually read.

    Inputs (ref, theme) come from the caption; outcomes come from post_instagram.insights().
    When the token lacks the insights scope that returns {}, so `like_count`/`comments_count`
    are recorded instead — plain media fields, no scope needed. Partial truth beats none, and
    the entry says which it is."""
    base, uid, token = api()
    if not (uid and token):
        raise SystemExit("set IG_USER_ID and IG_ACCESS_TOKEN (or IG_INSIGHTS_TOKEN)")
    print(f"reading via {base} as {uid}")

    themes, data = _themes(), metrics.load()
    listing = post_instagram._get(
        f"{base}/{uid}/media"
        f"?fields=id,timestamp,media_product_type,permalink,caption,like_count,comments_count"
        f"&limit={int(limit)}&access_token={token}")

    added = filled = 0
    for m in listing.get("data", []):
        entry = data.setdefault(m["id"], {})
        if not entry:
            added += 1
        ref = _REF.search(m.get("caption") or "")
        entry.setdefault("ref", ref.group(1) if ref else "")
        entry.setdefault("theme", themes.get(entry.get("ref", ""), ""))
        entry.setdefault("permalink", m.get("permalink", ""))
        entry.setdefault("kind", m.get("media_product_type", ""))
        if m.get("timestamp"):
            entry.setdefault("published", m["timestamp"])
        got = entry.get("insights") or {}
        if not got:
            try:
                got = post_instagram.insights(m["id"], token) or {}
            except Exception as e:
                print(f"  insights({m['id']}) failed: {e}")
                got = {}
            # No scope → no reach/shares. These two are plain fields and always readable, so
            # record them rather than storing an empty dict and calling it measured.
            got.setdefault("likes", m.get("like_count"))
            got.setdefault("comments", m.get("comments_count"))
            entry["insights"] = got
            filled += 1
    metrics.save(data)
    print(f"backfill: {added} new entr(ies), {filled} filled, {len(data)} total")
    return data


def followers():
    """Today's follower count → followers.json. `followers_count` is a plain profile field:
    it needs only instagram_basic, so the curve keeps building even while the insights scope
    is out of reach."""
    base, uid, token = api()
    try:
        prof = post_instagram._get(
            f"{base}/{uid}?fields=username,followers_count,media_count&access_token={token}")
    except Exception as e:
        print(f"profile unavailable ({e})")
        return {}
    try:
        with open(FOLLOWERS, encoding="utf-8") as f:
            curve = json.load(f)
    except Exception:
        curve = {}
    curve[datetime.now(KST).strftime("%Y-%m-%d")] = prof.get("followers_count")
    with open(FOLLOWERS, "w", encoding="utf-8") as f:
        json.dump(curve, f, ensure_ascii=False, indent=1, sort_keys=True)

    days = sorted(k for k, v in curve.items() if v is not None)
    if days:
        first, last = days[0], days[-1]
        print(f"followers {first}→{last}: {curve[first]} → {curve[last]} "
              f"({curve[last] - curve[first]:+d})   media: {prof.get('media_count')}")
    return curve


if __name__ == "__main__":
    backfill()
    followers()
    metrics.report()
