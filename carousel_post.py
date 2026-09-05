#!/usr/bin/env python3
"""
Weekly carousel: a 3-slide post (말씀 → 묵상 → 기도) for this week's theme.
Builds the slides; the runner hosts them and publishes the carousel.

    python3 carousel_post.py --emit     # build slides + metadata, no publish (CI)
    python3 carousel_post.py            # build + publish (needs PUBLIC_IMAGE_BASE)
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

import generate
import carousel
import hashtags
import post_instagram

KST = timezone(timedelta(hours=9))
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며")
THEME_ORDER = ["위로", "평안", "담대", "믿음", "감사", "사랑", "인도", "은혜", "지혜"]
# Hashtags are built per-post from the verse's theme — see hashtags.py (Instagram caps them at 5).


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        verses = [v for v in json.load(f)["verses"]
                  if not v["text"].rstrip().rstrip(".").endswith(INCOMPLETE_ENDINGS)]
    photos = generate.calm_photos(generate.pick_photos())   # busy-centred photos bury the verse

    week = datetime.now(KST).isocalendar()[1]
    theme = THEME_ORDER[week % len(THEME_ORDER)]
    pool = [v for v in verses if v.get("theme") == theme] or verses
    # The carousel used to take pool[week % len(pool)] blind, with no idea what the daily reels had
    # just posted — so it re-published 마태복음 28:20 14 hours after the reel (08-22) and 잠언 27:17
    # 11 hours after (08-29). Two posts of the same verse in one day is exactly the duplicate that
    # gets the whole account demoted (rule 10d), so walk forward past anything Instagram already has.
    import daily_post
    recent = set(daily_post.published_refs(limit=14))
    start = week % len(pool)
    verse = pool[start]
    for step in range(len(pool)):
        cand = pool[(start + step) % len(pool)]
        if cand["ref"] not in recent:
            verse = cand
            if step:
                print(f"skipped {step} verse(s) already on the feed → {verse['ref']}")
            break
    else:
        print("every verse in this theme is already on the feed — posting the scheduled one anyway")
    photo = photos[week % len(photos)] if photos else None

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    prefix = os.path.join(posts, f"carousel-{date_str}")
    slides = carousel.build_slides(verse, photo, prefix)
    rels = [os.path.relpath(s, generate.HERE) for s in slides]
    caption = f"{verse['text']}\n[{verse['ref']}]"   # 캡션은 말씀과 출처만 (규칙 10)
    tags = hashtags.first_comment(theme)   # 안내 한 줄 + 해시태그 5개
    print(f"carousel: [{theme}] {verse['ref']}  ({len(rels)} slides)")

    with open(os.path.join(generate.OUT_DIR, "_carousel.txt"), "w") as f:
        f.write("\n".join(rels) + "\n")   # trailing newline so `while read` gets every line
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    with open(os.path.join(generate.OUT_DIR, "_comment.txt"), "w", encoding="utf-8") as f:
        f.write(tags)

    if args.emit:
        print("\n--- caption ---\n" + caption + "\n--- comment ---\n" + tags)
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit")
    urls = [base.rstrip("/") + "/" + r for r in rels]
    result = post_instagram.publish_carousel(urls, caption)
    print("published:", result)
    if isinstance(result, dict) and result.get("id"):
        print("comment:", post_instagram.comment(result["id"], tags))
        try:                                     # 말씀 slide to Stories; never fail a live post
            print("story:", post_instagram.publish_story(urls[0]))
        except Exception as e:
            print(f"story failed ({e}) — carousel already published, continuing")


if __name__ == "__main__":
    main()
