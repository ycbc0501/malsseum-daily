#!/usr/bin/env python3
"""slots.py — the single implementation of which half of the clock each daily slot owns.

RULES.md C2d: a plain midnight/noon split left only 5h of delay margin on the evening side,
and GitHub has delayed this account's crons by 7+ hours (RULES.md I-1). These tests pin the
window definition itself; test_slot_media.py pins the two callers (daily_post.slot_state,
watch.slot_is_filled) that must agree with it.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import slots

KST = slots.KST


def _dt(y, m, d, h, mi=0):
    return datetime.datetime(y, m, d, h, mi, tzinfo=KST)


class WindowTilesTheFullDay(unittest.TestCase):
    def test_morning_window(self):
        lo, hi = slots.window(datetime.date(2026, 11, 11), 5)
        self.assertEqual(lo, _dt(2026, 11, 11, 5))
        self.assertEqual(hi, _dt(2026, 11, 11, 19))

    def test_evening_window_crosses_midnight(self):
        lo, hi = slots.window(datetime.date(2026, 11, 10), 19)
        self.assertEqual(lo, _dt(2026, 11, 10, 19))
        self.assertEqual(hi, _dt(2026, 11, 11, 5))

    def test_unknown_hour_rejected(self):
        with self.assertRaises(ValueError):
            slots.window(datetime.date(2026, 11, 11), 12)

    def test_no_gap_and_no_overlap_across_a_week(self):
        """Every minute of a week belongs to EXACTLY one of the two windows anchored on the
        day containing it or the day before — never zero, never two."""
        day = datetime.date(2026, 11, 1)
        minute = _dt(2026, 11, 1, 0, 0)
        end = _dt(2026, 11, 8, 0, 0)
        step = datetime.timedelta(minutes=37)   # coprime-ish stride, not every exact hour
        while minute < end:
            hits = 0
            for back in (0, 1):
                d = minute.date() - datetime.timedelta(days=back)
                for hour in slots.SLOTS:
                    lo, hi = slots.window(d, hour)
                    if lo <= minute < hi:
                        hits += 1
            self.assertEqual(hits, 1, f"{minute} belongs to {hits} windows, not exactly 1")
            minute += step


class CurrentDayPicksTheMostRecentNominalStart(unittest.TestCase):
    """The 2026-11-11 incident in miniature: a cron fires for TARGET_HOUR=19, but by the time
    it runs, the wall clock has already crossed into the next calendar day. The slot it is
    checking against is still "yesterday's 19:00", not "today's" (today's hasn't happened)."""

    def test_evening_hour_past_midnight_resolves_to_yesterday(self):
        now = _dt(2026, 11, 11, 2, 24)
        self.assertEqual(slots.current_day(19, now), datetime.date(2026, 11, 10))

    def test_evening_hour_after_its_own_nominal_time_resolves_to_today(self):
        now = _dt(2026, 11, 10, 20, 0)
        self.assertEqual(slots.current_day(19, now), datetime.date(2026, 11, 10))

    def test_morning_hour_after_its_own_nominal_time_resolves_to_today(self):
        now = _dt(2026, 11, 11, 9, 30)
        self.assertEqual(slots.current_day(5, now), datetime.date(2026, 11, 11))

    def test_morning_hour_before_its_own_nominal_time_resolves_to_yesterday(self):
        now = _dt(2026, 11, 11, 2, 0)
        self.assertEqual(slots.current_day(5, now), datetime.date(2026, 11, 10))

    def test_defaults_to_the_real_clock_when_now_is_not_given(self):
        # Just must not raise and must return a date near today — the real-clock default is
        # exercised by production callers, not pinned to a value here.
        self.assertIsInstance(slots.current_day(5), datetime.date)


class FilledChecksAnIterableOfTimestamps(unittest.TestCase):
    def test_a_timestamp_inside_the_window_counts(self):
        self.assertTrue(slots.filled(datetime.date(2026, 11, 10), 19, [_dt(2026, 11, 11, 2, 28)]))

    def test_a_timestamp_outside_the_window_does_not(self):
        self.assertFalse(slots.filled(datetime.date(2026, 11, 11), 5, [_dt(2026, 11, 11, 2, 28)]))

    def test_empty_times_is_never_filled(self):
        self.assertFalse(slots.filled(datetime.date(2026, 11, 11), 5, []))

    def test_reverse_the_actual_incident_the_old_way_would_have_disagreed(self):
        """역테스트 — 옛 자정/정오 분할이었다면 이 두 판정이 뒤집혔을 것임을 직접 계산해 확인."""
        post = _dt(2026, 11, 11, 2, 28)

        def old_half_day_filled(day, hour, times):
            lo = datetime.datetime.combine(day, datetime.time(0 if hour < 12 else 12), tzinfo=KST)
            hi = lo + datetime.timedelta(hours=12)
            return any(lo <= t < hi for t in times)

        # Old code: the late post WAS counted as filling the next morning (the bug).
        self.assertTrue(old_half_day_filled(datetime.date(2026, 11, 11), 5, [post]))
        # New code: it is not.
        self.assertFalse(slots.filled(datetime.date(2026, 11, 11), 5, [post]))
        # Old code: the same post was NOT recognised as filling its own (previous day's) evening
        # slot — the false "19:00 게시가 안 올라왔습니다" alert.
        self.assertFalse(old_half_day_filled(datetime.date(2026, 11, 10), 19, [post]))
        # New code: it is.
        self.assertTrue(slots.filled(datetime.date(2026, 11, 10), 19, [post]))


class OwningHourPicksTheSlotThatCoversNow(unittest.TestCase):
    """The 2026-11-11 incident: a manual catch-up run fired at 21:42 KST to fill a delayed
    19:00 slot, but the workflow hard-coded TARGET_HOUR=5 for every manual dispatch — so it
    checked the MORNING slot (already filled), reported "already posted", and exited without
    ever looking at the real gap. owning_hour() must answer 19 here, not 5."""

    def test_reproduces_the_actual_incident(self):
        now = _dt(2026, 11, 11, 21, 42)
        self.assertEqual(slots.owning_hour(now), 19)

    def test_just_after_morning_slot_start(self):
        self.assertEqual(slots.owning_hour(_dt(2026, 11, 11, 5, 0)), 5)

    def test_just_before_morning_slot_start(self):
        self.assertEqual(slots.owning_hour(_dt(2026, 11, 11, 4, 59)), 19)

    def test_just_after_evening_slot_start(self):
        self.assertEqual(slots.owning_hour(_dt(2026, 11, 11, 19, 0)), 19)

    def test_just_before_evening_slot_start(self):
        self.assertEqual(slots.owning_hour(_dt(2026, 11, 11, 18, 59)), 5)

    def test_past_midnight_still_belongs_to_the_evening_slot(self):
        self.assertEqual(slots.owning_hour(_dt(2026, 11, 11, 2, 24)), 19)

    def test_every_minute_of_a_week_resolves_to_exactly_one_hour(self):
        """Reverse of the no-gap-no-overlap window test: owning_hour must never raise and must
        always agree with slots.filled() for a single timestamp."""
        minute = _dt(2026, 11, 1, 0, 0)
        end = _dt(2026, 11, 8, 0, 0)
        step = datetime.timedelta(minutes=37)
        while minute < end:
            hour = slots.owning_hour(minute)
            self.assertIn(hour, slots.SLOTS)
            self.assertTrue(slots.filled(slots.current_day(hour, minute), hour, [minute]))
            minute += step

    def test_defaults_to_the_real_clock_when_now_is_not_given(self):
        self.assertIn(slots.owning_hour(), slots.SLOTS)

    def test_reverse_hard_coded_five_would_have_failed_the_incident(self):
        """역테스트 — 고치기 전 하드코딩(TARGET_HOUR=5)이었다면 이 사건에서 뭘 답했을지 그대로
        계산해, owning_hour()가 그와 다르다는 것을 직접 확인."""
        now = _dt(2026, 11, 11, 21, 42)
        hard_coded = 5
        self.assertNotEqual(slots.owning_hour(now), hard_coded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
