#!/usr/bin/env python3
"""
Daily 말씀 post — the hands-off orchestrator.

Run once per day (by cron / GitHub Actions / launchd). It:
  1. waits to hit 05:00 KST ± up to 10 min of random jitter,
  2. picks today's verse + a soft nature photo,
  3. renders the image,
  4. (optionally) hosts it at a public URL and publishes to Instagram.

Timing: schedule the runner to fire a little BEFORE 04:50 KST. This script then
sleeps until a random target in [04:50, 05:10] KST, so the actual post time is
5:00 ± 10 min each day. If the runner fires after the target, it posts immediately.

    python3 daily_post.py                 # full run: wait → render → publish
    python3 daily_post.py --now           # skip the wait (post right away)
    python3 daily_post.py --now --dry-run # render only, don't publish (for testing)
    python3 daily_post.py --emit          # wait → render → write metadata, NO publish
                                          #   (used by GitHub Actions: commit then publish)
    python3 daily_post.py --jitter 600    # +/- seconds of randomness (default 600 = 10min)
"""

import argparse
import os
import random
import time
from datetime import datetime, timedelta, timezone

import generate
import post_instagram

KST = timezone(timedelta(hours=9))

# default hashtags appended to every caption
HASHTAGS = "#말씀 #오늘의말씀 #성경말씀 #큐티 #묵상 #기독교 #신앙 #하나님 #은혜 #성경"


def wait_until_target(jitter_s):
    """Sleep until 05:00 KST shifted by a uniform random offset in [-jitter, +jitter]."""
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
    # deterministic rotation by KST date so a given day always maps to the same verse
    return verses[datetime.now(KST).toordinal() % len(verses)]


def pick_photo():
    pool = generate.pick_photos()
    if not pool:
        return None
    # vary by day without repeating too soon
    return pool[datetime.now(KST).toordinal() % len(pool)]


def build_caption(verse, translation):
    return f"\"{verse['text']}\"\n\n— {verse['ref']} ({translation})\n\n{HASHTAGS}"


def host_image(path):
    """
    Return a PUBLIC URL for the rendered image (Graph API requires a fetchable URL).
    Configured via env PUBLIC_IMAGE_BASE — e.g. the raw GitHub / Pages / R2 base where
    this file will be reachable. The actual upload is handled by the runner (see
    the GitHub Actions workflow, which commits the image and serves it via raw URL).
    """
    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit(
            "No PUBLIC_IMAGE_BASE set — can't give Instagram a public image URL.\n"
            "This is wired up by the runner (e.g. GitHub Actions). For a local dry run "
            "use --dry-run."
        )
    return base.rstrip("/") + "/" + os.path.basename(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", action="store_true", help="skip the timed wait")
    ap.add_argument("--dry-run", action="store_true", help="render only, do not publish")
    ap.add_argument("--emit", action="store_true",
                    help="wait+render+write metadata, no publish (for GitHub Actions)")
    ap.add_argument("--jitter", type=int, default=600, help="+/- seconds of randomness")
    ap.add_argument("--handle", default="@to_light_bible")
    args = ap.parse_args()

    if not args.now:
        wait_until_target(args.jitter)

    import json
    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        data = json.load(f)
    verse = todays_verse(data["verses"])
    photo = pick_photo()

    # render to a date-stamped path → stable, unique public URL (avoids CDN staleness)
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    rel_path = f"output/posts/{date_str}.png"
    out = os.path.join(generate.HERE, rel_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    generate.render(verse, "ivory", args.handle, out, photo=photo)
    print(f"rendered: {verse['ref']}  →  {rel_path}" + (f"  [{os.path.basename(photo)}]" if photo else "  [solid]"))

    caption = build_caption(verse, data.get("translation", ""))
    # write metadata the runner consumes (relative path + caption)
    with open(os.path.join(generate.OUT_DIR, "_path.txt"), "w") as f:
        f.write(rel_path)
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    if args.dry_run or args.emit:
        print("\n--- caption ---\n" + caption)
        print("\n--- (not publishing here) ---" if args.emit else "\n--- (dry run) ---")
        return

    url = host_image(out)
    result = post_instagram.publish(url, caption)
    print(f"published: {result}")


if __name__ == "__main__":
    main()
