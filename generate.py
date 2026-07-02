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
    os.path.join(FONTS_DIR, "NanumMyeongjo-Regular.ttf"),  # the 빌립보서 look — finer, more refined
    os.path.join(FONTS_DIR, "NanumMyeongjo-Bold.ttf"),
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


def _trim_flat_border(img, thr=3.0, max_frac=0.10):
    """Crop away any near-uniform synthetic border (e.g. the thin white margins the image
    model sometimes adds instead of a full-bleed photo). A real photo edge — even bright
    sky — has texture (stddev well above `thr`), so only flat manufactured borders trim."""
    g = img.convert("L")
    W, H = img.size
    flat_col = lambda x: ImageStat.Stat(g.crop((x, 0, x + 1, H))).stddev[0] < thr
    flat_row = lambda y: ImageStat.Stat(g.crop((0, y, W, y + 1))).stddev[0] < thr
    l, r, t, b = 0, W, 0, H
    while l < int(W * max_frac) and flat_col(l):        l += 1
    while r > W - int(W * max_frac) and flat_col(r - 1): r -= 1
    while t < int(H * max_frac) and flat_row(t):        t += 1
    while b > H - int(H * max_frac) and flat_row(b - 1): b -= 1
    if (l, t, r, b) != (0, 0, W, H) and r - l > W * 0.6 and b - t > H * 0.6:
        return img.crop((l, t, r, b))
    return img


def cover_crop(img, cw, ch):
    img = _trim_flat_border(img.convert("RGB"))
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


# Korean clause endings — break here so lines fall on natural phrase boundaries
_ENDERS = ("요", "고", "며", "니", "라", "면", "나", "사", "다", "야", "여")


def two_line_split(text):
    """Always exactly TWO lines. Comma → split there. Otherwise split at a word
    boundary near the middle, PREFERRING one right after a Korean clause ending
    (요/고/며/니/라…) so the break lands on a natural phrase."""
    text = " ".join(text.split())
    commas = [i for i, c in enumerate(text) if c in ",，"]
    if commas:
        mid = len(text) / 2
        i = min(commas, key=lambda x: abs(x - mid))
        return [s for s in (text[:i + 1].strip(), text[i + 1:].strip()) if s]

    words = text.split(" ")
    if len(words) < 2:
        return [text]
    mid = len(text) / 2
    nearest = None          # closest word-boundary to the middle (fallback)
    clause = None           # closest boundary right after a clause ending
    line1 = ""
    for k in range(len(words) - 1):
        line1 = words[k] if not line1 else line1 + " " + words[k]
        dist = abs(len(line1) - mid)
        if nearest is None or dist < nearest[0]:
            nearest = (dist, k + 1)
        if len(words[k]) >= 2 and words[k].endswith(_ENDERS) and (clause is None or dist < clause[0]):
            clause = (dist, k + 1)
    # use the clause break if it's reasonably balanced, else nearest-middle
    choice = clause if (clause and clause[0] <= len(text) * 0.32) else nearest
    k = choice[1]
    return [s for s in (" ".join(words[:k]), " ".join(words[k:])) if s]


# STRICT clause endings for line breaks — real Korean phrase/clause finals only
# (avoids false breaks like "나타나" → "나"). Order doesn't matter for endswith().
_LINE_ENDERS = ("말미암아", "하리로다", "리로다", "이로다", "었도다", "도다", "로다", "느니라",
                "니라", "으리라", "리라", "지어다", "이요", "으며", "하고", "하며", "거든",
                "으되", "으니", "리니", "지라", "으라", "하라", "고", "며", "니", "라", "요", "면", "매")


def clause_split(text):
    """Split into lines at real Korean clause endings → natural phrase lines (2..n)."""
    words = " ".join(text.split()).split(" ")
    lines, cur = [], ""
    for i, w in enumerate(words):
        cur = w if not cur else cur + " " + w
        if i < len(words) - 1 and len(w) >= 2 and w.endswith(_LINE_ENDERS):
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


_KIWI = None


def _kiwi():
    """Lazily load the Korean morphological analyzer (graceful if not installed)."""
    global _KIWI
    if _KIWI is None:
        try:
            from kiwipiepy import Kiwi
            _KIWI = Kiwi()
        except Exception:
            _KIWI = False
    return _KIWI


def _breakable_words(text):
    """Indices i such that we may break AFTER word i — its last morpheme is a Korean
    connective/closing ending (EC/EF). Uses kiwipiepy; None if unavailable."""
    k = _kiwi()
    if not k:
        return None
    words = text.split()
    ends, pos = [], 0
    for w in words:
        pos = text.index(w, pos) + len(w)
        ends.append(pos)
    toks = k.tokenize(text)
    out = []
    for i, end in enumerate(ends[:-1]):              # never break after the last word
        finals = [m for m in toks if m.start + m.len == end]
        if finals and finals[-1].tag in ("EC", "EF"):
            out.append(i)
    return out


def kiwi_split(text, draw, font, max_w):
    """Break Korean at real clause endings → 2 (preferred, near middle) or 3 lines that
    fit max_w. Returns None if kiwipiepy is unavailable or nothing fits."""
    bp = _breakable_words(text)
    if not bp:
        return None
    words = text.split()
    fits = lambda seg: text_w(draw, " ".join(seg), font) <= max_w
    mid, best = len(text) / 2, None
    for i in bp:                                     # best balanced 2-line at a clause ending
        a, b = words[:i + 1], words[i + 1:]
        if fits(a) and fits(b):
            d = abs(len(" ".join(a)) - mid)
            if best is None or d < best[0]:
                best = (d, [" ".join(a), " ".join(b)])
    if best:
        return best[1]
    for a in bp:                                     # else 3 lines at two clause endings
        for b in bp:
            if b <= a:
                continue
            segs = [words[:a + 1], words[a + 1:b + 1], words[b + 1:]]
            if all(fits(s) for s in segs):
                return [" ".join(s) for s in segs]
    return None


def _word_endings(text):
    """Per-word final-morpheme (tag, form) via kiwipiepy → lets us judge WHERE a break
    reads naturally. None if kiwipiepy is unavailable."""
    k = _kiwi()
    if not k:
        return None
    words = text.split()
    ends, pos = [], 0
    for w in words:
        pos = text.index(w, pos) + len(w)
        ends.append(pos)
    toks = k.tokenize(text)
    info = []
    for e in ends:
        finals = [m for m in toks if m.start + m.len == e]
        info.append((finals[-1].tag, finals[-1].form) if finals else (None, ""))
    return info


def _compositions(n, k):
    """All ways to split n items into k contiguous non-empty groups (as size tuples)."""
    if k == 1:
        yield (n,)
        return
    for first in range(1, n - k + 2):
        for rest in _compositions(n - first, k - 1):
            yield (first,) + rest


# Morphemes that grammatically ATTACH FORWARD — the word carrying them must stay on the same
# line as the word that follows. Breaking right after such a word tears a grammatical unit apart.
#   JKG 의 (genitive) · ETM 관형형 어미 · MM 관형사   → bind to the following NOUN
#   JC  접속 조사 (과/와/이나)                          → bind to the next list item (사랑과│희락과)
#   MAG 부사 · MAJ 접속부사                             → bind to what they modify (오직·다만·오래│참음)
_FWD_NOUN = ("JKG", "ETM", "MM", "MAG", "MAJ", "JC")
# conjunctive / comitative particle surfaces (과/와/이나/랑) — kiwi tags these inconsistently as
# JC or JKB, so we also match on the surface form to be robust: 사랑과│희락과, 너와│함께.
_CONJ_FORMS = ("과", "와", "이나", "랑", "이랑")


def balanced_split(draw, text, font, max_w):
    """Break a verse into lines at GRAMMATICAL boundaries, never inside a grammatical unit.

    Every possible split is scored. The dominant term is grammatical: a break after a
    forward-attaching morpheme (modifier→noun, conjunction→item, adverb→word, adverbial
    particle→predicate, connective→final verb) is effectively forbidden. Among the allowed
    break points, clause endings and commas are preferred, then length balance / few lines
    act only as gentle tie-breakers. Manual `lines` in verses.json still override upstream."""
    words = " ".join(text.split()).split(" ")
    n = len(words)
    if n <= 1:
        return [text or ""]
    if n > 18:
        return _greedy(draw, words, font, max_w)

    info = _word_endings(text)                        # (tag, form) per word, or None
    def tag(i):
        return info[i][0] if info and 0 <= i < n else None

    def is_comma(i):
        return words[i].endswith((",", "，"))

    def forward_attach(i):                            # is a break after word i grammatically wrong?
        if not info or i + 1 >= n or is_comma(i):     # a comma always licenses a break
            return False
        t, form = info[i]
        nxt = tag(i + 1)
        if t in _FWD_NOUN:                            # modifier / conjunction / adverb → next word
            return True
        if t == "NP":                                # a bare pronoun modifies the next word (너희│마음, 내│안에)
            return True
        if t and t.startswith("J") and form in _CONJ_FORMS:  # 과/와/이나 conjunction/comitative → next
            return True
        if t == "JKB" and nxt in ("EC", "EF", "ETM"):  # adverbial particle → a predicate (그에게│피하는)
            return True
        if t == "EC" and nxt == "EF":                # connective → completing final verb (맛보아│알지어다)
            return True
        return False

    def is_clause_end(i):                             # a natural, preferred break point
        return is_comma(i) or tag(i) in ("EC", "EF")

    seg = {}
    def seg_w(i, j):
        if (i, j) not in seg:
            seg[(i, j)] = text_w(draw, " ".join(words[i:j + 1]), font)
        return seg[(i, j)]

    P_FORBID = 100.0 * max_w                          # forward-attach break: never (unless unavoidable)
    P_SOFT   = 0.55 * max_w                           # allowed break that isn't a clause end/comma
    P_ORPHAN = 2.0 * max_w                            # a lonely ~1-word line is bad
    P_LINE   = 0.7 * max_w                            # prefer fewer lines, all else equal
    ORPHAN_W = 0.30 * max_w

    kmin = 1 if seg_w(0, n - 1) <= 0.55 * max_w else 2   # medium/long verses use ≥2 lines
    best = None
    for k in range(kmin, n + 1):
        for sizes in _compositions(n, k):
            widths, breaks, pos, ok = [], [], 0, True
            for gi, s in enumerate(sizes):
                w = seg_w(pos, pos + s - 1)
                if w > max_w:
                    ok = False
                    break
                widths.append(w)
                pos += s
                if gi < k - 1:
                    breaks.append(pos - 1)
            if not ok:
                continue
            score = (max(widths) - min(widths)) + P_LINE * k
            score += P_ORPHAN * sum(1 for w in widths if w < ORPHAN_W)
            for b in breaks:
                if forward_attach(b):
                    score += P_FORBID
                elif not is_clause_end(b):
                    score += P_SOFT
            if best is None or score < best[0]:
                cuts = [sum(sizes[:i]) for i in range(k)]
                best = (score, [" ".join(words[c:c + s]) for c, s in zip(cuts, sizes)])
    return best[1] if best else _greedy(draw, words, font, max_w)


def fit_verse(draw, text, max_w, size, lines=None):
    """FIXED font size. Manual `lines` (verses.json) win; otherwise a scored balanced
    split chooses natural, well-proportioned lines. Size never changes."""
    font = load_font(SERIF, size)
    line_h = int(size * 1.6)
    if lines:                                        # hand-tuned override in verses.json
        return font, lines, line_h, size
    return font, balanced_split(draw, text, font, max_w), line_h, size


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
    sx, sy = int(col_w * 0.10), int(line_h * 1.3)
    ImageDraw.Draw(s).ellipse(
        [col_left - sx, top_y - sy, col_left + col_w + sx, top_y + block_h + sy],
        fill=color + (alpha,))
    return s.filter(ImageFilter.GaussianBlur(55))


def render_italic(text, font, fill, stroke=0, stroke_fill=(0, 0, 0, 150)):
    asc, desc = font.getmetrics()
    h = asc + desc
    shear = 0.20
    pad = int(shear * h) + 8 + stroke
    vpad = stroke + 1
    tw = int(font.getlength(text))
    base = Image.new("RGBA", (tw + 2 * pad, h + 2 * vpad), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((pad, vpad), text, font=font, fill=fill,
                              stroke_width=stroke, stroke_fill=stroke_fill)
    return base.transform(base.size, Image.AFFINE, (1, shear, 0, 0, 1, 0), resample=Image.BICUBIC)


# ----- compose -----------------------------------------------------------------

def render(verse, theme_name, handle, out_path, photo=None, canvas=FEED,
           placement=("center", "middle"), shadow="scrim"):
    cw, ch = canvas
    halign, valign = placement
    verse_size = 44 if canvas == REEL else 40
    mx, my = int(cw * 0.08), int(ch * 0.10)
    if halign == "center":
        col_w = int(cw * (0.85 if canvas == REEL else 0.80))
        col_left = (cw - col_w) // 2
    else:                                      # offset to one side → narrower column
        col_w = int(cw * 0.60)
        col_left = mx if halign == "left" else cw - mx - col_w

    probe = ImageDraw.Draw(Image.new("RGB", (cw, ch)))
    font, lines, line_h, size = fit_verse(probe, verse["text"], col_w, verse_size,
                                          lines=verse.get("lines"))

    src_font = load_font(SERIF, max(22, int(size * 0.62)))   # source ref smaller than the verse
    src_asc, src_desc = src_font.getmetrics()
    src_h = src_asc + src_desc
    gap = int(line_h * 0.45)
    verse_h = len(lines) * line_h
    block_h = verse_h + gap + src_h
    if valign == "middle":
        top_y = ch // 2 - verse_h // 2        # verse's vertical center = image center
    elif valign == "top":
        top_y = my
    else:                                      # bottom
        top_y = ch - my - block_h
    if photo:
        base = cover_crop(Image.open(photo), cw, ch)         # keep the photo crisp (no blur)
        # Adaptive color (dailymayim/Alabaster): sample the actual text region → white text
        # on dark areas, dark text on light areas. Then the shadow only has to be a whisper
        # (it shows only where local contrast is weak, and vanishes where it's already fine).
        reg = base.convert("L").crop((col_left, max(0, top_y), col_left + col_w,
                                      min(ch, top_y + block_h)))
        rst = ImageStat.Stat(reg)
        rmean, rstd = rst.mean[0], rst.stddev[0]
        uniform = rstd < 48
        light = False                          # dark-text-on-light uses a soft aura, not a filled backing
        if uniform and rmean < 118:            # calm & dark → clean WHITE text
            fg, shadow_c, cap = (250, 248, 244), (0, 0, 0), 115
        elif uniform and rmean > 148:          # calm & light → clean DARK text, NO halo
            fg, shadow_c, cap, light = (38, 34, 30), (255, 255, 255), 0, True  # halo erodes thin strokes → none
        else:                                   # busy/mixed → white text + stronger even backing
            fg, shadow_c = (250, 248, 244), (0, 0, 0)
            cap = 200 if rmean > 165 else (165 if rmean > 118 else 140)
        busy = 0
    else:
        theme = THEMES.get(theme_name, THEMES["ivory"])
        base = Image.new("RGB", (cw, ch), theme["bg"])
        fg = theme["fg"]
        shadow_c = (255, 255, 255) if sum(theme["bg"]) > 380 else (0, 0, 0)
        busy = 0

    def line_x(w):                             # align within the column per halign
        if halign == "left":
            return col_left
        if halign == "right":
            return col_left + col_w - w
        return (cw - w) // 2

    base = base.convert("RGBA")
    stroke = 2 if (photo and shadow != "scrim") else 0   # outline (off for the soft-scrim style)
    txt = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))      # verse lines
    td = ImageDraw.Draw(txt)
    y = top_y
    for ln in lines:
        lw = text_w(td, ln, font)
        td.text((line_x(lw), y), ln, font=font, fill=fg + (255,),
                stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
        y += line_h
    if photo:
        src_fill = (228, 225, 219) if fg[0] > 128 else (74, 68, 62)   # match verse (light/dark)
    else:
        src_fill = tuple(int(c * 0.55 + (255 if fg[0] > 128 else 0) * 0.45) for c in fg)
    srctxt = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))   # source ref, kept SEPARATE (upright, no italic)
    sd = ImageDraw.Draw(srctxt)
    src_text = f"[{verse['ref']}]"
    sw = text_w(sd, src_text, src_font)
    sd.text((line_x(sw), y + gap), src_text, font=src_font, fill=src_fill + (255,),
            stroke_width=stroke, stroke_fill=(0, 0, 0, 150))

    if photo:
        def cloud(b, alpha, cap, blurreps):
            for blur, reps in blurreps:
                layer = Image.new("RGBA", (cw, ch), shadow_c + (0,))
                layer.putalpha(alpha.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(cap, v * 3)))
                for _ in range(reps):
                    b = Image.alpha_composite(b, layer)
            return b

        def even_cloud(b, alpha, cap):
            """One continuous, UNIFORM soft patch behind the text — not a per-stroke
            shadow. Solidify strokes → dilate so counters (ㅁ/ㅇ) and inter-stroke gaps
            fill in and neighbouring strokes merge → feather the outer edge → flatten to
            a single capped darkness. Result: every letter sits on the same even backing,
            no blotches, and it still hugs the text (never bleeds into empty margins)."""
            d = max(3, int(size * 0.34)) | 1            # dilation (odd) — merges strokes, fills counters
            g = size * 0.30                              # edge softness
            a = alpha.point(lambda v: 255 if v > 30 else 0)
            a = a.filter(ImageFilter.MaxFilter(d))
            a = a.filter(ImageFilter.GaussianBlur(g))
            a = a.point(lambda v: min(cap, v))          # interior→cap (flat), edge feathers 0..cap
            layer = Image.new("RGBA", (cw, ch), shadow_c + (0,))
            layer.putalpha(a)
            return Image.alpha_composite(b, layer)

        def glow(b, alpha, cap):
            """Soft OUTER aura for dark text on light backgrounds — blur only (NOT
            solidified/dilated), so it hugs the outside of strokes and never floods
            counters (ㅇ) or crooks (ㄴ) with white; thin strokes stay crisp."""
            a = alpha.filter(ImageFilter.GaussianBlur(size * 0.16)).point(lambda v: min(cap, int(v * 1.5)))
            layer = Image.new("RGBA", (cw, ch), shadow_c + (0,))
            layer.putalpha(a)
            return Image.alpha_composite(b, layer)

        va, sa = txt.getchannel("A"), srctxt.getchannel("A")
        if shadow == "outline":
            base = cloud(base, va, 200, ((3, 1),))
            base = cloud(base, sa, 120, ((3, 1),))
        else:   # "scrim" (default) — even backing (white text) or soft aura (dark text)
            if light:
                if cap > 0:                    # dark text: optional whisper-aura (0 = none, crispest)
                    base = glow(base, va, cap)
                    base = glow(base, sa, cap)
            else:
                base = even_cloud(base, va, cap)
                base = even_cloud(base, sa, cap)

    base = Image.alpha_composite(base, txt)
    base = Image.alpha_composite(base, srctxt)
    base.convert("RGB").save(out_path, "PNG")
    return out_path


def render_overlay(verse, out_path, frame_path, handle="", canvas=REEL):
    """Transparent text overlay (verse + italic source) for compositing over video.
    Color/placement chosen from `frame_path` (a representative frame); a soft shadow
    is baked in so the text stays legible over the moving footage."""
    cw, ch = canvas
    col_w = int(cw * 0.85)
    col_left = (cw - col_w) // 2
    probe = ImageDraw.Draw(Image.new("RGB", (cw, ch)))
    font, lines, line_h, size = fit_verse(probe, verse["text"], col_w, 44)
    src_font = load_font(SERIF, max(22, int(size * 0.62)))
    src_h = sum(src_font.getmetrics())
    gap = int(line_h * 0.45)
    verse_h = len(lines) * line_h
    block_h = verse_h + gap + src_h
    top_y = ch // 2 - verse_h // 2            # verse's vertical center = image center (same for 2 or 3 lines)
    # white text + dark scrim → reliable legibility over ANY moving footage
    fg, shadow_c = (252, 250, 246), (0, 0, 0)

    txt = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    y = top_y
    for ln in lines:
        lw = text_w(td, ln, font)
        td.text(((cw - lw) // 2, y), ln, font=font, fill=fg + (255,))
        y += line_h
    src_fill = (228, 225, 219)
    src_img = render_italic(f"[{verse['ref']}]", src_font, src_fill + (255,))
    txt.alpha_composite(src_img, ((cw - src_img.width) // 2, y + gap - src_h // 4))

    # strong soft dark scrim behind the text → legible even over busy/bright footage
    scrim = soft_scrim(cw, ch, col_left, col_w, top_y, block_h, line_h, shadow_c, alpha=160)
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
