#!/usr/bin/env python3
"""The reply poller must never reply to the same comment twice.

    python3 test_comment_reply.py

This is not hypothetical. Between 2026-09-14 and 2026-09-17 one comment received a reply on
EVERY workflow run — alternating 🙏 / 아멘🙏, a few hours apart, 26 in total — because
`pending_replies` is a work queue and ledger_merge.py cannot express a deletion: the entry we
removed after replying was restored from the remote copy on the next save. Nothing in the code
noticed, because the send loop trusted the queue instead of the done-list.
"""
import sys
import types

import comment_reply

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


class FakeIG:
    """Stands in for post_instagram — records what would be sent to Instagram."""

    def __init__(self, comments):
        self._comments = comments
        self.sent = []

    def username(self):
        return "saintseoul_studio"

    def recent_media(self):
        return [{"id": "m1", "timestamp": "2026-09-16T00:00:00+0000"}]

    def comments(self, media_id, token=None):
        return self._comments

    def reply(self, comment_id, message, token=None):
        self.sent.append((comment_id, message))
        return {"id": "reply-" + str(len(self.sent))}


def run(state, comments, now):
    fake = FakeIG(comments)
    real = sys.modules.get("post_instagram")
    sys.modules["post_instagram"] = types.SimpleNamespace(**{
        k: getattr(fake, k) for k in ("username", "recent_media", "comments", "reply")})
    try:
        comment_reply.poll(state, now=now)
    finally:
        if real is not None:
            sys.modules["post_instagram"] = real
        else:
            del sys.modules["post_instagram"]
    return fake.sent


NOW = 1789000000.0
FRESH = [{"id": "c1", "text": "아멘", "username": "someone",
          "timestamp": "2026-09-16T00:10:00+0000"}]

print("comment reply")

# The real failure, reproduced: the queue entry is back AND the comment is already answered.
# This is the exact shape of comments.json on 2026-09-17.
state = {"replied_publicly": ["c1"], "pending_replies": {"c1": NOW - 3600},
         "me": "saintseoul_studio", "reply_i": 26}
sent = run(state, FRESH, NOW)
check("a resurrected queue entry does not become a second reply", sent == [])
check("and the entry is dropped so it cannot come back again",
      "c1" not in state["pending_replies"])
check("the reply rotation does not advance on a non-send", state["reply_i"] == 26)

# The normal path still has to work — a guard that silences every reply is not a fix.
state = {"replied_publicly": [], "pending_replies": {"c1": NOW - 60},
         "me": "saintseoul_studio", "reply_i": 0}
sent = run(state, FRESH, NOW)
check("a genuinely due comment still gets exactly one reply", len(sent) == 1)
check("and it is recorded as replied", state["replied_publicly"] == ["c1"])
check("and the queue entry is gone", state["pending_replies"] == {})

# Run the very next poll against the state we just produced, with the API still returning the
# same comment. This is what actually happens every 10 minutes.
sent = run(state, FRESH, NOW + 600)
check("the next poll sends nothing", sent == [])

# A comment that is not due yet must wait — the delay is the whole reason this is not instant.
state = {"replied_publicly": [], "pending_replies": {"c1": NOW + 1200},
         "me": "saintseoul_studio", "reply_i": 0}
sent = run(state, FRESH, NOW)
check("an undue comment is not replied to early", sent == [])
check("and it stays queued", "c1" in state["pending_replies"])

# Our own comment (the hashtag first comment) must never be answered.
mine = [{"id": "c9", "text": "#오늘의말씀", "username": "saintseoul_studio",
         "timestamp": "2026-09-16T00:10:00+0000"}]
state = {"replied_publicly": [], "pending_replies": {}, "me": "saintseoul_studio"}
sent = run(state, mine, NOW)
check("we never reply to ourselves", sent == [] and state["pending_replies"] == {})

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
