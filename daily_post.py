#!/usr/bin/env python3
"""
Daily 말씀 post — the hands-off orchestrator.

Each day: waits for 05:00 KST ±10 min, picks the next verse + photo + hymn track
(sequentially, each used once before repeating), renders the 4:5 card, turns it into
a still-card Reel with music (shows in the feed via share_to_feed), and publishes.
No music yet → posts a plain 4:5 photo so the run never breaks.

    python3 daily_post.py --now --dry-run   # build, don't publish
    python3 daily_post.py --emit            # wait → build, no publish (CI)
    python3 daily_post.py --jitter 600
"""

import argparse
import glob
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import generate
import make_video
import post_instagram

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
STATE = os.path.join(generate.HERE, "state.json")
HASHTAGS = "#말씀 #오늘의말씀 #성경말씀 #큐티 #묵상 #기독교 #신앙 #찬양 #하나님 #은혜"


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


def load_count():
    try:
        return json.load(open(STATE)).get("i", 0)
    except Exception:
        return 0


def save_count(i):
    json.dump({"i": i}, open(STATE, "w"))


def music_tracks():
    return sorted(f for f in glob.glob(os.path.join(MUSIC_DIR, "*"))
                  if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")))


def build_caption(verse, translation):
    return f"\"{verse['text']}\"\n\n— {verse['ref']} ({translation})\n\n{HASHTAGS}"


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
    verses = data["verses"]
    photos = generate.pick_photos()
    tracks = music_tracks()

    # sequential rotation — everything cycles once before repeating
    i = load_count()
    verse = verses[i % len(verses)]
    photo = photos[i % len(photos)] if photos else None
    audio = tracks[i % len(tracks)] if tracks else None

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    img = os.path.join(posts, f"{date_str}.png")
    generate.render(verse, "ivory", "", img, photo=photo, canvas=generate.FEED)

    if audio:
        # still-card Reel with music (shows in feed via share_to_feed)
        rel_path = f"output/posts/{date_str}.mp4"
        make_video.make_video(img, audio, os.path.join(generate.HERE, rel_path), size=generate.FEED)
        print(f"reel: {verse['ref']}  [{os.path.basename(photo)} + {os.path.basename(audio)}]")
    else:
        rel_path = f"output/posts/{date_str}.png"
        print(f"photo (no music yet): {verse['ref']}  [{os.path.basename(photo) if photo else 'solid'}]")

    caption = build_caption(verse, data.get("translation", ""))
    save_count(i + 1)
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    if args.dry_run or args.emit:
        print("\n--- caption ---\n" + caption + "\n--- (not publishing here) ---")
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit")
    url = base.rstrip("/") + "/" + rel_path
    if rel_path.endswith(".mp4"):
        print(f"published reel: {post_instagram.publish_reel(url, caption)}")
    else:
        print(f"published photo: {post_instagram.publish(url, caption)}")


if __name__ == "__main__":
    main()
