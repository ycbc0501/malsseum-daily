"""자간(TRACK)과 장평(WIDTH) — RULES.md F-2b.

이 파일이 지키는 것은 두 가지다.
  ① 694절 전부가 44px 두 줄 안에 들어간다 ("글자 크기는 하나입니다").
  ② 재는 코드와 그리는 코드가 같은 두 숫자를 읽는다.
②가 깨지면 ①은 거짓말이 된다 — 분줄기는 "두 줄"이라 재고 캔버스는 세 줄로 그린다.
2026-10-16 이전이 정확히 그 상태였다(렌더러에 자간이 없는데 측정만 자간을 가정).
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
VERSES = json.load(open(os.path.join(HERE, "verses.json")))["verses"]
# 0.85 was wrong and it mattered: the reel sets type in 0.68 of the frame, and measuring the
# corpus against the wider feed column reported "every verse fits at full size" while 34 were
# shrinking in the posts that actually shipped. Ask generate.py for the column, never retype it.
COL_W = generate.verse_col_w(generate.REEL)


def _fit(text):
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    with contextlib.redirect_stdout(io.StringIO()):
        return generate.fit_verse(d, text, COL_W, 44)


class Settings(unittest.TestCase):
    def test_the_chosen_numbers_are_in_place(self):
        self.assertEqual(generate.TRACK, -0.05)
        self.assertEqual(generate.WIDTH, 0.80)

    def test_tracking_is_active(self):
        self.assertTrue(generate._tracked())


class EveryVerseAtFullSize(unittest.TestCase):
    """① — 하나도 빠짐없이. 한 개라도 작아지면 "한 크기"가 아니다."""

    def test_no_verse_shrinks(self):
        small = [v["ref"] for v in VERSES if _fit(v["text"])[3] != 44]
        self.assertEqual(small, [], f"{len(small)}절이 44px 아래로 내려갔다: {small[:5]}")

    def test_no_verse_needs_a_fourth_line(self):
        """세 줄까지는 같은 크기로 간다 — 네 줄은 블록이 아니라 문단이 된다."""
        long = [v["ref"] for v in VERSES if len(_fit(v["text"])[1]) > 3]
        self.assertEqual(long, [], f"{len(long)}절이 네 줄이 됐다: {long[:5]}")

    def test_most_verses_still_come_out_in_two(self):
        """세 줄은 예외여야 한다. 흔해지면 조판이 아니라 압축 실패다."""
        three = sum(1 for v in VERSES if len(_fit(v["text"])[1]) == 3)
        self.assertLess(three, 70, f"{three}절이 세 줄 — 10%를 넘었다")

    def test_text_cannot_be_cut_off_by_the_frame(self):
        """단이 꽉 차도 화면에서 잘리지는 않는다 — 단은 화면의 68%다.

        「글자가 잘린다」는 이 프로젝트가 실제로 겪은 고장이라 숫자로 박아 둔다. 가장 넓은
        줄조차 좌우에 프레임이 한참 남는다. 단을 거의 채우는 줄이 있는 것 자체는 정상이고,
        2026-10-19에 단을 99%로 줄여 봤지만 절벽이 옮겨갈 뿐이었다."""
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        widest = max(generate.text_w(d, ln, _fit(v["text"])[0])
                     for v in VERSES for ln in _fit(v["text"])[1])
        side = (generate.REEL[0] - widest) / 2
        self.assertGreater(side, 100,
                           f"가장 넓은 줄 {widest:.0f}px, 좌우 여백 {side:.0f}px")

    def test_every_line_fits_the_column(self):
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        over = []
        for v in VERSES:
            font, lines, _lh, _size = _fit(v["text"])
            for ln in lines:
                if generate.text_w(d, ln, font) > COL_W:
                    over.append(v["ref"])
                    break
        self.assertEqual(over, [], f"{len(over)}절이 단을 넘쳤다: {over[:5]}")


class WidthIsComputableNotJustMeasurable(unittest.TestCase):
    """RULES.md F-4-A — 한 줄에 몇 글자가 들어가는지 정확히 안다.

    나눔명조에서 한글은 전부 42.00px 고정이라 폭이 계산된다. 이 식이 렌더러와 어긋나면
    RULES.md에 적힌 「21~22자」가 거짓말이 되므로, 숫자가 아니라 이 테스트가 먼저 깨진다."""

    HANGUL = 42.0
    SPACE = 12.0

    def _predict(self, s, font):
        raw = 0.0
        for ch in s:
            if "가" <= ch <= "힣":
                raw += self.HANGUL
            elif ch == " ":
                raw += self.SPACE
            else:
                raw += font.getlength(ch)
        return (raw + (len(s) - 1) * generate.TRACK * font.size) * generate.WIDTH

    def test_every_hangul_syllable_is_the_same_width(self):
        font = generate.load_font(generate.SERIF, 44)
        widths = {font.getlength(ch) for v in VERSES for ch in v["text"] if "가" <= ch <= "힣"}
        self.assertEqual(widths, {self.HANGUL}, f"한글 폭이 하나가 아니다: {sorted(widths)}")
        self.assertEqual(font.getlength(" "), self.SPACE)

    def test_the_formula_matches_the_renderer_on_every_line(self):
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        off = []
        for v in VERSES:
            font, lines, _lh, _size = _fit(v["text"])
            for ln in lines:
                if abs(self._predict(ln, font) - generate.text_w(d, ln, font)) > 0.01:
                    off.append((v["ref"], ln))
        self.assertEqual(off, [], f"{len(off)}줄에서 식이 렌더러와 어긋났다: {off[:3]}")

    def test_the_documented_capacity_holds(self):
        """RULES.md가 적어 둔 21~22자가 실제 상한인가."""
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        longest = max(sum(1 for ch in ln if "가" <= ch <= "힣")
                      for v in VERSES for ln in _fit(v["text"])[1])
        self.assertEqual(longest, 22, f"원장의 최대 한글 글자 수가 {longest}자로 바뀌었다")
        font = generate.load_font(generate.SERIF, 44)
        # 5어절 22자가 단을 꽉 채운다 — 한 자 더 넣으면 넘친다.
        self.assertLessEqual(self._predict("가" * 18 + " 가 가 가 가", font), COL_W)
        self.assertGreater(self._predict("가" * 19 + " 가 가 가 가", font), COL_W)


class MeasuringMatchesDrawing(unittest.TestCase):
    """② — text_w()가 내놓는 폭과 draw_text()가 칠하는 폭이 같아야 한다."""

    SAMPLES = ["이제는 주 안에서 빛이라 빛의 자녀들처럼 행하라",
               "여호와는 나의 목자시니",
               "주의 날개 그늘 아래에 피하나이다"]

    def _painted_width(self, s, font):
        img = Image.new("RGBA", (2400, 300), (0, 0, 0, 0))
        generate.draw_text(img, (20, 20), s, font, (255, 255, 255, 255))
        box = img.getbbox()
        return box[2] - box[0]

    def test_the_gap_is_side_bearings_and_does_not_grow(self):
        """잰 폭은 자폭, 그린 폭은 잉크 범위다 — 마지막 글자의 사이드베어링만큼 늘 짧다.

        그 차이는 글자 수와 무관한 상수여야 한다. 그리는 쪽이 재는 쪽과 다른
        TRACK/WIDTH를 쓰면 차이가 길이에 **비례해서** 벌어지고, 그때 이 테스트가 잡는다."""
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        font = generate.load_font(generate.SERIF, 44)
        gaps = []
        for s in self.SAMPLES:
            measured = generate.text_w(d, s, font)
            painted = self._painted_width(s, font)
            self.assertGreater(measured, painted, f"{s!r}: 그린 게 잰 것보다 넓다")
            gaps.append(measured - painted)
        self.assertLess(max(gaps), 44, f"차이가 한 글자를 넘는다: {gaps}")
        self.assertLess(max(gaps) - min(gaps), 0.5 * 44,
                        f"차이가 길이에 따라 벌어진다 = 재는 쪽과 그리는 쪽이 갈렸다: {gaps}")

    def test_tracking_actually_narrows_what_is_drawn(self):
        """렌더러가 TRACK/WIDTH를 무시하면(= 2026-10-16 이전) 이 테스트가 잡는다."""
        font = generate.load_font(generate.SERIF, 44)
        tight = self._painted_width(self.SAMPLES[0], font)
        track, width = generate.TRACK, generate.WIDTH
        try:
            generate.TRACK, generate.WIDTH = 0.0, 1.0
            loose = self._painted_width(self.SAMPLES[0], font)
        finally:
            generate.TRACK, generate.WIDTH = track, width
        self.assertLess(tight, loose * 0.85,
                        f"눌린 폭 {tight} 이 안 눌린 폭 {loose} 보다 충분히 좁지 않다")


class DefaultsFallThrough(unittest.TestCase):
    """기본값에서는 PIL 경로 그대로 — 조판 기계가 평소 출력을 바꾸지 않는다."""

    def test_untracked_matches_pil_exactly(self):
        track, width = generate.TRACK, generate.WIDTH
        font = generate.load_font(generate.SERIF, 44)
        s = "여호와는 나의 목자시니"
        try:
            generate.TRACK, generate.WIDTH = 0.0, 1.0
            self.assertFalse(generate._tracked())
            mine = Image.new("RGBA", (900, 200), (0, 0, 0, 0))
            generate.draw_text(mine, (10, 10), s, font, (255, 255, 255, 255))
            pil = Image.new("RGBA", (900, 200), (0, 0, 0, 0))
            ImageDraw.Draw(pil).text((10, 10), s, font=font, fill=(255, 255, 255, 255))
            self.assertEqual(list(mine.getdata()), list(pil.getdata()))
            d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
            self.assertEqual(generate.text_w(d, s, font), d.textlength(s, font=font))
        finally:
            generate.TRACK, generate.WIDTH = track, width


if __name__ == "__main__":
    unittest.main(verbosity=2)
