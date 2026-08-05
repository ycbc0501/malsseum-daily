#!/usr/bin/env python3
"""
Daily 말씀 Reel — the hands-off orchestrator.

Each day: waits for 05:00 KST ±10 min, picks the next verse + a unique hymn, generates an
AI background, animates it with Veo into ~16s of real motion (two chained ~8s continuations,
played forward at native speed — never looped or reversed), overlays the verse (always
centered), mixes the hymn in softly, and publishes a Reel (shown in the profile grid via
share_to_feed) plus a Story.

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
import shutil
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import generate
import hashtags
import post_instagram
import fetch_higgsfield
import fetch_videos
import make_video

KST = timezone(timedelta(hours=9))
MUSIC_DIR = os.path.join(generate.HERE, "music")
VIDEO_DIR = os.path.join(generate.HERE, "videos")
STATE = os.path.join(generate.HERE, "state.json")
CLIPS = os.path.join(generate.HERE, "clips.json")  # human-approved Pexels video ids
# Hashtags are built per-post from the verse's theme — see hashtags.py. Instagram caps
# them at 5 (caption + comments share the same 5 slots), so there is no fixed set here.

# never post a verse that ends mid-clause (reads incomplete as a standalone card)
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며")

# weekly themed series — each week's posts are drawn from one theme (meaningful flow)
THEME_ORDER = ["위로", "평안", "담대", "믿음", "감사", "사랑", "인도", "은혜", "지혜"]

# How many chained Veo segments make up one reel. Veo's fast tier caps a single generation at
# ~8s, so length is built by animating each segment's tail frame into the next and playing them
# forward once (CONTENT_RULE 6 — never a loop, never a reverse). 2 ≈ 16s.
# Raising this is a TIMING-BUDGET decision, not a free knob: each segment is another Veo call
# (~2-6 min), rule 1 leaves only ~50 min of build time after the scheduler wait, and past ~30s
# the reel outlasts Lyria's hymn and the music would have to loop.
SEGMENTS = 2


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
    """Verse + reference, then a SHARE ask first and a follow ask second.

    The order is deliberate and it is the whole caption strategy. Instagram's stated ranking
    signals are watch time, sends per reach and likes per reach, and a send weighs several times
    a like when deciding whether to show the post to people who don't follow the account — so
    asking for a follow (which only the already-convinced can give) spends the strongest line of
    the caption on the weakest signal. Asking someone to forward a 말씀 to a friend who needs it
    is both the higher-weighted action and the honest purpose of the account; the follow follows
    from being seen. Measured by `insights.py` (send/reach per post), not assumed."""
    return (f"{verse['text']}\n[{verse['ref']}]\n\n"
            "오늘 이 말씀이 필요한 사람에게 보내주세요 🕊\n"
            "→ 매일 아침·저녁 @to_light_bible")


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
    photos = generate.calm_photos(generate.pick_photos())   # fallback backgrounds if Higgsfield is unavailable (calm centres only — the verse must stay legible)

    state = load_state()
    unused = [v for v in verses if v["ref"] not in state["used_verses"]]
    if not unused:                       # whole pool shown → start a new cycle
        state["used_verses"] = []
        unused = verses
    # this week's theme → draw from it (fall back to any unused if its verses run out)
    theme = THEME_ORDER[datetime.now(KST).isocalendar()[1] % len(THEME_ORDER)]
    pool = [v for v in unused if v.get("theme") == theme] or unused
    # within the theme, gently spread across books (least-posted book first) for balance — but books
    # MAY repeat; only VERSES never repeat (the used_verses ledger guarantees that).
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
    # MUSIC: generate a UNIQUE instrumental per post with Lyria (never the same music twice, and
    # no Content-ID risk). Falls back to the vetted library only if generation fails.
    audio = os.path.join(generate.OUT_DIR, "_music.mp3")
    music_i = state.get("music_i", 0)
    try:
        import fetch_lyria
        fetch_lyria.generate(audio, music_i)
        state["music_i"] = music_i + 1
        print(f"music: lyria unique (mood {music_i % len(fetch_lyria.MOODS)})")
    except Exception as e:
        print(f"lyria failed ({e}) → library fallback")
        audio = pick_music(state)   # no-repeat, family-interleaved fallback
    # EVERY post: a wondervisionary-style AI background → REAL Veo motion (water/mist/clouds/plants
    # move, camera locked so the verse stays put) → crisp centred verse + a unique gentle hymn.
    # Scenes walk a dedicated sequential counter so none repeats until the whole set is used.
    # Fallbacks keep it alive: Veo down → gentle background-zoom of the same image; image gen down →
    # a licensed photo from the pool. (No stock-footage path — it looked dull and repeated clips.)
    from PIL import Image
    bg = os.path.join(generate.OUT_DIR, "_bg.png")
    photo = None
    scene_i = state.get("scene_i", 0)
    post_i = state.get("post_i", 0)   # monotonic counter → rotates the light/angle variation
    scene_cats = state.setdefault("used_scene_cats", [])
    # Skip forward past any theme used in the last 2 posts so the feed never clusters (e.g. 3 water scenes).
    scene_i, scene_cat = fetch_higgsfield.pick_scene(scene_i, scene_cats)
    try:
        fetch_higgsfield.generate_checked(bg, scene_i, placement, aspect="9:16", var_t=post_i)
        state["scene_i"] = scene_i + 1
        state["post_i"] = post_i + 1
        scene_cats.append(scene_cat)
        del scene_cats[:-4]   # keep only the last few themes
        print(f"background: nano-banana 9:16 (scene {scene_i}, theme {scene_cat})")
    except Exception as e:
        print(f"higgsfield failed ({e}) → photo pool fallback")
        used_photos = state.setdefault("used_photos", [])
        pool_p = [p for p in photos if os.path.basename(p) not in used_photos] or photos
        photo = pool_p[n % len(pool_p)] if pool_p else None
        if photo:
            used_photos.append(os.path.basename(photo))
    generate.cover_crop(Image.open(photo or bg), *generate.REEL).save(bg, "PNG")
    overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
    generate.render_text_overlay(verse, overlay, canvas=generate.REEL, placement=placement)
    # Veo → REAL motion at NATIVE speed (no slow-mo: stretching made it coarse). An automatic motion
    # gate rejects an over-animated clip (racing/timelapse clouds or churning water): retry once, and
    # only if it is STILL too fast fall back to a calm still — a bad-motion clip can never post itself.
    # Tightened 2026-08-05: 2.6/0.7 was ~2x the calm reference and let visibly racing clouds and
    # churning water through (published reels the account owner flagged). Scored against the local
    # clip library, calm sits at 1.7/0.35 and frantic city at 7.3/0.4, so the bar now sits just
    # above calm instead of halfway to frantic.
    MOTION_MAX, SKY_MAX = 2.0, 0.45
    try:
        import fetch_veo
        clip = os.path.join(generate.OUT_DIR, "_veo.mp4")
        best = os.path.join(generate.OUT_DIR, "_veo_best.mp4")
        ov = sky = 99.0
        # Three tries, KEEPING THE CALMEST rather than the first one that squeaks under the bar —
        # otherwise a tighter threshold just buys more still fallbacks instead of better motion.
        for attempt in (1, 2, 3):
            fetch_veo.animate(bg, clip)                          # AI image → real motion
            o, s = make_video.motion_score(clip)
            print(f"veo motion attempt {attempt}: overall {o:.2f}, sky {s:.2f}")
            # A clip is only as calm as its WORST axis, so rank on the larger of the two ratios.
            if max(o / MOTION_MAX, s / SKY_MAX) < max(ov / MOTION_MAX, sky / SKY_MAX):
                ov, sky = o, s
                shutil.copyfile(clip, best)
            if ov <= MOTION_MAX and sky <= SKY_MAX:
                break
        if ov <= MOTION_MAX and sky <= SKY_MAX:
            # Chain from the CALMEST take, not the last one generated — `clip` holds whatever
            # attempt ran most recently, which may be the frantic one we rejected.
            segments = [best]
            # Extend, one segment at a time. A continuation gets ONE attempt and no retry: if it
            # errors or comes back too fast we publish the segments that already passed, so a bad
            # continuation costs us length but never the post. The motion gate applies to every
            # segment, so a frantic continuation can no more post itself than a frantic opening.
            for seg in range(2, SEGMENTS + 1):
                seed = os.path.join(generate.OUT_DIR, f"_veo{seg}_seed.png")
                nxt = os.path.join(generate.OUT_DIR, f"_veo{seg}.mp4")
                try:
                    make_video.last_frame(segments[-1], seed)
                    fetch_veo.animate(seed, nxt, prompt=fetch_veo.CONTINUE + fetch_veo.MOTION)
                    s_ov, s_sky = make_video.motion_score(nxt)
                    print(f"veo segment {seg}: overall {s_ov:.2f}, sky {s_sky:.2f}")
                    if s_ov > MOTION_MAX or s_sky > SKY_MAX:
                        print(f"veo segment {seg} too fast → keeping {len(segments)} segment(s)")
                        break
                    segments.append(nxt)
                except Exception as e:
                    print(f"veo segment {seg} failed ({e}) → keeping {len(segments)} segment(s)")
                    break
            # FORWARD ONLY, native speed. Never boomerang/reverse the clip — playing footage backwards
            # is exactly the kind of artificial post-processing that is banned (water and light running
            # backwards reads as fake). Length comes from Veo itself, not from replaying frames.
            joined = make_video.chain_clips(
                segments, os.path.join(generate.OUT_DIR, "_veo_long.mp4"))
            make_video.build_reel_native(joined, overlay, audio, out_mp4)
            print(f"reel(veo native, {len(segments)} segment(s), "
                  f"overall {ov:.2f}, sky {sky:.2f}): {verse['ref']}")
        else:
            print(f"veo still too fast (overall {ov:.2f}, sky {sky:.2f}) → calm still fallback")
            make_video.build_reel_still(bg, overlay, audio, out_mp4, duration=24)
            print(f"reel(still-fallback): {verse['ref']}")
    except Exception as e:
        print(f"veo motion failed ({e}) → background-zoom still")
        make_video.build_reel_still(bg, overlay, audio, out_mp4, duration=24)
        print(f"reel(still): {verse['ref']}")

    print(f"music={os.path.basename(audio) if audio else 'none'}")

    caption = build_caption(verse, data.get("translation", ""))
    tags = hashtags.build(verse.get("theme", "믿음"))
    # record what we used so it NEVER repeats
    state["used_verses"].append(verse["ref"])
    save_state(state)
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    with open(os.path.join(generate.OUT_DIR, "_comment.txt"), "w", encoding="utf-8") as f:
        f.write(tags)  # hashtags go in the first comment, not the caption

    if args.dry_run or args.emit:
        print("\n--- caption ---\n" + caption + "\n--- comment ---\n" + tags)
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit")
    url = base.rstrip("/") + "/" + rel_path
    result = (post_instagram.publish_reel if rel_path.endswith(".mp4") else post_instagram.publish)(url, caption)
    print("published:", result)
    if isinstance(result, dict) and result.get("id"):
        print("comment:", post_instagram.comment(result["id"], tags))
        # Also to Stories. `share_to_feed` on the reel only puts it in the profile GRID, so
        # without this the account has no story presence at all. Best-effort: a story that
        # fails must never fail the post that already published.
        try:
            print("story:", post_instagram.publish_story(url))
        except Exception as e:
            print(f"story failed ({e}) — feed post already published, continuing")
        # Remember which verse each post carries, so the one private reply we're allowed to
        # send a commenter can carry the 기도문 for THAT verse's theme (dm_reply.py). Bounded
        # to ~20: Meta's private-reply window is 7 days, which is 14 posts at 2/day.
        posted = state.setdefault("posted_media", {})
        posted[result["id"]] = verse.get("theme", "믿음")
        for old in list(posted)[:-20]:
            del posted[old]
        save_state(state)


if __name__ == "__main__":
    main()
