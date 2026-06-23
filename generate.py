#!/usr/bin/env python3
"""
말씀 이미지 생성기  —  verse → styled Instagram image (dailymayim/Alabaster style).

Design:
  • soft nature OR solemn photo background, kept bright & natural (no heavy scrim)
  • text placed in the calmest/emptiest region of the photo
  • ADAPTIVE color: dark text on light areas, light text on dark areas
  • small, elegant 명조(serif) type; comma-aware line breaks
  • source reference in *italic*, same serif, smaller, no divider line

Usage:
    python3 generate.py --ref "시편 23:1" --photo photos/x.jpg
    python3 generate.py --all --photos
    python3 generate.py --photos
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

W, H = 1080, 1350
TEXT_W = 720          # text column width (narrow → small, elegant lines like the reference)
COL_LEFT = (W - TEXT_W) // 2


def _resolve_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


SERIF = _resolve_font([
    os.path.join(FONTS_DIR, "NanumMyeongjo-Regular.ttf"),
    "/System/Library/Fonts/AppleMyungjo.ttf",
])

# solid-color fallback themes (used only when no photo is given)
THEMES = {
    "ivory": {"bg": (244, 240, 232), "fg": (54, 48, 42)},
    "ink":   {"bg": (26, 25, 24),    "fg": (236, 230, 220)},
}


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(SERIF, size)


def cover_crop(img):
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - W) // 2
    top = (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


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
    """Wrap a clause into the fewest lines, then even them out (no orphan words)."""
    words = clause.split(" ")
    target = len(_greedy(draw, words, font, max_w))
    if target <= 1:
        return [clause]
    lo, hi, best = 0, max_w, None
    for _ in range(14):  # binary-search the narrowest width that still gives `target` lines
        mid = (lo + hi) / 2
        w = _greedy(draw, words, font, mid)
        if len(w) <= target:
            best, hi = w, mid
        else:
            lo = mid
    return best or _greedy(draw, words, font, max_w)


def lines_for(draw, text, font, max_w):
    """Comma-aware word wrap: break after commas, then balance-wrap each clause."""
    text = " ".join(text.split())
    clauses = [c.strip() for c in re.split(r",", text) if c.strip()]
    clauses = [c + ("," if i < len(clauses) - 1 else "") for i, c in enumerate(clauses)]
    lines = []
    for clause in clauses:
        lines.extend(_wrap_balanced(draw, clause, font, max_w))
    return lines


def fit_verse(draw, text, max_w, max_h):
    """Small, refined serif sized to fit — reference uses delicate type."""
    for size in range(48, 27, -2):
        font = load_font(SERIF, size)
        lines = lines_for(draw, text, font, max_w)
        line_h = int(size * 1.6)
        if all(text_w(draw, ln, font) <= max_w for ln in lines) and len(lines) * line_h <= max_h:
            return font, lines, line_h, size
    font = load_font(SERIF, 28)
    return font, lines_for(draw, text, font, max_w), int(28 * 1.6), 28


# ----- adaptive color & placement ----------------------------------------------

def choose_placement(img, block_h):
    """Find the calmest vertical band for the text block; pick text color by its brightness."""
    gray = img.convert("L")
    sf = 8
    small = gray.resize((W // sf, H // sf))
    cl, cr = COL_LEFT // sf, (COL_LEFT + TEXT_W) // sf
    bh = max(1, block_h // sf)
    top_min, top_max = int(0.10 * H / sf), int((H - block_h) / sf) - int(0.06 * H / sf)
    best = None
    for top in range(top_min, max(top_min + 1, top_max), 2):
        region = small.crop((cl, top, cr, top + bh))
        st = ImageStat.Stat(region)
        busy, mean = st.stddev[0], st.mean[0]
        # prefer calm regions, slight nudge toward vertical center
        center_pen = abs((top + bh / 2) - (H / sf / 2)) * 0.04
        score = busy + center_pen
        if best is None or score < best[0]:
            best = (score, top * sf, mean, busy)
    _, top_full, mean, busy = best
    light_bg = mean > 150
    fg = (44, 40, 36) if light_bg else (250, 248, 244)
    shadow = (255, 255, 255) if light_bg else (0, 0, 0)
    return top_full, fg, shadow, busy


# ----- italic (faux) for the source reference ----------------------------------

def render_italic(text, font, fill):
    """Render text slanted (faux-italic) → RGBA image; Korean serif has no true italic."""
    asc, desc = font.getmetrics()
    h = asc + desc
    shear = 0.20
    pad = int(shear * h) + 8
    tw = int(font.getlength(text))
    base = Image.new("RGBA", (tw + 2 * pad, h), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((pad, 0), text, font=font, fill=fill)
    return base.transform(base.size, Image.AFFINE, (1, shear, 0, 0, 1, 0), resample=Image.BICUBIC)


# ----- compose -----------------------------------------------------------------

def render(verse, theme_name, handle, out_path, photo=None):
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    font, lines, line_h, size = fit_verse(probe, verse["text"], TEXT_W, 560)

    src_font = load_font(SERIF, max(22, int(size * 0.62)))
    src_asc, src_desc = src_font.getmetrics()
    src_h = src_asc + src_desc
    gap = int(line_h * 0.85)
    block_h = len(lines) * line_h + gap + src_h

    if photo:
        base = cover_crop(Image.open(photo)).filter(ImageFilter.GaussianBlur(1.2))
        top_y, fg, shadow_c, busy = choose_placement(base, block_h)
    else:
        theme = THEMES.get(theme_name, THEMES["ivory"])
        base = Image.new("RGB", (W, H), theme["bg"])
        fg = theme["fg"]
        shadow_c = (255, 255, 255) if sum(theme["bg"]) > 380 else (0, 0, 0)
        top_y = (H - block_h) // 2
        busy = 0

    base = base.convert("RGBA")

    # draw all text onto a transparent layer
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    y = top_y
    for ln in lines:
        lw = text_w(td, ln, font)
        td.text(((W - lw) // 2, y), ln, font=font, fill=fg + (255,))
        y += line_h
    # source reference, italic, same serif, smaller, muted — no divider line
    src_fill = tuple(int(c * 0.55 + (255 if fg[0] > 128 else 0) * 0.45) for c in fg)
    src_img = render_italic(verse["ref"], src_font, src_fill + (255,))
    txt.alpha_composite(src_img, ((W - src_img.width) // 2, y + gap - src_h // 4))

    # subtle shadow only as needed for legibility (busy area → a touch more)
    if photo:
        alpha = txt.getchannel("A")
        strength = 0.5 if busy > 16 else 0.3
        shadow = Image.new("RGBA", (W, H), shadow_c + (0,))
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
    ap.add_argument("--handle", default="")
    args = ap.parse_args()

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
        render(v, args.theme, args.handle, out, photo=photo)
        print(f"✓ {v['ref']}" + (f"  [{os.path.basename(photo)}]" if photo else "  [solid]"))


if __name__ == "__main__":
    main()
