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


# The claim window, in minutes before the target. It is exactly the cron spacing on purpose:
# with hourly crons, one and only one run in the chain can ever land inside (0, 60], so two runs
# can never claim the same slot concurrently and double-post. A run that arrives after the target
# claims nothing — unless it is the LAST cron of the chain (--catchup), which posts late rather
# than let the slot go empty.
CLAIM_WINDOW_MIN = 60

# The chain spans 4 hours (first cron to last). If the target has passed by at least that much,
# every cron in the chain fired late and none of them could claim, so the slot really is empty and
# --catchup posts it late. Any smaller lateness means an earlier cron DID claim it, and the catchup
# run must stand down rather than publish a second copy.
CATCHUP_AFTER_MIN = 240


def wait_until_target(jitter_s, hour=5, catchup=False):
    """Sleep until the target hour. Returns False if this run is too early to claim the slot.

    2026-08-28: GitHub's scheduler went from ~30 min late to 4-5 HOURS late. The old design was
    one cron fired 2h early plus a wait, so a 4h delay meant the target had already passed and
    the post went out at whatever hour the runner happened to start — 19:00 KST posts landed at
    21:30, 22:35, even 10:28. Reach fell from ~350 views to ~50 and did not recover.

    The fix is a CHAIN of hourly crons across the lead window. Each run asks how far it is from
    the target: too early and it exits in seconds so a later, closer cron takes the slot; near or
    past the target it posts. That absorbs several hours of scheduler drift at the cost of a few
    seconds per skipped run, instead of one run idling for hours against the job timeout."""
    now = datetime.now(KST)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    target += timedelta(seconds=random.randint(-jitter_s, jitter_s))
    delay = (target - now).total_seconds()
    if delay > CLAIM_WINDOW_MIN * 60:
        print(f"{delay/60:.0f} min before {target:%H:%M} KST — too early, leaving the slot to a later cron")
        return False
    if delay <= 0:
        late = -delay / 60
        if not (catchup and late >= CATCHUP_AFTER_MIN):
            print(f"{late:.0f} min past {target:%H:%M} KST — an earlier cron owns this slot, standing down")
            return False
        print(f"target {target:%H:%M:%S} KST passed by {late:.0f} min and the whole chain fired late → posting late")
        return True
    print(f"sleeping {int(delay)}s → posting at {target:%Y-%m-%d %H:%M:%S} KST")
    time.sleep(delay)
    return True


def slot_already_filled(hour):
    """True if this half of the day already has a post on Instagram (KST).

    The guard that makes the cron chain safe, and the last line of defence against the duplicate
    that started this: even with the ledger lost AND several crons firing, the account itself
    says whether the slot is taken. Morning owns 00:00-11:59 KST, evening 12:00-23:59."""
    try:
        import post_instagram
        today = datetime.now(KST).date()
        want_pm = hour >= 12
        for m in post_instagram.recent_media(limit=8):
            ts = m.get("timestamp") or ""
            when = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(KST)
            if when.date() == today and (when.hour >= 12) == want_pm:
                print(f"{'evening' if want_pm else 'morning'} slot already posted at {when:%H:%M} KST ({m.get('permalink')}) → skipping")
                return True
        return False
    except Exception as e:
        print(f"slot check failed ({e}) — proceeding rather than skipping a post")
        return False


def published_refs(limit=25):
    """Verse refs Instagram itself says we already posted, newest first.

    The local `used_verses` ledger is committed by the LAST workflow step, so a run that
    published and then lost the ledger push (a rebase conflict against a concurrently pushing
    bot — 2026-08-26) leaves the post live and the ledger stale, and the next run happily picks
    the SAME verse and the SAME scene. That shipped 잠언 18:10 twice (08-26, 08-28) and
    잠언 27:17 twice (08-29), and duplicate posts get the whole ACCOUNT demoted, not just the
    repeat. So the ledger is no longer trusted alone: the account's own captions are the truth.

    Best-effort — if the API call fails we fall back to the ledger rather than skip the post."""
    import re
    try:
        import post_instagram
        refs = []
        for m in post_instagram.recent_media(limit=limit):
            found = re.search(r"\[([^\[\]]+)\]", m.get("caption") or "")
            if found:
                refs.append(found.group(1).strip())
        return refs
    except Exception as e:
        print(f"published_refs failed ({e}) — falling back to the local ledger alone")
        return []


def last_published():
    """{verse ref: latest publish date} across every post we have ever recorded.

    The cycle used to reset by emptying used_verses, which made the pool wrap every 49 days and
    re-publish a verse whose caption was byte-identical to one from seven weeks earlier. Instagram
    read ten of those as 퍼온 콘텐츠 and restricted the account's reach. metrics.json remembers all
    of it, so even after a reset the oldest verse is chosen instead of the first one in the file."""
    try:
        with open(os.path.join(generate.HERE, "metrics.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"metrics.json unreadable ({e}) — falling back to ledger order alone")
        return {}
    seen = {}
    for post in data.values():
        ref, when = post.get("ref"), (post.get("published") or "")[:10]
        if ref and when:
            seen[ref] = max(seen.get(ref, ""), when)
    return seen


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
    """The caption is the 말씀 and its reference. Nothing else.

    Everything that talks ABOUT the account — the follow line — lives in the first comment
    (`hashtags.first_comment`). Decided 2026-08-01 on evidence: Instagram folds the caption
    behind "더 보기", and on a real post the cut landed right after the reference, so a CTA
    there shipped invisible. It also contradicted the constitution, which says the verse leads
    and the account never sells. (A share ask was briefly put back here on 2026-08-05 by a
    branch that had not seen this finding; it is removed again for the same two reasons.)"""
    return f"{verse['text']}\n[{verse['ref']}]"


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
    # Set on the LAST cron of each chain only: it posts late rather than leave the slot empty.
    ap.add_argument("--catchup", action="store_true")
    args = ap.parse_args()

    if not args.now:
        if not wait_until_target(args.jitter, args.hour, args.catchup) or slot_already_filled(args.hour):
            # Nothing to publish. The workflow reads this file and skips the remaining steps.
            os.makedirs(generate.OUT_DIR, exist_ok=True)
            open(os.path.join(generate.OUT_DIR, "_skip"), "w").close()
            return

    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    # safety: drop any verse that ends mid-clause so it can never be posted
    verses = [v for v in data["verses"]
              if not v["text"].rstrip().rstrip(".").endswith(INCOMPLETE_ENDINGS)]
    photos = generate.calm_photos(generate.pick_photos())   # fallback backgrounds if Higgsfield is unavailable (calm centres only — the verse must stay legible)

    state = load_state()
    # Trust Instagram over the local ledger — see published_refs().
    live = published_refs()
    if live:
        added = [r for r in live if r not in state["used_verses"]]
        if added:
            print(f"ledger was missing {len(added)} published verse(s) → recovered from Instagram: {added}")
            state["used_verses"].extend(added)
    unused = [v for v in verses if v["ref"] not in state["used_verses"]]
    if not unused:                       # whole pool shown → start a new cycle
        state["used_verses"] = []
        unused = verses
    # Oldest first. Within the cycle everything here is unpublished and this changes nothing; after
    # a reset it is what stops the pool replaying its own order seven weeks later.
    ago = last_published()
    unused.sort(key=lambda v: ago.get(v["ref"], ""))
    # this week's theme → draw from it (fall back to any unused if its verses run out)
    theme = THEME_ORDER[datetime.now(KST).isocalendar()[1] % len(THEME_ORDER)]
    pool = [v for v in unused if v.get("theme") == theme] or unused
    # within the theme, gently spread across books (least-posted book first) for balance — but books
    # MAY repeat; only VERSES never repeat (the used_verses ledger guarantees that).
    book = lambda r: r.rsplit(" ", 1)[0]
    used_books = Counter(book(r) for r in state["used_verses"])
    verse = min(pool, key=lambda v: (ago.get(v["ref"], ""), used_books[book(v["ref"])],
                                     verses.index(v)))
    n = len(state["used_verses"])
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)

    # REEL (text always centered — reads best in motion). Two background sources, alternated
    # for variety: (a) real Pexels footage (clouds/fields, gently moving) with a white-text
    # overlay, and (b) a Nano Banana still with a subtle Ken Burns zoom (adaptive color).
    # Verse-first (2026-07-30): the verse sits in the UPPER third over the empty part of the frame,
    # and COMPOSE anchors the subject in the lower third to leave that space genuinely open.
    placement = ("center", "top")
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
    # The verse must land on ONE precisely-contrasting tone. COMPOSE asks the model for a flat even
    # area, but a prompt is a request, not a guarantee — so we MEASURE the render under the real glyph
    # mask and regenerate when it fails. Same shape as the composition and motion gates: the pipeline
    # never trusts a generator it can check. Attempts are bounded by rule 1's build budget.
    ink = generate.verse_ink(verse, canvas=generate.REEL, placement=placement, grow=5)
    AREA_TRIES = 3
    try:
        for attempt in range(1, AREA_TRIES + 1):
            fetch_higgsfield.generate_checked(bg, scene_i, placement, aspect="9:16", var_t=post_i)
            ok, why, stats = generate.text_area_ok(bg, ink, canvas=generate.REEL)
            print(f"text-area gate attempt {attempt}: {why} "
                  f"(contrast {stats['contrast']}, spread {stats['spread']}, mean {stats['mean']})")
            if ok:
                break
            post_i += 1        # a different light/angle next try, not the same prompt again
        state["scene_i"] = scene_i + 1
        state["post_i"] = post_i + 1
        scene_cats.append(scene_cat)
        del scene_cats[:-4]   # keep only the last few themes
        print(f"background: nano-banana 9:16 (scene {scene_i}, theme {scene_cat})")
    except Exception as e:
        print(f"higgsfield failed ({e}) → photo pool fallback")
        used_photos = state.setdefault("used_photos", [])
        pool_p = [p for p in photos if os.path.basename(p) not in used_photos] or photos
        # Rank the fallback pool by the SAME measurement, so the photo path obeys the same rule
        # instead of a looser proxy. Ledger order still wins; this only breaks ties among unused.
        if pool_p:
            scored = sorted(pool_p, key=lambda p: -generate.text_area_contrast(
                p, ink, canvas=generate.REEL)[0])
            photo = scored[0]
            used_photos.append(os.path.basename(photo))
            c, sd, mean, _fg = generate.text_area_contrast(photo, ink, canvas=generate.REEL)
            print(f"photo fallback: {os.path.basename(photo)} (contrast {c:.2f}, spread {sd:.1f})")
    generate.cover_crop(Image.open(photo or bg), *generate.REEL).save(bg, "PNG")
    overlay = os.path.join(generate.OUT_DIR, "_overlay.png")
    # Final measurement of what actually shipped — recorded in _meta.json so metrics.py can correlate
    # legibility with performance, and visible in the log even when the gate had to give up.
    area_ok, area_why, area_stats = generate.text_area_ok(bg, ink, canvas=generate.REEL)
    if not area_ok:
        print(f"WARNING: shipping with an imperfect text area ({area_why}) — backing carries it")
    generate.render_text_overlay(verse, overlay, canvas=generate.REEL, placement=placement, bg=bg)
    # Veo → REAL motion at NATIVE speed (no slow-mo: stretching made it coarse). An automatic motion
    # gate rejects an over-animated clip (racing/timelapse clouds or churning water): retry once, and
    # only if it is STILL too fast fall back to a calm still — a bad-motion clip can never post itself.
    # Tightened 2026-08-05: 2.6/0.7 was ~2x the calm reference and let visibly racing clouds and
    # churning water through (published reels the account owner flagged). Scored against the local
    # clip library, calm sits at 1.7/0.35 and frantic city at 7.3/0.4, so the bar now sits just
    # above calm instead of halfway to frantic.
    MOTION_MAX, SKY_MAX = 2.0, 0.45
    n_segments = 0          # recorded in _meta.json so metrics.py can measure length changes
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
            n_segments = len(segments)
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
    tags = hashtags.first_comment(verse.get("theme", "믿음"))   # 안내 한 줄 + 해시태그 5개
    # record what we used so it NEVER repeats
    state["used_verses"].append(verse["ref"])
    save_state(state)
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    with open(os.path.join(generate.OUT_DIR, "_comment.txt"), "w", encoding="utf-8") as f:
        f.write(tags)  # hashtags go in the first comment, not the caption
    # What we CHOSE for this post. metrics.py pairs it with what Instagram reports, so a format
    # change (reel length, theme) becomes a measurable number instead of an opinion. Written here
    # because the publish itself happens later, in the workflow's post_instagram.py step.
    with open(os.path.join(generate.OUT_DIR, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"ref": verse["ref"], "theme": verse.get("theme", "믿음"),
                   "date": date_str, "format": "reel",
                   "segments": n_segments,
                   "duration": round(make_video._duration(out_mp4), 2),
                   # legibility of what actually shipped, so metrics.py can correlate a clean
                   # text area with performance instead of us assuming it matters
                   "text_contrast": area_stats["contrast"],
                   "text_spread": area_stats["spread"],
                   # The follow CTA left the caption on 2026-08-01 (rule 10). metrics.report()
                   # groups on this, so the change is answerable later instead of argued about;
                   # `follows` is the column that settles it. Derived, never hand-set — if the
                   # caption ever carries the CTA again this flips on its own.
                   "cta_in_caption": hashtags.FOLLOW_CTA in caption},
                  f, ensure_ascii=False)

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
        # NOTE: in production this branch never runs — the workflow calls daily_post.py with
        # --emit (which returns above) and publishes via post_instagram.py, whose CLI does the
        # story + metrics recording. This path exists for a local end-to-end publish, so it
        # must do the SAME things, not a second set of things.
        try:                                   # story is best-effort; the feed post already went
            print("story:", post_instagram.publish_story(url))
        except Exception as e:
            print(f"story failed ({e}) — feed post already published, continuing")
        # Which verse each post carries, so dm_reply.py can look up its theme. Bounded to ~20:
        # Meta's private-reply window is 7 days, which is 14 posts at 2/day.
        posted = state.setdefault("posted_media", {})
        posted[result["id"]] = verse.get("theme", "믿음")
        for old in list(posted)[:-20]:
            del posted[old]
        save_state(state)
        import metrics
        metrics.record(result["id"], json.load(
            open(os.path.join(generate.OUT_DIR, "_meta.json"), encoding="utf-8")))


if __name__ == "__main__":
    main()
