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

# Grand, cinematic scenes — DELIBERATELY DIVERSE in subject (mountains, seas, forests,
# deserts, fields, canyons, lakes, gardens…), so the feed never looks like the same cloudy
# sky over and over. Each scene carries its OWN light/mood (the QUALITY block no longer
# forces clouds or god-rays onto everything). Each still recedes into open distance, so a
# calmer area for the verse falls naturally near the center. Ordered to alternate the look
# post-to-post. No hype-word soup; the grandeur is in the scene itself.
SCENES = [
    "a vast mountain range and green valley receding to a distant horizon at golden hour",
    "an immense turquoise ocean and dramatic coastline seen from a high cliff, very low horizon",
    "a colossal waterfall thundering into a lush green misty gorge",
    "an endless desert of golden sand dunes rippling to a far horizon at sunrise",
    "a vast ancient forest of giant redwood trees with soft light falling through the canopy",
    "a boundless field of purple lavender stretching to distant hills at golden hour",
    "a grand red-rock canyon receding into immense depth at sunset",
    "a serene alpine lake perfectly mirroring towering snow-capped peaks",
    "rolling autumn hills ablaze with crimson and gold forest fading to a far horizon",
    "cherry blossom trees in full bloom along a calm river below distant mountains",
    "a shimmering green aurora over a vast snowy wilderness at night, low horizon",
    "a great river winding through an immense green valley toward distant blue mountains",
    "a vast meadow of wildflowers sweeping toward far snow-capped peaks",
    "terraced rice paddies curving down a vast misty mountainside at dawn",
    "a monumental glacier and still icy fjord under a soft polar sky",
    "an immense sea of clouds glowing at sunrise seen from a high summit",
    "a golden wheat field stretching endlessly under warm evening light, low horizon",
    "a lush tropical valley of waterfalls and mist beneath towering green peaks",
    "a vast calm lake at dawn with distant misty islands, very low horizon",
    "a rugged coastline with tall sea stacks and gentle surf at golden hour",
    "towering sandstone buttes and mesas glowing deep orange at sunset, immense scale",
    "a vast pine forest blanketed in soft morning mist with distant mountains",
    "a boundless salt flat mirroring a soft pastel sky to infinity at twilight",
    "endless rows of blooming tulips in bands of colour reaching a distant horizon",
    "a snow-covered mountain valley glowing soft pink at dawn",
    "a tranquil bamboo forest path opening to soft glowing light in the distance",
    "a lush green gorge with a winding turquoise river far below high cliffs",
    "rolling green pastures and hills bathed in soft golden evening light",
    # Christian / biblical places, grand and varied
    "a grand terraced vineyard sweeping down green hills to a distant valley at golden hour",
    "ancient olive groves on rolling hills stretching to a far horizon in warm morning light",
    "the vast rocky desert wilderness receding to distant mesas at sunset",
    "the great calm expanse of the Sea of Galilee at radiant sunrise, very low horizon",
    "a solitary green hill with a distant wooden cross against a wide glowing dawn sky",
]
COMPOSE = {
    ("center", "middle"): "Let the middle of the frame breathe: a calmer, softer, more open region "
        "of the scene (soft light, gentle haze, open distance, calm water or sky — whatever suits THIS "
        "scene) sits behind where the verse goes, flowing naturally out of the surrounding landscape. "
        "The grand detail lives mostly above and below it, easing softly toward that quiet middle — "
        "never a hard split.",
    ("left", "middle"): "Leave the left and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the right "
        "and lower part of the photo, keeping the text area clear.",
    ("right", "middle"): "Leave the right and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the left "
        "and lower part of the photo, keeping the text area clear.",
}
EVENTONE = ("CRUCIAL: render ONE single, continuous, natural scene with smooth, gradual transitions "
            "and absolutely NO hard horizontal line, band, strip or seam anywhere — never a "
            "pasted-together, stacked or panorama-collage look. The middle of the frame is simply a "
            "calmer, softer, more open part of the SAME scene (soft light, gentle haze, open distance, "
            "calm water or sky) where the verse can be read — arrived at gradually and organically, "
            "its edges dissolving softly into the surrounding drama, never a flat rectangular block or "
            "a sharp-edged strip. The boldest detail and light sit toward the top and the bottom and "
            "fade smoothly into that quiet middle. Keep tones in the middle gentle and even.")
COMPOSE_SAFE = ("Keep the composition natural and open: the horizon stays low and the scene recedes "
                "grandly into the far distance. Do NOT let any single object (a mountain, tree, "
                "building or rock) stand tall through the middle of the frame or dominate the center; "
                "keep such elements to the lower part and the far distance, easing into the quiet "
                "middle. Everything must read as one real, continuous photograph.")
QUALITY = ("It is a breathtaking, awe-inspiring cinematic photograph of monumental, epic scale — vast, "
           "majestic and immense, with sweeping depth and a profound sense of divine glory and grandeur. "
           "Glorious natural light and rich atmosphere suited to THIS particular scene, sublime and "
           "reverent, like a vision of heaven. Photoreal and richly detailed, high dynamic range, deep "
           "cinematic light and colour, sharp and clean — a real photograph, not a 3D render, not a "
           "video game.")
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
