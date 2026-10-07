#!/usr/bin/env python3
"""Ask the API about every single thing in ig_catalog.py, one at a time, and write down what it said.

    python3 ig_probe.py                 # probe everything, write api_support.json
    python3 ig_probe.py --media-only     # just the media fields + media metrics
    python3 ig_probe.py --show           # print the last verdict without calling the API

WHY
---
`ig_catalog.py` says what Meta's reference documents. That is not the same as what THIS account's
token can actually read, and on 2026-10-07 the gap between those two sentences cost two months:

  * `(#10) Application does not have permission` was read as "Instagram hides this" for eight
    weeks. It meant "this token never asked".
  * Sweeping `(#10)` across names cannot tell a real metric from a typo — without the scope,
    Meta returns `(#10)` for `view_sources`, which does not exist. So a probe is only evidence
    when its verdicts are recorded per name WITH the error text, and read together with the
    token's actual scope list.

So this file does the boring thing: one request per catalogued name, on a real media id, and the
answer — value, or Meta's own sentence — goes into `api_support.json`. Nothing here infers. A
name this repo has not probed is a name this repo must not claim anything about.

`api_support.json` is then the honest boundary between automatic and hand-entered. `metrics.py
note()` exists for the hand-entered side; this file is what decides how small that side is.

COST: ~85 requests, once. It is NOT part of the daily run — daily collection asks for the
bundle `ig_catalog.tiers()` builds, which is one call. Re-probe when a token changes, or monthly,
since several metrics are documented "in development" and will start answering without notice.
"""

import datetime
import json
import os
import sys
import urllib.parse

import ig_catalog
import ig_doctor
import post_instagram

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPORT = os.path.join(HERE, "api_support.json")
KST = datetime.timezone(datetime.timedelta(hours=9))


def _env():
    """(base, account, token, login) — read through the same door insights.py reads through.

    An IG_INSIGHTS_TOKEN is only valid against graph.instagram.com; sending it to
    graph.facebook.com fails OAuth and looks exactly like a missing permission."""
    s = ig_doctor.secrets()
    tok = s.get("IG_INSIGHTS_TOKEN") or os.environ.get("IG_INSIGHTS_TOKEN")
    if tok:
        return "https://graph.instagram.com/v21.0", "me", tok, "Instagram Login"
    tok = s.get("IG_ACCESS_TOKEN") or os.environ.get("IG_ACCESS_TOKEN")
    uid = s.get("IG_USER_ID") or os.environ.get("IG_USER_ID")
    return post_instagram.GRAPH, uid, tok, "Facebook Login"


def _try(url):
    """→ (ok, value_or_error). Never raises: a probe that dies mid-sweep loses every verdict
    it had already earned, which is how the last three attempts at this ended in a guess."""
    try:
        return True, post_instagram._get(url)
    except Exception as e:
        return False, str(e)[:240]


def _newest(base, account, token, want=1):
    """The most recent media ids, with their product types — a metric can only be probed
    against media it is documented for, and REELS and FEED do not share a metric list."""
    ok, got = _try(f"{base}/{account}/media?fields=id,media_product_type,media_type"
                   f"&limit={max(want, 6)}&access_token={token}")
    if not ok:
        return [], got
    out = []
    for m in got.get("data", []):
        pt = m.get("media_product_type") or m.get("media_type") or ""
        out.append((m["id"], pt))
    return out, None


def probe_media_fields(base, token, media_id):
    """Each documented media field, asked ALONE.

    Alone matters: `fields=a,b,c` is atomic, so one unreadable name fails the request and the
    other two look unreadable too. That is the same trap as the insight bundles, and asking one
    at a time is the only way the verdict means anything per name."""
    out = {}
    for field in ig_catalog.media_fields():
        ok, got = _try(f"{base}/{media_id}?fields={field}&access_token={token}")
        if ok:
            val = got.get(field)
            out[field] = {"ok": True, "sample": _snip(val),
                          "present": field in got}
        else:
            out[field] = {"ok": False, "error": got}
    return out


def probe_media_metrics(base, token, media):
    """Each documented metric, asked alone, against a media it is documented FOR.

    `media` is [(id, product_type)]. A metric documented FEED-only (`follows`, `profile_visits`)
    gets probed on a feed post if the account has one; if it does not, the verdict is
    "untested" — not "unsupported". Those are different sentences and conflating them is how
    `reels_skip_rate` sat unrequested while being in the docs."""
    by_type = {}
    for mid, pt in media:
        key = ig_catalog.FEED
        if (pt or "").upper() == "REELS":
            key = ig_catalog.REELS
        elif (pt or "").upper() == "STORY":
            key = ig_catalog.STORY
        by_type.setdefault(key, mid)

    out = {}
    for name, spec in sorted(ig_catalog.MEDIA_METRICS.items()):
        target = next((by_type[t] for t in spec["media"] if t in by_type), None)
        if not target:
            out[name] = {"ok": None, "error": "no media of type "
                                              + "/".join(spec["media"]) + " to probe against"}
            continue
        ok, got = _try(f"{base}/{target}/insights?metric={name}&access_token={token}")
        if ok:
            rows = got.get("data") or []
            val = (rows[0].get("values") or [{}])[0].get("value") if rows else None
            out[name] = {"ok": True, "sample": _snip(val), "probed_on": target}
        else:
            out[name] = {"ok": False, "error": got, "probed_on": target}
    return out


def probe_account_fields(base, account, token):
    out = {}
    for field in ig_catalog.account_fields():
        ok, got = _try(f"{base}/{account}?fields={field}&access_token={token}")
        out[field] = ({"ok": True, "sample": _snip(got.get(field))} if ok
                      else {"ok": False, "error": got})
    return out


def probe_account_insights(base, account, token):
    """Every (metric, period, metric_type, breakdown, timeframe) row the catalog lists.

    This whole dimension — is the ACCOUNT working, as opposed to did this post work — was never
    requested once before today. `reach` with `breakdown=follow_type` is the one that matters
    most: it reports non-follower reach outright, which §14 and §15 inferred from a ratio."""
    out = {}
    for metric, period, mtype, bd, tf in ig_catalog.account_requests():
        q = {"metric": metric, "period": period, "metric_type": mtype,
             "access_token": token}
        if bd:
            q["breakdown"] = bd
        if tf:
            q["timeframe"] = tf
        key = metric + (f"|{bd}" if bd else "")
        ok, got = _try(f"{base}/{account}/insights?" + urllib.parse.urlencode(q))
        if ok:
            rows = got.get("data") or []
            tv = (rows[0].get("total_value") if rows else None) or {}
            out[key] = {"ok": True, "period": period, "breakdown": bd,
                        "sample": _snip(tv.get("value") if "value" in tv else
                                        tv.get("breakdowns") or rows)}
        else:
            out[key] = {"ok": False, "period": period, "breakdown": bd, "error": got}
    return out


def _snip(val, limit=400):
    """A sample, not the data. The verdict file is read by humans deciding what to collect; a
    full demographics payload in it buries the one bit that matters (did this answer at all)."""
    if val is None:
        return None
    if isinstance(val, str) and val.startswith("http") and len(val) > 120:
        # A signed CDN URL. It answers the only question this file asks — did the field come
        # back — in four characters, and keeping the other 580 would expire in days AND rewrite
        # the whole file on every re-probe, which is the churn ledger_merge._style exists to
        # avoid. Same reason insights._NODE_SKIP drops thumbnail_url.
        return f"<url, {len(val)} chars>"
    if isinstance(val, (int, float, bool, str)):
        return val
    try:
        s = json.dumps(val, ensure_ascii=False)
    except Exception:
        s = str(val)
    return s if len(s) <= limit else s[:limit] + f"…(+{len(s) - limit} chars)"


def _count(d):
    ok = sum(1 for v in d.values() if v.get("ok") is True)
    bad = sum(1 for v in d.values() if v.get("ok") is False)
    unk = sum(1 for v in d.values() if v.get("ok") is None)
    return ok, bad, unk


def load():
    try:
        with open(SUPPORT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def show(data=None):
    data = data if data is not None else load()
    if not data:
        print("no api_support.json yet — run `python3 ig_probe.py`")
        return 1
    print(f"probed {data.get('checked', '?')} via {data.get('login', '?')} "
          f"({data.get('base', '?')})")
    scopes = data.get("scopes")
    if scopes:
        print("  scopes: " + ", ".join(scopes))
    # Without the insights scope, Meta answers (#10) for EVERY metric name — including names
    # that do not exist (`view_sources`, 2026-10-07). So a ❌ below is NOT evidence the metric
    # is unavailable; it may only mean the permission check ran first. Say so, every time,
    # because the reader of this file is about to decide what to stop collecting.
    insight_scope = any("insights" in s for s in (scopes or []))
    if not insight_scope:
        print("  ⚠️  no *_manage_insights scope on this token. Meta checks permission BEFORE the\n"
              "      metric name, so every ❌ under media_metrics / account_insights below is\n"
              "      'this token may not ask', NOT 'this metric does not exist'. The reference\n"
              "      (ig_catalog.py) is the authority on what exists; this file only says what\n"
              "      answered today.")
    for section in ("media_fields", "media_metrics", "account_fields", "account_insights"):
        d = data.get(section) or {}
        if not d:
            continue
        ok, bad, unk = _count(d)
        print(f"\n{section}  ✅ {ok}   ❌ {bad}" + (f"   ? {unk}" if unk else ""))
        for name, v in sorted(d.items()):
            mark = {True: "✅", False: "❌", None: "? "}[v.get("ok")]
            tail = (f"= {v['sample']}" if v.get("ok") and v.get("sample") is not None
                    else (v.get("error") or ""))
            print(f"  {mark} {name:34} {tail}")
    return 0


STALE_DAYS = 25


def is_stale(days=STALE_DAYS, data=None):
    """Has it been long enough that the verdict might have changed?

    Several catalogued metrics are documented "in development" and will start answering with no
    announcement, and a token gaining the insights scope flips thirty rows at once. So the
    boundary between automatic and hand-entered has to be re-measured, not remembered.

    Deliberately decided here and not in the workflow YAML: GitHub Actions has no date
    function, so doing it there means string-slicing a timestamp in an expression nothing can
    test. The scope list is checked too — a new token is reason enough on its own."""
    data = data if data is not None else load()
    if not data:
        return True, "never probed"
    checked = str(data.get("checked") or "")[:10]
    try:
        then = datetime.datetime.strptime(checked, "%Y-%m-%d").date()
    except ValueError:
        return True, f"unreadable date {checked!r}"
    age = (datetime.datetime.now(KST).date() - then).days
    if age >= days:
        return True, f"{age} days since {checked}"
    return False, f"probed {age} day(s) ago ({checked})"


def main(argv):
    if "--show" in argv:
        return show()
    if "--if-stale" in argv:
        stale, why = is_stale()
        if not stale:
            print(f"probe skipped — {why}; re-probes after {STALE_DAYS} days "
                  f"(force with `python3 ig_probe.py`)")
            return 0
        print(f"probing: {why}")
    base, account, token, login = _env()
    if not (account and token):
        print("no token — set IG_ACCESS_TOKEN/IG_USER_ID (or IG_INSIGHTS_TOKEN) in "
              "meta_secrets.txt or the environment")
        return 2
    print(f"probing via {login} at {base} as {account}")

    out = {"checked": datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
           "base": base, "login": login}
    s = ig_doctor.secrets()
    info, scope_err = ig_doctor.describe(
        token, s.get("META_APP_ID") or os.environ.get("META_APP_ID"),
        s.get("META_APP_SECRET") or os.environ.get("META_APP_SECRET"))
    if info:
        out["scopes"] = sorted(info.get("scopes") or [])
    else:
        out["scopes_error"] = str(scope_err)[:200]

    media, err = _newest(base, account, token)
    if err:
        print(f"cannot list media ({err}) — nothing else can be probed")
        out["media_error"] = err
        _write(out)
        return 1
    print(f"  probing against {len(media)} recent media: "
          + ", ".join(f"{m[1] or '?'}" for m in media))
    out["probed_media"] = [{"id": m, "product_type": pt} for m, pt in media]

    newest = media[0][0]
    print("  media fields…")
    out["media_fields"] = probe_media_fields(base, token, newest)
    print("  media metrics…")
    out["media_metrics"] = probe_media_metrics(base, token, media)
    if "--media-only" not in argv:
        print("  account fields…")
        out["account_fields"] = probe_account_fields(base, account, token)
        print("  account insights…")
        out["account_insights"] = probe_account_insights(base, account, token)
    _write(out)
    return show(out)


def _write(out):
    with open(SUPPORT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"\nwrote {SUPPORT}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
