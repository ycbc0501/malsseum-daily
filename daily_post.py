#!/usr/bin/env python3
"""
Daily 말씀 Reel — the hands-off orchestrator.

Each day: waits for 05:00 KST ±10 min, picks the next verse + hymn track + sky/cloud
clip (sequential rotation, each used once before repeating), makes the ~15s clip into
a seamless ~60s boomerang (forward+reverse), overlays the verse (always centered),
adds the hymn music, and publishes a Reel (shows in feed via share_to_feed).

Fallbacks keep it alive: no clip → still 4:5 card + music; no music → plain 4:5 photo.

    python3 daily_post.py --now --dry-run
    python3 daily_post.py --emit
    python3 daily_post.py --jitter 600
"""

import argparse
import glob
import json
import os
import random
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import generate
import post_instagram
import fetch_higgsfield

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
VIDEO_DIR = os.path.join(generate.HERE, "videos")
STATE = os.path.join(generate.HERE, "state.json")
CLIPS = os.path.join(generate.HERE, "clips.json")  # human-approved Pexels video ids
HASHTAGS = "#성경 #말씀 #오늘의말씀 #말씀묵상 #큐티 #말씀스타그램 #빛으로"

# never post a verse that ends mid-clause (reads incomplete as a standalone card)
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며")

# weekly themed series — each week's posts are drawn from one theme (meaningful flow)
THEME_ORDER = ["위로", "평안", "담대", "믿음", "감사", "사랑", "인도", "은혜", "지혜"]


def wait_until_target(jitter_s):
    now = datetime.now(KST)
    target = now.replace(hour=5, minute=0, second=0, microsecond=0)
    target += timedelta(seconds=random.randint(-jitter_s, jitter_s))
    delay = (target - now).total_seconds()
    if delay > 0:
        print(f"sleeping {int(delay)}s → posting at {target:%Y-%m-%d %H:%M:%S} KST")
        time.sleep(delay)
    else:
        print(f"target {target:%H:%M:%S} KST already passed → posting now")


def load_state():
    try:
        s = json.load(open(STATE))
    except Exception:
        s = {}
    s.setdefault("used_verses", [])   # verse refs already posted (never repeat)
    s.setdefault("used_clips", [])    # Pexels video ids already used (never repeat)
    return s


def save_state(s):
    json.dump(s, open(STATE, "w"))


def build_caption(verse, translation):
    return f"{verse['text']}\n[{verse['ref']}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--jitter", type=int, default=600)
    args = ap.parse_args()

    if not args.now:
        wait_until_target(args.jitter)

    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    # safety: drop any verse that ends mid-clause so it can never be posted
    verses = [v for v in data["verses"]
              if not v["text"].rstrip().rstrip(".").endswith(INCOMPLETE_ENDINGS)]
    photos = generate.pick_photos()   # fallback backgrounds if Higgsfield is unavailable

    state = load_state()
    unused = [v for v in verses if v["ref"] not in state["used_verses"]]
    if not unused:                       # whole pool shown → start a new cycle
        state["used_verses"] = []
        unused = verses
    # this week's theme → draw from it (fall back to any unused if its verses run out)
    theme = THEME_ORDER[datetime.now(KST).isocalendar()[1] % len(THEME_ORDER)]
    pool = [v for v in unused if v.get("theme") == theme] or unused
    # within the theme, spread across books (least-posted book first)
    book = lambda r: r.rsplit(" ", 1)[0]
    used_books = Counter(book(r) for r in state["used_verses"])
    verse = min(pool, key=lambda v: (used_books[book(v["ref"])], verses.index(v)))
    n = len(state["used_verses"])
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)

    # ~80% leave a calm empty area where the text sits (placement varies a little);
    # ~20% a fuller dramatic scene, centered, legible via the scrim
    OFFSETS = [("left", "middle"), ("right", "middle"), ("center", "top"),
               ("center", "bottom"), ("right", "top"), ("left", "bottom")]
    full_scene = (n % 5 == 4)
    placement = ("center", "top")          # text block (verse + source) sits in the upper open sky
    if not full_scene and len(verse["text"]) <= 28 and n % 5 == 2:
        placement = OFFSETS[(n // 5) % len(OFFSETS)]

    # background: generate a fresh, unique image via Higgsfield; fall back to the photo pool
    photo = None
    try:
        photo = fetch_higgsfield.generate_background(
            os.path.join(generate.OUT_DIR, "_bg.png"), n, placement, full_scene=full_scene)
        print(f"background: higgsfield ({'full' if full_scene else 'empty-space'})  placement={placement}")
    except Exception as e:
        print(f"higgsfield failed ({e}) → photo pool fallback")
        used_photos = state.setdefault("used_photos", [])
        pool_p = [p for p in photos if os.path.basename(p) not in used_photos] or photos
        photo = pool_p[n % len(pool_p)] if pool_p else None
        if photo:
            used_photos.append(os.path.basename(photo))

    rel_path = f"output/posts/{date_str}.png"
    generate.render(verse, "ivory", "", os.path.join(generate.HERE, rel_path),
                    photo=photo, canvas=generate.FEED, placement=placement)
    print(f"image: {verse['ref']}")

    caption = build_caption(verse, data.get("translation", ""))
    # record what we used so it NEVER repeats
    state["used_verses"].append(verse["ref"])
    save_state(state)
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    with open(os.path.join(generate.OUT_DIR, "_comment.txt"), "w", encoding="utf-8") as f:
        f.write(HASHTAGS)  # hashtags go in the first comment, not the caption

    if args.dry_run or args.emit:
        print("\n--- caption ---\n" + caption + "\n--- comment ---\n" + HASHTAGS)
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit")
    url = base.rstrip("/") + "/" + rel_path
    result = (post_instagram.publish_reel if rel_path.endswith(".mp4") else post_instagram.publish)(url, caption)
    print("published:", result)
    if isinstance(result, dict) and result.get("id"):
        print("comment:", post_instagram.comment(result["id"], HASHTAGS))


if __name__ == "__main__":
    main()
