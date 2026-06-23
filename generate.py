#!/usr/bin/env python3
"""
말씀 이미지 생성기  —  verse → styled image (dailymayim/Alabaster style).

Supports two canvas sizes:
  • feed  : 1080×1350 (4:5)
  • reel  : 1080×1920 (9:16, full-screen, for Reels with music)

Design: bright natural photo, text in the calmest region, ADAPTIVE color
(dark text on light areas / light on dark), small serif, comma-aware balanced
wrap, italic source reference, no divider, no handle.

Usage:
    python3 generate.py --ref "시편 23:1" --photo photos/x.jpg          # feed 4:5
    python3 generate.py --ref "시편 23:1" --photo photos/x.jpg --reel    # 9:16
    python3 generate.py --all --photos --reel
"""

import argparse
import glob
import json
import os
import re
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output")
PHOTO_DIR = os.path.join(HERE, "photos")
FONTS_DIR = os.path.join(HERE, "fonts")

FEED = (1080, 1350)
REEL = (1080, 1920)


def _resolve_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


SERIF = _resolve_font([
    os.path.join(FONTS_DIR, "NanumMyeongjo-Regular.ttf"),
    "/System/Library/Fonts/AppleMyungjo.ttf",
])

THEMES = {
    "ivory": {"bg": (244, 240, 232), "fg": (54, 48, 42)},
    "ink":   {"bg": (26, 25, 24),    "fg": (236, 230, 220)},
}


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(SERIF, size)


def cover_crop(img, cw, ch):
    img = img.convert("RGB")
    scale = max(cw / img.width, ch / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - cw) // 2
    top = (img.height - ch) // 2
    return img.crop((left, top, left + cw, top + ch))


# ----- text layout -------------------------------------------------------------

def text_w(draw, s, font):
    return draw.textlength(s, font=font)


def _greedy(draw, words, font, max_w):
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _wrap_balanced(draw, clause, font, max_w):
    words = clause.split(" ")
    target = len(_greedy(draw, words, font, max_w))
    if target <= 1:
        return [clause]
    lo, hi, best = 0, max_w, None
    for _ in range(14):
        mid = (lo + hi) / 2
        w = _greedy(draw, words, font, mid)
        if len(w) <= target:
            best, hi = w, mid
        else:
            lo = mid
    return best or _greedy(draw, words, font, max_w)


def lines_for(draw, text, font, max_w):
    text = " ".join(text.split())
    clauses = [c.strip() for c in re.split(r",", text) if c.strip()]
    clauses = [c + ("," if i < len(clauses) - 1 else "") for i, c in enumerate(clauses)]
    lines = []
    for clause in clauses:
        lines.extend(_wrap_balanced(draw, clause, font, max_w))
    return lines


def fit_verse(draw, text, max_w, max_h, max_size):
    for size in range(max_size, 27, -2):
        font = load_font(SERIF, size)
        lines = lines_for(draw, text, font, max_w)
        line_h = int(size * 1.6)
        if all(text_w(draw, ln, font) <= max_w for ln in lines) and len(lines) * line_h <= max_h:
            return font, lines, line_h, size
    font = load_font(SERIF, 28)
    return font, lines_for(draw, text, font, max_w), int(28 * 1.6), 28


# ----- adaptive color & placement ----------------------------------------------

def choose_placement(img, block_h, cw, ch, col_left, col_w):
    gray = img.convert("L")
    sf = 8
    small = gray.resize((cw // sf, ch // sf))
    cl, cr = col_left // sf, (col_left + col_w) // sf
    bh = max(1, block_h // sf)
    top_min = int(0.10 * ch / sf)
    top_max = int((ch - block_h) / sf) - int(0.06 * ch / sf)
    best = None
    for top in range(top_min, max(top_min + 1, top_max), 2):
        region = small.crop((cl, top, cr, top + bh))
        st = ImageStat.Stat(region)
        busy, mean = st.stddev[0], st.mean[0]
        center_pen = abs((top + bh / 2) - (ch / sf / 2)) * 0.04
        score = busy + center_pen
        if best is None or score < best[0]:
            best = (score, top * sf, mean, busy)
    _, top_full, mean, busy = best
    light_bg = mean > 150
    fg = (44, 40, 36) if light_bg else (250, 248, 244)
    shadow = (255, 255, 255) if light_bg else (0, 0, 0)
    return top_full, fg, shadow, busy


def render_italic(text, font, fill):
    asc, desc = font.getmetrics()
    h = asc + desc
    shear = 0.20
    pad = int(shear * h) + 8
    tw = int(font.getlength(text))
    base = Image.new("RGBA", (tw + 2 * pad, h), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((pad, 0), text, font=font, fill=fill)
    return base.transform(base.size, Image.AFFINE, (1, shear, 0, 0, 1, 0), resample=Image.BICUBIC)


# ----- compose -----------------------------------------------------------------

def render(verse, theme_name, handle, out_path, photo=None, canvas=FEED):
    cw, ch = canvas
    col_w = int(cw * (0.70 if canvas == REEL else 0.67))
    col_left = (cw - col_w) // 2
    max_size = 52 if canvas == REEL else 48
    max_text_h = int(ch * (0.34 if canvas == REEL else 0.42))

    probe = ImageDraw.Draw(Image.new("RGB", (cw, ch)))
    font, lines, line_h, size = fit_verse(probe, verse["text"], col_w, max_text_h, max_size)

    src_font = load_font(SERIF, max(22, int(size * 0.62)))
    src_asc, src_desc = src_font.getmetrics()
    src_h = src_asc + src_desc
    gap = int(line_h * 0.85)
    block_h = len(lines) * line_h + gap + src_h

    if photo:
        base = cover_crop(Image.open(photo), cw, ch).filter(ImageFilter.GaussianBlur(1.2))
        top_y, fg, shadow_c, busy = choose_placement(base, block_h, cw, ch, col_left, col_w)
    else:
        theme = THEMES.get(theme_name, THEMES["ivory"])
        base = Image.new("RGB", (cw, ch), theme["bg"])
        fg = theme["fg"]
        shadow_c = (255, 255, 255) if sum(theme["bg"]) > 380 else (0, 0, 0)
        top_y = (ch - block_h) // 2
        busy = 0

    base = base.convert("RGBA")
    txt = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    y = top_y
    for ln in lines:
        lw = text_w(td, ln, font)
        td.text(((cw - lw) // 2, y), ln, font=font, fill=fg + (255,))
        y += line_h
    src_fill = tuple(int(c * 0.55 + (255 if fg[0] > 128 else 0) * 0.45) for c in fg)
    src_img = render_italic(verse["ref"], src_font, src_fill + (255,))
    txt.alpha_composite(src_img, ((cw - src_img.width) // 2, y + gap - src_h // 4))

    if photo:
        alpha = txt.getchannel("A")
        strength = 0.5 if busy > 16 else 0.3
        shadow = Image.new("RGBA", (cw, ch), shadow_c + (0,))
        shadow.putalpha(alpha.point(lambda a: int(a * strength)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(5))
        base = Image.alpha_composite(base, shadow)

    base = Image.alpha_composite(base, txt)
    base.convert("RGB").save(out_path, "PNG")
    return out_path


# ----- cli ---------------------------------------------------------------------

def slug(ref):
    return ref.replace(" ", "_").replace(":", "-")


def pick_photos():
    return sorted(f for f in glob.glob(os.path.join(PHOTO_DIR, "*"))
                  if f.lower().endswith((".jpg", ".jpeg", ".png")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ref")
    ap.add_argument("--theme", default="ivory", choices=list(THEMES))
    ap.add_argument("--photo")
    ap.add_argument("--photos", action="store_true")
    ap.add_argument("--reel", action="store_true", help="9:16 canvas (for Reels)")
    ap.add_argument("--handle", default="")
    args = ap.parse_args()

    canvas = REEL if args.reel else FEED
    with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    verses = data["verses"]
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.all:
        targets = verses
    elif args.ref:
        targets = [v for v in verses if v["ref"] == args.ref]
        if not targets:
            raise SystemExit(f"verse not found: {args.ref}")
    else:
        targets = [verses[date.today().toordinal() % len(verses)]]

    pool = pick_photos()
    for i, v in enumerate(targets):
        photo = args.photo or (pool[i % len(pool)] if (args.photos and pool) else None)
        out = os.path.join(OUT_DIR, f"{slug(v['ref'])}.png")
        render(v, args.theme, args.handle, out, photo=photo, canvas=canvas)
        print(f"✓ {v['ref']}" + (f"  [{os.path.basename(photo)}]" if photo else "  [solid]"))


if __name__ == "__main__":
    main()
