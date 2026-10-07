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


def tmpjson(obj):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(obj, f)
        return f.name


def run():
    now = datetime.now(KST)
    ledger = {
        "keep_new":  {"ref": "A", "published": (now - timedelta(days=1)).isoformat()},
        "deleted":   {"ref": "B", "published": (now - timedelta(days=2)).isoformat(),
                      "insights": {"views": 321, "likes": 19}, "veo_seconds": 48.0},
        "keep_old":  {"ref": "C", "published": (now - timedelta(days=90)).isoformat()},
    }
    live = [{"id": "keep_new", "timestamp": utc(now - timedelta(days=1)), "caption": "… [A]"},
            {"id": "other",    "timestamp": utc(now - timedelta(days=3)), "caption": "… [D]"}]

    path = tmpjson(ledger)
    arch = tmpjson({})
    # Real state.json must never be touched by a test — and before this file patched STATE, a
    # single run of these checks would have rewritten the account's live no-repeat ledger.
    st = tmpjson({"used_verses": ["A", "B", "C", "D"], "music_i": 3})
    with mock.patch.object(metrics, "FILE", path), \
         mock.patch.object(metrics, "DELETED", arch), \
         mock.patch.object(metrics, "STATE", st), \
         mock.patch("post_instagram.recent_media", return_value=live):
        gone = metrics.prune_deleted()
        left = json.load(open(path))
        kept = json.load(open(arch))
        state = json.load(open(st))

    check("the deleted post is removed", "deleted" not in left)
    check("its ref is reported back", gone == ["B"])
    check("a live post is kept", "keep_new" in left)
    check("a post older than the window is kept", "keep_old" in left)

    # ── the measurement survives the deletion ────────────────────────────────────────────────
    # 83 posts' worth of views/shares is what RULES E-0c and E-0d now stand on. A post taken
    # down for a bad render still measured something, and pruning used to vaporise the row.
    check("the deleted post's measurements are archived", "deleted" in kept)
    check("the archive keeps its numbers", kept.get("deleted", {}).get("insights", {}).get("views") == 321)
    check("the archive records when it went", "deleted_noticed" in kept.get("deleted", {}))
    check("a surviving post is NOT archived", "keep_new" not in kept)

    # ── the verse goes back into the pool ────────────────────────────────────────────────────
    # C4b's whole purpose. used_verses is append-only, so without this the verse stays blocked
    # for a full cycle — which is what happened to 고린도전서 15:55 until it was fixed by hand.
    check("the deleted post's verse is released", "B" not in state["used_verses"])
    check("a surviving post's verse stays blocked", "A" in state["used_verses"])
    check("an untouched verse stays blocked", "C" in state["used_verses"])
    check("the rest of state.json is left alone", state.get("music_i") == 3)

    # A verse still live under a SECOND post must stay blocked: refs can repeat across media.
    dup = {"gone": {"ref": "E", "published": (now - timedelta(days=2)).isoformat()},
           "twin": {"ref": "E", "published": (now - timedelta(days=1)).isoformat()}}
    p2, a2 = tmpjson(dup), tmpjson({})
    s2 = tmpjson({"used_verses": ["E"]})
    with mock.patch.object(metrics, "FILE", p2), mock.patch.object(metrics, "DELETED", a2), \
         mock.patch.object(metrics, "STATE", s2), \
         mock.patch("post_instagram.recent_media",
                    return_value=[{"id": "twin", "timestamp": utc(now - timedelta(days=1)),
                                   "caption": "… [E]"},
                                  # The window has to REACH the deleted post, or this check
                                  # passes without ever pruning anything. It did, once.
                                  {"id": "anchor", "timestamp": utc(now - timedelta(days=5)),
                                   "caption": "… [Z]"}]):
        check("the duplicate case actually prunes", metrics.prune_deleted() == ["E"])
        check("a verse another surviving post still holds is NOT released",
              json.load(open(s2))["used_verses"] == ["E"])

    # And one still visible in a LIVE caption, even with no ledger row of its own.
    s3 = tmpjson({"used_verses": ["F"]})
    p3, a3 = tmpjson({"g": {"ref": "F", "published": (now - timedelta(days=2)).isoformat()}}), tmpjson({})
    with mock.patch.object(metrics, "FILE", p3), mock.patch.object(metrics, "DELETED", a3), \
         mock.patch.object(metrics, "STATE", s3), \
         mock.patch("post_instagram.recent_media",
                    return_value=[{"id": "zz", "timestamp": utc(now - timedelta(days=2)),
                                   "caption": "오늘의 말씀 [F]"}]):
        metrics.prune_deleted()
        check("a verse still in a live caption is NOT released",
              json.load(open(s3))["used_verses"] == ["F"])

    # A failed lookup must remove nothing — silence is not evidence of deletion.
    for name, kw in (("a failed lookup", {"side_effect": RuntimeError("api down")}),
                     ("an empty answer", {"return_value": []})):
        s4 = tmpjson({"used_verses": ["A", "B", "C"]})
        with mock.patch.object(metrics, "FILE", path), mock.patch.object(metrics, "DELETED", arch), \
             mock.patch.object(metrics, "STATE", s4), \
             mock.patch("post_instagram.recent_media", **kw):
            check(f"{name} prunes nothing", metrics.prune_deleted() == [])
            check(f"{name} releases no verse",
                  json.load(open(s4))["used_verses"] == ["A", "B", "C"])

    # ── the deletion must survive ledger_merge ───────────────────────────────────────────────
    # save_ledger.sh resets onto origin/main and unions our file over it, so the pruned row is
    # handed straight back by the remote. This is not a race — it is every run. Simulated here
    # the same way the real save step does it.
    import ledger_merge
    remote = dict(ledger)                       # origin/main still carries the deleted post
    ours = {k: v for k, v in ledger.items() if k != "deleted"}
    merged = ledger_merge.merge(ours, remote)
    check("ledger_merge does bring the deleted row back (this is the hazard)", "deleted" in merged)

    resur = tmpjson(merged)
    with mock.patch.object(metrics, "FILE", resur), mock.patch.object(metrics, "DELETED", arch):
        check("but load() drops it again, because the archive is the authority",
              "deleted" not in metrics.load())
        check("and keeps everything that was not deleted", "keep_new" in metrics.load())

    # The verse release has the same hazard: used_verses is a list and the union re-adds the ref.
    # Driving the release from the archive every run is what makes it converge.
    s5 = tmpjson({"used_verses": ["A", "B", "C"]})     # B is back after a merge
    with mock.patch.object(metrics, "FILE", resur), mock.patch.object(metrics, "DELETED", arch), \
         mock.patch.object(metrics, "STATE", s5), \
         mock.patch("post_instagram.recent_media", return_value=live):
        metrics.prune_deleted()
        check("a re-added verse is released again on the next run",
              "B" not in json.load(open(s5))["used_verses"])

    # An unreadable archive must not be silently replaced by an empty one.
    bad = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    bad.write("{not json"); bad.close()
    with mock.patch.object(metrics, "DELETED", bad.name):
        try:
            metrics.load_deleted()
            check("an unreadable archive raises rather than returning {}", False)
        except Exception:
            check("an unreadable archive raises rather than returning {}", True)
        # …and nothing may be pruned while it cannot be archived: that would destroy the
        # measurements instead of moving them.
        keepsafe = tmpjson(ledger)
        with mock.patch.object(metrics, "FILE", keepsafe), \
             mock.patch("post_instagram.recent_media", return_value=live):
            check("an unreadable archive prunes nothing", metrics.prune_deleted() == [])
            check("…and leaves the ledger whole", len(json.load(open(keepsafe))) == 3)
        # A reader must not drop rows just because the archive is unreadable either.
        with mock.patch.object(metrics, "FILE", keepsafe):
            check("…and load() still returns every row", len(metrics.load()) == 3)

    print("\n" + ("all good" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
