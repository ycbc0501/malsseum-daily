#!/usr/bin/env python3
"""
Reply 🙏 to every comment — publicly, in-thread, about half an hour later.

Why the delay: an instant reply reads as a bot and is the one thing that makes a warm
gesture feel mechanical. Each comment gets its own target time of **comment + 10..50 min**
(≈30 ± 20), drawn once when the comment is first seen and remembered in `comments.json`, so a
stateless cron still honours it. Replying is what we can actually do today: in-thread
replies use `instagram_manage_comments`, the permission the hashtag first-comment already
holds — no App Review, unlike the private reply in dm_reply.py.

    python3 comment_reply.py --dry-run    # show what would be replied to, send nothing
    python3 comment_reply.py              # poll + reply (the cron path)
"""

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

REPLIES = ["🙏", "아멘🙏"]
DELAY_MIN, DELAY_MAX = 10 * 60, 50 * 60   # 30 ± 20 minutes, in seconds
BACKFILL_AGE = 24 * 3600                  # older than this on first sight → never reply
MEDIA_WINDOW = 4 * 86400                  # only poll posts this recent for new comments
HERE = os.path.dirname(os.path.abspath(__file__))
# Its own ledger, NOT state.json: this runs every 10 minutes while daily_post.py commits
# state.json twice a day, and two jobs rebasing the same one-line JSON file is a conflict
# waiting to happen. Separate files never collide.
STATE = os.path.join(HERE, "comments.json")


def _epoch(ts):
    """Graph API timestamps ('2026-08-05T09:12:34+0000') → epoch seconds."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").timestamp()


def poll(state, now=None, dry_run=False):
    """One pass: schedule replies for new comments, send any that have come due.

    Returns (scheduled, sent) for logging. Never raises on a single bad media/comment —
    a poller that dies on one post stops replying to every other post too.
    """
    import post_instagram
    now = now or time.time()
    # Resolved from the API, never hardcoded — see post_instagram.username(). The last known
    # handle is cached so a flaky lookup can't turn into replying to ourselves; if we have no
    # handle at all we skip nothing and would reply to our own comment, so bail instead.
    me = os.environ.get("IG_USERNAME") or ""
    if not me:
        try:
            me = post_instagram.username() or ""
            state["me"] = me
        except Exception as e:
            me = state.get("me", "")
            print(f"username lookup failed ({e}) — using cached {me!r}")
    if not me:
        print("cannot determine our own handle; skipping this pass rather than self-replying")
        return [], []
    replied = state.setdefault("replied_publicly", [])
    pending = state.setdefault("pending_replies", {})
    scheduled, sent = [], []

    for media in post_instagram.recent_media():
        try:
            if now - _epoch(media["timestamp"]) > MEDIA_WINDOW:
                continue                                  # comments arrive early; old posts are done
            found = post_instagram.comments(media["id"])
        except Exception as e:
            print(f"comments({media.get('id')}) failed: {e}")
            continue
        for c in found:
            if c["id"] in replied or c["id"] in pending or c.get("username") == me:
                continue                                  # already handled, or our own hashtag comment
            try:
                made = _epoch(c["timestamp"])
            except Exception:
                made = now
            if now - made > BACKFILL_AGE:
                # First deploy sees every historical comment at once. Replying to all of them
                # in one burst is exactly the bot behaviour the delay exists to avoid, so old
                # comments are marked handled instead — we start clean, not with a spam wave.
                replied.append(c["id"])
                continue
            pending[c["id"]] = made + random.uniform(DELAY_MIN, DELAY_MAX)
            scheduled.append((c["id"], pending[c["id"]] - now))

    for cid, due in sorted(pending.items(), key=lambda kv: kv[1]):
        if due > now:
            continue
        text = REPLIES[state.get("reply_i", 0) % len(REPLIES)]
        if not dry_run:
            try:
                post_instagram.reply(cid, text)
            except Exception as e:
                print(f"reply({cid}) failed: {e}")
                continue                                  # leave it pending; retry next poll
        state["reply_i"] = state.get("reply_i", 0) + 1
        del pending[cid]
        replied.append(cid)
        sent.append((cid, text))

    del replied[:-500]
    return scheduled, sent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    scheduled, sent = poll(state, dry_run=args.dry_run)
    for cid, wait in scheduled:
        print(f"scheduled {cid} in {wait / 60:.0f} min")
    for cid, text in sent:
        print(f"{'would reply' if args.dry_run else 'replied'} {cid}: {text}")
    if not (scheduled or sent):
        print("nothing due")
    if not args.dry_run:
        json.dump(state, open(STATE, "w"))


if __name__ == "__main__":
    main()
