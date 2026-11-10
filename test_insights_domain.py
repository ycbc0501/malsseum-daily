#!/usr/bin/env python3
"""2026-11-10: IG_INSIGHTS_TOKEN started winning insights.api()'s token choice (it finally had
the right permission) — and the moment it did, `insights.py`'s scheduled run broke in two new
places that had never been exercised while that token was rejected outright.

1. `post_instagram.recent_media()` always asked `graph.facebook.com`, no matter which base
   `insights.api()` resolved. IG_INSIGHTS_TOKEN only answers on `graph.instagram.com` with
   account path "me" — sent to the wrong domain it fails with a generic "cannot parse access
   token" (code 190) that reads exactly like a malformed token, not a wrong host. That error
   was swallowed by `prune_deleted`'s `except Exception` into "prune skipped" — which reads like
   "nothing to prune" and would have left a hand-deleted post holding its verse out of rotation
   for a year, same failure mode RULES.md C4c/C4d/C4e already fixed once for a different cause.

2. `insights.account()`'s closing print assumed `got["reach|follow_type"]` is always the
   flattened breakdown dict. The API returned a bare total instead (nothing to break down yet),
   `r.items()` raised AttributeError, and the unhandled exception aborted the whole script
   before `solo_fields()`, `followers()` and `metrics.report()` ran — silently dropping that
   day's follower-curve point even though account.json had already been written successfully
   moments earlier.

Confirmed against the actual failed run (2026-11-10T01:34:31Z, run 42736744636) before fixing
either.
"""
import sys
import tempfile
from unittest import mock

import insights
import post_instagram


def tmpjson():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write("{}")
        return f.name

fails = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        fails.append(name)


def run():
    # --- recent_media: base must travel, and must default to the old behavior ---
    calls = []
    with mock.patch("post_instagram._get", side_effect=lambda url: (calls.append(url), {"data": []})[1]):
        post_instagram.recent_media(ig_user_id="123", token="tok")
        check("no `base` given → still asks graph.facebook.com (unchanged default)",
              calls[-1].startswith("https://graph.facebook.com/"))

        post_instagram.recent_media(ig_user_id="me", token="tok",
                                    base="https://graph.instagram.com/v21.0")
        check("explicit `base` → asks that host instead, not the hardcoded one",
              calls[-1].startswith("https://graph.instagram.com/v21.0/me/media"))

    # --- insights.account(): a bare total under reach|follow_type must not crash the run ---
    # total_value with a plain "value", no "breakdowns" — the shape the live run actually got
    # back once flattened into `got`, which is a scalar rather than the expected dict.
    with mock.patch.object(insights, "ACCOUNT", tmpjson()), \
         mock.patch("ig_catalog.account_fields", return_value=["username"]), \
         mock.patch("ig_catalog.account_requests",
                    return_value=[("reach", "lifetime", "total_value", "follow_type", None)]), \
         mock.patch("post_instagram._get",
                    side_effect=[{"username": "x"},
                                 {"data": [{"total_value": {"value": 42}}]}]):
        try:
            insights.account(base="b", uid="me", token="t")
            check("a scalar reach|follow_type does not crash account()", True)
        except AttributeError:
            check("a scalar reach|follow_type does not crash account()", False)

    print("\n" + ("all good" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
