#!/usr/bin/env python3
"""Every metric and field Meta's reference documents — transcribed, not curated.

WHY THIS FILE EXISTS
--------------------
For two months this repo asked Instagram for a hand-picked subset of metrics, and the subset
was picked from memory. On 2026-10-07 that cost us twice in one day:

  * `reels_skip_rate` — the number §15 named the account's #1 problem — was in the official
    reference the whole time and had never once been requested.
  * `reach` was declared unobtainable in three documents, when the only thing missing was a
    scope nobody had asked the token about.

Both failures have the same shape: *we decided what was available instead of reading what was
available.* So the order is now reversed. This file is the reference, transcribed field by
field. Collection code asks for EVERYTHING here and records whatever comes back. Choosing which
numbers to act on happens afterwards, in analysis — never at request time, where a choice is
invisible and silently permanent.

RULE: a metric is added here only with its documented media types, period and restrictions, and
only from the reference page. If a metric is in Meta's docs and not in this file, that is a bug.

THE ALL-OR-NOTHING TRAP
-----------------------
`GET /<id>/insights?metric=a,b,c` is atomic: one unsupported name returns an error for the whole
request and blanks the other two. That is how this account went 156 posts recording nothing but
likes — every bundle that carried `views` also carried `reach`, and `reach` needed a scope.

So each metric carries `bundle`:
  True  — documented for this media type with no conditional failure. Safe to batch.
  False — documented to THROW under conditions we may not meet (not cross-posted to Facebook)
          or restricted to an API flavour we may not be using (Facebook Login). Must be asked
          ALONE, where a rejection costs one call and takes nothing down with it.

Sources (fetched 2026-10-07):
  developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights
  developers.facebook.com/documentation/instagram-platform/api-reference/instagram-user/insights
  developers.facebook.com/docs/instagram-platform/reference/instagram-media
  developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user
Verbatim tables kept in notes/insight-metrics-catalog.md.
"""

# ---------------------------------------------------------------------------------------------
# 1. MEDIA INSIGHTS — GET /<IG_MEDIA_ID>/insights?metric=...
#
# `media`: the media types the reference lists for the metric. Asking for a metric outside its
# media type is not a degraded answer, it is an error that blanks the bundle — so the bundle is
# built per media type, not once globally.
# ---------------------------------------------------------------------------------------------
FEED, REELS, STORY = "FEED", "REELS", "STORY"

MEDIA_METRICS = {
    # name                            media                  bundle  note (from the reference)
    "comments":                      {"media": (FEED, REELS, STORY), "bundle": True,
                                      "note": "organic only; see total_comments for all surfaces"},
    "likes":                         {"media": (FEED, REELS), "bundle": True,
                                      "note": "organic only"},
    "reach":                         {"media": (FEED, REELS, STORY), "bundle": True,
                                      "note": "unique accounts; estimated"},
    "saved":                         {"media": (FEED, REELS), "bundle": True, "note": ""},
    "shares":                        {"media": (FEED, REELS, STORY), "bundle": True, "note": ""},
    "views":                         {"media": (FEED, REELS, STORY), "bundle": True,
                                      "note": "plays/displays on Instagram; in development"},
    "total_interactions":            {"media": (FEED, REELS, STORY), "bundle": True,
                                      "note": "likes+saves+comments+shares minus undos; in development"},
    "reposts":                       {"media": (FEED, REELS, STORY), "bundle": True,
                                      "note": "reposts minus deleted reposts"},
    "reels_skip_rate":               {"media": (REELS,), "bundle": True,
                                      "note": "share of views skipped in the first 3s; estimated, in development"},
    "ig_reels_avg_watch_time":       {"media": (REELS,), "bundle": True,
                                      "note": "average ms spent playing the reel"},
    "ig_reels_video_view_total_time": {"media": (REELS,), "bundle": True,
                                       "note": "total ms played including replays; in development"},
    "follows":                       {"media": (FEED, STORY), "bundle": True,
                                      "note": "follows attributed to this media; NOT available for REELS"},
    "profile_visits":                {"media": (FEED, STORY), "bundle": True,
                                      "note": "NOT available for REELS"},
    "profile_activity":              {"media": (FEED, STORY), "bundle": True,
                                      "note": "actions after visiting profile; breakdown=action_type; media after 2017-10-26"},
    "navigation":                    {"media": (STORY,), "bundle": True,
                                      "note": "breakdown=story_navigation_action_type"},
    "replies":                       {"media": (STORY,), "bundle": True,
                                      "note": "0 for EU (2020-12-01) / JP (2021-04-14) viewers"},
    "link_clicks":                   {"media": (STORY,), "bundle": True, "note": ""},

    # --- not bundle-safe: documented to throw, or restricted to one API flavour ---------------
    "crossposted_views":             {"media": (REELS,), "bundle": False,
                                      "note": "IG+FB aggregate; THROWS if the media was not shared to Facebook"},
    "facebook_views":                {"media": (FEED, REELS, STORY), "bundle": False,
                                      "note": "plays on Facebook; THROWS if not shared to Facebook"},
    "total_comments":                {"media": (FEED, REELS), "bundle": False,
                                      "note": "all surfaces incl. ads; Instagram API with FACEBOOK LOGIN only"},
    "total_likes":                   {"media": (FEED, REELS), "bundle": False,
                                      "note": "all surfaces incl. ads; FACEBOOK LOGIN only"},
    "total_views":                   {"media": (FEED, REELS, STORY), "bundle": False,
                                      "note": "all surfaces incl. ads and Facebook; FACEBOOK LOGIN only"},
    "impressions":                   {"media": (FEED, STORY), "bundle": False,
                                      "note": "DEPRECATED for media created after 2024-07-02"},
}

# Breakdowns the media endpoint documents, and the metric each belongs to.
MEDIA_BREAKDOWNS = {
    "profile_activity": ("action_type",),
    "navigation": ("story_navigation_action_type",),
}

# Which numbers we want FIRST when the account is only allowed a few. Ordering only — nothing is
# dropped. Used for the one-at-a-time salvage pass, so the most load-bearing metric is asked for
# before a rate limit can bite.
MEDIA_PRIORITY = ("reach", "views", "reels_skip_rate", "ig_reels_avg_watch_time", "shares",
                  "saved", "total_interactions", "reposts", "likes", "comments",
                  "ig_reels_video_view_total_time")


def media_metrics(product_type=REELS, bundle_only=False, fragile_only=False):
    """Every documented metric valid for `product_type`, in priority order then alphabetical.

    `product_type` comes from the media's own `media_product_type` field, so a carousel gets
    `follows`/`profile_visits` (documented for FEED) and a reel does not — asking anyway is an
    error that blanks the whole bundle, which is exactly the failure this file exists to stop."""
    pt = (product_type or REELS).upper()
    if pt in ("CAROUSEL_CONTAINER", "POST", "IMAGE", "VIDEO", "CAROUSEL_ALBUM", "AD", ""):
        pt = FEED                      # the reference groups all of these under FEED (posts)
    out = [n for n, spec in MEDIA_METRICS.items()
           if pt in spec["media"]
           and (spec["bundle"] if not fragile_only else not spec["bundle"])
           and (spec["bundle"] or not bundle_only)]
    rank = {n: i for i, n in enumerate(MEDIA_PRIORITY)}
    return tuple(sorted(out, key=lambda n: (rank.get(n, 99), n)))


def tiers(product_type=REELS):
    """Request bundles, widest first, for `insights()`'s degrade-until-something-answers loop.

    Tier 0 is EVERY bundle-safe metric for the media type — not a guess at what the token can
    see. Narrower tiers exist only so a token missing the insights scope still records something
    rather than nothing; they are a fallback, never the thing we ask for first."""
    full = media_metrics(product_type, bundle_only=True)
    core = tuple(m for m in full if m in ("reach", "likes", "comments", "shares", "saved",
                                          "total_interactions", "views"))
    return [full, core,
            tuple(m for m in core if m != "views"),
            ("reach", "likes", "comments"),
            ("reach",)]


# ---------------------------------------------------------------------------------------------
# 2. ACCOUNT INSIGHTS — GET /<IG_USER_ID>/insights?metric=...&period=...&metric_type=total_value
#
# A dimension this repo collected ZERO of until 2026-10-07. Media insights answer "did this post
# work?"; these answer "is the account working?" — and one of them, `reach` broken down by
# `follow_type`, directly reports non-follower reach, which §14 and §15 inferred from a ratio.
# ---------------------------------------------------------------------------------------------
ACCOUNT_METRICS = {
    "reach":                 {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("follow_type", "media_product_type"),
                              "note": "unique accounts reached; estimated. follow_type = the non-follower answer"},
    "views":                 {"period": "day", "metric_type": "total_value",
                              # The reference's own tables disagree here: the account-insights
                              # table lists `follower_type` for views and `follow_type` for
                              # reach. Both are tried and whichever answers is recorded.
                              "breakdowns": ("follower_type", "media_product_type"),
                              "note": "plays/displays across reels, posts, stories; in development"},
    "accounts_engaged":      {"period": "day", "metric_type": "total_value", "breakdowns": (),
                              "note": "accounts that interacted; estimated"},
    "total_interactions":    {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("media_product_type",), "note": ""},
    "likes":                 {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("media_product_type",), "note": ""},
    "comments":              {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("media_product_type",), "note": "in development"},
    "shares":                {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("media_product_type",), "note": ""},
    "saves":                 {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("media_product_type",),
                              "note": "account-level spelling is `saves`; media-level is `saved`"},
    "reposts":               {"period": "day", "metric_type": "total_value", "breakdowns": (),
                              "note": ""},
    "replies":               {"period": "day", "metric_type": "total_value", "breakdowns": (),
                              "note": "story replies"},
    "profile_links_taps":    {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("contact_button_type",), "note": ""},
    "follows_and_unfollows": {"period": "day", "metric_type": "total_value",
                              "breakdowns": ("follow_type",),
                              "note": "not returned below 100 followers"},
    "follower_demographics": {"period": "lifetime", "metric_type": "total_value",
                              "breakdowns": ("age", "city", "country", "gender"),
                              "note": "needs timeframe; not returned below 100 followers; top 45 only"},
    "engaged_audience_demographics": {"period": "lifetime", "metric_type": "total_value",
                                      "breakdowns": ("age", "city", "country", "gender"),
                                      "note": "needs timeframe; not returned below 100 engaged accounts"},
    "impressions":           {"period": "day", "metric_type": "total_value", "breakdowns": (),
                              "note": "DEPRECATED v22.0+, sunset 2025-04-21 — kept so the "
                                      "catalog matches the reference; collection skips it"},
}

# Documented values, so a breakdown's absence can be told apart from a breakdown returning zero.
BREAKDOWN_VALUES = {
    "follow_type": ("FOLLOWER", "NON_FOLLOWER", "UNKNOWN"),
    "follower_type": ("FOLLOWER", "NON_FOLLOWER", "UNKNOWN"),
    "media_product_type": ("AD", "STORY", "REEL", "CAROUSEL_CONTAINER", "POST"),
    "contact_button_type": ("BOOK_NOW", "CALL", "DIRECTION", "EMAIL", "INSTANT_EXPERIENCE",
                            "TEXT", "UNDEFINED"),
    "action_type": ("BIO_LINK_CLICKED", "CALL", "DIRECTION", "EMAIL", "OTHER", "TEXT"),
    "story_navigation_action_type": ("SWIPE_FORWARD", "TAP_BACK", "TAP_EXIT", "TAP_FORWARD"),
    "age": (), "city": (), "country": (), "gender": (),
}

# `last_14_days`/`last_30_days`/`last_90_days`/`prev_month` are deprecated for v20.0+.
TIMEFRAMES = ("this_week", "this_month")

# Deprecated metrics are catalogued (so this file can be checked against the reference) but not
# requested — a sunset metric returns an error, and an error per day forever is noise that
# teaches the log's readers to ignore it.
DEPRECATED = ("impressions",)


def account_metrics(include_deprecated=False):
    out = [m for m in ACCOUNT_METRICS if include_deprecated or m not in DEPRECATED]
    return tuple(sorted(out))


def account_requests(include_deprecated=False):
    """Every (metric, period, metric_type, breakdown, timeframe) request worth making, once.

    One request per row. The account endpoint will not batch across different periods or
    metric_types, and a breakdown applies to a single metric — so batching here buys nothing and
    risks the all-or-nothing blanking that cost this repo two months of reach."""
    rows = []
    for metric in account_metrics(include_deprecated):
        spec = ACCOUNT_METRICS[metric]
        tf = TIMEFRAMES[1] if spec["period"] == "lifetime" else None
        rows.append((metric, spec["period"], spec["metric_type"], None, tf))
        for bd in spec["breakdowns"]:
            rows.append((metric, spec["period"], spec["metric_type"], bd, tf))
    return rows


# ---------------------------------------------------------------------------------------------
# 3. MEDIA NODE FIELDS — GET /<IG_MEDIA_ID>?fields=...
#
# These are NOT insights. They need no insights scope, cost no extra call when asked for in the
# media listing, and four of them (`shares_count`, `saved_count`, `reposts_count`,
# `total_views_count`) carry numbers this repo spent two months calling unobtainable.
#
# Same atomicity trap: one unreadable field fails the whole listing. So `core` is the set already
# proven to work against this account, and `extra` is everything else the reference documents —
# tried, and dropped as a group if the listing rejects it.
# ---------------------------------------------------------------------------------------------
MEDIA_FIELDS_CORE = ("id", "timestamp", "media_product_type", "media_type", "permalink",
                     "caption", "like_count", "comments_count")

MEDIA_FIELDS_EXTRA = ("shares_count", "saved_count", "reposts_count", "total_views_count",
                      "total_like_count", "total_comments_count", "media_audio_type",
                      "is_shared_to_feed", "is_ai_generated", "is_comment_enabled", "shortcode",
                      "alt_text", "thumbnail_url", "boost_eligibility_info")

# Readable on ONE media, but fatal in a /media listing: asking for it across 40 posts returns
# `9005 Video content was not found` for the whole page, because one older post's video is gone
# and the error is not per-row. Measured 2026-10-07 by asking for each field alone against the
# listing — every other extra field survived. So these are fetched per media, never in a batch.
MEDIA_FIELDS_SOLO = ("copyright_check_information",)

# Plain field → the insights metric that means the same number. When the insights scope is
# missing these are the only source for views/shares/reposts, and the ledger must say so rather
# than letting them pass as something the insights endpoint returned.
#
# ORDERED, and the order is load-bearing: two fields can map to one metric, and the LAST one
# wins. `total_like_count` counts likes across all surfaces including ads; `like_count` excludes
# promoted posts — which is exactly what the media-insights `likes` metric is documented to
# measure ("organic only"). So the plain counts come last, and a future ad would not silently
# change the meaning of a column the ledger has been filling for months.
FIELD_AS_METRIC_ORDER = (
    ("total_views_count", "views"),
    ("total_like_count", "likes"),
    ("total_comments_count", "comments"),
    ("shares_count", "shares"),
    ("saved_count", "saved"),
    ("reposts_count", "reposts"),
    ("like_count", "likes"),
    ("comments_count", "comments"),
)
FIELD_AS_METRIC = dict(FIELD_AS_METRIC_ORDER)

# Metrics that can arrive from EITHER the insights endpoint or a plain field. Only these need a
# provenance marker: for everything else (reach, reels_skip_rate, watch time) there is one
# possible source, so a marker would be noise in a file people read by eye.
DUAL_SOURCE = tuple(dict.fromkeys(m for _f, m in FIELD_AS_METRIC_ORDER))

# ---------------------------------------------------------------------------------------------
# 4. ACCOUNT NODE FIELDS — GET /<IG_USER_ID>?fields=...
#
# `followers_count` was the only one of these ever requested. `is_published` is a sanction-shaped
# signal, and `media_count` is the independent check that a post actually landed.
# ---------------------------------------------------------------------------------------------
ACCOUNT_FIELDS_CORE = ("id", "username", "followers_count", "media_count")

ACCOUNT_FIELDS_EXTRA = ("follows_count", "name", "biography", "website", "profile_picture_url",
                        "has_profile_pic", "is_published", "shopping_product_tag_eligibility")


def media_fields(extra=True, solo=False):
    """Fields safe to ask for in one /media listing. `solo=True` adds the ones that are only
    safe on a single media id — see MEDIA_FIELDS_SOLO for why that distinction is not cosmetic."""
    return (MEDIA_FIELDS_CORE + (MEDIA_FIELDS_EXTRA if extra else ())
            + (MEDIA_FIELDS_SOLO if solo else ()))


def account_fields(extra=True):
    return ACCOUNT_FIELDS_CORE + (ACCOUNT_FIELDS_EXTRA if extra else ())


if __name__ == "__main__":
    print("MEDIA INSIGHTS — documented:", len(MEDIA_METRICS))
    for pt in (REELS, FEED, STORY):
        safe = media_metrics(pt, bundle_only=True)
        frag = media_metrics(pt, fragile_only=True)
        print(f"  {pt:6} bundle-safe {len(safe):2}  ask-alone {len(frag)}")
        print(f"         {', '.join(safe)}")
        if frag:
            print(f"         alone: {', '.join(frag)}")
    rows = account_requests()
    print(f"\nACCOUNT INSIGHTS — {len(account_metrics())} metrics, {len(rows)} requests/day")
    for m, period, mt, bd, tf in rows:
        print(f"  {m:32} period={period:8} {('breakdown=' + bd) if bd else ''}"
              f"{(' timeframe=' + tf) if tf else ''}")
    print(f"\nMEDIA FIELDS   {len(media_fields())}: {', '.join(media_fields())}")
    print(f"ACCOUNT FIELDS {len(account_fields())}: {', '.join(account_fields())}")
