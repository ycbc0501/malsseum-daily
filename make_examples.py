#!/usr/bin/env python3
"""Generate preview examples for docs/reels/ — demonstrates the new theme diversity AND the
same-theme light/angle variation. Each: generate_checked (with composition gate) → cover-crop to
9:16 → composite the centred verse overlay → save PNG."""
import os
from PIL import Image
import generate
import fetch_higgsfield as F

OUT = os.path.join(generate.HERE, "docs", "reels")
os.makedirs(OUT, exist_ok=True)

# (filename, scene_index, var_t, ref, text)
# scene_index: variant-0 position of each theme in the round-robin SCENES list.
SETS = [
    # ── DIVERSITY: six different themes, each its own light/angle ──
    ("dv_wheat",  5,  3, "시편 126:5", "눈물을 흘리며 씨를 뿌리는 자는 기쁨으로 거두리로다"),
    ("dv_wild",   11, 1, "시편 18:2",  "여호와는 나의 반석이시요 나의 요새시요 나를 건지시는 이시라"),
    ("dv_stars",  16, 0, "시편 19:1",  "하늘이 하나님의 영광을 선포하고 궁창이 그의 손으로 하신 일을 나타내는도다"),
    ("dv_church", 2,  4, "시편 46:1",  "하나님은 우리의 피난처시요 힘이시니 환난 중에 만날 큰 도움이시라"),
    ("dv_light",  7,  8, "요한복음 8:12", "나는 세상의 빛이니 나를 따르는 자는 생명의 빛을 얻으리라"),
    ("dv_river",  13, 2, "시편 23:2",  "그가 나를 푸른 풀밭에 누이시며 쉴 만한 물 가으로 인도하시는도다"),
    # ── VARIATION: the SAME theme (sea) three ways — different light + angle each time ──
    ("var_sea1",  0,  0, "이사야 43:2", "네가 물 가운데로 지날 때에 내가 너와 함께 할 것이라"),      # cold blue-grey, wide
    ("var_sea2",  0,  18, "시편 46:10", "너희는 가만히 있어 내가 하나님 됨을 알지어다"),               # warm low-golden, intimate
    ("var_sea3",  0,  14, "시편 93:4",  "많은 물 소리와 바다의 큰 파도보다 높이 계신 여호와는 능력이 크시도다"),  # dim near-dark, high
]

for name, idx, t, ref, text in SETS:
    bg = os.path.join(generate.OUT_DIR, f"_ex_{name}.png")
    F.generate_checked(bg, idx, ("center", "middle"), aspect="9:16", var_t=t)
    base = generate.cover_crop(Image.open(bg), *generate.REEL).convert("RGBA")
    ov = os.path.join(generate.OUT_DIR, f"_exov_{name}.png")
    generate.render_text_overlay({"ref": ref, "text": text}, ov, canvas=generate.REEL)
    base = Image.alpha_composite(base, Image.open(ov).convert("RGBA"))
    dest = os.path.join(OUT, f"{name}.png")
    base.convert("RGB").save(dest, "PNG")
    light = F.LIGHT[t % len(F.LIGHT)]
    print(f"✓ {name}: theme={F.SCENE_CATS[idx]} | {light} | {ref}")
