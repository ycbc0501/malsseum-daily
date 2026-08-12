#!/usr/bin/env python3
"""
Keep the Instagram-login insights token alive, so the 60-day expiry is never a human problem.

A long-lived Instagram token lasts 60 days and can be refreshed any time it is at least 24
hours old. Refreshed, it lasts another 60 days from that moment — so a weekly refresh means
the token is never more than a week from freshly issued, and eight consecutive failures would
have to go unnoticed before anything actually expired.

Writes the new token to a FILE, never to stdout: a token printed into a CI log is a leaked
token, and GitHub only masks secrets it already knows about.

    python3 refresh_token.py --out new_token.txt
"""

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.instagram.com"


def refresh(token):
    url = f"{GRAPH}/refresh_access_token?" + urllib.parse.urlencode({
        "grant_type": "ig_refresh_token", "access_token": token})
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="file to write the refreshed token to")
    args = ap.parse_args()

    token = os.environ.get("IG_INSIGHTS_TOKEN")
    if not token:
        raise SystemExit("IG_INSIGHTS_TOKEN is not set — run ig_login.py first")

    try:
        got = refresh(token)
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:
            why = ""
        raise SystemExit(f"refresh failed ({e.code}): {why}")

    new = got.get("access_token")
    if not new:
        raise SystemExit(f"refresh returned no token: {got}")
    with open(args.out, "w") as f:
        f.write(new)
    days = (got.get("expires_in") or 0) // 86400
    print(f"refreshed — valid {days} more days")   # the token itself is never printed


if __name__ == "__main__":
    main()
