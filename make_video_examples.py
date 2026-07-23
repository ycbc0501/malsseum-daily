#!/usr/bin/env python3
"""Generate 3 real production-pipeline REEL examples for docs/reels/ — exactly what production does:
generate_checked (image + composition gate) → cover-crop 9:16 → Veo native motion → motion-speed gate
(retry once, else calm still) → unique Lyria hymn → build_reel_native. FORWARD native speed, no boomerang."""
import os
import generate
import fetch_higgsfield as F
import fetch_veo
import fetch_lyria
import make_video
from PIL import Image

OUT = os.path.join(generate.HERE, "docs", "reels")
MOTION_MAX, SKY_MAX = 2.6, 0.7

# (name, theme, var_t, music_idx, ref, text)
JOBS = [
    ("pv_dusk",   "dusk_sky",   4, 5, "시편 4:8",   "내가 평안히 눕고 자기도 하리니 나를 안전히 살게 하시는 이는 오직 여호와시니이다"),
    ("pv_light",  "lighthouse", 8, 2, "요한복음 8:12", "나는 세상의 빛이니 나를 따르는 자는 생명의 빛을 얻으리라"),
    ("pv_forest", "forest_path", 1, 8, "잠언 3:6",  "너는 범사에 그를 인정하라 그리하면 네 길을 지도하시리라"),
]

for name, theme, var_t, midx, ref, text in JOBS:
    idx = [n for n, c in enumerate(F.SCENE_CATS) if c == theme][0]
    print(f"\n=== {name} ({theme}) ===")
    bg = os.path.join(generate.OUT_DIR, f"_pv_{name}.png")
    F.generate_checked(bg, idx, ("center", "middle"), aspect="9:16", var_t=var_t)
    generate.cover_crop(Image.open(bg), *generate.REEL).save(bg, "PNG")

    overlay = os.path.join(generate.OUT_DIR, f"_pvov_{name}.png")
    generate.render_text_overlay({"ref": ref, "text": text}, overlay, canvas=generate.REEL)

    audio = os.path.join(generate.OUT_DIR, f"_pv_{name}.mp3")
    try:
        fetch_lyria.generate(audio, midx)
        print(f"  music: lyria mood {midx}")
    except Exception as e:
        print(f"  lyria failed ({e})")
        audio = None

    out = os.path.join(OUT, f"{name}.mp4")
    clip = os.path.join(generate.OUT_DIR, f"_pv_{name}.mp4")
    ov = sky = 99.0
    for attempt in (1, 2):
        fetch_veo.animate(bg, clip)
        ov, sky = make_video.motion_score(clip)
        print(f"  veo motion attempt {attempt}: overall {ov:.2f}, sky {sky:.2f}")
        if ov <= MOTION_MAX and sky <= SKY_MAX:
            break
    if ov <= MOTION_MAX and sky <= SKY_MAX:
        make_video.build_reel_native(clip, overlay, audio, out)
        print(f"  ✓ {name}: veo native forward | {ref}")
    else:
        make_video.build_reel_still(bg, overlay, audio, out, duration=24)
        print(f"  ✓ {name}: still fallback (motion too fast) | {ref}")
