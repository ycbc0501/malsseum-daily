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


def two_line_split(text):
    """Always exactly TWO lines: split at the comma nearest the middle if there is one,
    otherwise at the space nearest the middle."""
    text = " ".join(text.split())
    commas = [i for i, c in enumerate(text) if c in ",，"]
    if commas:
        mid = len(text) / 2
        i = min(commas, key=lambda x: abs(x - mid))
        a, b = text[:i + 1].strip(), text[i + 1:].strip()
    else:
        spaces = [i for i, c in enumerate(text) if c == " "]
        if spaces:
            mid = len(text) / 2
            i = min(spaces, key=lambda x: abs(x - mid))
            a, b = text[:i].strip(), text[i:].strip()
        else:
            a, b = text, ""
    return [x for x in (a, b) if x]


def fit_verse(draw, text, max_w, max_h, max_size):
    """Force the verse onto 2 lines; shrink the font until both lines fit the width."""
    lines = two_line_split(text)
    for size in range(max_size, 17, -2):
        font = load_font(SERIF, size)
        line_h = int(size * 1.6)
        if all(text_w(draw, ln, font) <= max_w for ln in lines) and len(lines) * line_h <= max_h:
            return font, lines, line_h, size
    font = load_font(SERIF, 18)
    return font, lines, int(18 * 1.6), 18


# ----- adaptive color & placement ----------------------------------------------

def band_color(img, top, block_h, cw, col_left, col_w):
    """Pick text color from the brightness of the (centered) text band: dark text on
    light areas, light text on dark areas."""
    gray = img.convert("L")
    region = gray.crop((col_left, max(0, top), col_left + col_w,
                        min(img.height, top + block_h)))
    st = ImageStat.Stat(region)
    mean, busy = st.mean[0], st.stddev[0]
    light_bg = mean > 150
    fg = (44, 40, 36) if light_bg else (250, 248, 244)
    shadow = (255, 255, 255) if light_bg else (0, 0, 0)
    return fg, shadow, busy


def soft_scrim(cw, ch, col_left, col_w, top_y, block_h, line_h, color, alpha=120):
    """A soft, feathered darkening/brightening behind the text block so it stays
    legible over busy backgrounds (no hard box — just a gentle glow)."""
    s = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sx, sy = int(col_w * 0.14), int(line_h * 1.3)
    ImageDraw.Draw(s).ellipse(
        [col_left - sx, top_y - sy, col_left + col_w + sx, top_y + block_h + sy],
        fill=color + (alpha,))
    return s.filter(ImageFilter.GaussianBlur(80))


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

    top_y = (ch - block_h) // 2     # text always vertically centered
    if photo:
        base = cover_crop(Image.open(photo), cw, ch).filter(ImageFilter.GaussianBlur(1.2))
        fg, shadow_c, busy = band_color(base, top_y, block_h, cw, col_left, col_w)
    else:
        theme = THEMES.get(theme_name, THEMES["ivory"])
        base = Image.new("RGB", (cw, ch), theme["bg"])
        fg = theme["fg"]
        shadow_c = (255, 255, 255) if sum(theme["bg"]) > 380 else (0, 0, 0)
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
        base = Image.alpha_composite(base, soft_scrim(cw, ch, col_left, col_w, top_y, block_h, line_h, shadow_c))
        shadow = Image.new("RGBA", (cw, ch), shadow_c + (0,))
        shadow.putalpha(txt.getchannel("A").point(lambda a: int(a * 0.8)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(6))
        base = Image.alpha_composite(base, shadow)

    base = Image.alpha_composite(base, txt)
    base.convert("RGB").save(out_path, "PNG")
    return out_path


def render_overlay(verse, out_path, frame_path, handle="", canvas=REEL):
    """Transparent text overlay (verse + italic source) for compositing over video.
    Color/placement chosen from `frame_path` (a representative frame); a soft shadow
    is baked in so the text stays legible over the moving footage."""
    cw, ch = canvas
    col_w = int(cw * 0.70)
    col_left = (cw - col_w) // 2
    probe = ImageDraw.Draw(Image.new("RGB", (cw, ch)))
    font, lines, line_h, size = fit_verse(probe, verse["text"], col_w, int(ch * 0.34), 52)
    src_font = load_font(SERIF, max(22, int(size * 0.62)))
    src_h = sum(src_font.getmetrics())
    gap = int(line_h * 0.85)
    block_h = len(lines) * line_h + gap + src_h

    frame = cover_crop(Image.open(frame_path), cw, ch)
    top_y = (ch - block_h) // 2
    fg, shadow_c, busy = band_color(frame, top_y, block_h, cw, col_left, col_w)

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

    # soft scrim behind the text → legible even over busy footage
    scrim = soft_scrim(cw, ch, col_left, col_w, top_y, block_h, line_h, shadow_c)
    shadow = Image.new("RGBA", (cw, ch), shadow_c + (0,))
    shadow.putalpha(txt.getchannel("A").point(lambda a: int(a * 0.8)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    out = Image.alpha_composite(scrim, shadow)
    out = Image.alpha_composite(out, txt)
    out.save(out_path, "PNG")
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
