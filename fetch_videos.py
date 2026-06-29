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

# allowed keywords (pure nature, no people/animals/structures)
QUERIES = ["waves", "cloud", "sun", "field", "flower field"]

# skip clips whose URL slug hints at a human / animal / man-made thing
BLOCK_SLUG = (
    "road", "street", "car", "truck", "vehicle", "traffic", "building", "city",
    "house", "home", "bridge", "boat", "ship", "train", "plane", "airport",
    "person", "people", "man", "woman", "girl", "boy", "child", "kid", "baby",
    "crowd", "hand", "face", "portrait", "dog", "cat", "bird", "horse", "cow",
    "sheep", "animal", "fish", "deer", "duck", "wedding", "couple", "window",
    "phone", "tower", "wind-turbine", "windmill", "farmer", "worker",
)


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
    """Pick a crisp portrait file: at least 1920 tall (so we never upscale to the
    1080×1920 reel), the smallest such to avoid 4K bloat; else the largest available."""
    portrait = [v for v in video_files if v.get("height", 0) >= v.get("width", 1)] or video_files
    big = sorted([v for v in portrait if v.get("height", 0) >= 1920], key=lambda v: v.get("height", 0))
    if big:
        return big[0]["link"]
    return sorted(portrait, key=lambda v: v.get("height", 0), reverse=True)[0]["link"] if portrait else None


def fetch_one(query, dest, pick=0, key=None):
    """Fetch a portrait clip for `query` to `dest`, skipping human/animal/man-made
    clips (by URL slug). `pick` rotates which result is chosen for day-to-day variety."""
    key = key or get_key()
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                     "per_page": 15, "size": "medium"})
    data = _get(f"https://api.pexels.com/videos/search?{params}", key)
    vids = [v for v in data.get("videos", [])
            if not any(b in v.get("url", "").lower() for b in BLOCK_SLUG)]
    if not vids:
        vids = data.get("videos", [])
    if not vids:
        return None
    for off in range(len(vids)):
        vid = vids[(pick + off) % len(vids)]
        link = best_portrait_file(vid.get("video_files", []))
        if link:
            _download(link, dest)
            return dest
    return None


def candidates(query, key=None):
    """Return [(video_id, portrait_link)] for a query, filtered for people/animals/structures."""
    key = key or get_key()
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                     "per_page": 30, "size": "medium"})
    data = _get(f"https://api.pexels.com/videos/search?{params}", key)
    out = []
    for vid in data.get("videos", []):
        if any(b in vid.get("url", "").lower() for b in BLOCK_SLUG):
            continue
        link = best_portrait_file(vid.get("video_files", []))
        if link:
            out.append((vid["id"], link, vid.get("duration", 0)))
    out.sort(key=lambda t: t[2], reverse=True)   # longer clips first (smoother slow-mo)
    return out


def fetch_by_id(vid_id, dest, key=None):
    """Fetch a specific (human-approved) Pexels clip by id."""
    key = key or get_key()
    data = _get(f"https://api.pexels.com/videos/videos/{vid_id}", key)
    link = best_portrait_file(data.get("video_files", []))
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
