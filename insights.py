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
import urllib.parse
from datetime import datetime, timedelta, timezone

import ig_catalog
import metrics
import post_instagram

HERE = os.path.dirname(os.path.abspath(__file__))
FOLLOWERS = os.path.join(HERE, "followers.json")
# Daily account-level ledger. Separate from metrics.json on purpose: that file is keyed by
# media id and answers "did this post work?", while this one is keyed by date and answers "is
# the account working?" — including the non-follower reach breakdown that no per-post row can
# carry. Mixing them would mean one of the two keys had to be faked.
ACCOUNT = os.path.join(HERE, "account.json")
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
    # Environment first (that is what CI sets), then meta_secrets.txt. Without the file
    # fallback this collector could not be run by hand on the machine that owns the secrets,
    # while ig_doctor.py and ig_probe.py could — so every check of "does collection actually
    # work?" had to be done with a different code path than the one that runs. That asymmetry
    # is how today's four wrong claims survived: the thing being verified was never the thing
    # running. The file is gitignored; nothing is printed from it.
    def _s(key):
        val = os.environ.get(key)
        if val:
            return val
        try:
            import ig_doctor
            return ig_doctor.secrets().get(key)
        except Exception:
            return None

    tok = _s("IG_INSIGHTS_TOKEN")
    if tok:
        return "https://graph.instagram.com/v21.0", "me", tok
    return post_instagram.GRAPH, _s("IG_USER_ID"), _s("IG_ACCESS_TOKEN")


def _themes():
    """verse ref → theme, so posts predating any bookkeeping still resolve (the caption
    carries the reference)."""
    try:
        with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
            return {v["ref"]: v.get("theme", "") for v in json.load(f)["verses"]}
    except Exception:
        return {}


def _is_young(published):
    """Is this post still accumulating? Only young posts are worth spending scoped calls on.

    Reads through metrics.published_kst() because the field carries two zones (metrics.py
    writes KST, this file copies Instagram's UTC) and a raw read is silently 9 hours out."""
    when = metrics.published_kst({"published": published or ""})
    if not when:
        return False
    return (datetime.now(KST) - when).days <= metrics.MATURE_DAYS


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
    listing, dropped = _listing(base, uid, token, limit)
    if dropped:
        print(f"  listing fell back to core fields (dropped {len(dropped)}): "
              f"{', '.join(dropped)}")

    added = filled = empties = 0
    skip_insights = False
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
        got = dict(entry.get("insights") or {})
        was = dict(got)
        node_was = dict(entry.get("node") or {})
        entry["node"] = _node(m, entry["node"] if "node" in entry else {})

        # Plain media FIELDS, not insights: they ride along in the listing above at no extra
        # call and — this is the part that cost two months — no insights scope. On 2026-10-07 a
        # probe of every documented field showed `total_views_count`, `shares_count`,
        # `reposts_count`, `total_like_count` and `total_comments_count` all answering for this
        # token, while `metrics.note()`'s own docstring said "the API cannot give us most of
        # these". Validated against the fourteen hand-entered posts: shares matched EXACTLY
        # 3/3, and views was >= the hand-entered snapshot in 13/13 with the gap explained by
        # the days since the screenshot. See notes/insight-metrics-catalog.md §4.
        #
        # Precedence: a value from the insights ENDPOINT wins over the same number from a plain
        # field (the endpoint is what Instagram's own screens show), and a plain field beats a
        # hand-entered one. Provenance is marked EXPLICITLY — `<metric>_api` when the endpoint
        # answered, `<metric>_field` naming the field it came from — and absence of a marker
        # means "unknown provenance", which must NOT be read as "the endpoint said so".
        #
        # That distinction is not theoretical. The first version of this loop inferred
        # endpoint-provenance from the absence of a marker, and every `likes` recorded before
        # today — all written from `like_count` by a loop that marked nothing — instantly
        # qualified as untouchable. 골로새서 3:14 froze at likes=2 while the API was returning
        # 4. Provenance has to be written down, not deduced from what is missing.
        for field, metric in ig_catalog.FIELD_AS_METRIC_ORDER:
            val = m.get(field)
            if val is None or got.get(f"{metric}_api"):
                continue
            got[metric] = val
            got[f"{metric}_field"] = field
            got.pop(f"{metric}_manual", None)

        # The scoped metrics (reach, saved, reels_skip_rate, watch time) cost a call each, so
        # only chase them where they are still missing and still moving. `reach` is the one the
        # plain fields cannot substitute for: views counts plays, reach counts people.
        young = _is_young(entry.get("published"))
        if young and "reach" not in got and not skip_insights:
            try:
                # `base` matters: an IG_INSIGHTS_TOKEN is only valid against
                # graph.instagram.com. api() has always known that and insights() never got
                # told, so an Instagram-Login token would have failed OAuth and printed
                # "insights unavailable" — indistinguishable from having no permission.
                fresh = post_instagram.insights(
                    m["id"], token, base=base,
                    product_type=m.get("media_product_type") or entry.get("kind"),
                    extras=_extras()) or {}
            except Exception as e:
                print(f"  insights({m['id']}) failed: {e}")
                fresh = {}
            # MERGE. A partial answer must never delete what we already had — the same
            # mistake metrics.refresh() made until 2026-09-09. And a real answer supersedes a
            # plain-field stand-in, marker and all: leaving `views_field` next to a value the
            # insights endpoint returned would keep the ledger apologising for a number that
            # no longer needs it.
            for k, v in fresh.items():
                if v is None:
                    continue
                got[k] = v
                got.pop(f"{k}_field", None)
                got.pop(f"{k}_manual", None)
                if k in ig_catalog.DUAL_SOURCE:
                    got[f"{k}_api"] = True   # so the plain field stops overwriting it
            if fresh:
                empties = 0
            else:
                empties += 1
                # The token has no insights scope (or Meta is rate-limiting). Asking 90 more
                # times in the same run cannot change that, and burning the call budget is how
                # the 400s that blinded the duplicate guards started.
                if empties >= 3:
                    skip_insights = True
                    print("  insights unavailable (3 empty in a row) — skipping the rest of "
                          "this run. Set IG_INSIGHTS_TOKEN (see ig_login.py) to record views.")

        if got != was:
            entry["insights"] = got
            filled += 1
        if entry.get("node") != node_was:
            filled = filled or 1
    metrics.save(data)
    print(f"backfill: {added} new entr(ies), {filled} filled, {len(data)} total")
    return data


# --- everything the catalog documents, collected on a schedule ------------------------------

# Written into metrics.json entries under "node": the plain media fields. Four of these are
# metrics in disguise (see ig_catalog.FIELD_AS_METRIC) and get copied into "insights"; the rest
# are inputs we never had — what audio a reel used, whether it was shared to feed, whether Meta
# flagged a copyright match, whether the account is still eligible to boost.
_NODE_SKIP = (
    "id",            # the ledger key already is the id
    "caption",       # `ref` is extracted from it; the full text would double the ledger
    "permalink",     # stored at the top level of the entry
    "thumbnail_url",  # a signed CDN URL that expires in days — committing it records nothing
)


def _node(m, prev):
    """Media node fields worth keeping, merged over what we had.

    MERGE, not replace: a field missing from one response (the listing dropped the extras, say)
    must not erase the value a previous run recorded. That is the same rule as the insights
    merge, and it is broken the same way — by assigning the response."""
    out = dict(prev)
    for k, v in m.items():
        if k in _NODE_SKIP or v is None:
            continue
        out[k] = v
    return out


def _listing(base, uid, token, limit):
    """The media listing with EVERY documented field, falling back only if Meta refuses.

    `fields=` is atomic across the whole page: ask for `copyright_check_information` over 40
    posts and one older post whose video is gone returns `9005 Video content was not found`
    for the entire request — not for that row. Measured 2026-10-07 by asking for each field
    alone; every other documented field survived the batch, so that one is fetched per media
    (see `solo_fields`) and the batch keeps the other twenty-one.

    Returns (listing, dropped_fields) so the log says which numbers are missing and why,
    instead of a page that silently carries eight fields where it used to carry twenty-two."""
    full = ig_catalog.media_fields(extra=True)
    try:
        return post_instagram._get(
            f"{base}/{uid}/media?fields={','.join(full)}"
            f"&limit={int(limit)}&access_token={token}"), ()
    except Exception as e:
        print(f"  full field listing rejected ({str(e)[:140]}) — retrying with core fields")
    core = ig_catalog.media_fields(extra=False)
    return (post_instagram._get(f"{base}/{uid}/media?fields={','.join(core)}"
                                f"&limit={int(limit)}&access_token={token}"),
            tuple(f for f in full if f not in core))


def _extras():
    """Fragile metrics still worth asking for alone — minus whatever a probe already ruled out.

    Without this the daily run would re-ask five metrics per post forever to collect five
    identical rejections. `api_support.json` is written by `ig_probe.py`; when it does not
    exist we ask for everything once, which is the right default for a file whose whole purpose
    is to stop us deciding availability from memory."""
    fragile = ig_catalog.media_metrics(ig_catalog.REELS, fragile_only=True)
    try:
        import ig_probe
        verdict = (ig_probe.load().get("media_metrics") or {})
    except Exception:
        return fragile
    if not verdict:
        return fragile
    return tuple(m for m in fragile if verdict.get(m, {}).get("ok") is not False)


def solo_fields(limit=8, base=None, uid=None, token=None):
    """Fields that are only safe one media at a time — currently the copyright check.

    `copyright_check_information` reports whether Meta matched the reel's audio or video against
    someone else's content. That is the originality question §7.1 spent weeks arguing from
    screenshots of the account-status screen, answered per post by the API. It cannot ride in
    the listing (see `_listing`), so it is fetched for the newest few posts only."""
    if base is None:
        base, uid, token = api()
    data, touched = metrics.load(), 0
    recent = sorted((e for e in data.items() if e[1].get("published")),
                    key=lambda kv: kv[1]["published"], reverse=True)[:int(limit)]
    for media_id, entry in recent:
        fields = ",".join(ig_catalog.MEDIA_FIELDS_SOLO)
        try:
            got = post_instagram._get(
                f"{base}/{media_id}?fields={fields}&access_token={token}")
        except Exception as e:
            print(f"  solo fields {media_id}: {str(e)[:110]}")
            continue
        node = entry.setdefault("node", {})
        before = dict(node)
        for k, v in got.items():
            if k != "id" and v is not None:
                node[k] = v
        if node != before:
            touched += 1
    metrics.save(data)
    print(f"solo fields: {touched} post(s) updated with {', '.join(ig_catalog.MEDIA_FIELDS_SOLO)}")
    return touched


def account(base=None, uid=None, token=None):
    """Every documented ACCOUNT metric and field, appended to account.json under today's date.

    This dimension was collected ZERO times before 2026-10-07. Media insights answer "did this
    post work"; these answer "is the account working" — and `reach` with `breakdown=follow_type`
    reports NON-FOLLOWER reach outright, which §14 and §15 both inferred from a ratio of reach
    to follower count. An inference that the API will hand over on request is not a finding.

    One request per (metric, period, metric_type, breakdown) row, deliberately. The endpoint
    will not batch across differing periods, and batching metrics is how a single unsupported
    name blanks the rest — the failure that cost this repo 156 posts of reach.

    Rejections are RECORDED, not swallowed: an empty day and a day the token was not allowed to
    ask are different facts, and a log line that scrolls away is not a record of either."""
    if base is None:
        base, uid, token = api()
    if not (uid and token):
        print("account(): no credentials")
        return {}

    today = datetime.now(KST).strftime("%Y-%m-%d")
    try:
        with open(ACCOUNT, encoding="utf-8") as f:
            book = json.load(f)
    except Exception:
        book = {}
    day = book.setdefault(today, {})

    fields = ",".join(ig_catalog.account_fields())
    try:
        prof = post_instagram._get(f"{base}/{uid}?fields={fields}&access_token={token}")
        day["profile"] = {k: v for k, v in prof.items()
                          if k != "profile_picture_url" and v is not None}
    except Exception as e:
        print(f"  account fields rejected ({str(e)[:120]}) — retrying core only")
        try:
            prof = post_instagram._get(
                f"{base}/{uid}?fields={','.join(ig_catalog.account_fields(extra=False))}"
                f"&access_token={token}")
            day["profile"] = {k: v for k, v in prof.items() if v is not None}
        except Exception as e2:
            day["profile_error"] = str(e2)[:160]

    got = day.setdefault("insights", {})
    # Values ACCUMULATE across runs (a metric that answered this morning is still true this
    # evening), but errors do NOT: they describe this run's outcome. Carried over, a compressed
    # "everything was refused" summary from the morning would still be sitting next to this
    # evening's working metrics, reading as though both were true at once.
    errors = {}
    ok = bad = 0
    for metric, period, mtype, bd, tf in ig_catalog.account_requests():
        q = {"metric": metric, "period": period, "metric_type": mtype, "access_token": token}
        if bd:
            q["breakdown"] = bd
        if tf:
            q["timeframe"] = tf
        key = metric + (f"|{bd}" if bd else "")
        try:
            res = post_instagram._get(f"{base}/{uid}/insights?"
                                      + urllib.parse.urlencode(q))
        except Exception as e:
            errors[key] = str(e)[:160]
            bad += 1
            continue
        rows = res.get("data") or []
        tv = (rows[0].get("total_value") if rows else None) or {}
        if "value" in tv:
            got[key] = tv["value"]
        elif tv.get("breakdowns"):
            # breakdowns → {"NON_FOLLOWER": 123, ...}. Flattened on the way in: a nested
            # dimension_keys/results shape is unreadable at a glance and every reader of this
            # ledger would have to re-flatten it, differently each time.
            flat = {}
            for b in tv["breakdowns"]:
                for r in b.get("results") or []:
                    name = "/".join(str(x) for x in (r.get("dimension_values") or []))
                    flat[name or "?"] = r.get("value")
            got[key] = flat
        else:
            got[key] = res.get("data") or None
        ok += 1
    day["errors"] = errors
    if not errors:
        day.pop("errors", None)
    elif len(set(errors.values())) == 1 and not ok:
        # Every request refused with the SAME sentence — one missing permission, not 33 facts.
        # Writing it out 33 times a day would add ~12,000 lines a year to a ledger whose whole
        # value is being readable by eye, and it would do it for exactly as long as the problem
        # went unfixed. Record the fact once, and say how many requests it covered.
        day["errors"] = {"*": next(iter(errors.values())),
                         "*_requests": len(ig_catalog.account_requests())}

    with open(ACCOUNT, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=1, sort_keys=True)
    note = ""
    if bad and not ok:
        note = ("  — every one was rejected. Check `python3 ig_doctor.py`: without "
                "*_manage_insights this whole dimension is unreadable, and the errors are "
                "recorded in account.json rather than lost to the log.")
    print(f"account: {ok} metric(s) recorded, {bad} rejected for {today}{note}")
    if got.get("reach|follow_type"):
        r = got["reach|follow_type"]
        print(f"  reach by follow type: " + " ".join(f"{k}={v}" for k, v in sorted(r.items())))
    return book


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
    # Before anything is read back, drop posts the account no longer has. A deletion cannot
    # survive ledger_merge's union on its own, so it has to come from the account each day —
    # otherwise a removed post keeps its verse out of rotation for a year.
    # Hand the token down rather than letting prune_deleted() read the environment on its own:
    # a run started from meta_secrets.txt would otherwise see no token, print "prune skipped"
    # and keep a deleted post's verse out of rotation for a year.
    _base, _uid, _tok = api()
    metrics.prune_deleted(token=_tok, ig_user_id=_uid)
    backfill()
    # The two collections the catalog says are available and this repo never made. `account()`
    # is the dimension that answers "is the account working?"; `solo_fields()` picks up the
    # copyright verdict, which cannot ride in the listing without failing the whole page.
    account()
    solo_fields()
    followers()
    metrics.report()
    # The bill is ~80% Veo and was being estimated from logs; posts record their seconds now.
    metrics.spend()
