#!/usr/bin/env python3
"""
Add a preview image to the scrollable gallery (docs/) — does NOT post to Instagram.
    python3 preview.py --ref "시편 23:1" --scene 1
    python3 preview.py --ref "시편 46:10" --scene 4 --halign left
Newest images appear at the BOTTOM of the page. Pages URL:
    https://ycbc0501.github.io/malsseum-daily/
"""
import argparse
import glob
import json
import os
import re

import generate
import fetch_higgsfield as hf

DOCS = os.path.join(generate.HERE, "docs")
IMG = os.path.join(DOCS, "img")


def next_idx():
    os.makedirs(IMG, exist_ok=True)
    nums = [int(re.match(r"(\d+)", os.path.basename(f)).group(1))
            for f in glob.glob(IMG + "/*.png") if re.match(r"\d+", os.path.basename(f))]
    return (max(nums) + 1) if nums else 1


def build_html():
    files = sorted(glob.glob(IMG + "/*.png"), key=lambda f: os.path.basename(f), reverse=True)
    cards = "\n".join(
        f'<figure><img src="img/{os.path.basename(f)}" loading="lazy">'
        f'<figcaption>{os.path.basename(f)[:-4]}</figcaption></figure>' for f in files)
    html = (
        '<!doctype html><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>빛으로 미리보기</title>'
        '<style>body{margin:0;background:#111;font-family:-apple-system,sans-serif}'
        'h2{color:#eee;padding:14px 12px 4px;margin:0;font-weight:600}'
        'p.sub{color:#888;padding:0 12px 12px;margin:0;font-size:13px}'
        'figure{margin:0 0 26px}img{width:100%;display:block}'
        'figcaption{color:#888;font-size:12px;padding:6px 12px}</style>'
        '<h2>빛으로 · 미리보기</h2><p class="sub">맨 위가 최신 ↑</p>'
        + cards)
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--scene", type=int, default=0)
    ap.add_argument("--halign", default="center")
    ap.add_argument("--valign", default="middle")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--model", default=hf.MODEL)
    a = ap.parse_args()

    verses = json.load(open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8"))["verses"]
    v = next(x for x in verses if x["ref"] == a.ref)

    idx = next_idx()
    bg = f"/tmp/prev_bg_{idx}.png"
    hf.generate_background(bg, a.scene, (a.halign, a.valign), full_scene=a.full, model=a.model)
    out = os.path.join(IMG, f"{idx:04d}-{generate.slug(a.ref)}.png")
    generate.render(v, "ivory", "", out, photo=bg, placement=(a.halign, a.valign))
    build_html()
    print("added", os.path.basename(out))


if __name__ == "__main__":
    main()
