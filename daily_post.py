#!/usr/bin/env python3
"""
Daily 말씀 Reel — the hands-off orchestrator.

Each day it: waits for 05:00 KST ±10 min, picks today's verse, fetches a solemn
moving nature clip (Pexels), overlays the verse, adds a hymn track, and publishes
a Reel. Fallbacks keep it alive: no clip → still-image reel; no music → feed photo.

    python3 daily_post.py --now --dry-run   # build today's media, don't publish
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
import fetch_videos

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
VIDEO_DIR = os.path.join(generate.HERE, "videos")
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


def _by_date(pool):
    return pool[datetime.now(KST).toordinal() % len(pool)] if pool else None


def todays_verse(verses):
    return _by_date(verses)


def pick_photo():
    return _by_date(generate.pick_photos())


def pick_audio():
    return _by_date(sorted(f for f in glob.glob(os.path.join(MUSIC_DIR, "*"))
                           if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg"))))


def fetch_clip():
    """Fetch one solemn nature clip for today (rotates query). None on failure."""
    try:
        q = _by_date(fetch_videos.QUERIES)
        os.makedirs(VIDEO_DIR, exist_ok=True)
        return fetch_videos.fetch_one(q, os.path.join(VIDEO_DIR, "today.mp4"))
    except Exception as e:
        print(f"video fetch failed ({e}) → fallback")
        return None


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
    verse = todays_verse(data["verses"])
    audio = pick_audio()

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)

    if audio:
        rel_path = f"output/posts/{date_str}.mp4"
        out_mp4 = os.path.join(generate.HERE, rel_path)
        clip = fetch_clip()
        if clip:
            # video reel: clip background + text overlay + music
            frame = os.path.join(generate.OUT_DIR, "_frame.png")
            overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
            make_video.extract_frame(clip, frame)
            generate.render_overlay(verse, overlay, frame, canvas=generate.REEL)
            make_video.build_reel(clip, overlay, audio, out_mp4)
            print(f"reel(video): {verse['ref']}  [{os.path.basename(clip)} + {os.path.basename(audio)}]")
        else:
            # still-image reel fallback
            img = os.path.join(posts, f"{date_str}.png")
            generate.render(verse, "ivory", "", img, photo=pick_photo(), canvas=generate.REEL)
            make_video.make_video(img, audio, out_mp4)
            print(f"reel(still): {verse['ref']}  [{os.path.basename(audio)}]")
    else:
        # no music → clean feed photo (keeps automation alive)
        rel_path = f"output/posts/{date_str}.png"
        img = os.path.join(generate.HERE, rel_path)
        generate.render(verse, "ivory", "", img, photo=pick_photo(), canvas=generate.FEED)
        print(f"photo (no music yet): {verse['ref']}")

    caption = build_caption(verse, data.get("translation", ""))
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
