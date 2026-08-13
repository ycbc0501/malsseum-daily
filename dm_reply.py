#!/usr/bin/env python3
"""
The ONE private reply we send to someone who comments on a post.

Meta's Private Replies allow exactly one DM per comment, within 7 days of it, and Meta's
spam policy forbids making a follow the price of content. So this message asks for
nothing at all: it is the 기도문 matched to the theme of the verse they commented on, and
that is the whole message.

We deliberately never send a second one — no sequence, no follow-up, and no "무엇을 위해
기도할까요?" reply bait. A reply would open a 24-hour window, but this account is
hands-off by design, and inviting someone to share a burden that nobody will ever read
is worse than staying quiet. One gift, then silence.

Sending is NOT wired into the pipeline: no workflow calls this module, and
`reply_to_new_comments()` defaults to dry-run. It stays dormant until
instagram_manage_messages clears App Review.

    python3 dm_reply.py --preview      # print every message this would ever send
"""

import argparse
import json
import os

import carousel

# Greeting × closing = 9 wordings per theme, 81 across the nine themes. The recipient only
# ever gets one message, so this variety is not for them — it is so the account never emits
# the same block of text over and over. Meta flags repetitive identical outbound, and
# CONTENT_RULE §11 counts perceived sameness as a repeat, not just literal reuse.
GREETINGS = [
    "오늘 말씀에 마음 나눠주셔서 감사합니다.",
    "댓글로 마음 전해주셔서 감사합니다.",
    "말씀에 함께해 주셔서 감사합니다.",
]
CLOSINGS = [
    "오늘 하루 평안하시기를 기도합니다.",
    "오늘도 주님의 평안이 함께하시기를 바랍니다.",
    "당신의 하루에 따뜻한 빛이 머물기를 바랍니다.",
]


def compose(theme, dm_i):
    """The message for a commenter on a `theme` verse. `dm_i` is the monotonic send
    counter: greeting and closing step at coprime rates so all 9 pairings cycle before
    any repeats — the same trick the scene variation uses."""
    prayer = carousel.PRAYER.get(theme) or carousel.PRAYER["믿음"]
    greeting = GREETINGS[dm_i % len(GREETINGS)]
    closing = CLOSINGS[(dm_i // len(GREETINGS)) % len(CLOSINGS)]
    return f"안녕하세요 🙏\n{greeting}\n\n“{prayer}”\n\n{closing}"


def reply_to_new_comments(state, dry_run=True):
    """Private-reply once to every unanswered comment on our recent posts.

    Safe to run repeatedly: `replied_comments` makes one-per-comment a hard invariant,
    which matters because a poller sees the same comment on every pass and Meta allows
    only one. Returns the messages it sent (or would have sent, when dry_run)."""
    import post_instagram

    posted = state.get("posted_media", {})            # media_id → verse theme
    replied = state.setdefault("replied_comments", [])
    me = os.environ.get("IG_USERNAME") or ""       # never hardcode the handle — see rule 10c
    if not me:
        try:
            me = post_instagram.username() or ""
        except Exception as e:
            print(f"username lookup failed ({e}) — not DMing, to avoid replying to ourselves")
            return []
    sent = []
    for media_id, theme in posted.items():
        try:
            found = post_instagram.comments(media_id)
        except Exception as e:                        # never let one bad media stop the rest
            print(f"comments({media_id}) failed: {e}")
            continue
        for c in found:
            if c["id"] in replied or c.get("username") == me:   # never reply to our own hashtag comment
                continue
            dm_i = state.get("dm_i", 0)
            text = compose(theme, dm_i)
            if not dry_run:
                try:
                    post_instagram.private_reply(c["id"], text)
                except Exception as e:
                    print(f"private_reply({c['id']}) failed: {e}")
                    continue
            replied.append(c["id"])
            state["dm_i"] = dm_i + 1
            sent.append((c["id"], text))
    del replied[:-500]
    return sent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true",
                    help="print every message this module can send, then exit")
    args = ap.parse_args()
    if args.preview:
        for theme in carousel.PRAYER:
            for dm_i in range(len(GREETINGS) * len(CLOSINGS)):
                print(f"--- {theme}  (dm_i={dm_i}) ---\n{compose(theme, dm_i)}\n")
        return
    print(__doc__.strip().splitlines()[0])
    print("sending is not wired up — see the module docstring. Try --preview.")


if __name__ == "__main__":
    main()
