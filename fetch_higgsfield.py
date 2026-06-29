#!/usr/bin/env python3
"""
Generate a fresh serene-nature background via the Higgsfield Cloud API (Flux Pro).
Each call returns a unique image — so backgrounds never repeat, no licensing, no Pexels.

Credentials: env HF_API_KEY + HF_API_SECRET, or a local higgsfield_key.txt with those lines.
"""

import base64
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "gemini"        # default backend: Nano Banana Pro (photoreal, clean, respects "no text")
GEMINI_MODEL = "gemini-3-pro-image"
FLUX = "flux-pro/kontext/max/text-to-image"   # Higgsfield fallback options
SOUL_APP = "v1/text2image/soul"
SOUL_BASE = "https://platform.higgsfield.ai"

# diverse, sublime nature — each has a CALM EMPTY ZONE (not only sky: also water, field,
# mist, snow, smooth ground) where the verse text sits. Vast, majestic, sacred. No people/text.
# grandeur from a VAST SKY / open area + the subject kept LOW or to one side, so the
# vertically-centered text always sits on a clear area. Diverse, beautiful, dignified.
SCENES = [
    "a calm vast sea meeting a very low horizon under an immense deep sky",
    "majestic distant mountains low on the horizon under a vast deep sky",
    "endless golden wheat fields along a very low horizon under a colossal sky",
    "a vast field of blooming wildflowers low under a huge soft pastel sky",
    "an immense lavender field low on the horizon under a vast luminous sky",
    "soft morning fog over a low valley under a vast pale sky",
    "vast desert dunes along a low horizon under an enormous glowing sky",
    "a serene snow plain along a low horizon under a vast pastel sky",
    "a calm mirror lake with distant low mountains under a huge open sky",
    "a vast sea of soft clouds seen from above under an open sky",
    "a starry night sky and milky way over a low dark horizon",
    "golden god-rays streaming through soft clouds in a vast open sky",
    "rolling autumn hills low on the horizon under a vast deep sky",
    "soft pastel sunrise clouds filling a vast open sky over a low calm sea",
    "delicate cherry blossom branches framing a vast open pastel sky",
    "vast green rolling meadows along a very low horizon under a deep sky",
    "a vast tulip field in soft rows along a very low horizon under a pastel sky",
    "a wide calm river winding through a low valley under a vast sky",
    "terraced green tea fields in soft morning mist under an open sky",
    "soft golden pampas grass swaying low under a vast warm sky",
    "a tranquil olive grove on a low hillside under a soft Mediterranean sky",
    "a serene rice paddy mirroring a vast pastel dawn sky, very low horizon",
    "gentle ocean waves rolling onto a smooth empty shore under a soft sky",
    "a single graceful tree alone on a vast plain under an enormous sky",
    "soft pink and lavender twilight clouds over a calm low sea",
    "a quiet pine forest edge under soft drifting mist and open sky",
    "rolling sand dunes at golden hour with soft shadows, low horizon",
    "a calm alpine lake reflecting a vast clear sky, low far shore",
]
DRAMATIC = [   # the ~20%: fuller hyperreal scenes (incl. sacred architecture) — legible via the outline
    "the vast light-filled nave of a real Gothic stone cathedral, sunbeams through stained glass, architectural photography",
    "an ancient stone monastery cloister with soft daylight, architectural photography",
    "towering weathered marble columns of an ancient temple in warm golden light",
    "an immense real grand canyon glowing at golden hour, landscape photography",
    "a thundering waterfall in a vast lush green canyon, fine mist",
    "brilliant aurora borealis over real snow-capped peaks at night, long exposure photo",
    "the milky way arching over a vast silent mountain range, astrophotography",
    "god-rays bursting through dramatic storm clouds over a vast sea",
    "towering misty mountain peaks ablaze at a real dramatic sunrise",
    "a vast field of sunflowers under a dramatic late-afternoon sky",
    "a serene reflecting pool in a quiet stone courtyard, soft light",
    "sunlight streaming through a misty ancient redwood forest, god-rays",
]
MOOD = (", sublime, vast, majestic, awe-inspiring, sacred and reverent, elegant and beautiful, "
        "HYPERREALISTIC PHOTOGRAPH, ultra-realistic, shot on a full-frame DSLR with a prime lens, "
        "8k, sharp natural focus, true-to-life detail and lighting, natural soft light, rich depth")
NEGATIVE = (", no people, no person, no text, no words, no letters, no watermark, no modern buildings, "
            "no city, no cars, NOT CGI, not a 3d render, not a video game, not an illustration, "
            "not a painting, not surreal, no fake plastic artificial look, not tacky, not cheesy")

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


def generate_background(dest, index=0, placement=("center", "middle"), full_scene=False, model=MODEL):
    """Generate one sublime background → save to `dest`, return the path.
    Default: Nano Banana Pro (model='gemini'). Higgsfield flux/soul/reve also supported.
    ~80%: a calm empty area where the text sits; ~20% (full_scene): a fuller dramatic scene."""
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

    if model == "gemini":
        return _gemini(prompt, dest)

    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    if model == "soul":
        url = _soul(client, prompt)
    else:
        args = {"prompt": prompt, "aspect_ratio": "3:4"}
        if "flux" in model:
            args["safety_tolerance"] = 2
        url = client.subscribe(model, args)["images"][0]["url"]
    urllib.request.urlretrieve(url, dest)
    return dest


def _gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    kf = os.path.join(HERE, "gemini_key.txt")
    if not key and os.path.exists(kf):
        for line in open(kf):
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("Missing GEMINI_API_KEY")
    return key


def _gemini(prompt, dest, aspect="3:4"):
    """Nano Banana Pro (Gemini 3 Pro Image) → save image to dest."""
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"imageConfig": {"aspectRatio": aspect}}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={_gemini_key()}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    data = json.load(urllib.request.urlopen(req, timeout=180))
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            with open(dest, "wb") as f:
                f.write(base64.b64decode(part["inlineData"]["data"]))
            return dest
    raise RuntimeError("gemini: no image in response")


def _soul(client, prompt, wh="1536x2048"):
    """Higgsfield Soul (flagship). Its response shape differs from the SDK's, so we call
    the endpoint via the SDK's transport and poll the status ourselves."""
    t = client._transport
    job = t.request("POST", f"{SOUL_BASE}/{SOUL_APP}",
                    json={"params": {"prompt": prompt, "width_and_height": wh}}, timeout=120).json()
    jid = job["id"]
    for _ in range(60):
        st = t.request("GET", f"{SOUL_BASE}/requests/{jid}/status", timeout=30).json()
        if st["status"] == "completed":
            return st["images"][0]["url"]
        if st["status"] in ("failed", "error", "canceled"):
            raise RuntimeError(f"soul {st['status']}")
        time.sleep(3)
    raise RuntimeError("soul timeout")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "hf_bg.png"
    print(generate_background(out, 0))
