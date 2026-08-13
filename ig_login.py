#!/usr/bin/env python3
"""
Get an insights token by logging in with INSTAGRAM — no Facebook account involved.

Why this exists: the account's publishing token is a Facebook-login system-user token, and
adding `instagram_manage_insights` to it needs a Business-Manager action gated behind SMS 2FA
on a Facebook account whose phone number can't receive Meta's codes. Instagram Login is a
separate door into the same data: it needs no Facebook Page and no Business Manager, only the
Instagram password. See CONTENT_RULE rule 13.

The publishing token is NOT replaced. This one is read-only and used only by insights.py.

    export IG_APP_ID=...  IG_APP_SECRET=...            # from the Meta app, Instagram product
    python3 ig_login.py --auth-url                     # 1. open the printed URL, log in, approve
    python3 ig_login.py --code 'AQB...'                # 2. paste the code= from the redirect
                                                       #    prints a 60-day token
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

AUTH = "https://www.instagram.com/oauth/authorize"
TOKEN = "https://api.instagram.com/oauth/access_token"
GRAPH = "https://graph.instagram.com"
# Meta's Business Login page lists four scopes and does not name an insights one, while the
# Insights reference names instagram_business_manage_insights. Rather than bet on either, ask
# for both basic and insights and let --code report exactly what came back: the token response
# tells us the granted permissions, and insights.py probes the metrics regardless.
SCOPES = "instagram_business_basic,instagram_business_manage_insights"
REDIRECT = os.environ.get("IG_REDIRECT_URI", "https://localhost/")


def _app():
    app_id = os.environ.get("IG_APP_ID")
    secret = os.environ.get("IG_APP_SECRET")
    if not (app_id and secret):
        raise SystemExit("set IG_APP_ID and IG_APP_SECRET (Meta app → Instagram → API setup)")
    return app_id, secret


def auth_url():
    app_id, _ = _app()
    return AUTH + "?" + urllib.parse.urlencode({
        "client_id": app_id, "redirect_uri": REDIRECT,
        "response_type": "code", "scope": SCOPES})


def exchange(code):
    """authorization code → short-lived token → 60-day long-lived token."""
    app_id, secret = _app()
    code = code.split("#")[0]          # Instagram appends '#_' to the redirect; it is not part of it
    data = urllib.parse.urlencode({
        "client_id": app_id, "client_secret": secret, "grant_type": "authorization_code",
        "redirect_uri": REDIRECT, "code": code}).encode()
    req = urllib.request.Request(TOKEN, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        short = json.load(r)
    print(f"user id: {short.get('user_id')}  granted: {short.get('permissions')}")

    got = json.load(urllib.request.urlopen(
        f"{GRAPH}/access_token?" + urllib.parse.urlencode({
            "grant_type": "ig_exchange_token", "client_secret": secret,
            "access_token": short["access_token"]}), timeout=30))
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-url", action="store_true")
    ap.add_argument("--code", default="")
    args = ap.parse_args()

    if args.auth_url:
        print("\n1. Open this URL and log in as @saintseoul_studio, then approve:\n")
        print(auth_url())
        print(f"\n2. You will land on {REDIRECT}?code=XXXXX (the page itself will not load —")
        print("   that is fine and expected). Copy the code= value from the address bar.")
        print("\n3. python3 ig_login.py --code 'PASTE_IT_HERE'\n")
        return
    if not args.code:
        raise SystemExit("use --auth-url first, then --code '<the code from the redirect>'")

    got = exchange(args.code)
    days = (got.get("expires_in") or 0) // 86400
    print(f"\nlong-lived token ({days} days):\n\n{got['access_token']}\n")
    print("Store it, then never paste it anywhere else:")
    print("  gh secret set IG_INSIGHTS_TOKEN")
    print("\nrefresh_token.py keeps it alive from here on — it never has to be done by hand again.")


if __name__ == "__main__":
    main()
