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

# wondervisionary-style: LUSH, warm, dreamy CINEMATIC scenes with rich (but tasteful) colour,
# golden light, and a shallow-depth-of-field foreground (soft out-of-focus flowers / grass /
# leaves framing a luminous subject beyond). Diverse subjects — meadows, water & reflections,
# windows framing views, gardens, flowering architecture, coasts — each with a calm sky / water
# / soft area for the verse, and natural motion potential (drifting clouds, rippling water,
# swaying flowers). Ordered to alternate the look post-to-post.
SCENES = [
    # ── meadows & flowers (foreground bokeh) ──
    "a lush wildflower meadow at golden hour, soft out-of-focus poppies and daisies in the "
        "foreground, a luminous open sky above",
    "a golden field of buttercups on rolling hills with a small wooden barn, soft blurred "
        "flowers in the foreground, warm hazy light",
    "a dreamy field of pink cosmos swaying, soft bokeh blossoms in front, a bright soft sky beyond",
    "a sunlit lavender field rolling to the sea, soft purple blur in the foreground, open sky",
    "tall wildflowers and grasses seen looking gently upward toward a bright soft sky with drifting clouds",
    "a meadow of poppies and cornflowers by the sea, soft focus flowers in front, calm bright horizon",
    # ── water & reflections ──
    "a lone tree on a riverbank mirrored in still water, tall summer clouds above, calm reflective surface",
    "gentle rain dimpling a still green pond that reflects trees and a soft bright sky, delicate ripples",
    "a calm lake at golden hour with soft mist and warm light, mountains reflected, a bright open sky",
    "sunlight sparkling on gently rippling sea water seen from a flowered shore, bright open horizon",
    "a quiet river winding through a green valley, big soft clouds above, warm cinematic light",
    # ── windows framing a view ──
    "a rustic open window with sheer curtains framing a sunlit sea and distant hills, plants on the sill",
    "an arched old stone window framing a small boat on a glittering sea, warm light",
    "an open window framing a lush green garden and blue sky, roses climbing the frame",
    "a train window with roses and petals along the sill, a soft green landscape sliding past",
    # ── flowering architecture / places ──
    "a weathered wooden pergola arch covered in vines over a wildflower meadow, blue sky beyond",
    "a Mediterranean stone house with flower-filled balconies in warm golden afternoon light",
    "a brick garden wall overflowing with climbing pink and orange roses, soft warm light",
    "a small storybook cottage in a green meadow ringed by blossoming trees, soft cinematic light",
    "a cobblestone European lane lined with flowers, warm morning sun and long soft shadows",
    # ── skies, hills, coasts ──
    "a single tree on a green hill under towering soft cumulus clouds, warm afternoon light",
    "a winding country road through green hills toward a distant sunlit sea, wildflowers along it",
    "white chalk sea cliffs above a calm turquoise shore under a big soft sky",
    "rolling green pastures with a small cabin, warm low sun and golden bokeh in the foreground",
    "soft pink and gold sunset clouds over a calm sea, a lone tree silhouette on the shore",
    # ── forests, seasons, moody ──
    "a soft forest clearing where cherry blossoms open into golden light, petals drifting",
    "an autumn forest glowing red and gold, a soft misty path receding into warm light",
    "a single glowing wildflower on a dark mossy forest floor, a soft shaft of light, dreamy",
    "a quiet street lamp glowing warm over roses on a rainy night, soft reflections",
    "a dewy patch of clover with one small white flower catching a soft morning sunbeam",
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
EVENTONE = ("Render ONE single, continuous, real photograph with smooth, natural transitions and "
            "absolutely NO hard horizontal line, band, strip or seam anywhere, and NO framed picture, "
            "inset, border, panel or photo-within-a-photo — never a pasted-together or collage look. "
            "The middle of the frame is a calmer, softer, more open part of the SAME "
            "scene (soft light, gentle haze, calm water, sky, a wall, still ground or gentle blur) where "
            "the verse can be read — even in tone, quietly lit, arrived at organically. Keep the richer "
            "detail toward the edges, top and bottom, easing softly into that quiet middle.")
COMPOSE_SAFE = ("Keep it a real, natural, uncluttered composition — one continuous photograph. Do not let "
                "any object crowd, block or sit dead-center in the calm middle where the text goes; keep "
                "the main subject and busy detail toward the edges, top or bottom of the frame.")
QUALITY = ("It is a breathtaking, dreamy, cinematic photograph — lush and richly beautiful, with warm "
           "golden natural light, vivid yet tasteful colour, and a romantic sense of wonder. Shallow "
           "depth of field: soft, out-of-focus foreground detail (flowers, grass or leaves) framing a "
           "luminous, sharp subject beyond, with gentle bokeh and a soft glow. Atmospheric, magical and "
           "serene, like a beautiful dream — an image that stops the scroll. Photoreal and cinematic, "
           "high detail, a gentle warm film-like grade, natural and believable — not a flat 3D render, "
           "not a video game, not an obviously-AI picture.")
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
