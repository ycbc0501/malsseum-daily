#!/usr/bin/env python3
"""A post deleted from the account must leave the ledger — and nothing else may.

ledger_merge is a union, so a deletion made by hand is undone by the next workflow's merge. The
only durable way to express one is to take it from the account itself, which is the same rule the
rest of the pipeline already follows. These checks pin the two halves that matter: the deleted
post goes, and posts merely outside the API's window stay.
"""
import json
import sys
import tempfile
from datetime import datetime, timedelta
from unittest import mock

import metrics

KST = metrics.KST
fails = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        fails.append(name)


def utc(dt):
    return (dt - timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S+0000")


def run():
    now = datetime.now(KST)
    ledger = {
        "keep_new":  {"ref": "A", "published": (now - timedelta(days=1)).isoformat()},
        "deleted":   {"ref": "B", "published": (now - timedelta(days=2)).isoformat()},
        "keep_old":  {"ref": "C", "published": (now - timedelta(days=90)).isoformat()},
    }
    live = [{"id": "keep_new", "timestamp": utc(now - timedelta(days=1))},
            {"id": "other",    "timestamp": utc(now - timedelta(days=3))}]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(ledger, f)
        path = f.name
    with mock.patch.object(metrics, "FILE", path), \
         mock.patch("post_instagram.recent_media", return_value=live):
        gone = metrics.prune_deleted()
        left = json.load(open(path))

    check("the deleted post is removed", "deleted" not in left)
    check("its ref is reported back", gone == ["B"])
    check("a live post is kept", "keep_new" in left)
    check("a post older than the window is kept", "keep_old" in left)

    # A failed lookup must remove nothing — silence is not evidence of deletion.
    with mock.patch.object(metrics, "FILE", path), \
         mock.patch("post_instagram.recent_media", side_effect=RuntimeError("api down")):
        check("a failed lookup prunes nothing", metrics.prune_deleted() == [])
    with mock.patch.object(metrics, "FILE", path), \
         mock.patch("post_instagram.recent_media", return_value=[]):
        check("an empty answer prunes nothing", metrics.prune_deleted() == [])

    print("\n" + ("all good" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
