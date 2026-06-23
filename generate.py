#!/usr/bin/env python3
"""
말씀 이미지 생성기  —  verse → styled Instagram image.

Reads verses.json, renders a clean, Alabaster/dailymayim-style 1080×1350 PNG
for each verse into output/. Supports solid muted themes OR soft nature photo
backgrounds (flowers, sunsets, meadows...) with a legibility scrim + soft text shadow.

Usage:
    python3 generate.py                      # today's verse (rotates by date)
    python3 generate.py --all                # render every verse
    python3 generate.py --ref "시편 23:1"      # one specific verse
    python3 generate.py --theme ink          # ivory | ink | sage | clay | mist | stone
    python3 generate.py --compare "시편 23:1"  # one verse across all solid themes
    python3 generate.py --photo photos/x.jpg # render over a specific photo
    python3 generate.py --photos             # auto-pick a random photo from photos/ per verse
    python3 generate.py --handle @daily.malsseum
"""

import argparse
import glob
import json
import os
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output")
PHOTO_DIR = os.path.join(HERE, "photos")

SERIF = "/System/Library/Fonts/AppleMyungjo.ttf"
SANS = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

W, H = 1080, 1350
MARGIN = 135

THEMES = {
    "ivory": {"top": (247, 243, 235), "bot": (240, 234, 222), "fg": (44, 40, 35),  "muted": (160, 148, 130)},
    "ink":   {"top": (33, 32, 30),    "bot": (22, 21, 20),    "fg": (236, 230, 220), "muted": (140, 132, 120)},
    "sage":  {"top": (221, 225, 213), "bot": (209, 215, 201), "fg": (46, 52, 42),   "muted": (120, 130, 106)},
    "clay":  {"top": (227, 211, 199), "bot": (216, 197, 183), "fg": (66, 48, 40),   "muted": (160, 128, 110)},
    "mist":  {"top": (217, 223, 227), "bot": (203, 211, 217), "fg": (40, 48, 54),   "muted": (122, 136, 144)},
    "stone": {"top": (225, 220, 211), "bot": (213, 207, 196), "fg": (54, 49, 42),   "muted": (150, 140, 126)},
}

# text colors when over a photo
PHOTO_FG = (252, 250, 246)
PHOTO_MUTED = (244, 240, 233)


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(SERIF, size)


def solid_bg(theme):
    """Vertical gradient + faint grain for tactile depth."""
    top, bot = theme["top"], theme["bot"]
    img = Image.new("RGB", (W, H), top)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        px_row = (round(top[0] + (bot[0] - top[0]) * t),
                  round(top[1] + (bot[1] - top[1]) * t),
                  round(top[2] + (bot[2] - top[2]) * t))
        for x in range(W):
            px[x, y] = px_row
    grain = Image.effect_noise((W, H), 14).convert("RGB")
    return Image.blend(img, grain, 0.035)


def photo_bg(path):
    """Cover-crop a photo to WxH, soft dreamy blur, gentle scrim for legibility."""
    img = Image.open(path).convert("RGB")
    # cover-crop
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - W) // 2
    top = (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))
    # soft, dreamy
    img = img.filter(ImageFilter.GaussianBlur(2.5))
    # scrim: overall gentle darken so light/pastel photos still hold white text
    scrim = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.blend(img, scrim, 0.30)
    return img


def text_w(draw, s, font):
    l, _, r, _ = draw.textbbox((0, 0), s, font=font)
    return r - l


def tracked_w(draw, s, font, tracking):
    return sum(text_w(draw, ch, font) + tracking for ch in s) - tracking if s else 0


def draw_tracked(draw, xy, s, font, fill, tracking):
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=font, fill=fill)
        x += text_w(draw, ch, font) + tracking


def wrap(draw, text, font, max_w):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            trial = word if not line else line + " " + word
            if text_w(draw, trial, font) <= max_w:
                line = trial
            else:
                if line:
                    lines.append(line)
                if text_w(draw, word, font) > max_w:
                    chunk = ""
                    for ch in word:
                        if text_w(draw, chunk + ch, font) <= max_w:
                            chunk += ch
                        else:
                            lines.append(chunk)
                            chunk = ch
                    line = chunk
                else:
                    line = word
        lines.append(line)
    return lines


def fit_verse(draw, text, max_w, max_h, line_ratio=1.6):
    for size in range(76, 33, -2):
        font = load_font(SERIF, size)
        lines = wrap(draw, text, font, max_w)
        line_h = int(size * line_ratio)
        if len(lines) * line_h <= max_h:
            return font, lines, line_h
    font = load_font(SERIF, 34)
    return font, wrap(draw, text, font, max_w), int(34 * line_ratio)


def paint_text(draw, verse, fg, muted, layout):
    """Draw verse block + divider + reference + handle using a precomputed layout."""
    font, lines, line_h, start_y, handle = layout
    y = start_y
    for line in lines:
        lw = text_w(draw, line, font)
        draw.text(((W - lw) // 2, y), line, font=font, fill=fg)
        y += line_h
    div_y = y + 44
    draw.line([(W // 2 - 22, div_y), (W // 2 + 22, div_y)], fill=muted, width=1)
    ref_font = load_font(SANS, 33)
    rw = tracked_w(draw, verse["ref"], ref_font, 7)
    draw_tracked(draw, ((W - rw) // 2, div_y + 32), verse["ref"], ref_font, muted, 7)
    if handle:
        h_font = load_font(SANS, 25)
        hw = tracked_w(draw, handle, h_font, 3)
        draw_tracked(draw, ((W - hw) // 2, H - 80), handle, h_font, muted, 3)


def render(verse, theme_name, handle, out_path, photo=None):
    # measure with a throwaway draw context
    probe = ImageDraw.Draw(Image.new("RGB", (W, H)))
    font, lines, line_h = fit_verse(probe, verse["text"], W - 2 * MARGIN, 720)
    start_y = (H - len(lines) * line_h) // 2 - 50
    layout = (font, lines, line_h, start_y, handle)

    if photo:
        base = photo_bg(photo).convert("RGBA")
        # draw text on its own layer so we can build a soft shadow from it
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        paint_text(ImageDraw.Draw(txt), verse, PHOTO_FG + (255,), PHOTO_MUTED + (255,), layout)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow.putalpha(txt.getchannel("A"))            # black silhouette of the text
        shadow = shadow.filter(ImageFilter.GaussianBlur(7))
        base = Image.alpha_composite(base, shadow)       # soft dark halo
        base = Image.alpha_composite(base, shadow)       # doubled = a touch stronger
        base = Image.alpha_composite(base, txt)
        base.convert("RGB").save(out_path, "PNG")
    else:
        theme = THEMES.get(verse.get("theme", theme_name), THEMES["ivory"])
        img = solid_bg(theme)
        paint_text(ImageDraw.Draw(img), verse, theme["fg"], theme["muted"], layout)
        img.save(out_path, "PNG")
    return out_path


def slug(ref):
    return ref.replace(" ", "_").replace(":", "-")


def pick_photos():
    files = sorted(f for f in glob.glob(os.path.join(PHOTO_DIR, "*"))
                   if f.lower().endswith((".jpg", ".jpeg", ".png")) and "_placeholder" not in f
                   and "_demo" not in f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ref")
    ap.add_argument("--compare")
    ap.add_argument("--theme", default="ivory", choices=list(THEMES))
    ap.add_argument("--photo", help="render over a specific photo file")
    ap.add_argument("--photos", action="store_true", help="auto-pick a photo from photos/ per verse")
    ap.add_argument("--handle", default="@daily.malsseum")
    args = ap.parse_args()

    with open(os.path.join(HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    verses = data["verses"]
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.compare:
        v = next((x for x in verses if x["ref"] == args.compare), None)
        if not v:
            raise SystemExit(f"verse not found: {args.compare}")
        for name in THEMES:
            vv = dict(v); vv.pop("theme", None)
            render(vv, name, args.handle, os.path.join(OUT_DIR, f"_compare_{name}.png"))
            print(f"✓ [{name}] {v['ref']}")
        return

    if args.all:
        targets = verses
    elif args.ref:
        targets = [v for v in verses if v["ref"] == args.ref]
        if not targets:
            raise SystemExit(f"verse not found: {args.ref}")
    else:
        targets = [verses[date.today().toordinal() % len(verses)]]

    photo_pool = pick_photos() if (args.photos or not args.photo) else []
    for i, v in enumerate(targets):
        photo = args.photo
        if args.photos:
            if not photo_pool:
                raise SystemExit("no photos in photos/ — run fetch_photos.py first")
            photo = photo_pool[i % len(photo_pool)]
        out = os.path.join(OUT_DIR, f"{slug(v['ref'])}.png")
        render(v, args.theme, args.handle, out, photo=photo)
        print(f"✓ {v['ref']}  →  {out}" + (f"  [{os.path.basename(photo)}]" if photo else ""))


if __name__ == "__main__":
    main()
