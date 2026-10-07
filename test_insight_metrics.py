#!/usr/bin/env python3
"""The API's metric names must actually be asked for, and the read token must reach its host.

Two months of strategy rested on "the API cannot give us reach or shares". It can. The token
was missing one permission nobody ever checked, and — separately, and ours — the code never
asked for `reels_skip_rate` or `reposts` even though the reference lists both for REELS. So
when the permission does arrive, the two numbers hand-entered off the app last night would
STILL have been missing, and it would have looked like Meta's fault.

These checks pin the three things that have to hold the moment a token with
instagram_manage_insights exists:

  1. every metric the reference lists for REELS and this account cares about is requested
  2. the single-metric salvage path asks for them too (a bundle is all-or-nothing)
  3. insights() sends the token to the host that token is valid for

(3) is the one that would have wasted a human's OAuth trip: an Instagram-Login token sent to
graph.facebook.com fails with an OAuth error, insights() swallows it into {}, and the log
prints "insights unavailable" — the same sentence a missing permission prints.
"""
import inspect
import sys

import insights
import post_instagram

fails = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        fails.append(name)


# Verbatim from the Instagram media-insights reference, read 2026-10-07. If Meta changes this
# list, this constant is the thing to update — deliberately, not by accident.
REFERENCE_REELS = {
    "comments", "crossposted_views", "facebook_views", "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time", "likes", "reach", "reels_skip_rate", "reposts",
    "saved", "shares", "total_interactions", "views", "total_comments", "total_likes",
    "total_views",
}

# The subset this account's strategy is actually built on. Every one of these was being typed
# in by hand on 2026-10-07 while the API had a name for it.
MUST_ASK = {"reach", "views", "shares", "saved", "likes", "comments", "total_interactions",
            "reels_skip_rate", "reposts", "ig_reels_avg_watch_time"}


def run():
    asked = {m for tier in post_instagram.INSIGHT_TIERS for m in tier}

    check("every requested metric is a real reference metric",
          asked <= REFERENCE_REELS or print(f"    not in reference: {sorted(asked - REFERENCE_REELS)}"))
    missing = sorted(MUST_ASK - asked)
    check(f"every metric the strategy relies on is requested{'' if not missing else f' (missing {missing})'}",
          not missing)
    # These two specifically: they are the 건너뛰기 비율 and 리포스트 off the app screen.
    check("reels_skip_rate is asked for (= 건너뛰기 비율)", "reels_skip_rate" in asked)
    check("reposts is asked for (= 🔁)", "reposts" in asked)

    # A bundle is all-or-nothing, so the salvage path has to carry them too — otherwise one
    # unsupported name in a tier silently costs us the metric on every fallback.
    singles = set(post_instagram.INSIGHT_SINGLES)
    check("the one-at-a-time fallback also asks for skip rate and reposts",
          {"reels_skip_rate", "reposts"} <= singles)
    check("the fallback asks only for real metrics", singles <= REFERENCE_REELS)

    # Tiers must degrade: each one no larger than the last, so a rejection actually retries
    # with less rather than the same.
    sizes = [len(t) for t in post_instagram.INSIGHT_TIERS]
    check("tiers degrade monotonically", all(a >= b for a, b in zip(sizes, sizes[1:])))
    check("the last tier is a single metric", sizes[-1] == 1)

    # --- the host bug -------------------------------------------------------------------
    sig = inspect.signature(post_instagram.insights)
    check("insights() accepts a base host", "base" in sig.parameters)
    src = inspect.getsource(post_instagram.insights)
    check("insights() never hardcodes the publishing host",
          "{GRAPH}/" not in src and "{base}/" in src)
    check("insights.py hands the base down",
          "base=base" in inspect.getsource(insights.backfill))
    # api() is the thing that knows an Instagram-Login token lives elsewhere.
    check("api() still routes an insights token to graph.instagram.com",
          "graph.instagram.com" in inspect.getsource(insights.api))

    print("\n" + ("all good" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
