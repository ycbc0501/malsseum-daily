#!/usr/bin/env python3
"""A missed slot should get fixed, not just reported — cron_health.dispatch_workflow() and
watch.auto_retry_missed_slots()/resolve_retries(), the 2026-11-12 fix (RULES.md G-1).

2026-11-12: the 05:00 KST slot sat empty for ~6 hours until a human read the alert and ran
`gh workflow run ... -f force=true` by hand. Measured live the same day: GitHub's own
`schedule:` trigger on daily-post.yml was 270-453min late even with one cron per slot, while a
`workflow_dispatch` fired via the REST API started in ~2 seconds. watch.yml already wakes up
every ~4h to check for exactly this — these tests cover the new code that makes that wake-up
fix the miss instead of only naming it.

A structural review of the first version of this fix (same day) found two real bugs, both
covered below: (1) the dispatch carried no hour, so two slots missed at once would both resolve
to whatever slot owned the clock when the dispatched run executed — at most one was ever really
fixed, while both got permanently marked as retried; (2) a bare network exception (not a clean
(False, reason) return) used to propagate out of dispatch_workflow and crash watch.py's main()
before it could save ANY of this run's alert bookkeeping.

No test here calls the real GitHub API (this repo's convention — see test_cron_health.py):
dispatch_workflow() is exercised by monkeypatching cron_health._gh_post, the one function that
does network I/O; auto_retry_missed_slots()/resolve_retries() are exercised with a fake
`dispatch` callable and plain dicts/sets — no need to touch main()'s real wall clock or STATE
file at all.

    python3 test_auto_retry.py
"""
import sys

import cron_health as ch
import watch

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


print("cron_health.dispatch_workflow()")

# No repo/token configured → fails closed, no network attempted at all.
ok, detail = ch.dispatch_workflow("daily-post.yml", repo=None, token=None)
check("missing repo/token returns ok=False", ok is False)
check("...and says why", "GITHUB_REPOSITORY" in detail or "GITHUB_TOKEN" in detail)

# Happy path: _gh_post is called with the right path/body and nothing raises.
calls = []
real_post = ch._gh_post
ch._gh_post = lambda path, token, body: calls.append((path, token, body))
try:
    ok, detail = ch.dispatch_workflow("daily-post.yml", repo="o/r", token="t")
finally:
    ch._gh_post = real_post
check("success returns ok=True", ok is True)
check("hits the right workflow's dispatches endpoint",
      calls and calls[0][0] == "/repos/o/r/actions/workflows/daily-post.yml/dispatches")
check("carries the token through", calls and calls[0][1] == "t")
check("defaults ref to main, no inputs key when none given", calls and calls[0][2] == {"ref": "main"})

# `inputs` is forwarded, and included in the body only when given — a bug this exact fix closes
# (the first version always dispatched with no hour at all).
calls = []
ch._gh_post = lambda path, token, body: calls.append((path, token, body))
try:
    ch.dispatch_workflow("daily-post.yml", repo="o/r", token="t", inputs={"hour": "19"})
finally:
    ch._gh_post = real_post
check("inputs are carried into the body", calls and calls[0][2] == {"ref": "main", "inputs": {"hour": "19"}})

# A rejected dispatch (e.g. missing actions:write) must surface WHY, not just that it failed —
# this repo's H0 lesson (a dropped error body is a dropped reason) applies here too.
ch._gh_post = lambda path, token, body: (_ for _ in ()).throw(
    RuntimeError("POST ... failed: HTTP 403 Resource not accessible by integration"))
try:
    ok, detail = ch.dispatch_workflow("daily-post.yml", repo="o/r", token="t")
finally:
    ch._gh_post = real_post
check("a rejected dispatch returns ok=False", ok is False)
check("...and the real HTTP reason survives", "403" in detail)

# A structural review (2026-11-12) found a plain network failure (not an HTTPError, so not the
# RuntimeError _gh_post raises for a clean HTTP error) used to propagate straight out of this
# function and crash the caller. dispatch_workflow must never raise, full stop.
class _NetworkIsDown(OSError):
    pass


ch._gh_post = lambda path, token, body: (_ for _ in ()).throw(_NetworkIsDown("Network is unreachable"))
try:
    ok, detail = ch.dispatch_workflow("daily-post.yml", repo="o/r", token="t")
    raised = False
except Exception:
    raised = True
finally:
    ch._gh_post = real_post
check("a non-HTTP network exception does not propagate", raised is False)
check("...and is still reported as a failed attempt", ok is False and "unreachable" in detail)


print("watch.auto_retry_missed_slots()")


def fake_dispatch_ok(workflow_file, hour):
    calls.append((workflow_file, hour))
    return True, "dispatched"


# A missed-slot finding gets exactly one dispatch attempt, and the HOUR is parsed out of the key
# and passed through — not left to daily-post.yml's current-wall-clock fallback.
calls = []
state = {}
found = [("missed-2026-11-12-5", "⚠️ 05:00 게시가 안 올라왔습니다")]
attempts = watch.auto_retry_missed_slots(found, state, dispatch=fake_dispatch_ok)
check("one attempt is made", len(attempts) == 1)
check("it targets daily-post.yml with the parsed hour (int 5, not the string '05')",
      calls == [("daily-post.yml", 5)])
check("the attempt is recorded as (key, ok, detail)",
      attempts[0][0] == "missed-2026-11-12-5" and attempts[0][1] is True)
check("state now remembers this slot was retried",
      state.get(watch.RETRIED_PREFIX + "2026-11-12-5") is True)

# The SAME still-live finding on a later run must not dispatch again.
calls = []
attempts = watch.auto_retry_missed_slots(found, state, dispatch=fake_dispatch_ok)
check("a second call for the same slot does not dispatch again", calls == [])
check("...and reports nothing attempted", attempts == [])

# Findings unrelated to a missed slot (engagement drop, dead posts, cron health) are untouched.
calls = []
state2 = {}
other = [("likes-drop", "좋아요 급락"), ("dead-posts", "반응 없음")]
attempts = watch.auto_retry_missed_slots(other, state2, dispatch=fake_dispatch_ok)
check("non-slot findings never trigger a dispatch", calls == [] and attempts == [])

# THE bug a structural review caught: two different slots missed at once (e.g. a multi-slot
# GitHub outage, this repo's own 08-27 precedent) must each get dispatched with THEIR OWN hour,
# not two identical hour-less calls that can only ever fix one of them.
calls = []
state3 = {}
two = [("missed-2026-11-11-5", "..."), ("missed-2026-11-12-19", "...")]
attempts = watch.auto_retry_missed_slots(two, state3, dispatch=fake_dispatch_ok)
check("two distinct missed slots both get a dispatch attempt", len(attempts) == 2)
check("...and each dispatch names ITS OWN hour, not a shared/absent one",
      sorted(calls) == [("daily-post.yml", 5), ("daily-post.yml", 19)])
check("each has its own retry key",
      state3.get(watch.RETRIED_PREFIX + "2026-11-11-5") is True and
      state3.get(watch.RETRIED_PREFIX + "2026-11-12-19") is True)

# A failed dispatch (e.g. token/permission problem) still only gets ONE attempt, not a retry
# storm — the human alert is what covers a persistently broken path, not this.
def fake_dispatch_fail(workflow_file, hour):
    calls.append((workflow_file, hour))
    return False, "HTTP 403 Resource not accessible by integration"


calls = []
state4 = {}
attempts = watch.auto_retry_missed_slots(found, state4, dispatch=fake_dispatch_fail)
check("a failed attempt is still recorded as tried (no retry storm)",
      state4.get(watch.RETRIED_PREFIX + "2026-11-12-5") is True)
check("...and is reported with ok=False so main() can tell a human",
      attempts and attempts[0][1] is False)
attempts2 = watch.auto_retry_missed_slots(found, state4, dispatch=fake_dispatch_fail)
check("...so a second run does not try again even though it failed", attempts2 == [])

# A `dispatch` that RAISES (rather than returning (False, detail) cleanly) must not crash this
# function either — the exact crash a structural review found could discard a whole run's state.
def fake_dispatch_raises(workflow_file, hour):
    raise OSError("Network is unreachable")


state7 = {}
try:
    attempts7 = watch.auto_retry_missed_slots(found, state7, dispatch=fake_dispatch_raises)
    raised = False
except Exception:
    raised = True
check("a dispatch that raises does not propagate out of auto_retry_missed_slots", raised is False)
check("...and is still recorded as a (failed) attempt, not silently dropped",
      attempts7 and attempts7[0][1] is False)
check("...and the slot is still marked as having had its one attempt",
      state7.get(watch.RETRIED_PREFIX + "2026-11-12-5") is True)


print("watch.resolve_retries()")

# Mirrors resolve_failures()'s role for FAILED_PREFIX: a RETRIED_PREFIX key must survive while
# its missed- finding is still live, and be deleted the run after the slot fills and the finding
# stops appearing. Getting this backwards (deleting it immediately because it is not itself
# "live") was the exact shape of the 2026-11-08 scene_i / 2026-11-10 ledger_merge.errors bugs
# this repo has already hit twice — it would dispatch the same catch-up again every single run.
state5 = {watch.RETRIED_PREFIX + "2026-11-12-5": True, "missed-2026-11-12-5": "2026-11-12"}
watch.resolve_retries(state5, live={"missed-2026-11-12-5"})
check("still-live missed finding keeps its retried- key",
      watch.RETRIED_PREFIX + "2026-11-12-5" in state5)

state6 = {watch.RETRIED_PREFIX + "2026-11-12-5": True}
watch.resolve_retries(state6, live=set())           # the slot filled — no longer live
check("a resolved slot's retried- key is cleaned up, not kept forever",
      watch.RETRIED_PREFIX + "2026-11-12-5" not in state6)

# Keys unrelated to RETRIED_PREFIX must never be touched by this function — it owns exactly one
# prefix, same as resolve_failures() only ever touches FAILED_PREFIX.
state8 = {"_reply_counters": {"sent": 1}, watch.FAILED_PREFIX + "2026-11-12-5": "2026-11-12"}
watch.resolve_retries(state8, live=set())
check("resolve_retries never deletes keys outside RETRIED_PREFIX", state8 == {
    "_reply_counters": {"sent": 1}, watch.FAILED_PREFIX + "2026-11-12-5": "2026-11-12"})


print()
if FAIL:
    print(f"{len(FAIL)} check(s) failed:")
    for name in FAIL:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
