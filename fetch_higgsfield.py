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

# diverse, sublime nature with a big OPEN SKY (so text sits on clean sky, not crossed
# by the landscape). Vast, majestic, sacred. No people, no text.
SCENES = [
    "a vast calm ocean meeting the sky at a low horizon",
    "endless plains stretching to a low horizon under an immense sky",
    "a distant mountain range low on the horizon under a vast open sky",
    "a serene sea with gentle waves under a boundless clear sky",
    "soft rolling hills low on the horizon beneath an endless sky",
    "a tranquil lake and a low far shore under a vast reflected sky",
    "golden wheat fields low in the frame under a wide open sky",
    "a misty layered mountain horizon under a luminous open sky",
    "a quiet coastline with a low horizon under a soft open sky",
    "distant snow mountains low on the horizon under a pastel sky",
    "a wide desert of low dunes under an immense glowing sky",
    "a calm meadow stretching to a low horizon under a vast sky",
    "gentle sea and sky at golden hour with a very low horizon",
    "a vast lavender field low in the frame under a wide luminous sky",
    "layered distant blue mountains low under a soft dawn sky",
    "soft clouds drifting across a vast sky over a far low landscape",
]
MOOD = (", sublime, vast, majestic, awe-inspiring, sacred and reverent atmosphere, "
        "cinematic, soft natural light, rich depth, ultra detailed, photographic")
NEGATIVE = (", no people, no person, no text, no words, no letters, no watermark, "
            "no buildings, nothing crossing the sky")

# composition per placement: keep the TEXT area clean empty sky, push scenery away from it
COMP = {
    ("center", "middle"): "a vast expanse of clean empty open sky fills the upper and central "
                          "area for text, with a very low horizon and all landscape kept in the lower third",
    ("center", "top"): "clean empty open sky across the upper area for text, landscape kept low",
    ("center", "bottom"): "a calm smooth empty foreground across the lower area for text, "
                          "with the open sky and horizon in the upper portion",
    ("left", "middle"): "clean empty open sky on the left side for text, scenery only on the right",
    ("right", "middle"): "clean empty open sky on the right side for text, scenery only on the left",
    ("left", "top"): "clean empty open sky in the upper left for text, scenery low on the right",
    ("right", "top"): "clean empty open sky in the upper right for text, scenery low on the left",
    ("left", "bottom"): "a calm smooth empty area in the lower left for text, scenery in the upper right",
    ("right", "bottom"): "a calm smooth empty area in the lower right for text, scenery in the upper left",
}


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


def generate_background(dest, index=0, placement=("center", "middle")):
    """Generate one sublime nature background with calm negative space where the text
    will sit (per `placement`) → save to `dest`, return the path."""
    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    comp = COMP.get(tuple(placement), COMP[("center", "middle")])
    prompt = (SCENES[index % len(SCENES)] + MOOD + ", " + comp
              + ", generous text-safe negative space, unobstructed, minimal" + NEGATIVE)
    result = client.subscribe(MODEL, {
        "prompt": prompt, "aspect_ratio": "3:4", "safety_tolerance": 2})
    url = result["images"][0]["url"]
    urllib.request.urlretrieve(url, dest)
    return dest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "hf_bg.png"
    print(generate_background(out, 0))
