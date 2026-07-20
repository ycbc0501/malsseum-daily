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

# WIDE-RANGING, dreamy cinematic scenes — deliberately across MANY subjects (water, city streets,
# windows, architecture, weather, coasts, whimsical objects, cozy corners), NOT just fields and
# flowers. Each is chosen to also ANIMATE cleanly in Veo (one clear, simple motion — rippling or
# reflecting water, rain, drifting mist/clouds, gently swaying elements) rather than a busy field of
# many small flowers (which comes out coarse). Each keeps a soft area for the verse. Ordered to
# alternate the subject so the feed never looks the same twice.
SCENES = [
    # ── water & reflections (clean motion) ──
    "gentle rain rippling a still pond that mirrors autumn trees and a soft sky",
    "an old town canal reflecting flower-draped balconies, the water rippling softly",
    "a wooden rowboat resting on a glassy misty lake at dawn, faint drifting mist",
    "a puddle on a cobblestone street mirroring a glowing sunset sky",
    "a quiet stone fountain in an empty plaza, water falling softly in warm evening light",
    # ── windows (curtains, light, rain outside) ──
    "a rain-speckled window with soft roses blurred beyond the wet glass",
    "an open window, sheer curtains drifting gently, a calm sea and soft sky beyond",
    "a train window with a green countryside gliding gently past, soft daylight",
    # ── city / street ──
    "a narrow European alley with flower boxes, warm morning light and long soft shadows",
    "a lone street lamp glowing over wet cobblestones and reflections on a rainy night",
    "an empty cafe terrace with string lights swaying softly at dusk",
    "a red bicycle with a flower basket leaning against an old stone wall in soft light",
    "a rainy city crosswalk at night, glowing neon and headlights reflected in the wet street",
    # ── architecture / places ──
    "a Mediterranean stone house with flowering balconies above a shimmering calm sea",
    "an arched stone window framing a small boat on a glittering sea, warm light",
    "a weathered seaside chapel under slowly drifting soft clouds",
    "the tall interior of a cathedral with soft coloured light drifting from stained glass",
    # ── sky / weather ──
    "soft towering clouds drifting slowly over a single tree on a green hill",
    "warm sunbeams shifting through mist in a quiet forest clearing",
    "gentle snow drifting down over a lone park bench at dusk",
    "fireflies drifting over a dark meadow at deep-blue twilight",
    "a soft rainbow arching over misty green hills after the rain",
    # ── coast / mountains / nature (varied) ──
    "a lighthouse on a cliff with slow drifting clouds and gentle surf below",
    "white sea cliffs above a calm turquoise shore, slow gentle waves rolling in",
    "a waterfall spilling into a misty emerald pool, soft spray drifting",
    "a calm alpine lake mirroring snow peaks at dawn, faint mist on the water",
    "cherry blossom branches swaying softly, a few petals drifting down",
    "an autumn forest path with leaves drifting slowly in soft golden light",
    # ── whimsical / cozy (tasteful) ──
    "a lone wooden bench facing a calm, misty sea at dawn",
    "a clear umbrella cradling soft flowers on wet cobblestones in the gentle rain",
    "a paper lantern drifting gently over a calm dark river at night, soft reflections",
    "a windowsill of potted plants in soft daylight, leaves stirring in a light breeze",
]
COMPOSE = {
    ("center", "middle"): "COMPOSITION: compose so the CENTER of the frame — where the verse will sit — "
        "stays soft, open and easy to read text over (open sky, soft mist, calm water or gentle "
        "out-of-focus blur, whatever suits THIS scene). Keep the main subject and any tall elements "
        "(trees, buildings, branches) LOW in the frame or off to the sides, well clear of the centre, so "
        "nothing crosses the middle where the text goes. It must be ONE single natural photograph filling "
        "the whole frame — NEVER a framed picture, inset, border, panel, photo-within-a-photo, polaroid "
        "or collage; the whole image is one continuous scene. Show each subject only ONCE, never "
        "duplicated or mirrored, and never dead-centre.",
    ("left", "middle"): "Leave the left and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the right "
        "and lower part of the photo, keeping the text area clear.",
    ("right", "middle"): "Leave the right and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the left "
        "and lower part of the photo, keeping the text area clear.",
}
EVENTONE = ("Render ONE single, continuous, real photograph — one coherent scene with ONE horizon line "
            "only. It must NOT be split or stacked into two scenes: NEVER two horizons, NEVER a second "
            "body of water, second lake, second sky or second landscape above or below the first, NEVER a "
            "mirrored, doubled or repeated view, and never a framed picture, inset, panel, collage, "
            "photo-within-a-photo or any hard horizontal seam. There is only one sky and (if any) one "
            "water surface, in their natural real-world places — sky above, ground or water below, a "
            "single horizon. Compose it so the calm, soft, open area where the verse sits (soft sky, "
            "gentle haze, calm water or quiet out-of-focus light) falls naturally across the middle of "
            "this ONE scene — reached organically, never by pasting a second scene into the centre.")
COMPOSE_SAFE = ("Keep it a real, natural, uncluttered composition — one continuous photograph. Do not let "
                "any object crowd, block or sit dead-center in the calm middle where the text goes; keep "
                "the main subject and busy detail toward the edges, top or bottom of the frame.")
QUALITY = ("It is a breathtaking, dreamy, cinematic photograph — richly beautiful and atmospheric, with "
           "a romantic sense of wonder, tasteful colour and beautiful natural light suited to THIS "
           "particular scene (golden, soft, moody, bright or blue as fits — NOT always golden hour). "
           "Cinematic depth of field with gentle bokeh and a soft glow where it suits the scene. Magical "
           "yet believable — photoreal, high detail, a gentle film-like grade — not a flat 3D render, "
           "not a video game, not an obviously-AI picture. An image that stops the scroll.")
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
    prompt = f"A breathtaking, dreamy cinematic photograph of {scene}. {compose} {COMPOSE_SAFE} {EVENTONE} {QUALITY} {NOTEXT}"

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
