#!/usr/bin/env python3
"""cron_health.py — the pure staleness/failure logic, and findings()'s composition of it.

No test here calls the real GitHub API (this repo's convention — see test_catalog.py,
test_reference_study.py): evaluate() takes already-fetched JSON so it needs no network at all,
and findings() is exercised by monkeypatching fetch_and_evaluate(), the one function that does.
"""
import sys
from datetime import datetime, timedelta, timezone

import cron_health as ch

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
ENTRY = {"file": "x.yml", "label": "테스트 워크플로", "max_gap_h": 24}


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def run(info_created=None, info_updated=None, last_run_created=None, last_run_conclusion=None,
        now=NOW):
    info = None
    if info_created or info_updated:
        info = {"created_at": info_created, "updated_at": info_updated}
    last_run = None
    if last_run_created:
        last_run = {"created_at": last_run_created, "conclusion": last_run_conclusion,
                    "html_url": "https://example/run"}
    return ch.evaluate(ENTRY, info, last_run, now)


# ---------------------------------------------------------------------------------------------
# evaluate() — staleness.
# ---------------------------------------------------------------------------------------------
ok, detail = run(last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion="success")
check("a run an hour ago, inside the 24h limit, is healthy", ok is True and detail is None)

ok, detail = run(last_run_created=iso(NOW - timedelta(hours=23, minutes=59)),
                  last_run_conclusion="success")
check("a run just under the limit is still healthy (boundary)", ok is True)

ok, detail = run(last_run_created=iso(NOW - timedelta(hours=25)), last_run_conclusion="success")
check("a run just OVER the limit alerts", ok is False and "시간째" in detail)

ok, detail = run(last_run_created=iso(NOW - timedelta(days=30)), last_run_conclusion="success")
check("a run a month ago alerts, not just slightly late", ok is False)

# Reverse-test: proves max_gap_h is actually read, not hardcoded — raising the limit must turn
# the SAME stale gap back into "healthy".
loose_entry = dict(ENTRY, max_gap_h=24 * 40)
ok, _ = ch.evaluate(loose_entry, None, {"created_at": iso(NOW - timedelta(days=30)),
                                        "conclusion": "success"}, NOW)
check("reverse-test: raising max_gap_h un-alerts the same gap", ok is True)

# ---------------------------------------------------------------------------------------------
# evaluate() — "never run yet" must not be mistaken for "dead".
# ---------------------------------------------------------------------------------------------
ok, detail = run(info_created=iso(NOW - timedelta(hours=2)))
check("a workflow registered 2h ago with no run yet is NOT an alert (too new to judge)", ok is True)

ok, detail = run(info_created=iso(NOW - timedelta(days=90)))
check("a workflow registered 90 days ago with STILL no run ever alerts", ok is False)

ok, detail = run()
check("nothing at all to go on (no info, no run) returns None — cannot judge, not healthy",
      ok is None and "판정 불가" in detail)

# ---------------------------------------------------------------------------------------------
# evaluate() — the baseline is the MOST RECENT evidence of life, whichever field it's in.
# ---------------------------------------------------------------------------------------------
ok, _ = run(info_created=iso(NOW - timedelta(days=200)),
            info_updated=iso(NOW - timedelta(hours=1)))       # recently edited, never run
check("a recent updated_at (just edited) counts as evidence of life too", ok is True)

ok, _ = run(info_created=iso(NOW - timedelta(days=200)),
            info_updated=iso(NOW - timedelta(days=200)),
            last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion="success")
check("a recent run outweighs an old registration date", ok is True)

# Regression test for a real bug an independent review caught before this shipped: evaluate()
# used to fold workflow_info's created_at/updated_at into the baseline UNCONDITIONALLY (max of
# everything), so an unrelated same-day edit to the workflow file (bumping updated_at) could mask
# a genuinely dead cron by resetting the staleness clock to "now" — worst on refresh-token.yml,
# the one entry this file calls the most dangerous to miss. last_run must win whenever it exists;
# workflow_info is ONLY the fallback for "never run yet".
ok, detail = run(info_created=iso(NOW - timedelta(days=200)),
                  info_updated=iso(NOW - timedelta(minutes=5)),      # edited moments ago
                  last_run_created=iso(NOW - timedelta(days=30)),    # but hasn't actually FIRED
                  last_run_conclusion="success")
check("reverse-test: a fresh file edit must NOT mask a stale last_run", ok is False and detail)

# ---------------------------------------------------------------------------------------------
# evaluate() — failure of the most recent scheduled run, independent of staleness.
# ---------------------------------------------------------------------------------------------
ok, detail = run(last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion="failure")
check("a recent run that FAILED alerts even though it is not stale",
      ok is False and "실패" in detail and "https://example/run" in detail)

for conclusion in ("cancelled", "timed_out", "action_required"):
    ok, _ = run(last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion=conclusion)
    check(f"conclusion={conclusion!r} is treated as a failure, not silently ok", ok is False)

for conclusion in (None, "success", "skipped"):
    ok, _ = run(last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion=conclusion)
    check(f"conclusion={conclusion!r} is healthy", ok is True)

# Reverse-test: proves the conclusion check is actually wired, not a tautology that always
# returns True regardless of input — flip OK_CONCLUSIONS membership and watch the same input
# change answer.
real_ok = ch.OK_CONCLUSIONS
try:
    ch.OK_CONCLUSIONS = ()      # nothing is acceptable any more
    ok, _ = run(last_run_created=iso(NOW - timedelta(hours=1)), last_run_conclusion="success")
    check("reverse-test: emptying OK_CONCLUSIONS makes even success alert", ok is False)
finally:
    ch.OK_CONCLUSIONS = real_ok


# ---------------------------------------------------------------------------------------------
# findings() — composition, with the network call swapped out.
# ---------------------------------------------------------------------------------------------
def fake_results(mapping):
    def fetch(entry, repo, token, now=None):
        return mapping[entry["file"]]
    return fetch


watchlist = [dict(ENTRY, file="healthy.yml"), dict(ENTRY, file="dead.yml"),
             dict(ENTRY, file="unjudgeable.yml")]

real_fetch = ch.fetch_and_evaluate
try:
    ch.fetch_and_evaluate = fake_results({
        "healthy.yml": (True, None),
        "dead.yml": (False, "12시간째 ..."),
        "unjudgeable.yml": (None, "조회 실패"),
    })
    out = ch.findings(repo="o/r", token="t", watchlist=watchlist)
    keys = {k for k, _ in out}
    check("only the dead workflow produces a finding", keys == {"cron-dead.yml"})
    check("the message names the workflow file to check",
          ".github/workflows/dead.yml" in out[0][1])
    check("a workflow that cannot be judged is NOT reported as an alert",
          "unjudgeable.yml" not in str(out))
finally:
    ch.fetch_and_evaluate = real_fetch

check("findings() with no repo/token configured returns nothing (fails closed, not open)",
      ch.findings(repo=None, token=None) == [])

# evaluate()'s docstring promises ok=None is "reported separately and must never be read as
# fine" — this is that separate report. All-unjudgeable is itself a strong signal (a broken
# GITHUB_TOKEN scope breaks every entry identically, not one at a time), so it must fire
# immediately rather than being swallowed the same way a single unjudgeable entry correctly is.
try:
    ch.fetch_and_evaluate = fake_results({
        "healthy.yml": (None, "조회 실패"),
        "dead.yml": (None, "조회 실패"),
        "unjudgeable.yml": (None, "조회 실패"),
    })
    out = ch.findings(repo="o/r", token="t", watchlist=watchlist)
    check("all-unjudgeable escalates to ONE alert, not silence",
          [k for k, _ in out] == ["cron-health-unreachable"])
finally:
    ch.fetch_and_evaluate = real_fetch

# Reverse-test: proves the escalation path is reachable in the first place — a mapping with at
# least one non-None result must NOT take the all-unjudgeable branch (covered above too, but
# explicit here so a change that makes the branch unconditionally "escalate" is also caught).
try:
    ch.fetch_and_evaluate = fake_results({
        "healthy.yml": (True, None), "dead.yml": (None, "x"), "unjudgeable.yml": (None, "x")})
    out = ch.findings(repo="o/r", token="t", watchlist=watchlist)
    check("reverse-test: even one judged entry suppresses the all-unjudgeable escalation",
          "cron-health-unreachable" not in {k for k, _ in out})
finally:
    ch.fetch_and_evaluate = real_fetch


# ---------------------------------------------------------------------------------------------
# WATCHLIST / DELIBERATELY_UNWATCHED — sanity, enforced structurally by check_rules.py's I-1
# checks against the real .github/workflows/*.yml files; this just guards the data shape.
# ---------------------------------------------------------------------------------------------
check("WATCHLIST and DELIBERATELY_UNWATCHED don't overlap",
      {e["file"] for e in ch.WATCHLIST}.isdisjoint(ch.DELIBERATELY_UNWATCHED))
check("every WATCHLIST entry has a positive max_gap_h",
      all(e["max_gap_h"] > 0 for e in ch.WATCHLIST))
check("every DELIBERATELY_UNWATCHED exclusion has an actual reason, not a blank string",
      all(isinstance(v, str) and len(v) > 10 for v in ch.DELIBERATELY_UNWATCHED.values()))


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall cron_health checks hold")
    sys.exit(1 if FAIL else 0)
