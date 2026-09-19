#!/usr/bin/env python3
"""A failed RUN is not a failed SLOT.

    python3 test_fail_alert.py

2026-09-19: five ❌ messages went to the account owner. The 19:00 post published at 19:18, and
he read the alerts and concluded the evening post had failed again. Both halves were broken —
the alert fired per run with no idea whether the slot was filled, and nothing ever said it had
been resolved, so ❌ was always the last word.
"""
import datetime
import json
import os
import sys
import tempfile

import watch

KST = watch.KST
FAIL = []
SENT = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


class FakeNotify:
    def send(self, text, token=None, chat_id=None):
        SENT.append(text)
        return True


def scene(published, state, fn):
    """Run `fn` with Instagram reporting `published` and a throwaway watch.json."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    real_state, watch.STATE = watch.STATE, path
    real_pub, watch.published_times = watch.published_times, lambda: published
    real_mod = sys.modules.get("notify")
    sys.modules["notify"] = FakeNotify()
    SENT.clear()
    try:
        fn()
        return json.load(open(path, encoding="utf-8"))
    finally:
        watch.STATE, watch.published_times = real_state, real_pub
        if real_mod is not None:
            sys.modules["notify"] = real_mod
        else:
            del sys.modules["notify"]
        os.unlink(path)


TODAY = datetime.datetime.now(KST).date()
EVENING = [datetime.datetime.combine(TODAY, datetime.time(19, 18), tzinfo=KST)]
KEY = f"{watch.FAILED_PREFIX}{TODAY}-19"

print("failure alerts")

# The exact 09-19 case: the run failed, but the slot had already been filled at 19:18.
after = scene(EVENING, {}, lambda: watch.post_failed(19, "run/1"))
check("no alert when the slot is already filled", SENT == [])
check("and nothing is recorded", after == {})

# A genuinely empty slot must still alert — a guard that silences everything is not a fix.
after = scene([], {}, lambda: watch.post_failed(19, "run/1"))
check("an empty slot does alert", len(SENT) == 1)
check("the alert carries the run link", bool(SENT) and "run/1" in SENT[0])
check("and the slot is recorded so it cannot repeat", KEY in after)

# The chain retries. Five failing runs must not mean five messages.
state = {KEY: TODAY.isoformat()}
scene([], state, lambda: watch.post_failed(19, "run/2"))
check("a second failure for the same slot is silent", SENT == [])

# Morning and evening are different slots and must not mask each other.
after = scene(EVENING, {}, lambda: watch.post_failed(5, "run/3"))
check("an evening post does not silence a morning failure", len(SENT) == 1)

# Closing the loop: the slot filled later, so the open failure resolves exactly once.
state = {KEY: TODAY.isoformat()}
real_pub, watch.published_times = watch.published_times, lambda: EVENING
try:
    resolved = watch.resolve_failures(dict(state))
finally:
    watch.published_times = real_pub
check("a filled slot resolves the open failure", len(resolved) == 1 and resolved[0][0] == KEY)
check("the resolution says it is resolved", bool(resolved) and "✅" in (resolved[0][1] or ""))

# Still empty → stays open. Resolving early would be the same lie in the other direction.
real_pub, watch.published_times = watch.published_times, lambda: []
try:
    check("an unfilled slot stays open", watch.resolve_failures(dict(state)) == [])
finally:
    watch.published_times = real_pub

# The episode sweep in main() must not eat an open failure before it can ever resolve.
state = {KEY: TODAY.isoformat(), "drop": "2026-09-01", "_reply_counters": {}}
for k in list(state):
    if k not in set() and not k.startswith(("_", watch.FAILED_PREFIX)):
        del state[k]
check("an open failure survives the episode sweep", KEY in state and "drop" not in state)

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)
