#!/usr/bin/env python3
"""
Publish a single image to Instagram via the Meta Graph API (Content Publishing API).

Requires (from your Meta app + Instagram Business/Creator account):
    IG_USER_ID        — the Instagram Business account's user id
    IG_ACCESS_TOKEN   — a long-lived access token with instagram_content_publish

The image must be at a PUBLIC URL — the Graph API fetches it; it can't take a raw upload.
"""

import json
import os
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def publish(image_url, caption, ig_user_id=None, token=None):
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    if not (ig_user_id and token):
        raise SystemExit("Set IG_USER_ID and IG_ACCESS_TOKEN (env or args).")

    # 1) create a media container
    container = _post(f"{GRAPH}/{ig_user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    creation_id = container["id"]

    # 2) wait until Instagram has fetched & processed the image
    for _ in range(15):
        status = _get(f"{GRAPH}/{creation_id}?fields=status_code&access_token={token}")
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise SystemExit(f"media processing error: {status}")
        time.sleep(3)

    # 3) publish the container
    result = _post(f"{GRAPH}/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image_url")
    ap.add_argument("caption")
    args = ap.parse_args()
    print(publish(args.image_url, args.caption))
