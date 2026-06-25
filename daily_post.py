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
from datetime import datetime, timedelta, timezone

import generate
import make_video
import post_instagram
import fetch_videos

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
VIDEO_DIR = os.path.join(generate.HERE, "videos")
STATE = os.path.join(generate.HERE, "state.json")
CLIPS = os.path.join(generate.HERE, "clips.json")  # human-approved Pexels video ids
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


def approved_ids():
    try:
        return json.load(open(CLIPS)).get("ids", [])
    except Exception:
        return []


def fetch_clip(i, query):
    """Prefer the next human-approved clip (clips.json); else keyword fallback."""
    os.makedirs(VIDEO_DIR, exist_ok=True)
    dest = os.path.join(VIDEO_DIR, "today.mp4")
    ids = approved_ids()
    try:
        if ids:  # optional: pin specific approved clips via clips.json
            return fetch_videos.fetch_by_id(ids[i % len(ids)], dest)
        # otherwise pull fresh by keyword (rotates keyword + result for variety)
        return fetch_videos.fetch_one(query, dest, pick=i // len(fetch_videos.QUERIES))
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
    verses = data["verses"]
    photos = generate.pick_photos()
    tracks = music_tracks()

    i = load_count()
    verse = verses[i % len(verses)]
    photo = photos[i % len(photos)] if photos else None
    audio = tracks[i % len(tracks)] if tracks else None
    query = fetch_videos.QUERIES[i % len(fetch_videos.QUERIES)]

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    clip = fetch_clip(i, query) if audio else None

    if clip and audio:
        # video reel: cloud/sky clip → boomerang ~60s → centered verse + music
        boom = os.path.join(generate.OUT_DIR, "_boom.mp4")
        frame = os.path.join(generate.OUT_DIR, "_frame.png")
        overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
        make_video.make_boomerang(clip, boom)
        make_video.extract_frame(boom, frame)
        generate.render_overlay(verse, overlay, frame, canvas=generate.REEL)
        rel_path = f"output/posts/{date_str}.mp4"
        make_video.build_reel(boom, overlay, audio, os.path.join(generate.HERE, rel_path), duration=60)
        print(f"reel(video): {verse['ref']}  [{query} + {os.path.basename(audio)}]")
    elif audio:
        # still 4:5 card + music
        img = os.path.join(posts, f"{date_str}.png")
        generate.render(verse, "ivory", "", img, photo=photo, canvas=generate.FEED)
        rel_path = f"output/posts/{date_str}.mp4"
        make_video.make_video(img, audio, os.path.join(generate.HERE, rel_path), size=generate.FEED)
        print(f"reel(still): {verse['ref']}  [{os.path.basename(audio)}]")
    else:
        # no music → plain 4:5 feed photo
        rel_path = f"output/posts/{date_str}.png"
        generate.render(verse, "ivory", "", os.path.join(generate.HERE, rel_path),
                        photo=photo, canvas=generate.FEED)
        print(f"photo (no music yet): {verse['ref']}")

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
