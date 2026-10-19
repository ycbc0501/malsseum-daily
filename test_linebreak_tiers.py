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
        """하나님의(관형격) · 말씀과(접속조사) · 기도로(부사격→서술어) — 끊을 자리가 전부 금지다.

        찢김에 등급을 둔 건 이 구절 때문이었다. 그런데 절이 하나뿐이고 567px이라 단(734px)에
        들어간다 — 2026-10-19에 「절이 하나면 한 줄」이 되면서 **찢을 일 자체가 없어졌다.**
        등급은 여전히 필요하다(에베소서 6:24는 한 줄에 안 들어가고 여전히 찢어야 한다)."""
        self.assertEqual(lines_of("디모데전서 4:5"), ["하나님의 말씀과 기도로 거룩하여짐이라"])

    def test_the_complement_stays_with_its_verb(self):
        lines = lines_of("잠언 29:6")
        self.assertNotEqual(lines[0].split()[-1], "올무가", lines)


class SenseGroupsFromThePaper(unittest.TestCase):
    """박연옥(2021) 「의미단위 끊어 읽기 10개 기준」 — 계정 주인이 2026-10-16에 지적한 세 건.

    셋 다 같은 원리다: **핵이 바로 이어지면 그 사이에서 끊지 않는다.** 논문의 기준
    4(부사어+용언)·5(목적어+타동사)·6(관형어+체언)·10(보어+되다)이 전부 같은 말이고,
    여기서는 그걸 연결어미와 주어·주제어까지 넓힌 것이다."""

    def test_comparative_closes_the_line(self):
        """「것 같이」 뒤에서 끊는다. 주어 너희도를 앞줄에 떼어 놓지 않는다.

        같이는 양쪽에 용접돼 있었다 — kiwi가 MAG로 읽어 뒤에 붙고, _BIND_LEFT가 앞에
        붙여서, 어느 줄도 같이로 끝내거나 시작할 수 없었다."""
        self.assertEqual(lines_of("요한복음 15:12"),
                         ["내 계명은 곧 내가 너희를 사랑한 것 같이",
                          "너희도 서로 사랑하라 하는 이것이니라"])

    def test_subject_goes_with_its_predicate(self):
        """의인은은 노래하고 기뻐하느니라와 한 줄. 앞 절 꼬리에 붙지 않는다."""
        self.assertEqual(lines_of("잠언 29:6"),
                         ["악인이 범죄하는 것은",
                          "스스로 올무가 되게 하는 것이나",
                          "의인은 노래하고 기뻐하느니라"])

    def test_serial_verbs_are_one_predicate(self):
        """도와 건지시되 · 건져 구원하심은 — 보조적 연결어미 뒤의 용언은 같은 서술이다."""
        self.assertEqual(lines_of("시편 37:40"),
                         ["여호와께서 그들을 도와 건지시되",
                          "악인들에게서 건져 구원하심은",
                          "그를 의지한 까닭이로다"])

    def test_subject_is_not_left_on_the_line_above_its_verb(self):
        """주어 뒤에 서술어가 바로 오면 주어를 윗줄에 떼어 놓지 않는다 (기준 2).

        전수로 16절을 바꾸는 규칙인데, 잠언 29:6은 「것이나」 태그 보정만으로도 맞아서
        그 구절만으로는 이 규칙이 일하는지 알 수 없었다 — 그래서 사례를 따로 둔다."""
        self.assertEqual(lines_of("시편 118:4"),
                         ["이제 여호와를 경외하는 자는 말하기를",
                          "그의 인자하심이 영원하다 할지로다"])

    def test_line_count_comes_from_clause_count(self):
        """줄 수는 절 수에서 나온다 — 절을 가로질러 줄을 아끼지 않는다.

        전에는 한 등급 내려간 경계 하나가 절 경계 두 개와 같은 값이었다(비용이 선형이라
        1×2 = 2×1). 그래서 예레미야 31:17이 세 절인데 「너의 자녀가 │ 자기들의」로 두 줄이
        됐다. 절 경계에서 끊는 건 이제 공짜고, 그 아래는 가파르게 매긴다."""
        self.assertEqual(lines_of("예레미야 31:17"),
                         ["너의 장래에 소망이 있을 것이라",
                          "너의 자녀가 자기들의 지경으로 돌아오리라",
                          "여호와의 말씀이니라"])

    def test_two_lines_when_two_lines_fit(self):
        """거꾸로도 성립한다 — 잠언 13:18은 세 줄이지만 그건 두 줄이 **안 들어가서**다.

        2줄 판(「…궁핍과 수욕이 이르거니와」)은 741px이고 단은 734px다. 7px 차이다.
        단이 넓어지면 이 테스트가 깨지고, 그때는 두 줄이 맞는 답이다."""
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        font = generate.load_font(generate.SERIF, 44)
        two = "훈계를 저버리는 자에게는 궁핍과 수욕이 이르거니와"
        self.assertGreater(generate.text_w(d, two, font), COL_W,
                           "2줄 판이 단에 들어간다 — 그러면 세 줄은 틀렸다")
        self.assertEqual(len(lines_of("잠언 13:18")), 3)

    def test_one_clause_is_one_line(self):
        """절이 하나면 한 줄. 모양을 위해 주제어를 혼자 세우지 않는다.

        옛 기준은 폭 하나였고(단의 0.55) 둘 다 틀렸다 — 사도행전 13:52(503px)를 쪼갰고,
        두 절짜리 시편 81:13(733px)은 단을 가득 채운 한 줄로 둘 뻔했다."""
        self.assertEqual(lines_of("사도행전 13:52"), ["제자들은 기쁨과 성령이 충만하니라"])
        self.assertEqual(len(lines_of("시편 81:13")), 2)

    def test_coordinated_verbs_may_break(self):
        """-며로 대등하게 이어진 용언은 보조 구성이 아니다 — 끊어도 된다.

        「맛보아 알지어다」를 막던 규칙이 연결어미를 가리지 않아서 「떨며 │ 즐거워할지어다」
        까지 막았고, 시편 2:11이 두 절인데 한 줄이 될 뻔했다."""
        self.assertEqual(len(lines_of("시편 2:11")), 2)
        habakkuk = "너희는 여호와의 선하심을 맛보아 알지어다 그에게 피하는 자는 복이 있도다"
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        with contextlib.redirect_stdout(io.StringIO()):
            lines = generate.balanced_split(d, habakkuk,
                                            generate.load_font(generate.SERIF, 44), COL_W)
        self.assertTrue(any("맛보아 알지어다" in ln for ln in lines), lines)

    def test_repeated_imperatives_are_not_chained(self):
        """「찬송하라 찬송하라」는 이어진 서술이 아니다 — kiwi가 명령형 라를 EC로 읽는다."""
        self.assertEqual(lines_of("시편 47:6"),
                         ["찬송하라 하나님을 찬송하라",
                          "찬송하라 우리 왕을 찬송하라"])

    def test_object_stays_with_its_verb(self):
        """기준 5 — 목적어 뒤에 타동사가 바로 오면 그 사이에서 끊지 않는다."""
        bad = []
        for ref, v in VERSES.items():
            lines = lines_of(ref)
            if len(lines) < 2:
                continue
            info = generate._word_endings(v["text"])
            preds = generate._word_is_predicate(v["text"])
            for li in range(len(lines) - 1):
                k = sum(len(x.split()) for x in lines[:li + 1])
                if info and preds and k < len(preds) and info[k - 1][0] == "JKO" and preds[k]:
                    bad.append(ref)
        # 에베소서 6:24는 끊을 자리가 전부 금지다. 두 줄로 들어가는 자리가 「그리스도를 │ 변함」
        # 하나뿐이고 나머지는 맨명사·관형사·변함│없이 — 전부 더 심한 찢김이다. 등급제가
        # 가장 가벼운 쪽을 고른 것이고, 그게 이 구조가 하라고 만든 일이다.
        self.assertEqual(bad, ["에베소서 6:24"],
                         f"목적어와 타동사 사이에서 끊긴 구절이 달라졌다: {bad[:5]}")

    def test_no_break_leaves_a_bare_noun_hanging(self):
        """조사 없는 명사 뒤에서 끊는 것은 동격일 때뿐이다."""
        bare = []
        for ref, v in VERSES.items():
            lines = lines_of(ref)
            if len(lines) < 2:
                continue
            info = generate._word_endings(v["text"])
            for li in range(len(lines) - 1):
                k = sum(len(x.split()) for x in lines[:li + 1])
                if info and k - 1 < len(info) and info[k - 1][0] in ("NNG", "NNP"):
                    bare.append(ref)
        self.assertEqual(bare, [], f"맨명사 뒤에서 끊긴 구절: {bare[:5]}")


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
