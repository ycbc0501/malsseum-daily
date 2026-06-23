#!/usr/bin/env python3
"""
Daily 말씀 Reel — the hands-off orchestrator.

Run once per day (GitHub Actions). It:
  1. waits to hit 05:00 KST ± up to 10 min of random jitter,
  2. picks today's verse + a photo + a hymn track,
  3. renders a 9:16 image and turns it into a still-image Reel (MP4) with music,
  4. (optionally) publishes it to Instagram as a Reel.

    python3 daily_post.py --now --dry-run   # render image + build mp4, don't publish
    python3 daily_post.py --emit            # wait → render → build mp4, no publish (CI)
    python3 daily_post.py --jitter 600      # +/- seconds of randomness (default 600)
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


def todays_verse(verses):
    return verses[datetime.now(KST).toordinal() % len(verses)]


def pick_photo():
    pool = generate.pick_photos()
    return pool[datetime.now(KST).toordinal() % len(pool)] if pool else None


def pick_audio():
    pool = sorted(f for f in glob.glob(os.path.join(MUSIC_DIR, "*"))
                  if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")))
    return pool[datetime.now(KST).toordinal() % len(pool)] if pool else None


def build_caption(verse, translation):
    return f"\"{verse['text']}\"\n\n— {verse['ref']} ({translation})\n\n{HASHTAGS}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true", help="skip the timed wait")
    ap.add_argument("--dry-run", action="store_true", help="render+build, do not publish")
    ap.add_argument("--emit", action="store_true",
                    help="wait+render+build mp4, no publish (for GitHub Actions)")
    ap.add_argument("--jitter", type=int, default=600)
    ap.add_argument("--handle", default="")
    args = ap.parse_args()

    if not args.now:
        wait_until_target(args.jitter)

    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    verse = todays_verse(data["verses"])
    photo = pick_photo()
    audio = pick_audio()

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    img = os.path.join(posts, f"{date_str}.png")

    if audio:
        # Reel: 9:16 still → still-image video with hymn music
        generate.render(verse, "ivory", args.handle, img, photo=photo, canvas=generate.REEL)
        rel_path = f"output/posts/{date_str}.mp4"
        make_video.make_video(img, audio, os.path.join(generate.HERE, rel_path))
        print(f"reel: {verse['ref']}  →  {rel_path}  [{os.path.basename(photo)} + {os.path.basename(audio)}]")
    else:
        # fallback: no music yet → post a normal 4:5 feed photo so the daily run never breaks
        generate.render(verse, "ivory", args.handle, img, photo=photo, canvas=generate.FEED)
        rel_path = f"output/posts/{date_str}.png"
        print(f"photo (no music yet): {verse['ref']}  →  {rel_path}  [{os.path.basename(photo)}]")

    caption = build_caption(verse, data.get("translation", ""))
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    if args.dry_run or args.emit:
        print("\n--- caption ---\n" + caption)
        print("\n--- (not publishing here) ---")
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit (publish handled by runner)")
    url = base.rstrip("/") + "/" + rel_path
    if rel_path.endswith(".mp4"):
        print(f"published reel: {post_instagram.publish_reel(url, caption)}")
    else:
        print(f"published photo: {post_instagram.publish(url, caption)}")


if __name__ == "__main__":
    main()
