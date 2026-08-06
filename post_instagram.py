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


def publish_story(media_url, ig_user_id=None, token=None):
    """Publish the post to Stories as well (media_type=STORIES).

    Same container→publish flow as everything else; the only difference is that a story
    carries no caption (Instagram ignores one) and expires after 24h. `share_to_feed` on
    a Reel puts it in the profile GRID, which is not this — a story has to be published
    separately."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    is_video = media_url.rsplit("?", 1)[0].lower().endswith((".mp4", ".mov"))
    params = {"media_type": "STORIES", "access_token": token}
    params["video_url" if is_video else "image_url"] = media_url
    container = _post(f"{GRAPH}/{ig_user_id}/media", params)
    creation_id = container["id"]

    for _ in range(60):
        status = _get(f"{GRAPH}/{creation_id}?fields=status_code&access_token={token}")
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise SystemExit(f"story processing error: {status}")
        time.sleep(5)
    else:
        raise SystemExit("story processing timed out")

    return _post(f"{GRAPH}/{ig_user_id}/media_publish", {
        "creation_id": creation_id, "access_token": token})


def recent_media(limit=8, ig_user_id=None, token=None):
    """The account's most recent media: [{id, timestamp, media_product_type, permalink, caption}].

    Read straight from the API rather than from a local ledger so the comment poller and the
    insights collector both work on posts published before any bookkeeping existed — the caption
    carries the verse reference, which is how an old post is matched back to its theme."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    # like_count/comments_count are plain media FIELDS, not insights — they need only
    # instagram_basic, so they keep working when instagram_manage_insights is missing.
    got = _get(f"{GRAPH}/{ig_user_id}/media"
               f"?fields=id,timestamp,media_product_type,permalink,caption,"
               f"like_count,comments_count"
               f"&limit={int(limit)}&access_token={token}")
    return got.get("data", [])


def comments(media_id, token=None):
    """Every comment on a published media, newest first: [{id, text, timestamp, username}]."""
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    got = _get(f"{GRAPH}/{media_id}/comments"
               f"?fields=id,text,timestamp,username&access_token={token}")
    return got.get("data", [])


def reply(comment_id, message, token=None):
    """Reply publicly, in-thread, to a comment.

    Uses instagram_manage_comments — the permission the hashtag first-comment already needs —
    so unlike a private reply this works today with no extra App Review."""
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    return _post(f"{GRAPH}/{comment_id}/replies",
                 {"message": message, "access_token": token})


def private_reply(comment_id, message, ig_user_id=None, token=None):
    """Send the ONE private reply Meta allows for a comment (Private Replies).

    Meta's limits, which the caller must respect: exactly one message per comment,
    within 7 days of it, and it may not make a follow the price of the content. If the
    commenter doesn't already follow the account the DM lands in their Requests folder.
    Needs instagram_manage_messages on the token (App Review)."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    return _post(f"{GRAPH}/{ig_user_id}/messages", {
        "recipient": json.dumps({"comment_id": comment_id}),
        "message": json.dumps({"text": message}),
        "access_token": token})


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
