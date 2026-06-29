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

# diverse, sublime nature — vast, majestic, sacred. No people, no text.
SCENES = [
    "vast mountain range rising above a sea of clouds at dawn",
    "endless desert dunes under an immense glowing sky",
    "a towering waterfall plunging into a misty canyon",
    "aurora borealis shimmering over snow-capped peaks",
    "a starry night sky over a silent mountain valley",
    "dramatic sea cliffs with waves crashing at golden hour",
    "an ancient forest of giant trees pierced by god rays",
    "a vast green valley with a winding river beneath towering clouds",
    "a glacier and icy fjord under a soft polar sky",
    "rolling golden plains stretching to the far horizon at sunset",
    "layered blue misty mountains receding to infinity at dawn",
    "a single tree standing alone on a vast windswept plain",
    "sunbeams breaking through storm clouds over the open sea",
    "alpine peaks glowing rose and gold at sunrise",
    "a vast lavender field beneath a wide luminous sky",
    "a deep canyon carved in warm light and long shadows",
    "a still mirror lake reflecting immense snow mountains",
    "a heavenly cloudscape seen from above, bathed in golden light",
    "terraced rice fields under soft morning mist and warm light",
    "a vast salt flat mirroring a pastel twilight sky",
]
MOOD = (", sublime, vast, majestic, awe-inspiring, sacred and reverent atmosphere, "
        "cinematic, soft natural light, rich depth, ultra detailed, photographic")
NEGATIVE = ", no people, no person, no text, no words, no letters, no watermark, no buildings"

# where to leave empty/calm space so the verse text can sit there
SPACE = {
    ("center", "middle"): "in the center",
    ("left", "middle"): "on the left side",
    ("right", "middle"): "on the right side",
    ("center", "top"): "across the upper area",
    ("center", "bottom"): "across the lower area",
    ("left", "top"): "in the upper left",
    ("right", "top"): "in the upper right",
    ("left", "bottom"): "in the lower left",
    ("right", "bottom"): "in the lower right",
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
    space = SPACE.get(tuple(placement), "in the center")
    prompt = (SCENES[index % len(SCENES)] + MOOD
              + f", with calm uncluttered empty negative space {space} for text" + NEGATIVE)
    result = client.subscribe(MODEL, {
        "prompt": prompt, "aspect_ratio": "3:4", "safety_tolerance": 2})
    url = result["images"][0]["url"]
    urllib.request.urlretrieve(url, dest)
    return dest


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "hf_bg.png"
    print(generate_background(out, 0))
