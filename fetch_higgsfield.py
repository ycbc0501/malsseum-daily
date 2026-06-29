#!/usr/bin/env python3
"""
Generate a fresh serene-nature background via the Higgsfield Cloud API (Flux Pro).
Each call returns a unique image — so backgrounds never repeat, no licensing, no Pexels.

Credentials: env HF_API_KEY + HF_API_SECRET, or a local higgsfield_key.txt with those lines.
"""

import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "flux-pro/kontext/max/text-to-image"

# serene, reverent nature scenes — no people, no text
PROMPTS = [
    "serene misty mountains at dawn, soft pastel sky, layered blue hills, ethereal fog, cinematic calm light",
    "soft pastel morning sky with gentle clouds over a calm sea, dreamy, peaceful, minimal, golden light",
    "golden hour over a quiet wildflower meadow, soft bokeh, warm gentle light, serene, shallow depth",
    "calm ocean waves under a soft pink and lavender sunset sky, minimal, tranquil, cinematic",
    "sunlight streaming through a misty forest, soft god rays, peaceful, ethereal green, calm",
    "a wheat field swaying under a vast pastel sky at golden hour, calm, cinematic, soft warm light",
    "snowy mountain peaks under a soft pastel dawn, serene, minimal, majestic, gentle clouds",
    "soft clouds drifting over a calm lake at sunrise, mirror reflection, peaceful, dreamy pastel tones",
]
NEGATIVE = ", no people, no person, no text, no words, no letters, no watermark"


def _credentials():
    key, sec = os.environ.get("HF_API_KEY"), os.environ.get("HF_API_SECRET")
    kf = os.path.join(HERE, "higgsfield_key.txt")
    if (not key or not sec) and os.path.exists(kf):
        for line in open(kf):
            if line.startswith("HF_API_KEY="):
                key = line.split("=", 1)[1].strip()
            elif line.startswith("HF_API_SECRET="):
                sec = line.split("=", 1)[1].strip()
    if not (key and sec):
        raise SystemExit("Missing HF_API_KEY / HF_API_SECRET")
    return f"{key}:{sec}"


def generate_background(dest, index=0):
    """Generate one serene background → save to `dest`, return the path."""
    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    prompt = PROMPTS[index % len(PROMPTS)] + NEGATIVE
    result = client.subscribe(MODEL, {
        "prompt": prompt, "aspect_ratio": "3:4", "safety_tolerance": 2})
    url = result["images"][0]["url"]
    urllib.request.urlretrieve(url, dest)
    return dest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "hf_bg.png"
    print(generate_background(out, 0))
