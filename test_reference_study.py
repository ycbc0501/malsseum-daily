#!/usr/bin/env python3
"""The reference-study cadence, comparison and report logic — the parts that don't touch the
network. No test here calls Gemini or Instagram (this repo's convention — see test_catalog.py);
`classify_image`/`try_api_fetch` are exercised live by the workflow, not mocked here.
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta

import fetch_image as hf
import reference_study as rs

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


# ---------------------------------------------------------------------------------------------
# due() / advance() — pure date logic.
# ---------------------------------------------------------------------------------------------
check("a ledger that has never run is due", rs.due({"history": [], "next_due": None}, today="2026-11-04"))
check("a ledger with no next_due key at all is due", rs.due({}, today="2026-11-04"))

ledger = {"next_due": "2026-11-18"}
check("not due the day before next_due", not rs.due(ledger, today="2026-11-17"))
check("due exactly on next_due", rs.due(ledger, today="2026-11-18"))
check("due after next_due", rs.due(ledger, today="2026-11-20"))

advanced = rs.advance({}, today="2026-11-04")
check("advance sets next_due STUDY_INTERVAL_DAYS ahead",
      advanced["next_due"] == (date(2026, 11, 4) + timedelta(days=rs.STUDY_INTERVAL_DAYS)).isoformat())
check("advance records last_run", advanced["last_run"] == "2026-11-04")
# Reverse-test: an interval of 0 must make the NEXT day already due — proves advance() is actually
# driving due(), not two unrelated functions that happen to agree by coincidence.
zero_interval = rs.advance({}, today="2026-11-04", days=0)
check("reverse-test: a 0-day interval is due again the very next day",
      rs.due(zero_interval, today="2026-11-05"))


# ---------------------------------------------------------------------------------------------
# gap_report() — pure comparison, the actual "what's missing" logic.
# ---------------------------------------------------------------------------------------------
ref = ["water"] * 5 + ["sky_mountain"] * 4 + ["room"] * 2 + ["NEW: fireworks at night"] * 2 + ["NEW: piano room"]
our_recent = ["sea", "shore", "bedroom"]   # water x2, room x1 in our own recent rotation

gap = rs.gap_report(ref, our_recent)
check("ref_dist counts every bucket seen in the reference", gap["ref_dist"]["water"] == 5)
check("our_recent_dist is mapped through SCENE_STRUCTURE, not the raw category",
      gap["our_recent_dist"].get("water") == 2 and gap["our_recent_dist"].get("room") == 1)
check("sky_mountain is flagged underused: reference leans on it (4), we used it 0 times recently",
      "sky_mountain" in gap["underused_in_rotation"])
check("water is NOT flagged underused — we used it recently too",
      "water" not in gap["underused_in_rotation"])
check("NEW labels are collected as new-category candidates, not folded into a known bucket",
      set(gap["new_candidates"]) == {"NEW: fireworks at night", "NEW: piano room"})
check("catalog_dist reflects SCENE_STRUCTURE's real bucket set",
      set(gap["catalog_dist"]) == set(hf.SCENE_STRUCTURE.values()))

# Reverse-test: if nothing in the reference repeats (every bucket seen once), nothing should be
# flagged "underused" — the >=2 threshold exists precisely to avoid reading noise as a pattern.
single_ref = ["sky_mountain", "forest", "landmark"]
single_gap = rs.gap_report(single_ref, [])
check("reverse-test: a bucket seen only once in the reference is not flagged underused",
      not single_gap["underused_in_rotation"])


# ---------------------------------------------------------------------------------------------
# write_report() — the markdown actually gets written, with the content it claims to have.
# ---------------------------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp()
try:
    out_path = os.path.join(tmpdir, "2026-11-04.md")
    rs.write_report(["dailymayim"], "manual", gap, today="2026-11-04", path=out_path)
    check("the report file actually exists", os.path.isfile(out_path))
    text = open(out_path, encoding="utf-8").read()
    check("the report names the account studied", "@dailymayim" in text)
    check("the report states the collection mode", "manual" in text)
    check("the report lists the underused bucket", "sky_mountain" in text)
    check("the report lists the new-category candidates", "fireworks at night" in text)
    check("the report explicitly disclaims auto-editing fetch_image.py",
          "자동으로 바꾸지 않습니다" in text)
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# Empty gap must still render something sane (no bare "- " list items, no crash).
empty_gap = rs.gap_report([], [])
tmpdir2 = tempfile.mkdtemp()
try:
    out_path2 = os.path.join(tmpdir2, "empty.md")
    rs.write_report(["dailymayim"], "unavailable", empty_gap, today="2026-11-04", path=out_path2)
    text2 = open(out_path2, encoding="utf-8").read()
    check("an empty gap report still renders a placeholder, not a bare bullet",
          "(없음)" in text2)
finally:
    shutil.rmtree(tmpdir2, ignore_errors=True)


# ---------------------------------------------------------------------------------------------
# record_run() — the ledger actually accumulates history and advances due(), in one call.
#
# ALWAYS pass an explicit tmp `path=` here. record_run()/save_ledger() used to ignore any custom
# `ledger=` dict and write straight to the real reference_study.json regardless — so the first
# time this test file ran (2026-11-04, same day written), it silently clobbered the genuine first
# manual study (5 "NEW:" candidates, real state.json data) with this test's toy fixture the
# moment `verify.sh` ran this file. Caught by noticing the committed ledger didn't match what had
# just been generated. Fixed by threading `path=` through load_ledger/save_ledger/record_run; the
# snapshot/compare below is the regression test for exactly that bug.
# ---------------------------------------------------------------------------------------------
real_ledger_snapshot = (
    open(rs.LEDGER_PATH, "rb").read() if os.path.exists(rs.LEDGER_PATH) else None)

tmp_ledger_dir = tempfile.mkdtemp()
tmp_ledger_path = os.path.join(tmp_ledger_dir, "reference_study.json")
try:
    led = {}
    led = rs.record_run(["dailymayim"], "manual", gap, "notes/reference-study/2026-11-04.md",
                         ledger=led, today="2026-11-04", path=tmp_ledger_path)
    check("record_run appends one history entry", len(led["history"]) == 1)
    check("the history entry carries the mode and accounts",
          led["history"][0]["mode"] == "manual" and led["history"][0]["accounts"] == ["dailymayim"])
    check("record_run advances next_due so the same day is no longer due",
          not rs.due(led, today="2026-11-04"))
    led2 = rs.record_run(["dailymayim"], "manual", gap, "notes/reference-study/2026-11-18.md",
                          ledger=led, today="2026-11-18", path=tmp_ledger_path)
    check("a second run appends rather than replacing the first", len(led2["history"]) == 2)
    check("record_run with an explicit path actually wrote THAT file",
          os.path.exists(tmp_ledger_path)
          and len(json.load(open(tmp_ledger_path, encoding="utf-8"))["history"]) == 2)

    # The regression check itself: a real-ledger-touching bug would show up here as a changed
    # mtime/content on rs.LEDGER_PATH even though every call above named a tmp path explicitly.
    after = open(rs.LEDGER_PATH, "rb").read() if os.path.exists(rs.LEDGER_PATH) else None
    check("reverse-test would catch it: the REAL reference_study.json was not touched by any "
          "record_run() call above that named an explicit tmp path",
          after == real_ledger_snapshot)
finally:
    shutil.rmtree(tmp_ledger_dir, ignore_errors=True)


# ---------------------------------------------------------------------------------------------
# This file must never be able to mutate fetch_image.py — a gap report is a suggestion, the
# actual prompt-pool edit stays a reviewed code change (module docstring's own promise).
# ---------------------------------------------------------------------------------------------
src = open("reference_study.py", encoding="utf-8").read()
check("reference_study.py never opens fetch_image.py for writing",
      not any(tok in src for tok in ('open("fetch_image.py", "w"', "open('fetch_image.py', 'w'",
                                      'fetch_image.py", "a"', "fetch_image.py', 'a'")))


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
