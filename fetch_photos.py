#!/usr/bin/env python3
"""
Fetch soft nature photos for use as 말씀 backgrounds — from Unsplash OR Pexels.

Both need a free API key (no keyless option exists anymore):
  • Unsplash:  https://unsplash.com/developers  → create an app → copy the "Access Key"
       License: free commercial use. Their API guidelines ask for photographer
       attribution (saved to photos/credits.json so you can credit in captions).
  • Pexels:    https://www.pexels.com/api/      → copy your API key
       License: free commercial use, NO attribution required.

Save the key to a file in this folder:  unsplash_key.txt  or  pexels_key.txt
(or set env UNSPLASH_ACCESS_KEY / PEXELS_API_KEY).

Usage:
    python3 fetch_photos.py                       # default: unsplash, curated set
    python3 fetch_photos.py --provider pexels
    python3 fetch_photos.py --per-query 3
    python3 fetch_photos.py --queries "들꽃,노을,라벤더"

Then:  python3 generate.py --photos
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(HERE, "photos")
CREDITS = os.path.join(PHOTO_DIR, "credits.json")

# soft, feminine nature — flowers, sunsets, fields, woods, soft light
DEFAULT_QUERIES = [
    "flower field", "wildflowers", "spring flowers", "lavender field",
    "cherry blossom", "soft sunset", "golden hour field", "meadow",
    "misty forest", "pink flowers", "rose garden", "peony",
    "tulip field", "daisy field", "sunflower field", "autumn forest light",
    "ocean sunset", "morning grass dew", "pastel sky clouds", "magnolia",
]


def get_key(provider):
    env = {"unsplash": "UNSPLASH_ACCESS_KEY", "pexels": "PEXELS_API_KEY"}[provider]
    key = os.environ.get(env)
    keyfile = os.path.join(HERE, f"{provider}_key.txt")
    if not key and os.path.exists(keyfile):
        with open(keyfile) as f:
            key = f.read().strip()
    if not key:
        url = {"unsplash": "https://unsplash.com/developers",
               "pexels": "https://www.pexels.com/api/"}[provider]
        raise SystemExit(
            f"Missing {provider} key.\n"
            f"  1) Get a free key at {url}\n"
            f"  2) Save it to {provider}_key.txt here (or export {env})\n"
            f"  3) re-run"
        )
    return key


# Pexels/Unsplash reject the default Python-urllib User-Agent → send a normal one.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) malsseum-bot/1.0"


def _get(url, headers):
    req = urllib.request.Request(url, headers={**headers, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def fetch_unsplash(key, query, n):
    """Returns list of (id, image_url, credit_dict)."""
    headers = {"Authorization": f"Client-ID {key}"}
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait", "per_page": n})
    data = _get(f"https://api.unsplash.com/search/photos?{params}", headers)
    out = []
    for p in data.get("results", []):
        # request an exactly-cropped 1080×1350 via Unsplash's dynamic image params
        img = p["urls"]["raw"] + "&w=1080&h=1350&fit=crop&crop=entropy&q=80"
        # best-effort download ping (Unsplash API guideline)
        try:
            _get(p["links"]["download_location"], headers)
        except Exception:
            pass
        out.append((p["id"], img, {
            "photographer": p["user"]["name"],
            "link": p["user"]["links"]["html"],
            "source": "Unsplash",
        }))
    return out


def fetch_pexels(key, query, n):
    headers = {"Authorization": key}
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                     "per_page": n, "size": "large"})
    data = _get(f"https://api.pexels.com/v1/search?{params}", headers)
    out = []
    for p in data.get("photos", []):
        img = p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"]
        out.append((p["id"], img, {
            "photographer": p.get("photographer", ""),
            "link": p.get("photographer_url", ""),
            "source": "Pexels",
        }))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="unsplash", choices=["unsplash", "pexels"])
    ap.add_argument("--per-query", type=int, default=2)
    ap.add_argument("--queries")
    args = ap.parse_args()

    key = get_key(args.provider)
    fetch = {"unsplash": fetch_unsplash, "pexels": fetch_pexels}[args.provider]
    queries = [q.strip() for q in args.queries.split(",")] if args.queries else DEFAULT_QUERIES

    os.makedirs(PHOTO_DIR, exist_ok=True)
    credits = {}
    if os.path.exists(CREDITS):
        with open(CREDITS) as f:
            credits = json.load(f)

    seen, n = set(), 0
    for q in queries:
        try:
            items = fetch(key, q, args.per_query)
        except Exception as e:
            print(f"  ! {q}: {e}")
            continue
        for pid, url, credit in items:
            tag = f"{args.provider}_{pid}"
            if tag in seen:
                continue
            seen.add(tag)
            dest = os.path.join(PHOTO_DIR, f"{tag}.jpg")
            if os.path.exists(dest):
                continue
            try:
                _download(url, dest)
                credits[os.path.basename(dest)] = credit
                n += 1
                print(f"✓ {q:24s} → {os.path.basename(dest)}  ({credit['photographer']})")
            except Exception as e:
                print(f"  ! download {pid}: {e}")

    with open(CREDITS, "w") as f:
        json.dump(credits, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {n} new photos in {PHOTO_DIR}  (credits → {os.path.basename(CREDITS)})")
    print("Next:  python3 generate.py --photos")


if __name__ == "__main__":
    main()
