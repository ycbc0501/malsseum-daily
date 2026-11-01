#!/usr/bin/env python3
"""주간 캐러셀은 일일 슬롯을 채우지 않는다 — RULES.md C4f.

2026-11-01(일) 저녁 릴이 안 올라갔다. 아무것도 실패하지 않았고 알림도 없었다.
주간 캐러셀의 일요일 크론이 ~7시간 밀려 17:58 KST에 올라갔고, 「이 반나절에 뭔가
올라왔나」를 묻던 두 함수가 **종류를 가리지 않아서** 둘 다 "찼다"고 답했다.
daily_post는 서고, watch는 조용했다. 10-18 · 10-25 · 11-01 — 캐러셀이 생긴 뒤
**모든 일요일**이 그랬다.

구분자는 명확하다: 일일 릴 `media_product_type == "REELS"`, 주간 캐러셀 `"FEED"`.
"""
import datetime
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KST = datetime.timezone(datetime.timedelta(hours=9))


def _media(stamp_kst, product_type):
    """Instagram 응답 한 건. timestamp는 API와 같이 UTC로 돌려준다."""
    utc = stamp_kst.astimezone(datetime.timezone.utc)
    return {"id": "1", "permalink": "https://example.test/p/1",
            "timestamp": utc.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "media_product_type": product_type, "caption": "[시편 23:1] …"}


class CarouselDoesNotFillTheDailySlot(unittest.TestCase):
    def setUp(self):
        import daily_post
        import watch
        self.daily_post, self.watch = daily_post, watch
        self.today = datetime.datetime.now(KST).replace(hour=17, minute=58,
                                                        second=0, microsecond=0)

    def _with(self, rows, fn):
        import post_instagram
        with mock.patch.object(post_instagram, "recent_media", return_value=rows):
            return fn()

    def test_daily_post_stands_up_when_only_a_carousel_is_there(self):
        rows = [_media(self.today, "FEED")]
        state = self._with(rows, lambda: self.daily_post.slot_state(19))
        self.assertNotEqual(state, "filled",
                            "캐러셀 하나로 저녁 릴 슬롯이 찼다고 판단했다")

    def test_daily_post_still_sees_a_real_reel(self):
        rows = [_media(self.today, "REELS")]
        self.assertEqual(self._with(rows, lambda: self.daily_post.slot_state(19)), "filled")

    def test_watch_does_not_count_a_carousel(self):
        rows = [_media(self.today, "FEED")]
        filled = self._with(rows, lambda: self.watch.slot_is_filled(19))
        self.assertFalse(filled, "감시자가 캐러셀을 저녁 릴로 셌다 — 그래서 조용했다")

    def test_watch_counts_a_real_reel(self):
        rows = [_media(self.today, "REELS")]
        self.assertTrue(self._with(rows, lambda: self.watch.slot_is_filled(19)))

    def test_the_sunday_shape_exactly(self):
        """11-01에 실제로 있었던 것: 아침 릴 + 저녁 캐러셀. 저녁은 비어 있어야 한다."""
        morning = self.today.replace(hour=5, minute=11)
        rows = [_media(self.today, "FEED"), _media(morning, "REELS")]
        self.assertEqual(self._with(rows, lambda: self.daily_post.slot_state(5)), "filled")
        self.assertNotEqual(self._with(rows, lambda: self.daily_post.slot_state(19)), "filled")
        self.assertFalse(self._with(rows, lambda: self.watch.slot_is_filled(19)))


class MotionLossIsAnnounced(unittest.TestCase):
    """움직임이 조용히 사라지는 것 — 2026-10-23~31에 15건이 그렇게 나갔다.

    구글이 Veo 모델을 예고 없이 내렸고 모든 호출이 404로 정지 화면 폴백에 떨어졌다.
    아무것도 실패하지 않았으므로 아무 경보도 없었고, 8일 뒤 계정 주인이 눈으로 발견했다."""

    def _ledger(self, segments_newest_first):
        import datetime as dt
        base = dt.datetime(2026, 10, 31, 5, 0)
        return {str(i): {"published": (base - dt.timedelta(hours=12 * i)).isoformat(),
                         "segments": seg}
                for i, seg in enumerate(segments_newest_first)}

    def _run(self, segments_newest_first):
        import watch
        with mock.patch.object(watch, "_load",
                               return_value=self._ledger(segments_newest_first)):
            return watch.still_run()

    def _gate_run(self, passed_newest_first):
        import datetime as dt, watch
        base = dt.datetime(2026, 10, 31, 5, 0)
        led = {str(i): {"published": (base - dt.timedelta(hours=12 * i)).isoformat(),
                        "gate_passed": p}
               for i, p in enumerate(passed_newest_first)}
        with mock.patch.object(watch, "_load", return_value=led):
            return watch.unchecked_run()

    def test_a_rejected_picture_shipping_three_times_is_announced(self):
        import watch
        self.assertGreaterEqual(self._gate_run([False, False, False, True]),
                                watch.MOTION_DEAD_RUN)

    def test_one_rejected_picture_is_not_news(self):
        import watch
        self.assertLess(self._gate_run([False, True, True]), watch.MOTION_DEAD_RUN)

    def test_the_two_counters_do_not_share_a_field(self):
        """같은 질문을 두 번 구현하지 않는다 — 한 헬퍼에 필드만 다르다."""
        import watch, inspect
        src = inspect.getsource(watch)
        self.assertEqual(src.count("def _tail_run"), 1)
        self.assertIn('_tail_run("segments", 0)', src)
        self.assertIn('_tail_run("gate_passed", False)', src)

    def test_a_single_fallback_is_not_news(self):
        import watch
        self.assertLess(self._run([0, 1, 1, 1]), watch.MOTION_DEAD_RUN)

    def test_a_run_of_fallbacks_is(self):
        import watch
        self.assertGreaterEqual(self._run([0, 0, 0, 1, 1]), watch.MOTION_DEAD_RUN)

    def test_the_october_outage_would_have_been_caught(self):
        import watch
        self.assertGreaterEqual(self._run([0] * 15 + [1]), watch.MOTION_DEAD_RUN)

    def test_motion_returning_clears_it(self):
        self.assertEqual(self._run([1, 0, 0, 0, 0]), 0)

    def test_posts_without_the_field_do_not_count_as_motion_loss(self):
        """segments 가 없는 옛 글은 0으로 **추측하지 않는다** — 세지 않고 멈춘다."""
        import datetime as dt, watch
        led = {"a": {"published": "2026-10-20T05:00:00", "likes": 3},
               "b": {"published": "2026-10-21T05:00:00", "segments": 1}}
        with mock.patch.object(watch, "_load", return_value=led):
            self.assertEqual(watch.still_run(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
