#!/usr/bin/env python3
"""The 퍼온 콘텐츠 flag ledger — what the app shows, kept as data instead of screenshots.

    python3 test_flag_ledger.py

Why this is tested at all: the flag is the fastest signal the account has (attached within
hours, where likes take ~36h to mature and a week to beat noise), and it arrives ONLY as a
screenshot. A recorder that silently matched nothing would look exactly like "no posts are
flagged" — the most dangerous wrong answer available here.
"""
import json
import os
import sys
import tempfile

import metrics

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


def with_ledger(rows, fn):
    """Run `fn` against a throwaway metrics.json → the ledger after it ran."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    real, metrics.FILE = metrics.FILE, path
    try:
        fn()
        return json.load(open(path, encoding="utf-8"))
    finally:
        metrics.FILE = real
        os.unlink(path)


LEDGER = {
    "111": {"ref": "전도서 11:4", "kind": "REELS",
            "permalink": "https://www.instagram.com/reel/AAA/",
            "published": "2026-09-15T09:59:00+0000"},
    "222": {"ref": "시편 4:8", "kind": "FEED",
            "permalink": "https://www.instagram.com/p/BBB/",
            "published": "2026-09-13T07:21:00+0000"},
}

print("flag ledger")

got = with_ledger(LEDGER, lambda: metrics.note_flag(["전도서 11:4"]))
check("a ref marks that post flagged", got["111"]["reposted_flag"]["flagged"] is True)
check("the check is dated", bool(got["111"]["reposted_flag"].get("checked")))
check("other posts are left unknown, not assumed clean", "reposted_flag" not in got["222"])

# "not in the list" has to be storable. A negative that cannot be written down is a negative
# that never becomes evidence, and the whole point is comparing flagged against not-flagged.
got = with_ledger(LEDGER, lambda: metrics.note_flag(["시편 4:8"], flagged=False))
check("notflagged records a positive absence", got["222"]["reposted_flag"]["flagged"] is False)

# The app gives a permalink far more readily than our internal ref.
got = with_ledger(LEDGER, lambda: metrics.note_flag(["https://www.instagram.com/reel/AAA/"]))
check("a permalink resolves too", got["111"].get("reposted_flag", {}).get("flagged") is True)

# A typo must not look like a successful recording.
hits = []
with_ledger(LEDGER, lambda: hits.append(metrics.note_flag(["없는 구절 1:1"])))
check("an unknown ref matches nothing and says so", hits == [0])

# Several refs at once — the app lists them that way and re-typing one command per post is
# how a reading gets half-entered.
got = with_ledger(LEDGER, lambda: metrics.note_flag(["전도서 11:4", "시편 4:8"]))
check("multiple refs in one call", all("reposted_flag" in got[k] for k in ("111", "222")))

print("\nreport")
# The report must not crash on a ledger where nothing has been checked yet — that is its
# state on every fresh clone, and it is also the state it has to invite action from.
with_ledger(LEDGER, lambda: metrics.flag_report("2026-09-01"))
check("report runs on an unchecked ledger", True)


def _checked():
    metrics.note_flag(["전도서 11:4"])
    metrics.flag_report("2026-09-01")


with_ledger(LEDGER, _checked)
check("report runs once something is checked", True)

# The before/after split is the only thing this ledger is for. If REFLECTION_SINCE ever drifts
# past the first post that carried the line, every row lands on the wrong side of the compare.
check("REFLECTION_SINCE precedes the first caption-line post",
      metrics.REFLECTION_SINCE < metrics.published_kst({"published": "2026-09-15T20:19:00+0000"}))

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
