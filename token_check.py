#!/usr/bin/env python3
"""
What is IG_ACCESS_TOKEN, actually? — app, account, scopes and expiry.

Written because "(#10) Application does not have permission" says nothing about WHICH app
is missing WHICH permission, and the answer decides where you have to log in to fix it.
Prints identity and scopes only; the token itself is never echoed.

    python3 token_check.py          # needs IG_USER_ID + IG_ACCESS_TOKEN in the environment
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

FB = "https://graph.facebook.com/v21.0"
IG = "https://graph.instagram.com"


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _try(label, url):
    """Run one probe and report it. Meta puts the real reason in the error body."""
    try:
        got = _get(url)
        print(f"  {label}: {json.dumps(got, ensure_ascii=False)[:400]}")
        return got
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        print(f"  {label}: HTTP {e.code} {msg}")
    except Exception as e:
        print(f"  {label}: {e}")
    return None


def main():
    tok = os.environ.get("IG_ACCESS_TOKEN")
    uid = os.environ.get("IG_USER_ID")
    if not (tok and uid):
        raise SystemExit("set IG_USER_ID and IG_ACCESS_TOKEN")
    q = urllib.parse.urlencode({"access_token": tok})

    print("WHICH LOGIN OWNS THIS TOKEN")
    # A token minted through 'Instagram API with Instagram Login' answers on graph.instagram.com;
    # one minted through a Meta app + Facebook Page answers on graph.facebook.com. Which host
    # replies tells you which dashboard to sign in to.
    _try("facebook /me      ", f"{FB}/me?fields=id,name&{q}")
    _try("instagram /me     ", f"{IG}/me?fields=id,username&{q}")
    _try("debug_token       ", f"{FB}/debug_token?input_token={urllib.parse.quote(tok)}&{q}")

    print("\nSCOPES ON THIS TOKEN")
    perms = _try("granted           ", f"{FB}/me/permissions?{q}")
    if perms:
        rows = perms.get("data", [])
        ok = sorted(p["permission"] for p in rows if p.get("status") == "granted")
        no = sorted(p["permission"] for p in rows if p.get("status") != "granted")
        print(f"  granted: {ok}")
        print(f"  not granted: {no}")
        need = "instagram_manage_insights"
        print(f"  >>> {need}: {'PRESENT' if need in ok else 'MISSING — this is the blocker'}")

    print("\nWHICH ACCOUNT IT POSTS AS")
    _try("profile           ",
         f"{FB}/{uid}?fields=username,followers_count,media_count&{q}")


if __name__ == "__main__":
    main()
