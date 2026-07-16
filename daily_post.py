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
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import generate
import post_instagram
import fetch_higgsfield
import fetch_videos
import make_video

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


def wait_until_target(jitter_s, hour=5):
    now = datetime.now(KST)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
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
    # verse + reference, then a gentle follow CTA (turns reach → followers)
    return (f"{verse['text']}\n[{verse['ref']}]\n\n"
            "매일 아침·저녁, 마음에 닿는 말씀을 전합니다 🕊\n"
            "→ @to_light_bible 팔로우하고 하루를 말씀으로 시작하세요")


def _music_family(path):
    """Group near-identical cuts from the same source series (e.g. both 'harmony-of-heaven…'
    tracks → one family, both 'misselle-bible…' → another) so the same SOUND never plays on
    back-to-back posts. Keyed on the leading title tokens, which name the series."""
    b = os.path.basename(path).lower().replace("_", "-")
    tokens = [t for t in b.split("-") if t and not t.isdigit() and t != "instrumental"]
    return "-".join(tokens[:2])


def _instrumental_tracks():
    """All instrumental tracks, with families INTERLEAVED (A,B,A,B,…) so rotating through the
    list alternates the mood every post instead of playing two similar cuts in a row."""
    tracks = sorted(f for f in glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
                    if "instrumental" in os.path.basename(f).lower())
    tracks = tracks or sorted(glob.glob(os.path.join(MUSIC_DIR, "*.mp3")))
    fams = {}
    for t in tracks:
        fams.setdefault(_music_family(t), []).append(t)
    queues = [list(reversed(v)) for v in fams.values()]
    ordered = []
    while any(queues):
        for q in queues:
            if q:
                ordered.append(q.pop())
    return ordered


def pick_music(state):
    """Pick an instrumental with NO repeat until the whole set has been used (a ledger in
    state), and with families interleaved so the same sound never lands on consecutive posts.
    (Royalty-free instrumentals only → minimal Content-ID risk.)"""
    tracks = _instrumental_tracks()
    if not tracks:
        return None
    used = state.setdefault("used_music", [])
    unused = [t for t in tracks if os.path.basename(t) not in used]
    if not unused:                        # whole set played → start a fresh cycle
        used.clear()
        unused = tracks
    pick = unused[0]
    used.append(os.path.basename(pick))
    return pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--jitter", type=int, default=600)
    ap.add_argument("--hour", type=int, default=5)   # 5 = morning, 19 = evening (KST)
    args = ap.parse_args()

    if not args.now:
        wait_until_target(args.jitter, args.hour)

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

    # REEL (text always centered — reads best in motion). Two background sources, alternated
    # for variety: (a) real Pexels footage (clouds/fields, gently moving) with a white-text
    # overlay, and (b) a Nano Banana still with a subtle Ken Burns zoom (adaptive color).
    placement = ("center", "middle")
    rel_path = f"output/posts/{date_str}.mp4"
    out_mp4 = os.path.join(generate.HERE, rel_path)
    audio = pick_music(state)   # no-repeat, family-interleaved (never same track/sound twice)
    made = False

    if n % 2 == 1:                                   # odd runs → real moving footage
        keyword = ("clouds", "field")[(n // 2) % 2]  # 구름 / 들판, alternating
        try:
            clip = os.path.join(generate.OUT_DIR, "_clip.mp4")
            # a clip already ≥20s → play FORWARD only (no weird reverse/boomerang)
            fetch_videos.fetch_long(keyword, clip, min_dur=20, pick=n)
            overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
            generate.render_text_overlay(verse, overlay, canvas=generate.REEL, placement=placement)
            make_video.build_reel(clip, overlay, audio, out_mp4, duration=20)
            print(f"reel(clip:{keyword}): {verse['ref']}")
            made = True
        except Exception as e:
            print(f"clip path failed ({e}) → nano-banana still")

    if not made:                                     # even runs, or clip fetch failed
        photo = None
        bg = os.path.join(generate.OUT_DIR, "_bg.png")
        # Walk the SCENES list with its OWN sequential counter — only ~half the posts reach this
        # grand path, so keying off `n` would silently skip every other scene. This visits them
        # all in order (no scene repeats until the whole diverse set has been used).
        scene_i = state.get("scene_i", 0)
        try:
            photo = fetch_higgsfield.generate_background(bg, scene_i, placement, aspect="9:16")
            state["scene_i"] = scene_i + 1
            print(f"background: nano-banana  9:16  (scene {scene_i})")
        except Exception as e:
            print(f"higgsfield failed ({e}) → photo pool fallback")
            used_photos = state.setdefault("used_photos", [])
            pool_p = [p for p in photos if os.path.basename(p) not in used_photos] or photos
            photo = pool_p[n % len(pool_p)] if pool_p else None
            if photo:
                used_photos.append(os.path.basename(photo))
        # A grand background deserves REAL motion, not a zoom: animate the still into a moving
        # clip (Veo image-to-video) and lay the crisp verse on top. If Veo is unavailable, fall
        # back to the background-only Ken Burns zoom (text still added AFTER, so it never shakes).
        from PIL import Image
        src = photo if photo else bg
        generate.cover_crop(Image.open(src), *generate.REEL).save(bg, "PNG")
        overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
        generate.render_text_overlay(verse, overlay, canvas=generate.REEL, placement=placement)
        try:
            import fetch_veo
            clip = os.path.join(generate.OUT_DIR, "_veo.mp4")
            fetch_veo.animate(bg, clip)                          # grand still → real motion
            slow = os.path.join(generate.OUT_DIR, "_veo_slow.mp4")
            make_video.make_slowmo(clip, slow, target=20)        # serene ~20s pace, no loop seam
            make_video.build_reel(slow, overlay, audio, out_mp4, duration=20)
            print(f"reel(grand-veo): {verse['ref']}")
        except Exception as e:
            print(f"veo motion failed ({e}) → background-zoom still")
            make_video.build_reel_still(bg, overlay, audio, out_mp4, duration=20)
            print(f"reel(grand-still): {verse['ref']}")

    print(f"music={os.path.basename(audio) if audio else 'none'}")

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
