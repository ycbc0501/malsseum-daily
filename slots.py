"""Single source of truth for the two daily post slots (05:00 / 19:00 KST) and which part of
the clock each one owns when asking "did this slot already post".

2026-11-11: `daily_post.slot_state()` and `watch.slot_is_filled()` answered that question with
the SAME half-day arithmetic, written twice — split at midnight/noon, whichever half the slot's
hour falls in. That boundary choice is the bug. The 19:00 KST evening slot on 11/10 was delayed
7h23m by GitHub (ordinary — see RULES.md I-1) and actually posted at 02:28 KST on 11/11. Midnight
sits only 5 hours after 19:00, so the delayed post landed PAST the boundary, in what the old code
called "11/11's morning half":

    daily_post.slot_state(5)    saw a REEL in [00:00, 12:00) today → "morning slot already
                                 posted" → the real 05:00 build skipped. No post, no alert.
    watch.slot_is_filled(19)    checked [12:00 yesterday, 00:00 today) → the post was NOT in
                                 that window → "19:00 게시가 안 올라왔습니다" sent at 04:08 KST,
                                 36 minutes after that exact post had already gone out.

One bug, two opposite wrong answers: silence on the real miss, a false alarm on the fake one.
Both functions were asking "which calendar half-day is `when` in", when the real question is
"which SLOT built this". A slot owns the clock from its OWN nominal time up to the other slot's
next one, not a fixed midnight/noon split — mirroring how the two crons actually alternate:

    05:00 slot owns [05:00, 19:00) the same day   — 14h of delay margin before it's ambiguous
    19:00 slot owns [19:00, 05:00 next day)        — 10h of delay margin

Together the two windows tile the full 24h with no gap and no overlap, so any timestamp belongs
to exactly one slot. Both margins are comfortably above every delay this repo has measured
(worst seen: 7h23m), where the old midnight/noon split left as little as 5h on the evening side.
"""
import datetime

KST = datetime.timezone(datetime.timedelta(hours=9))
SLOTS = (5, 19)


def window(day, hour):
    """[lo, hi) KST datetimes that the `hour` slot (05 or 19) on `day` owns."""
    if hour not in SLOTS:
        raise ValueError(f"not a known slot hour: {hour}")
    other = SLOTS[1] if hour == SLOTS[0] else SLOTS[0]
    lo = datetime.datetime.combine(day, datetime.time(hour), tzinfo=KST)
    hi_day = day + datetime.timedelta(days=1) if hour == SLOTS[1] else day
    hi = datetime.datetime.combine(hi_day, datetime.time(other), tzinfo=KST)
    return lo, hi


def current_day(hour, now=None):
    """Which calendar day's `hour` slot is the one in effect right now -- the slot whose own
    nominal start time (`hour`:00 KST) is the most recent one at or before `now`.

    Needed by any caller that does not already have an explicit day to check (daily_post.py's
    slot_already_filled() takes only an hour): a cron that fires very late can have its process
    wall-clock already past midnight, so "today" at call time is not necessarily the day this
    run's slot belongs to. The 19:00 KST slot delayed to 02:24 KST the next day is still that
    slot — its own 19:00 start was yesterday, which is "the most recent `hour`:00 at or before
    now", not today's (today's 19:00 has not happened yet)."""
    now = now.astimezone(KST) if now else datetime.datetime.now(KST)
    today = now.date()
    nominal_today = datetime.datetime.combine(today, datetime.time(hour), tzinfo=KST)
    return today if nominal_today <= now else today - datetime.timedelta(days=1)


def filled(day, hour, times):
    """Is there a timestamp in `times` (any iterable of tz-aware datetimes) inside this slot's
    window? `times` is the caller's own list (e.g. recent REELS only) — this module knows nothing
    about Instagram or media types, only the clock."""
    lo, hi = window(day, hour)
    return any(lo <= t.astimezone(KST) < hi for t in times)
