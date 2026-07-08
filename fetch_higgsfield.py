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

# Grand, cinematic scenes (Gemini follows prose, NOT keyword soup). Vast, majestic and
# awe-inspiring — a sense of divine glory — yet each keeps a calm sky / upper-center area
# for the overlaid verse. No hype-word soup; the grandeur is in the scene itself.
SCENES = [
    "a vast mountain range and green valley receding to a distant low horizon under an immense sky",
    "an endless calm ocean meeting a radiant sky at a very low horizon, god-rays over the water",
    "towering luminous clouds and sunbeams over a boundless plain, low horizon",
    "a great canyon receding into vast distance under an immense open sky",
    "immense snow-capped peaks far in the distance beyond a wide valley, low horizon",
    "a vast desert of rolling dunes stretching to a distant horizon under a dramatic sky",
    "a sweeping sea of clouds seen from a great height under a glowing sky",
    "an enormous starry night sky and the milky way over a vast dark plain, low horizon",
    "a grand golden sunrise over an endless calm sea, very low horizon",
    "a majestic glacier valley receding to distant peaks under a wide radiant sky",
    "vast rolling green hills stretching to a far horizon under towering luminous clouds",
    "an immense aurora over a vast snowy wilderness under a starry sky, low horizon",
    "a boundless flower plain stretching to a distant low horizon under a glowing sky",
    "a colossal glowing cloudscape at golden hour over a distant low land",
    "a great river winding through an immense valley to a distant horizon under a wide sky",
    "towering thunderclouds parting with radiant light over a wide calm sea, low horizon",
    "a vast alpine lake mirroring immense distant peaks under a wide radiant sky, low far shore",
    "a boundless golden wheat plain rippling to a far horizon under a dramatic glowing sky",
    "immense misty ridgelines fading into the vast distance under a soft radiant sky",
    "a great open plateau falling away to a vast distant horizon under towering clouds",
    "a vast twilight sky of soft pink and gold over a calm endless sea, very low horizon",
    # Christian / biblical places, made grand
    "the vast rocky wilderness of Sinai receding to distant mesas under an immense dramatic sky",
    "the great calm expanse of the Sea of Galilee at radiant sunrise, very low horizon",
    "the ancient walls of Jerusalem far across a vast valley at golden dawn under an immense sky",
    "a grand vineyard-covered hillside sweeping down to a distant valley under a glowing sky",
    "a solitary hill with a distant cross far off, a vast radiant sky with sunbeams above, low horizon",
    "immense olive groves on hills sweeping to a far horizon under a soft radiant sky",
    "a vast promised land of green valleys and distant blue hills under a glorious open sky",
    "the great wilderness of the Jordan valley receding to distant hills under a wide radiant sky",
    "an immense field of lilies stretching toward distant hills under a soft glowing sky, low horizon",
    "a grand ancient stone archway opening onto a vast radiant landscape beyond, low horizon",
    "a majestic waterfall plunging into a vast misty gorge, an immense open sky above",
]
COMPOSE = {
    ("center", "middle"): "Leave the upper and central part of the photo calm and simple for the "
        "overlaid verse text — it can be open sky, soft daylight, gentle water or a quiet plain "
        "background, whatever suits the scene. Place the main subject across the LOWER part of the "
        "photo, keeping the upper-center clear and easy to read text over.",
    ("left", "middle"): "Leave the left and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the right "
        "and lower part of the photo, keeping the text area clear.",
    ("right", "middle"): "Leave the right and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the left "
        "and lower part of the photo, keeping the text area clear.",
}
EVENTONE = ("CRUCIAL: keep the whole CENTER of the image — a wide horizontal band across the "
            "vertical middle — calm, open and smooth, so the overlaid verse can be read clearly. "
            "That center band must be a single even tone (evenly light OR evenly dark, no strong "
            "bright-and-dark contrast, no busy clouds, no bright cloud edge or sunbeam cutting "
            "through it). Put all the drama — towering clouds, sunbeams, peaks, detail — in the "
            "UPPER edge and LOWER part of the frame, leaving that middle band clear and quiet.")
COMPOSE_SAFE = ("Keep the composition natural and open: the horizon stays low and the scene recedes "
                "grandly into the far distance. Do NOT let any single object (a mountain, tree, "
                "building or rock) stand tall through the middle of the frame or dominate the center; "
                "keep such elements to the lower part and the far distance, never looming over the "
                "clear center band.")
QUALITY = ("It is a breathtaking, awe-inspiring cinematic landscape — vast, majestic and immense in "
           "scale and depth, with a sense of divine glory and grandeur. Radiant light and god-rays "
           "through towering luminous clouds, a glowing atmospheric sky, a sweeping epic vista; "
           "reverent, serene and glorious, like a glimpse of heaven. Photoreal and richly detailed, "
           "high dynamic range, deep cinematic light and colour, sharp and clean — a real photograph, "
           "not a 3D render, not a video game.")
NOTEXT = ("There are no people, and absolutely no text, letters, words, captions, numbers, signs, "
          "watermark or logo anywhere. It is a single full-bleed photograph that completely fills "
          "the image, edge to edge.")


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


def generate_background(dest, index=0, placement=("center", "middle"), full_scene=False,
                        model=MODEL, aspect="3:4"):
    """Generate one background → save to `dest`. Clean natural-language prompt (Gemini follows
    prose); the text area is kept clear per `placement`. `aspect` = "3:4" (feed) or "9:16" (reel)."""
    scene = SCENES[index % len(SCENES)]
    compose = COMPOSE.get(tuple(placement), COMPOSE[("center", "middle")])
    prompt = f"A breathtaking, grand cinematic photograph of {scene}. {compose} {COMPOSE_SAFE} {EVENTONE} {QUALITY} {NOTEXT}"

    if model == "gemini":
        return _gemini(prompt, dest, aspect=aspect)

    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    if model == "soul":
        url = _soul(client, prompt)
    else:
        args = {"prompt": prompt, "aspect_ratio": aspect}
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
            "generationConfig": {"imageConfig": {"aspectRatio": aspect, "imageSize": "2K"}}}
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
