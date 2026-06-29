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
import post_instagram

KST = timezone(timedelta(hours=9))
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며")
THEME_ORDER = ["위로", "평안", "담대", "믿음", "감사", "사랑", "인도", "은혜", "지혜"]
HASHTAGS = "#성경 #말씀 #오늘의말씀 #말씀묵상 #큐티 #말씀스타그램 #빛으로"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(generate.HERE, "verses.json"), encoding="utf-8") as f:
        verses = [v for v in json.load(f)["verses"]
                  if not v["text"].rstrip().rstrip(".").endswith(INCOMPLETE_ENDINGS)]
    photos = generate.pick_photos()

    week = datetime.now(KST).isocalendar()[1]
    theme = THEME_ORDER[week % len(THEME_ORDER)]
    pool = [v for v in verses if v.get("theme") == theme] or verses
    verse = pool[week % len(pool)]
    photo = photos[week % len(photos)] if photos else None

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    posts = os.path.join(generate.HERE, "output", "posts")
    os.makedirs(posts, exist_ok=True)
    prefix = os.path.join(posts, f"carousel-{date_str}")
    slides = carousel.build_slides(verse, photo, prefix)
    rels = [os.path.relpath(s, generate.HERE) for s in slides]
    caption = f"{verse['text']}\n[{verse['ref']}]"
    print(f"carousel: [{theme}] {verse['ref']}  ({len(rels)} slides)")

    with open(os.path.join(generate.OUT_DIR, "_carousel.txt"), "w") as f:
        f.write("\n".join(rels))
    with open(os.path.join(generate.OUT_DIR, "_caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    with open(os.path.join(generate.OUT_DIR, "_comment.txt"), "w", encoding="utf-8") as f:
        f.write(HASHTAGS)

    if args.emit:
        print("\n--- caption ---\n" + caption)
        return

    base = os.environ.get("PUBLIC_IMAGE_BASE")
    if not base:
        raise SystemExit("set PUBLIC_IMAGE_BASE or use --emit")
    urls = [base.rstrip("/") + "/" + r for r in rels]
    result = post_instagram.publish_carousel(urls, caption)
    print("published:", result)
    if isinstance(result, dict) and result.get("id"):
        print("comment:", post_instagram.comment(result["id"], HASHTAGS))


if __name__ == "__main__":
    main()
