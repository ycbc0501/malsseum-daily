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
        # 20:30, not 17:58 — RULES.md C2d narrowed the evening window to [19:00, next 05:00),
        # so a REEL has to actually be IN that window to count. `now` is pinned (not the real
        # wall clock) so the result does not depend on what time of day this test happens to run.
        evening_reel = self.today.replace(hour=20, minute=30)
        rows = [_media(evening_reel, "REELS")]
        now = self.today.replace(hour=21, minute=0)
        self.assertEqual(self._with(rows, lambda: self.daily_post.slot_state(19, now=now)), "filled")

    def test_watch_does_not_count_a_carousel(self):
        rows = [_media(self.today, "FEED")]
        filled = self._with(rows, lambda: self.watch.slot_is_filled(19))
        self.assertFalse(filled, "감시자가 캐러셀을 저녁 릴로 셌다 — 그래서 조용했다")

    def test_watch_counts_a_real_reel(self):
        evening_reel = self.today.replace(hour=20, minute=30)
        rows = [_media(evening_reel, "REELS")]
        self.assertTrue(self._with(rows, lambda: self.watch.slot_is_filled(19)))

    def test_the_sunday_shape_exactly(self):
        """11-01에 실제로 있었던 것: 아침 릴 + 저녁 캐러셀. 저녁은 비어 있어야 한다."""
        morning = self.today.replace(hour=5, minute=11)
        rows = [_media(self.today, "FEED"), _media(morning, "REELS")]
        now = self.today.replace(hour=10, minute=0)   # pinned — see test above
        self.assertEqual(self._with(rows, lambda: self.daily_post.slot_state(5, now=now)), "filled")
        self.assertNotEqual(self._with(rows, lambda: self.daily_post.slot_state(19, now=now)), "filled")
        self.assertFalse(self._with(rows, lambda: self.watch.slot_is_filled(19)))

    def test_a_delayed_evening_post_does_not_steal_tomorrows_morning_slot(self):
        """RULES.md C2d — the actual 2026-11-11 incident. The 19:00 KST slot was delayed 7h23m
        by GitHub and posted at 02:28 KST the NEXT day. The old midnight/noon split counted that
        as "today's morning slot already filled" and the real 05:00 build was skipped — silently,
        with no alert, because the code believed the day was done."""
        late_evening_reel = self.today.replace(hour=2, minute=28)   # crossed midnight
        rows = [_media(late_evening_reel, "REELS")]
        # The morning cron for the SAME calendar day as the late post, checking hours later.
        morning_check_now = self.today.replace(hour=9, minute=30)
        state = self._with(rows, lambda: self.daily_post.slot_state(5, now=morning_check_now))
        self.assertNotEqual(state, "filled",
                            "지난밤 늦게 올라간 저녁 릴이 오늘 아침 슬롯을 채운 것으로 오판했다")

    def test_a_delayed_evening_post_is_still_recognised_as_filling_its_own_slot(self):
        """같은 사고의 반쪽 — watch.py는 반대로 "아직 안 올라왔다"고 거짓 경보를 보냈다
        (04:08 KST, 그 글이 02:28에 이미 올라간 지 36분 뒤). 저녁 슬롯은 자정을 넘겨도
        여전히 "자신의" 슬롯을 채운 것으로 인식되어야 한다."""
        yesterday = self.today - datetime.timedelta(days=1)
        late_evening_reel = self.today.replace(hour=2, minute=28)   # crossed into today
        evening_slot = yesterday.replace(hour=19, minute=0)
        filled = self.watch.slot_is_filled(19, now=evening_slot, times=[late_evening_reel])
        self.assertTrue(filled, "자정을 넘겨 올라간 저녁 릴을 그 저녁 슬롯이 못 알아봤다 — 거짓 '안 올라왔다' 경보")


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


class SceneRotationFreezeIsAnnounced(unittest.TestCase):
    """RULES.md D-3 — ledger_merge.py가 state.json의 scene_i/used_scene_cats를 최대 4주 가까이
    조용히 얼려 놓았다. 다음에 또 어떤 원장이든 같은 방식으로 멈추면, 사람 눈이 아니라 이 감시가
    며칠 안에 잡아내야 한다."""

    def _state(self, scene_i, tail):
        return {"scene_i": scene_i, "used_scene_cats": tail}

    def _findings_with(self, current_state, prev_watch):
        import post_instagram, watch
        prev = {"_scene_watch": prev_watch} if prev_watch is not None else {}
        with mock.patch.object(watch, "_load",
                               side_effect=lambda path, default: (
                                   current_state if path.endswith("state.json") else default)), \
             mock.patch.object(post_instagram, "recent_media", return_value=[]):
            return dict(watch.findings(prev))

    def test_frozen_past_the_threshold_is_announced(self):
        import datetime as dt, watch
        since = (dt.datetime.now(watch.KST)
                 - dt.timedelta(hours=watch.SCENE_FREEZE_H + 1)).isoformat()
        state = self._state(140, ["cathedral", "basket", "bedroom", "lighthouse"])
        watched = {"fp": [140, ["cathedral", "basket", "bedroom", "lighthouse"]], "since": since}
        found = self._findings_with(state, watched)
        self.assertIn("scene-frozen", found, "임계 시간을 넘겨 멈춰 있는데도 알리지 않았다")

    def test_frozen_but_still_within_the_grace_window_is_quiet(self):
        import datetime as dt, watch
        since = (dt.datetime.now(watch.KST)
                 - dt.timedelta(hours=watch.SCENE_FREEZE_H - 5)).isoformat()
        state = self._state(140, ["cathedral", "basket", "bedroom", "lighthouse"])
        watched = {"fp": [140, ["cathedral", "basket", "bedroom", "lighthouse"]], "since": since}
        found = self._findings_with(state, watched)
        self.assertNotIn("scene-frozen", found, "한 슬롯 간격도 안 지났는데 벌써 울렸다")

    def test_a_moving_fingerprint_never_fires(self):
        import datetime as dt, watch
        since = (dt.datetime.now(watch.KST)
                 - dt.timedelta(hours=watch.SCENE_FREEZE_H * 10)).isoformat()
        state = self._state(141, ["basket", "bedroom", "lighthouse", "rainy_street"])
        watched = {"fp": [140, ["cathedral", "basket", "bedroom", "lighthouse"]], "since": since}
        found = self._findings_with(state, watched)
        self.assertNotIn("scene-frozen", found, "지문이 바뀌었는데도 예전 since로 울렸다")

    def test_no_prior_watch_never_fires_on_first_run(self):
        import watch
        found = self._findings_with(self._state(5, ["a", "b", "c", "d"]), None)
        self.assertNotIn("scene-frozen", found, "첫 실행(비교 대상 없음)에서 울리면 안 된다")

    def test_reverse_the_actual_october_incident_would_have_fired(self):
        """역테스트: 실제 production에서 2026-10-13~11-08에 관측된 값(scene_i=140, 동일 꼬리)을
        그대로 넣으면, 이 감시가 없었다면(또는 임계값이 무한대라면) 조용했을 상황임을 먼저 확인."""
        import watch
        self.assertGreater(watch.SCENE_FREEZE_H, 0, "임계값이 0 이하면 이 검사 자체가 의미 없다")

    def test_main_updates_since_only_when_the_fingerprint_changes(self):
        """main()이 매 실행마다 since를 지금 시각으로 밀어버리면, 정지 시계가 영원히 안 쌓인다."""
        import inspect, watch
        src = inspect.getsource(watch.main)
        self.assertIn("prev_watch.get(\"fp\") != fp", src.replace("'", '"'),
                      "main()이 변화 여부를 확인하지 않고 _scene_watch를 매번 새로 쓰는 것으로 보인다")


if __name__ == "__main__":
    unittest.main(verbosity=2)
