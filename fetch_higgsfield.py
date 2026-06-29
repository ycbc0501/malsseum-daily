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
    "immense towering snow mountains low on the horizon beneath a vast deep sky",
    "a colossal mountain range along a low horizon under an enormous deep sky",
    "a vast sea of clouds with towering peaks rising along a low horizon",
    "endless plains to a low horizon under a colossal dramatic deep sky",
    "a vast deep ocean to a very low horizon under an immense sky",
    "an immense glacier and peaks low on the horizon under a vast deep sky",
    "towering dunes low in the frame under an enormous deep sky",
    "a giant still lake below towering distant mountains, very low horizon",
    "vast misty valleys far below under an immense deep sky",
    "vast dramatic storm clouds over distant plains at a low horizon",
    "immense rolling hills to a low horizon under a vast deep sky",
    "a grand coastline low in the frame under an enormous deep sky",
    "vast golden grasslands to a low horizon under a colossal sky",
    "immense layered mountains low under a vast deep dawn sky",
    "a vast deep twilight sky over towering peaks on a low horizon",
    "an immense canyon rim low in the frame under a vast deep sky",
]
DRAMATIC = [   # the ~20%: full, grand, well-composed sublime scenes (legible via the scrim)
    "colossal sunbeams pouring through a vast misty ancient forest",
    "an immense thundering waterfall in a giant green canyon",
    "vast aurora borealis blazing over towering snow peaks at night",
    "enormous god-rays bursting through dramatic clouds over a vast sea",
    "an immense deep canyon glowing at golden hour",
    "the vast milky way arching over a colossal mountain range",
    "towering mountain peaks ablaze at a dramatic sunrise",
    "an endless field of wildflowers under a towering golden sky",
]
MOOD = (", sublime, vast, immense, majestic, monumental, epic grand scale, breathtaking, "
        "awe-inspiring, sacred and reverent atmosphere, REALISTIC PHOTOGRAPH, photorealistic, "
        "shot on a DSLR, natural authentic detail and texture, true-to-life colors, "
        "soft natural light, rich depth, ultra detailed")
NEGATIVE = (", no people, no person, no text, no words, no letters, no watermark, no buildings, "
            "not CGI, not a 3d render, not an illustration, not a painting, not surreal, "
            "no fake plastic artificial look")

# composition per placement: leave a CALM EMPTY area (any smooth surface) where text sits
COMP = {
    ("center", "middle"): "a vast open sky fills the upper two-thirds for the text, with the grand "
                          "landscape kept low along the bottom third (very low horizon)",
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
    TONE = (", the calm empty area is deeply and richly toned — deep saturated sky or rich "
            "calm tones, NOT pale or washed out — so white text stands out clearly")
    if full_scene:
        prompt = (DRAMATIC[index % len(DRAMATIC)] + MOOD
                  + ", epic full cinematic composition with a gently softer, richly toned area "
                    "where centered white text stays readable" + NEGATIVE)
    else:
        comp = COMP.get(tuple(placement), COMP[("center", "middle")])
        prompt = (SCENES[index % len(SCENES)] + MOOD + ", " + comp + TONE
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
