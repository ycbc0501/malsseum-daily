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
# grandeur comes from the VAST SKY + distant majestic subject kept LOW on the horizon,
# so the vertically-centered text always sits on clear open sky.
SCENES = [
    "majestic snow mountains along a very low horizon, a vast deep sky filling the frame",
    "distant grand peaks low on the horizon under a colossal dramatic sky",
    "a calm vast sea meeting a very low horizon under an immense deep sky",
    "endless plains along a very low horizon under a colossal deep sky",
    "a serene lake with distant mountains low on the horizon, a huge open sky",
    "soft rolling hills along a very low horizon under a vast deep sky",
    "a quiet coastline low on the horizon under an enormous open sky",
    "golden fields along a very low horizon under a vast luminous sky",
    "distant misty mountains low on the horizon under a vast hazy sky",
    "vast dramatic storm clouds over distant plains at a very low horizon",
    "soft clouds drifting in a vast deep sky over a low distant landscape",
    "a wide calm river valley low under a vast open sky",
    "distant glaciers low on the horizon under a vast pale sky",
    "a vast lavender field low under an immense luminous sky",
    "a gentle sea at golden hour, very low horizon, a huge open sky",
    "vast grasslands along a low horizon under a dramatic deep sky",
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

# text is ALWAYS vertically centered; only the horizontal side of the empty area changes.
# Landscape is pushed to the very bottom so the centered text (verse + source) sits on clear sky.
COMP = {
    ("center", "middle"): "the middle of the frame is a vast open empty sky where the centered text "
                          "sits (room for two lines and a small caption below); keep the grand landscape "
                          "very low, only along the very bottom edge, far below the text",
    ("left", "middle"): "the left and center, vertically centered, is open empty sky where the text sits "
                        "(room for two lines and a caption below); keep the landscape to the right and the "
                        "very bottom edge, away from the text",
    ("right", "middle"): "the right and center, vertically centered, is open empty sky where the text sits "
                         "(room for two lines and a caption below); keep the landscape to the left and the "
                         "very bottom edge, away from the text",
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
