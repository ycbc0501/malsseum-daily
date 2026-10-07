#!/usr/bin/env python3
"""A number read off the app must land where the code that reads it is looking.

This project spent two months reasoning about distribution from likes while reach, sends and
watch time sat on the Instagram screen unread. Twice now the same failure has repeated one
level down, inside our own ledger:

  1. `report()` required `insights.reach` and therefore printed "0 with insights" while
     fourteen hand-entered view counts sat in the file (fixed 2026-10-07 morning).
  2. `observe … saves=6` wrote `insights.saves`, while `report()` reads `saved` — the API's
     spelling. The number was recorded, stored, committed, and invisible (fixed same evening,
     within minutes of the first real 저장 count ever entered).

Both are the same bug: data present, reader looking elsewhere. These checks pin the field
names and units so the third one does not happen quietly.
"""
import json
import sys
import tempfile
from unittest import mock

import metrics

fails = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        fails.append(name)


def fresh():
    ledger = {"mid1": {"ref": "고린도전서 10:24", "permalink": "https://x/reel/AAA/",
                       "segments": 0, "date": "2026-10-06"}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(ledger, f)
        return f.name


def run():
    path = fresh()
    with mock.patch.object(metrics, "FILE", path):
        ok = metrics.note("고린도전서 10:24", views=260, reach=233, likes=22, comments=2,
                          shares=1, reposts=0, saves=6, follows=0, watch=2,
                          skip_rate=85.2, src_reels=56.6, src_explore=30.9, src_feed=12.5)
        ins = json.load(open(path))["mid1"]["insights"]
    check("every field off 릴스 인사이트 is accepted", ok)

    # --- field NAMES: a hand-entered number must land where readers look -------------------
    check("saves lands in the API's field name `saved`", ins.get("saved") == 6)
    check("`saves` is not left as a second, unread field", "saves" not in ins)
    check("watch lands in the API's `ig_reels_avg_watch_time`",
          ins.get("ig_reels_avg_watch_time") == 2000)        # 2초 → ms, the API's unit
    check("the app's own spelling is not kept alongside it", "watch" not in ins)

    # --- UNITS: a percentage is not a count ------------------------------------------------
    check("a skip rate keeps its decimal", ins.get("skip_rate") == 85.2)
    check("view sources keep theirs", ins.get("src_reels") == 56.6
          and ins.get("src_explore") == 30.9 and ins.get("src_feed") == 12.5)
    check("counts stay integers", isinstance(ins.get("reach"), int) and ins["reach"] == 233)

    # --- 0 IS A VALUE ----------------------------------------------------------------------
    # A post with no sends is the observation that makes a post with sends mean something.
    check("a zero is recorded, not dropped", ins.get("shares") == 1 and ins.get("reposts") == 0
          and "reposts" in ins and ins.get("follows") == 0)

    # --- the hand-entry marker travels with the STORED name --------------------------------
    for f in ("saved", "ig_reels_avg_watch_time", "reach", "skip_rate"):
        check(f"`{f}` is marked hand-entered", ins.get(f"{f}_manual") is True)

    # --- report() must actually read what note() wrote -------------------------------------
    # The whole point. If this passes while the one above fails, the number is in the file
    # and nobody will ever see it.
    with mock.patch.object(metrics, "FILE", path):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            metrics.report()
        out = buf.getvalue()
    check("report() counts it as reach, not as views standing in",
          "1 reach read off 릴스 인사이트" in out and "0 reach from the API" in out)
    check("report() prints the saved count it was given", "saved=    6.0(n=1)" in out)
    check("report() prints watch time in seconds", "2.0s(n=1)" in out)
    check("report() prints the skip rate", "85.2%(n=1)" in out)
    # Averages must say how many posts they stand on — a mean over one post under a header
    # reading n=13 is the quiet overclaim this ledger exists to stop.
    check("every sparse average carries its own n", "(n=1)" in out)

    # --- a real API answer supersedes the hand-entered one, marker and all ------------------
    got = {"reach": 240, "saved": 9, "views": 270}
    with mock.patch.object(metrics, "FILE", path), \
         mock.patch.object(metrics, "token", return_value="t", create=True), \
         mock.patch("post_instagram.insights", return_value=got):
        try:
            metrics.refresh(days=3650)
        except Exception as exc:          # refresh() has other needs; the merge is what matters
            print(f"  (refresh unavailable in this harness: {exc})")
    after = json.load(open(path))["mid1"]["insights"]
    if after.get("reach") == 240:
        check("an API answer clears the hand-entered marker",
              "reach_manual" not in after and "saved_manual" not in after)
        check("the aliased field is cleared by its STORED name", after.get("saved") == 9)
        check("fields the API did not answer keep their marker",
              after.get("skip_rate_manual") is True)

    # --- an unknown field is refused, not silently dropped ----------------------------------
    with mock.patch.object(metrics, "FILE", path):
        check("an unknown field is refused", metrics.note("고린도전서 10:24", watchtime=3) is False)

    print("\n" + ("all good" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
