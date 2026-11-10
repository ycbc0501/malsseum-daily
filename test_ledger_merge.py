#!/usr/bin/env python3
"""ledger_merge.py의 일반 규칙(dict: OURS가 이김, list: 합집합, int: max)이 state.json의 두 필드와
충돌한 사고의 재현 + 수정 확인 — RULES.md D-3.

scene_i는 len(SCENES)를 법으로 도는 회전 인덱스라서 "끝없이 증가"가 거짓이고, used_scene_cats는
"최근 4개" 창이라서 "지금까지 쓴 것의 합집합"이 거짓이다. 둘 다 2026-10-13~11-08 production에서
그대로 멈춰 있었다(이 테스트 파일의 숫자는 실제로 그 기간 git 이력에서 읽은 값).

역테스트가 핵심이다: 이 수정이 ledger_merge.py가 애초에 존재하는 이유(동시 쓰기로 원장이
통째로 사라지는 것, 08-26/08-29 중복 게시)를 깨지 않는지 — post_i/used_verses/used_clips 같은
진짜 단조 카운터·누적 집합은 여전히 max()/합집합이어야 한다."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_merge


class SceneCounterWrapDoesNotStickForever(unittest.TestCase):
    """scene_i: 실제 production 사고를 그대로 재현한다.

    140(len(SCENES))에 한 번 닿은 뒤, 로컬이 회전을 계속 돌려 2를 계산해도 원격은 여전히 140을
    들고 있다 — max()라면 140이 영원히 이긴다."""

    def test_the_actual_freeze_is_fixed(self):
        ours = {"scene_i": 2, "used_scene_cats": ["forest_path", "sea", "snowfall"]}
        theirs = {"scene_i": 140, "used_scene_cats": ["cathedral", "basket", "bedroom",
                                                        "lighthouse", "rainy_street",
                                                        "mist_mountain"]}
        merged = ledger_merge.merge(ours, theirs)
        self.assertEqual(merged["scene_i"], 2,
                          "scene_i가 여전히 원격의 옛 천장(140)에 묶여 있다 — 회전이 또 멈춘다")

    def test_reverse_max_would_have_stuck_it(self):
        """역테스트: max()가 실제로 이 값에 적용됐다면 140에서 못 내려온다는 것을 먼저 확인."""
        self.assertEqual(max(2, 140), 140,
                          "이 가정이 깨지면 위 테스트가 애초에 아무것도 증명하지 못한다")

    def test_scene_i_not_special_cased_would_fail(self):
        """scene_i를 OURS_REPLACES_KEYS에서 빼면(원래 코드로 되돌리면) 이 테스트가 실패해야 한다
        — 즉 지금 이 테스트가 실제로 그 수정을 검사하고 있다는 증거."""
        with_old_rule = set(ledger_merge.OURS_REPLACES_KEYS)
        ledger_merge.OURS_REPLACES_KEYS.discard("scene_i")
        try:
            merged = ledger_merge.merge({"scene_i": 2}, {"scene_i": 140})
            self.assertEqual(merged["scene_i"], 140,
                              "scene_i를 빼도 여전히 2가 나온다면 이 테스트가 뭘 보는지 다시 봐야 한다")
        finally:
            ledger_merge.OURS_REPLACES_KEYS.clear()
            ledger_merge.OURS_REPLACES_KEYS.update(with_old_rule)


class UsedSceneCatsWindowIsNotAUnion(unittest.TestCase):
    """used_scene_cats: "최근 4개" 창이 합집합 중복 제거에 깨지는 production 사고를 재현한다."""

    def test_a_repeated_category_is_not_silently_dropped(self):
        ours = {"used_scene_cats": ["basket", "bedroom", "lighthouse", "forest_path"]}
        theirs = {"used_scene_cats": ["sea", "snowfall", "reflection_lake", "cathedral",
                                      "basket", "bedroom", "lighthouse", "rainy_street",
                                      "mist_mountain"]}
        merged = ledger_merge.merge(ours, theirs)
        self.assertEqual(merged["used_scene_cats"], ours["used_scene_cats"],
                          "로컬이 방금 트리밍한 '최근 4개' 창이 원격의 묵은 전체 이력으로 되돌아갔다")

    def test_reverse_union_would_have_dropped_the_repeat(self):
        """역테스트: 합집합(값 중복 제거)이 실제로 적용됐다면 새로 고른 'forest_path'가 원격에 이미
        있을 경우 꼬리 끝에 다시 나타나지 않는다는 것을 먼저 확인."""
        theirs = ["sea", "forest_path", "snowfall"]
        ours = ["basket", "bedroom", "forest_path"]   # forest_path를 오늘 다시 골랐다
        seen = set(theirs)
        out = list(theirs)
        for x in ours:
            if x not in seen:
                seen.add(x)
                out.append(x)
        self.assertNotEqual(out[-1], "forest_path",
                             "이 가정이 깨지면 위 테스트가 애초에 아무것도 증명하지 못한다")


class MonotonicLedgersStillMergeTheOldWay(unittest.TestCase):
    """이 수정이 ledger_merge.py가 존재하는 이유(동시 쓰기로 원장을 통째로 잃는 것)를 깨지
    않는지 확인한다 — scene_i/used_scene_cats가 아닌 모든 것은 그대로 max()/합집합이어야 한다."""

    def test_post_i_still_takes_max(self):
        merged = ledger_merge.merge({"post_i": 298}, {"post_i": 326})
        self.assertEqual(merged["post_i"], 326, "post_i는 진짜 단조 카운터다 — max()가 맞다")

    def test_music_i_still_takes_max(self):
        merged = ledger_merge.merge({"music_i": 5}, {"music_i": 9})
        self.assertEqual(merged["music_i"], 9)

    def test_used_verses_still_unions(self):
        merged = ledger_merge.merge({"used_verses": ["시편 23:1"]},
                                    {"used_verses": ["시편 23:1", "요한복음 3:16"]})
        self.assertEqual(set(merged["used_verses"]), {"시편 23:1", "요한복음 3:16"},
                          "used_verses는 '지금까지 쓴 것'이다 — 합집합이 맞고, 잃으면 중복 게시로 돌아간다")

    def test_used_clips_and_used_photos_still_union(self):
        for key in ("used_clips", "used_photos"):
            merged = ledger_merge.merge({key: ["a.mp4"]}, {key: ["a.mp4", "b.mp4"]})
            self.assertEqual(set(merged[key]), {"a.mp4", "b.mp4"})

    def test_a_concurrent_deleted_row_in_metrics_json_still_survives(self):
        """test_prune.py가 이미 지키는 계약이지만, 여기서도 scene_i 수정이 전혀 다른 파일
        (metrics.json)의 병합 경로를 건드리지 않았다는 것을 한 번 더 확인한다."""
        ours = {"deleted": {"123": {"ref": "잠언 18:10"}}}
        theirs = {}
        merged = ledger_merge.merge(ours, theirs)
        self.assertIn("deleted", merged)
        self.assertIn("123", merged["deleted"])


class StateJsonFullMergeShape(unittest.TestCase):
    """실제 state.json 모양 전체를 한 번에 병합해, 두 수정 키와 나머지 키가 서로를 건드리지
    않는다는 것을 통째로 확인한다."""

    def test_full_state_merge(self):
        ours = {
            "used_verses": ["시편 23:1"], "used_clips": ["a.mp4"], "used_photos": [],
            "music_i": 10, "scene_i": 3, "used_scene_cats": ["sea", "forest_path"],
            "post_i": 300,
        }
        theirs = {
            "used_verses": ["시편 23:1", "요한복음 3:16"], "used_clips": ["a.mp4", "b.mp4"],
            "used_photos": ["p.jpg"], "music_i": 8, "scene_i": 140,
            "used_scene_cats": ["cathedral", "basket", "bedroom", "lighthouse"],
            "post_i": 326,
        }
        merged = ledger_merge.merge(ours, theirs)
        self.assertEqual(merged["scene_i"], 3)
        self.assertEqual(merged["used_scene_cats"], ["sea", "forest_path"])
        self.assertEqual(merged["post_i"], 326)
        self.assertEqual(merged["music_i"], 10)
        self.assertEqual(set(merged["used_verses"]), {"시편 23:1", "요한복음 3:16"})
        self.assertEqual(set(merged["used_photos"]), {"p.jpg"})


class ThisRunsErrorsAreNotImmortal(unittest.TestCase):
    """`errors` in account.json states what THIS run hit. The merge used to make it permanent.

    insights.account() accumulates values across runs on purpose and deliberately does NOT
    accumulate errors — it removes the key when a run has none. But merge() starts from
    `dict(theirs)` and only walks `ours.items()`, so a key ours dropped was never visited and
    the remote copy survived. Live on 2026-11-10 the run printed "0 rejected" while the
    committed ledger still carried the rejection it had just stopped making.
    """

    def test_dropping_errors_removes_them(self):
        ours = {"2026-11-10": {"insights": {"reach": 713}}}
        theirs = {"2026-11-10": {"insights": {"reach": 700},
                                 "errors": {"views|follower_type": "HTTP 400"}}}
        self.assertNotIn("errors", ledger_merge.merge(ours, theirs)["2026-11-10"])

    def test_a_current_error_replaces_rather_than_unions(self):
        # A union would report this morning's fixed rejection next to tonight's real one.
        ours = {"d": {"errors": {"new": "real"}}}
        theirs = {"d": {"errors": {"old": "fixed at lunch"}}}
        self.assertEqual(ledger_merge.merge(ours, theirs)["d"]["errors"], {"new": "real"})

    def test_a_day_ours_never_saw_is_left_alone(self):
        # Deletion applies only where ours rewrote the parent dict. A stale local file must not
        # erase another day's record.
        ours = {"2026-11-09": {"a": 1}}
        theirs = {"2026-11-08": {"errors": {"y": "z"}}}
        self.assertEqual(ledger_merge.merge(ours, theirs)["2026-11-08"],
                         {"errors": {"y": "z"}})

    def test_the_counters_this_file_protects_still_union(self):
        # Reverse guard: OURS_OMITS_DELETES must not leak into the no-repeat ledgers, whose
        # whole job is that a key present remotely is never dropped (08-26/08-29 duplicates).
        ours = {"used_verses": ["a"], "post_i": 3}
        theirs = {"used_verses": ["b"], "post_i": 9}
        got = ledger_merge.merge(ours, theirs)
        self.assertEqual(sorted(got["used_verses"]), ["a", "b"])
        self.assertEqual(got["post_i"], 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
