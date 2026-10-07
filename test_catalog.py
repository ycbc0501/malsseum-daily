#!/usr/bin/env python3
"""The catalog must stay a transcription of Meta's reference, and collection must ask for ALL of it.

The instruction this file exists to enforce, 2026-10-07: *"독스에 있는 거 다 받고 거기서 우리가
쓸 걸 정해"* — collect everything the docs document, then choose. Every previous version of this
code chose at REQUEST time, which made the choice invisible and permanent: `reels_skip_rate` sat
in the reference for months while the strategy document called it the account's #1 unknown.

So the checks here are deliberately about COMPLETENESS rather than correctness of any one value:

  1. every metric the reference lists is in ig_catalog, with its documented media types
  2. the request bundles ARE the catalog — not a subset someone remembered
  3. a metric documented to throw never rides in a bundle (a bundle is all-or-nothing)
  4. the account dimension asks for every metric AND every documented breakdown
  5. provenance is written down, never inferred from a missing marker
"""
import json
import os
import sys
import tempfile

import ig_catalog
import insights
import metrics
import post_instagram

fails = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------------------------------------
# Verbatim from the reference pages, fetched 2026-10-07. These constants are the authority; if
# Meta changes the docs, THESE lines get edited — deliberately, with a date — and the catalog
# follows. The point is that nothing can quietly diverge.
# ---------------------------------------------------------------------------------------------
REF_MEDIA = {
    "comments", "crossposted_views", "facebook_views", "follows", "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time", "impressions", "likes", "link_clicks", "navigation",
    "profile_activity", "profile_visits", "reach", "reels_skip_rate", "replies", "reposts",
    "saved", "shares", "total_interactions", "views", "total_comments", "total_likes",
    "total_views",
}
REF_REELS = {
    "comments", "crossposted_views", "facebook_views", "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time", "likes", "reach", "reels_skip_rate", "reposts",
    "saved", "shares", "total_interactions", "views", "total_comments", "total_likes",
    "total_views",
}
REF_ACCOUNT = {
    "accounts_engaged", "comments", "engaged_audience_demographics", "follows_and_unfollows",
    "follower_demographics", "impressions", "likes", "profile_links_taps", "reach", "replies",
    "reposts", "saves", "shares", "total_interactions", "views",
}
# Documented to throw, or restricted to the Facebook-Login flavour. These are the names that
# must never appear in a bundle — one of them fails the request and blanks the rest.
REF_FRAGILE = {"crossposted_views", "facebook_views", "total_comments", "total_likes",
               "total_views", "impressions"}

print("1. the catalog is the reference, transcribed")
check("every documented media metric is catalogued",
      REF_MEDIA <= set(ig_catalog.MEDIA_METRICS))
check("no invented media metric", set(ig_catalog.MEDIA_METRICS) <= REF_MEDIA)
check("every documented account metric is catalogued",
      REF_ACCOUNT <= set(ig_catalog.ACCOUNT_METRICS))
check("no invented account metric", set(ig_catalog.ACCOUNT_METRICS) <= REF_ACCOUNT)
check("REELS media types match the reference",
      set(ig_catalog.media_metrics(ig_catalog.REELS, bundle_only=True))
      | set(ig_catalog.media_metrics(ig_catalog.REELS, fragile_only=True)) == REF_REELS)
check("follows/profile_visits are FEED-only, as documented",
      "follows" not in ig_catalog.media_metrics(ig_catalog.REELS)
      and "follows" in ig_catalog.media_metrics(ig_catalog.FEED))
check("a carousel is treated as FEED, not as an unknown type",
      ig_catalog.media_metrics("CAROUSEL_CONTAINER") == ig_catalog.media_metrics(ig_catalog.FEED))

print("2. the request bundle IS the catalog")
tier0 = set(ig_catalog.tiers(ig_catalog.REELS)[0])
check("tier 0 asks for every bundle-safe REELS metric",
      tier0 == set(ig_catalog.media_metrics(ig_catalog.REELS, bundle_only=True)))
check("tier 0 carries reels_skip_rate (the metric that was missing for months)",
      "reels_skip_rate" in tier0)
check("post_instagram.INSIGHT_TIERS is derived, not hand-typed",
      post_instagram.INSIGHT_TIERS[0] == ig_catalog.tiers(ig_catalog.REELS)[0])
check("the one-at-a-time salvage list covers every REELS metric",
      set(post_instagram.INSIGHT_SINGLES) == REF_REELS)
check("FEED bundles differ from REELS bundles",
      set(ig_catalog.tiers(ig_catalog.FEED)[0]) != tier0)

print("3. nothing fragile rides in a bundle")
for i, tier in enumerate(ig_catalog.tiers(ig_catalog.REELS)):
    check(f"tier {i} is free of throw-prone metrics", not (set(tier) & REF_FRAGILE))
for i, tier in enumerate(ig_catalog.tiers(ig_catalog.FEED)):
    check(f"FEED tier {i} is free of throw-prone metrics", not (set(tier) & REF_FRAGILE))
check("tiers narrow monotonically (a fallback that grows is not a fallback)",
      all(len(a) >= len(b) for a, b in zip(ig_catalog.tiers(ig_catalog.REELS),
                                           ig_catalog.tiers(ig_catalog.REELS)[1:])))
check("copyright_check_information is kept OUT of the batch listing",
      "copyright_check_information" not in ig_catalog.media_fields()
      and "copyright_check_information" in ig_catalog.media_fields(solo=True))

print("4. the account dimension asks for everything, breakdowns included")
rows = ig_catalog.account_requests()
asked = {m for m, *_ in rows}
check("every non-deprecated account metric is requested",
      asked == set(ig_catalog.account_metrics()))
check("the deprecated metric is catalogued but NOT requested",
      "impressions" in ig_catalog.ACCOUNT_METRICS and "impressions" not in asked)
pairs = {(m, bd) for m, _p, _t, bd, _tf in rows if bd}
check("reach is broken down by follow_type (the non-follower answer)",
      ("reach", "follow_type") in pairs)
check("every documented breakdown is requested",
      all((m, bd) in pairs
          for m, spec in ig_catalog.ACCOUNT_METRICS.items() if m not in ig_catalog.DEPRECATED
          for bd in spec["breakdowns"]))
check("lifetime metrics carry a timeframe (they are rejected without one)",
      all(tf for m, p, _t, _bd, tf in rows if p == "lifetime"))
check("day metrics carry no timeframe",
      all(tf is None for m, p, _t, _bd, tf in rows if p == "day"))
check("account fields go well past followers_count",
      len(ig_catalog.account_fields()) >= 10
      and "is_published" in ig_catalog.account_fields())

print("5. provenance is written down, not inferred")
check("total_like_count is overridden by like_count (organic, matching the metric's docs)",
      [f for f, m in ig_catalog.FIELD_AS_METRIC_ORDER if m == "likes"]
      == ["total_like_count", "like_count"])
check("DUAL_SOURCE lists exactly the metrics a plain field can also supply",
      set(ig_catalog.DUAL_SOURCE) == {"views", "likes", "comments", "shares", "saved", "reposts"})

_tmp = tempfile.mkdtemp()
metrics.FILE = os.path.join(_tmp, "metrics.json")
insights.ACCOUNT = os.path.join(_tmp, "account.json")
insights.FOLLOWERS = os.path.join(_tmp, "followers.json")

MEDIA = {"id": "m1", "timestamp": "2026-10-06T20:00:00+0000", "media_product_type": "REELS",
         "media_type": "VIDEO", "permalink": "p", "caption": "x [요한복음 3:16]",
         "like_count": 9, "comments_count": 2, "shares_count": 3, "total_views_count": 400,
         "total_like_count": 9, "total_comments_count": 2, "reposts_count": 1,
         "media_audio_type": "ORIGINAL_SOUND", "is_shared_to_feed": True}


def run_backfill(start, media=None, fresh=None):
    """backfill() against a stubbed API, so provenance can be asserted without a token."""
    metrics.save({"m1": dict(start)})
    real_get, real_ins = post_instagram._get, post_instagram.insights
    post_instagram._get = lambda url: {"data": [dict(media or MEDIA)]}
    post_instagram.insights = lambda *a, **k: dict(fresh or {})
    try:
        insights.backfill(limit=5)
    finally:
        post_instagram._get, post_instagram.insights = real_get, real_ins
    return (metrics.load()["m1"].get("insights") or {}), (metrics.load()["m1"].get("node") or {})


os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"] = "u", "t"
ins, node = run_backfill({"published": "2026-10-06T20:00:00+0000", "ref": "요한복음 3:16",
                          "insights": {"likes": 2}})
check("an UNMARKED stored value is refreshed from the plain field (the 골로새서 likes=2 bug)",
      ins.get("likes") == 9)
check("the field it came from is recorded, not just the number",
      ins.get("likes_field") == "like_count" and ins.get("views_field") == "total_views_count")
check("views arrives with no insights scope at all", ins.get("views") == 400)
check("shares arrives with no insights scope at all", ins.get("shares") == 3)
check("plain fields are kept on the entry as inputs too",
      node.get("media_audio_type") == "ORIGINAL_SOUND" and node.get("is_shared_to_feed") is True)
check("the expiring CDN thumbnail is not written into a committed ledger",
      "thumbnail_url" not in node and "caption" not in node)

ins, _ = run_backfill({"published": "2026-10-06T20:00:00+0000",
                       "insights": {"views": 999, "views_api": True}})
check("an endpoint value is NOT overwritten by a plain field", ins.get("views") == 999)

ins, _ = run_backfill({"published": "2026-10-06T20:00:00+0000",
                       "insights": {"views": 260, "views_manual": True}})
check("a hand-entered value IS replaced by the API's", ins.get("views") == 400)
check("and its hand-entered marker is cleared", "views_manual" not in ins)

ins, _ = run_backfill({"published": "2026-10-06T20:00:00+0000", "insights": {}},
                      fresh={"views": 500, "reach": 233, "reels_skip_rate": 85.2})
check("an endpoint answer wins over the plain field", ins.get("views") == 500)
check("and is marked as the endpoint's, so the field stops overwriting it",
      ins.get("views_api") is True and "views_field" not in ins)
check("reach only ever comes from the endpoint and needs no marker",
      ins.get("reach") == 233 and "reach_api" not in ins)

print("6. account collection records rejections instead of losing them")
real_get = post_instagram._get


def _boom(url):
    raise RuntimeError("HTTP 400: (#10) Application does not have permission")


post_instagram._get = _boom
try:
    book = insights.account(base="b", uid="u", token="t")
finally:
    post_instagram._get = real_get
day = next(iter(book.values()))
check("a fully rejected day is written down, not silently empty",
      bool(day.get("errors")))
# 33 copies of one sentence, every day, for as long as the permission is missing, is ~12,000
# lines a year in a ledger whose value is being readable by eye. One fact, with its scale.
check("an all-identical refusal is recorded ONCE, with how many requests it covered",
      (day["errors"].get("*") or "").startswith("HTTP 400: (#10)")
      and day["errors"].get("*_requests") == len(ig_catalog.account_requests()))


def _mixed(url):
    if "metric=reach" in url and "breakdown=follow_type" in url:
        raise RuntimeError("HTTP 400: (#10) no permission for this breakdown")
    if "/insights?" in url:
        return {"data": [{"total_value": {"value": 1}}]}
    return {"id": "u", "followers_count": 215}


post_instagram._get = _mixed
try:
    book = insights.account(base="b", uid="u", token="t")
finally:
    post_instagram._get = real_get
day = next(iter(book.values()))
check("a PARTIAL refusal is still recorded per request key, not collapsed",
      list(day.get("errors") or {}) == ["reach|follow_type"])


def _ok(url):
    if "/insights?" in url and "breakdown=follow_type" in url and "metric=reach" in url:
        return {"data": [{"total_value": {"breakdowns": [{"results": [
            {"dimension_values": ["NON_FOLLOWER"], "value": 180},
            {"dimension_values": ["FOLLOWER"], "value": 53}]}]}}]}
    if "/insights?" in url:
        return {"data": [{"total_value": {"value": 7}}]}
    return {"id": "u", "username": "saintseoul_studio", "followers_count": 215}


post_instagram._get = _ok
try:
    book = insights.account(base="b", uid="u", token="t")
finally:
    post_instagram._get = real_get
day = next(iter(book.values()))
check("breakdowns are flattened to a readable dict",
      (day["insights"].get("reach|follow_type") or {}).get("NON_FOLLOWER") == 180)
check("a plain total_value lands as a number", day["insights"].get("accounts_engaged") == 7)
check("yesterday's error is cleared once the metric answers", not day.get("errors"))
check("profile fields are recorded alongside", day["profile"].get("followers_count") == 215)
check("the signed profile picture URL is not committed",
      "profile_picture_url" not in day.get("profile", {}))

print(f"\n{'FAILED: ' + ', '.join(fails) if fails else 'all catalog checks hold'}")
sys.exit(1 if fails else 0)
