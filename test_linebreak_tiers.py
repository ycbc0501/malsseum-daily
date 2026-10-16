"""찢는 데도 경중이 있다 — RULES.md F-4a/4b/4c.

끊을 자리가 전부 금지인 구절이 있다. 그때 금지 점수가 전부 같으면 다음 기준인 길이
균형이 고르고, 균형은 가장 나쁜 자리를 골랐다. 여기 실린 구절들은 전부 2026-10-16에
원장에서 실제로 저렇게 나오던 것들이다 — 고른 예가 아니라 **발견된 결함**이다.
"""
import io
import json
import contextlib
import os
import sys
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate

HERE = os.path.dirname(os.path.abspath(__file__))
VERSES = {v["ref"]: v for v in json.load(open(os.path.join(HERE, "verses.json")))["verses"]}
COL_W = generate.verse_col_w(generate.REEL)


def lines_of(ref):
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    with contextlib.redirect_stdout(io.StringIO()):
        return generate.fit_verse(d, VERSES[ref]["text"], COL_W, 44)[1]


class NeverSplitOneWord(unittest.TestCase):
    """TEAR_WORD — 두 단어가 사실 한 단어인 자리. 독자에게는 줄바꿈이 아니라 오타로 읽힌다."""

    # (구절, 앞줄이 끝나면 안 되는 말, 뒷줄이 시작하면 안 되는 말)
    CASES = [
        ("전도서 7:19", "열", "명의"),              # 수사 → 단위명사
        ("에베소서 4:3", "하나", "되게"),
        ("누가복음 6:36", "자비로우심", "같이"),      # 비교 접미
        ("요한복음 15:12", "것", "같이"),
        ("에베소서 6:24", "변함", "없이"),           # 변함없이 = 한 단어
        ("시편 93:4", "물", "소리와"),               # 물소리
        ("사도행전 28:31", "예수", "그리스도에"),
        ("데살로니가전서 5:18", "그리스도", "예수"),
        ("디모데전서 1:14", "그리스도", "예수"),
        ("시편 119:14", "주의", "증거들의"),
    ]

    def test_none_of_these_words_are_split(self):
        for ref, tail, head in self.CASES:
            with self.subTest(ref=ref):
                lines = lines_of(ref)
                for a, b in zip(lines, lines[1:]):
                    self.assertFalse(
                        a.split()[-1] == tail and b.split()[0] == head,
                        f"{ref}: '{tail} │ {head}' 로 찢겼다 — {lines}")


class ForcedChoiceTakesTheMildestTear(unittest.TestCase):
    """끊을 자리가 전부 금지일 때, 가장 가벼운 찢김을 고른다."""

    def test_the_conjoined_pair_survives(self):
        # 하나님의(관형격) · 말씀과(접속조사) · 기도로(부사격→서술어) — 셋 다 금지.
        # 접속쌍을 쪼개는 것보다 구를 서술어에서 떼는 쪽이 가볍다.
        lines = lines_of("디모데전서 4:5")
        self.assertEqual(lines, ["하나님의 말씀과 기도로", "거룩하여짐이라"], lines)

    def test_the_complement_stays_with_its_verb(self):
        lines = lines_of("잠언 29:6")
        self.assertNotEqual(lines[0].split()[-1], "올무가", lines)


class BoundNounsClosePhrases(unittest.TestCase):
    """F-4c — 대로·것·바·줄은 앞의 관형절을 닫는다. 붙이는 말로 보면 멀쩡한 자리가 나빠진다."""

    def test_daero_ends_the_line(self):
        for ref in ("시편 33:22", "누가복음 2:29"):
            with self.subTest(ref=ref):
                self.assertEqual(lines_of(ref)[0].split()[-1], "대로", lines_of(ref))


class TheCorpusDoesNotPayForIt(unittest.TestCase):
    """문법을 얻자고 크기를 팔지 않았다 — 694절 전부 44px 두 줄 그대로."""

    def test_every_verse_still_fits_at_full_size(self):
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        bad = []
        for ref, v in VERSES.items():
            with contextlib.redirect_stdout(io.StringIO()):
                _f, lines, _lh, size = generate.fit_verse(d, v["text"], COL_W, 44)
            if size != 44 or len(lines) > 3:
                bad.append(ref)
        self.assertEqual(bad, [], f"{len(bad)}절이 크기나 줄수를 잃었다: {bad[:5]}")

    def test_almost_every_break_is_at_a_verb_ending_or_a_particle(self):
        """맨명사 뒤에서 끊는 것은 동격일 때뿐이어야 한다 — 전수로 한 자릿수."""
        bare = 0
        for ref, v in VERSES.items():
            lines = lines_of(ref)
            if len(lines) < 2:
                continue
            info = generate._word_endings(v["text"])
            k = len(lines[0].split())
            if info and k - 1 < len(info) and info[k - 1][0] in ("NNG", "NNP"):
                bare += 1
        self.assertLessEqual(bare, 5, f"맨명사 뒤에서 끊은 구절이 {bare}개")


if __name__ == "__main__":
    unittest.main(verbosity=2)
