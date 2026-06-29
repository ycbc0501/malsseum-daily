#!/usr/bin/env python3
"""
Build a 3-slide carousel for a verse:
  1) the verse card (photo background, like the daily post)
  2) a short reflection (묵상) — theme-based
  3) a short prayer (기도) — theme-based
Reflection/prayer text is ORIGINAL and chosen by the verse's theme.
"""

import os
from PIL import Image, ImageDraw
import generate

IVORY = (244, 240, 232)
INK = (54, 48, 42)
MUTED = (150, 140, 125)

REFLECT = {
    "위로": "지치고 무거운 오늘, 주님은 당신의 마음을 누구보다 잘 아십니다.",
    "평안": "염려를 내려놓을 때, 마음 깊은 곳에 참된 평안이 찾아옵니다.",
    "담대": "두려움 앞에서도, 함께하시는 주님이 우리를 담대하게 하십니다.",
    "믿음": "보이지 않아도 신뢰할 때, 믿음은 가장 단단한 힘이 됩니다.",
    "감사": "작은 일상 속에서도 감사를 발견하는 하루가 되기를.",
    "사랑": "받은 사랑을 기억하며, 오늘 한 사람을 더 사랑해 보아요.",
    "인도": "내 계획보다 크신 그분의 인도하심을 믿고 한 걸음 내딛어요.",
    "은혜": "자격이 아니라 은혜로, 우리는 날마다 새롭게 살아갑니다.",
    "지혜": "말씀 앞에 잠시 멈추어, 오늘 필요한 지혜를 구해 보아요.",
}
PRAYER = {
    "위로": "주님, 무거운 마음을 주께 맡깁니다. 따뜻한 평안으로 채워 주세요.",
    "평안": "주님, 모든 염려를 내려놓습니다. 흔들리지 않는 평안을 주세요.",
    "담대": "주님, 두려움 대신 담대함을 주세요. 함께하심을 믿습니다.",
    "믿음": "주님, 흔들릴 때에도 변함없이 주를 신뢰하게 하소서.",
    "감사": "주님, 오늘 누리는 모든 것에 감사드립니다.",
    "사랑": "주님, 받은 사랑으로 이웃을 사랑하게 하소서.",
    "인도": "주님, 제 길을 주께 맡깁니다. 선한 길로 인도하여 주세요.",
    "은혜": "주님, 날마다 새로운 은혜로 살아가게 하소서.",
    "지혜": "주님, 말씀 안에서 참된 지혜를 얻게 하소서.",
}


def render_text_slide(out_path, body, header=""):
    cw, ch = generate.FEED
    img = Image.new("RGBA", (cw, ch), IVORY + (255,))
    d = ImageDraw.Draw(img)
    col_w = int(cw * 0.78)
    font = generate.load_font(generate.SERIF, 46)
    line_h = int(46 * 1.6)
    lines = generate.lines_for(d, body, font, col_w)
    block_h = len(lines) * line_h
    top = (ch - block_h) // 2
    for ln in lines:
        w = generate.text_w(d, ln, font)
        d.text(((cw - w) // 2, top), ln, font=font, fill=INK)
        top += line_h
    if header:
        hf = generate.load_font(generate.SERIF, 30)
        hi = generate.render_italic(header, hf, MUTED + (255,))
        hy = (ch - block_h) // 2 - int(line_h * 1.4)
        img.alpha_composite(hi, ((cw - hi.width) // 2, hy))
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def build_slides(verse, photo, prefix):
    """Return [slide1, slide2, slide3] image paths for `verse` (uses its theme)."""
    theme = verse.get("theme", "믿음")
    s1, s2, s3 = prefix + "-1.png", prefix + "-2.png", prefix + "-3.png"
    generate.render(verse, "ivory", "", s1, photo=photo, canvas=generate.FEED)
    render_text_slide(s2, REFLECT.get(theme, REFLECT["믿음"]), header="묵상")
    render_text_slide(s3, PRAYER.get(theme, PRAYER["믿음"]), header="오늘의 기도")
    # flow: 묵상(마음) → 말씀(치유) → 기도
    return [s2, s1, s3]
