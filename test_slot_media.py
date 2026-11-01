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


if __name__ == "__main__":
    unittest.main(verbosity=2)
