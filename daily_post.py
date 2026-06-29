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
import make_video
import post_instagram
import fetch_videos

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
VIDEO_DIR = os.path.join(generate.HERE, "videos")
STATE = os.path.join(generate.HERE, "state.json")
CLIPS = os.path.join(generate.HERE, "clips.json")  # human-approved Pexels video ids
HASHTAGS = "#성경 #말씀 #오늘의말씀 #말씀묵상 #큐티 #말씀스타그램 #빛으로"

# never post a verse that ends mid-clause (reads incomplete as a standalone card)
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며")


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


def music_tracks():
    return sorted(f for f in glob.glob(os.path.join(MUSIC_DIR, "*"))
                  if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")))


def pick_clip(used_clips, start):
    """Fetch a portrait clip that has NEVER been used. Rotates keywords from `start`.
    Returns (path, video_id). Resets the ledger only if every candidate is exhausted."""
    os.makedirs(VIDEO_DIR, exist_ok=True)
    dest = os.path.join(VIDEO_DIR, "today.mp4")
    Q = fetch_videos.QUERIES
    order = [Q[(start + k) % len(Q)] for k in range(len(Q))]
    for reset in (False, True):
        if reset:
            used_clips.clear()        # exhausted all keywords → start a fresh cycle
        for kw in order:
            try:
                cands = fetch_videos.candidates(kw)
            except Exception as e:
                print(f"  candidates({kw}) failed: {e}")
                continue
            for vid, link in cands:
                if vid in used_clips:
                    continue
                try:
                    fetch_videos._download(link, dest)
                    return dest, vid
                except Exception as e:
                    print(f"  download {vid} failed: {e}")
    return None, None


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
    photos = generate.pick_photos()
    tracks = music_tracks()

    state = load_state()
    unused = [v for v in verses if v["ref"] not in state["used_verses"]]
    if not unused:                       # whole pool shown → start a new cycle
        state["used_verses"] = []
        unused = verses
    # spread across books: pick a verse from the least-posted book (ties → file order)
    book = lambda r: r.rsplit(" ", 1)[0]
    used_books = Counter(book(r) for r in state["used_verses"])
    verse = min(unused, key=lambda v: (used_books[book(v["ref"])], verses.index(v)))
    n = len(state["used_verses"])        # rotation index for music + photo
    photo = photos[n % len(photos)] if photos else None
    audio = tracks[n % len(tracks)] if tracks else None

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    clip, clip_id = pick_clip(state["used_clips"], n) if audio else (None, None)

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
        print(f"reel(video): {verse['ref']}  [clip {clip_id} + {os.path.basename(audio)}]")
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
    # record what we used so it NEVER repeats
    state["used_verses"].append(verse["ref"])
    if clip_id:
        state["used_clips"].append(clip_id)
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
