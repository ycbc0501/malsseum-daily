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


def publish_reel(video_url, caption, ig_user_id=None, token=None):
    """Publish a Reel (video). Used for still-image-with-music posts."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    if not (ig_user_id and token):
        raise SystemExit("Set IG_USER_ID and IG_ACCESS_TOKEN (env or args).")

    container = _post(f"{GRAPH}/{ig_user_id}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",     # also show in the profile feed grid
        "access_token": token,
    })
    creation_id = container["id"]

    # video processing takes longer than images — poll generously
    for _ in range(60):
        status = _get(f"{GRAPH}/{creation_id}?fields=status_code,status&access_token={token}")
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise SystemExit(f"reel processing error: {status}")
        time.sleep(5)
    else:
        raise SystemExit("reel processing timed out")

    return _post(f"{GRAPH}/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })


def publish_carousel(image_urls, caption, ig_user_id=None, token=None):
    """Publish a multi-image carousel post."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    if not (ig_user_id and token):
        raise SystemExit("Set IG_USER_ID and IG_ACCESS_TOKEN (env or args).")
    children = []
    for u in image_urls:
        c = _post(f"{GRAPH}/{ig_user_id}/media", {
            "image_url": u, "is_carousel_item": "true", "access_token": token})
        children.append(c["id"])
    container = _post(f"{GRAPH}/{ig_user_id}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children),
        "caption": caption, "access_token": token})
    for _ in range(20):
        status = _get(f"{GRAPH}/{container['id']}?fields=status_code&access_token={token}")
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise SystemExit(f"carousel processing error: {status}")
        time.sleep(3)
    return _post(f"{GRAPH}/{ig_user_id}/media_publish", {
        "creation_id": container["id"], "access_token": token})


def comment(media_id, message, ig_user_id=None, token=None):
    """Post a comment on a published media (used for the hashtag first-comment).
    Needs the instagram_manage_comments permission on the token."""
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    return _post(f"{GRAPH}/{media_id}/comments", {"message": message, "access_token": token})


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default="", help="public image/video URL")
    ap.add_argument("caption", nargs="?", default="")
    ap.add_argument("--reel", action="store_true", help="publish as a Reel (video)")
    ap.add_argument("--carousel", default="", help="comma-separated image URLs for a carousel")
    ap.add_argument("--caption-text", default="", help="caption when using --carousel")
    ap.add_argument("--comment", default="", help="post this as a first comment (hashtags)")
    args = ap.parse_args()
    if args.carousel:
        urls = [u for u in args.carousel.split(",") if u]
        result = publish_carousel(urls, args.caption_text or args.url)
    elif args.reel:
        result = publish_reel(args.url, args.caption)
    else:
        result = publish(args.url, args.caption)
    print(result)
    if args.comment and isinstance(result, dict) and result.get("id"):
        print("comment:", comment(result["id"], args.comment))
