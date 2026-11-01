#!/usr/bin/env python3
"""글자가 실제로 가운데 있는가 — 계산이 아니라 **칠해진 픽셀**로 잰다. RULES.md F-2d.

2026-10-25 · 11-01 주간 캐러셀 세 장이 전부 오른쪽으로 77~91px 밀려 나갔고 계정 주인이
지웠다. 원인은 한 줄이다 — `carousel.py` 가 폭은 `generate.text_w`(자간·장평 적용)로 재고
그리기는 `d.text`(미적용)로 했다. **잰 폭이 그린 폭의 0.8배**라 가운데 계산이 그만큼 틀렸다.

어떤 단위 테스트도 이걸 못 잡았다. 둘 다 "정상 동작"이고 어긋남은 **합성 결과에만** 있다.
그래서 이 파일은 실제로 렌더해서 잉크의 좌우 여백을 센다.
"""
import os
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carousel
import generate

OUT = os.environ.get("CENTERING_OUT", "/tmp")
TOL = 12          # 사이드베어링 비대칭의 한계. 고치기 전은 155~182px이었다.


def ink_margins(path):
    """좌우 여백(px). 어두운 픽셀이 있는 열의 양 끝으로 센다."""
    a = np.array(Image.open(path).convert("L"))
    cols = np.where((a < 150).any(axis=0))[0]
    return int(cols.min()), int(a.shape[1] - 1 - cols.max())


class CarouselSlidesAreCentred(unittest.TestCase):
    def _slide(self, name, body, header):
        path = os.path.join(OUT, f"_centering_{name}.png")
        carousel.render_text_slide(path, body, header=header)
        return path

    def test_every_reflection_is_centred(self):
        worst = []
        for theme, body in carousel.REFLECT.items():
            left, right = ink_margins(self._slide(f"r_{theme}", body, "묵상"))
            if abs(left - right) > TOL:
                worst.append((theme, left, right))
        self.assertEqual(worst, [], f"묵상 슬라이드가 가운데가 아니다: {worst[:3]}")

    def test_every_prayer_is_centred(self):
        worst = []
        for theme, body in carousel.PRAYER.items():
            left, right = ink_margins(self._slide(f"p_{theme}", body, "오늘의 기도"))
            if abs(left - right) > TOL:
                worst.append((theme, left, right))
        self.assertEqual(worst, [], f"기도 슬라이드가 가운데가 아니다: {worst[:3]}")

    def test_the_header_is_centred_too(self):
        """레이아웃 수식을 여기 베끼지 않는다 — 머리말 있는 장과 없는 장의 **차이**가 머리말이다."""
        with_h = np.array(Image.open(self._slide("hdr", carousel.REFLECT["지혜"],
                                                 "오늘의 기도")).convert("L")).astype(int)
        without = np.array(Image.open(self._slide("nohdr", carousel.REFLECT["지혜"],
                                                  "")).convert("L")).astype(int)
        diff = np.abs(with_h - without) > 12
        cols = np.where(diff.any(axis=0))[0]
        self.assertGreater(cols.size, 0, "머리말이 아예 안 그려졌다")
        left, right = int(cols.min()), int(with_h.shape[1] - 1 - cols.max())
        self.assertLessEqual(abs(left - right), TOL, f"머리말 좌 {left} 우 {right}")


class MeasuringAndDrawingCannotBeMixed(unittest.TestCase):
    """정적으로도 막는다 — text_w 로 재고 PIL 로 그리는 조합이 다시 생기지 않게."""

    def test_no_module_measures_with_text_w_and_draws_with_pil(self):
        here = os.path.dirname(os.path.abspath(__file__))
        bad = []
        for name in sorted(os.listdir(here)):
            if not name.endswith(".py") or name in ("generate.py",) or name.startswith("test_"):
                continue
            src = open(os.path.join(here, name), encoding="utf-8").read()
            if "text_w(" not in src:
                continue
            for i, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # d.text(...) / draw.text(...) — PIL 직접 그리기
                if ".text(" in stripped and "draw_text" not in stripped \
                        and "text_w" not in stripped and "getlength" not in stripped:
                    bad.append(f"{name}:{i}")
        self.assertEqual(bad, [],
                         "text_w 로 재면서 PIL 로 그리는 곳이 있다 — "
                         f"generate.draw_text 를 써야 한다: {bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
