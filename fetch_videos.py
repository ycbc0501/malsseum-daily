#!/usr/bin/env python3
"""
Fetch solemn, gently-moving nature video clips from Pexels (for Reel backgrounds).
Uses the same Pexels key as photos. Pexels License: free commercial use, no attribution.

    python3 fetch_videos.py                 # default solemn nature set
    python3 fetch_videos.py --per-query 1
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(HERE, "videos")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) malsseum-bot/1.0"

# solemn, reverent, gentle motion
QUERIES = [
    "ocean waves", "mountain clouds", "wheat field wind", "forest sunlight",
    "river stream", "calm sea sunset", "meadow wind", "sheep grazing",
    "snow mountain", "sunrise sky", "clouds moving", "light rays forest",
]


def get_key():
    key = os.environ.get("PEXELS_API_KEY")
    kf = os.path.join(HERE, "pexels_key.txt")
    if not key and os.path.exists(kf):
        key = open(kf).read().strip()
    if not key:
        raise SystemExit("Missing Pexels key (pexels_key.txt or PEXELS_API_KEY)")
    return key


def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def best_portrait_file(video_files):
    """Pick the SMALLEST portrait file that's still ≥1080 tall (keeps downloads small)."""
    portrait = [v for v in video_files if v.get("height", 0) >= v.get("width", 1)
                and v.get("height", 0) >= 1080]
    pool = portrait or [v for v in video_files if v.get("height", 0) >= v.get("width", 1)] or video_files
    pool = sorted(pool, key=lambda v: v.get("height", 99999))  # smallest first
    return pool[0]["link"] if pool else None


def fetch_one(query, dest, key=None):
    """Fetch a single portrait clip for `query` to `dest`. Used at runtime."""
    key = key or get_key()
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                     "per_page": 8, "size": "medium"})
    data = _get(f"https://api.pexels.com/videos/search?{params}", key)
    for vid in data.get("videos", []):
        link = best_portrait_file(vid.get("video_files", []))
        if link:
            _download(link, dest)
            return dest
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-query", type=int, default=1)
    args = ap.parse_args()
    key = get_key()
    os.makedirs(VIDEO_DIR, exist_ok=True)
    n = 0
    for q in QUERIES:
        params = urllib.parse.urlencode({"query": q, "orientation": "portrait",
                                         "per_page": args.per_query, "size": "medium"})
        try:
            data = _get(f"https://api.pexels.com/videos/search?{params}", key)
        except Exception as e:
            print(f"  ! {q}: {e}")
            continue
        for vid in data.get("videos", []):
            link = best_portrait_file(vid.get("video_files", []))
            if not link:
                continue
            dest = os.path.join(VIDEO_DIR, f"pexels_{vid['id']}.mp4")
            if os.path.exists(dest):
                continue
            try:
                _download(link, dest)
                mb = os.path.getsize(dest) / 1e6
                n += 1
                print(f"✓ {q:22s} → {os.path.basename(dest)}  ({mb:.1f} MB)")
            except Exception as e:
                print(f"  ! download {vid['id']}: {e}")
    print(f"\nDone. {n} clips in {VIDEO_DIR}")


if __name__ == "__main__":
    main()
