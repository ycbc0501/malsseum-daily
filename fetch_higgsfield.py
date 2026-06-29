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

# diverse, sublime nature — each has a CALM EMPTY ZONE (not only sky: also water, field,
# mist, snow, smooth ground) where the verse text sits. Vast, majestic, sacred. No people/text.
SCENES = [
    "a vast calm ocean meeting a low horizon",
    "endless plains rolling to a low far horizon",
    "soft morning fog drifting over a quiet valley",
    "a smooth wide snowfield under gentle soft light",
    "smooth sculpted golden sand dunes in soft light",
    "a still mirror-calm lake at dawn",
    "a quiet wildflower meadow in soft focus",
    "distant misty layered mountains fading into haze",
    "a calm coastline with a low horizon and smooth water",
    "soft rolling green hills under gentle light",
    "a gentle sea at golden hour, very low horizon",
    "a vast lavender field under soft luminous light",
    "soft clouds drifting over a far low landscape",
    "soft pampas grass swaying in warm golden light",
    "a serene riverbank with smooth still water",
    "a tranquil tea field in soft morning mist",
]
DRAMATIC = [   # the ~20%: full, well-composed sublime scenes (legible via the scrim)
    "sunbeams streaming through a misty ancient forest",
    "a powerful waterfall in a lush green canyon",
    "aurora borealis over snow-capped peaks at night",
    "god-rays bursting through dramatic clouds over the sea",
    "a deep canyon glowing warm at golden hour",
    "the milky way over a silent mountain range",
    "misty mountain peaks at a dramatic sunrise",
    "a field of wildflowers glowing in golden backlight",
]
MOOD = (", sublime, vast, majestic, awe-inspiring, sacred and reverent atmosphere, "
        "cinematic, soft natural light, rich depth, ultra detailed, photographic")
NEGATIVE = (", no people, no person, no text, no words, no letters, no watermark, no buildings")

# composition per placement: leave a CALM EMPTY area (any smooth surface) where text sits
COMP = {
    ("center", "middle"): "with a large calm, smooth, uncluttered empty area filling the center "
                          "(open sky, calm water, mist, snow, or soft ground) for text, detail kept to the edges",
    ("center", "top"): "with a calm smooth empty area across the upper portion for text, detail kept lower",
    ("center", "bottom"): "with a calm smooth empty area across the lower portion for text, detail kept higher",
    ("left", "middle"): "with a calm smooth empty area on the left for text, detail only on the right",
    ("right", "middle"): "with a calm smooth empty area on the right for text, detail only on the left",
    ("left", "top"): "with a calm smooth empty area in the upper left for text, detail lower right",
    ("right", "top"): "with a calm smooth empty area in the upper right for text, detail lower left",
    ("left", "bottom"): "with a calm smooth empty area in the lower left for text, detail upper right",
    ("right", "bottom"): "with a calm smooth empty area in the lower right for text, detail upper left",
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


def generate_background(dest, index=0, placement=("center", "middle"), full_scene=False):
    """Generate one sublime nature background → save to `dest`, return the path.
    Default (~80%): a calm empty area where the text sits (per `placement`).
    full_scene (~20%): a fuller, dramatic, well-composed scene (legible via the scrim)."""
    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    if full_scene:
        prompt = (DRAMATIC[index % len(DRAMATIC)] + MOOD
                  + ", epic full cinematic composition with a gently softer, less busy area "
                    "where centered text stays readable" + NEGATIVE)
    else:
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
