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
# dailymayim-style: calm, real, muted FILM photography — the variety is in DIVERSE everyday
# subjects (nature, quiet architecture, gardens, interiors, windows, paths, still life), all
# sharing one soft, understated, contemplative mood. Each has a naturally calm area for the
# verse. Ordered to alternate the subject type so the feed never repeats a look. NOT epic.
SCENES = [
    # ── nature (soft, muted) ──
    "soft layered misty hills fading into a pale pastel sunset, gentle and quiet",
    "a calm sea meeting a soft hazy sky with a small distant island, very low horizon",
    "gentle ocean waves rolling onto a quiet shore under a soft overcast sky",
    "a still lake at dawn with soft mist, faint golden light and a gentle lens flare",
    "a quiet forest path dappled with soft golden light through the leaves",
    "a misty pine forest in soft grey-green morning light",
    "a wooded green hillside glowing gently in warm golden-hour light",
    "an autumn forest in muted red and gold with a soft leaf-covered path",
    "a quiet snowy field under a soft pale winter sky, bare trees in the distance",
    "a meadow of wildflowers swaying in soft overcast light",
    "a lavender field at soft dusk, muted purple fading into gentle haze",
    "rolling green hills under a soft, calm overcast sky",
    "distant blue mountains fading into layered haze at dusk",
    "delicate cherry blossom branches against a soft, pale sky",
    "tall grass glowing softly in warm low backlight, blurred and gentle",
    "a river winding quietly through a green valley in soft flat light",
    "a golden wheat field under a soft muted overcast sky",
    "soft pink and grey dawn clouds drifting over a calm quiet plain",
    # ── quiet architecture / places (no people) ──
    "a small black wooden church standing alone in a vast green field under a soft pale sky",
    "a modern house with large glass windows and a neat green lawn at soft blue-hour dusk",
    "a quiet country road curving gently through open fields at soft dawn",
    "an old stone bridge over a calm river in soft, flat morning light",
    "a lone cabin beside a still misty lake at dawn",
    "a garden with a small table and two chairs under dappled tree light",
    "a weathered white chapel steeple against a soft pastel evening sky",
    "a wooden dock reaching out into a calm, misty lake",
    "warm string lights strung over an empty garden terrace at dusk",
    "a greenhouse glowing softly with warm light at blue-hour dusk",
    "a quiet cobblestone alley in soft, hazy morning light",
    # ── interior / window / intimate ──
    "a sunlit room with a large leafy potted plant and soft warm afternoon light",
    "sheer white curtains at an open window looking out to a calm sea, plants on the sill",
    "a cozy windowsill with a small plant, soft morning light spilling in",
    "an open window framing a green garden, gentle daylight streaming through",
    "a quiet corner of a room, a plant in soft shadow lit by a warm glow",
    "a simple wooden desk by a bright window in soft, calm daylight",
    # ── still life (soft, real) ──
    "a simple cup of coffee on a wooden table by a bright soft window",
    "a small vase of wildflowers on a windowsill in gentle morning light",
    "an open book resting on rumpled linen in soft morning light",
    "a loaf of rustic bread and a folded linen cloth on a wooden table by a window",
    "a single candle glowing warm and soft on a quiet dark table",
    "fresh olive branches resting on pale linen in soft daylight",
    "a small bowl of figs and grapes on a wooden table in soft window light",
]
COMPOSE = {
    ("center", "middle"): "COMPOSITION IS KEY: keep the UPPER and CENTRAL part of the frame calm, soft "
        "and open — an even, low-detail, gently-lit area (soft sky, mist, still water, a plain wall, "
        "gentle blur or a shaft of light, whatever suits THIS scene) big enough to hold two centered "
        "lines of text. Place the single main subject and the richest detail in the LOWER part of the "
        "frame or off toward the edges, so it never intrudes into that calm upper-center. Show each "
        "subject only ONCE — never duplicate, mirror, repeat or stack it. The subject must not sit "
        "dead-center.",
    ("left", "middle"): "Leave the left and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the right "
        "and lower part of the photo, keeping the text area clear.",
    ("right", "middle"): "Leave the right and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the left "
        "and lower part of the photo, keeping the text area clear.",
}
EVENTONE = ("Render ONE single, continuous, real photograph with smooth, natural transitions and "
            "absolutely NO hard horizontal line, band, strip or seam anywhere — never a pasted-together "
            "or collage look. The middle of the frame is a calmer, softer, more open part of the SAME "
            "scene (soft light, gentle haze, calm water, sky, a wall, still ground or gentle blur) where "
            "the verse can be read — even in tone, quietly lit, arrived at organically. Keep the richer "
            "detail toward the edges, top and bottom, easing softly into that quiet middle.")
COMPOSE_SAFE = ("Keep it a real, natural, uncluttered composition — one continuous photograph. Do not let "
                "any object crowd, block or sit dead-center in the calm middle where the text goes; keep "
                "the main subject and busy detail toward the edges, top or bottom of the frame.")
QUALITY = ("It is a REAL photograph with the natural, understated look of 35mm film — soft true-to-life "
           "detail, gentle available light, slightly muted and desaturated natural colours, fine film "
           "grain, and a calm, quiet, contemplative mood. It looks like a genuine, beautifully-composed "
           "moment someone captured on a film camera: intimate, serene and elegant, tasteful and "
           "understated — never flashy, never oversaturated, never over-dramatic, NOT a cinematic 3D "
           "render, NOT a video game, NOT an obvious AI image.")
NOTEXT = ("There are no visible human faces, and absolutely no text, letters, words, captions, numbers, "
          "signs, watermark or logo anywhere. It is a single full-bleed photograph that completely fills "
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
    prompt = f"A beautiful, natural film photograph of {scene}. {compose} {COMPOSE_SAFE} {EVENTONE} {QUALITY} {NOTEXT}"

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
