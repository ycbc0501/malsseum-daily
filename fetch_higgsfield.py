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

# Plain, natural-language scenes (Gemini follows prose, NOT keyword soup). Each can keep a
# clear calm area for the text. Diverse, beautiful, dignified — no hype words.
SCENES = [
    "a calm sea under a soft open sky, very low horizon",
    "distant mountains low on the horizon under a wide open sky",
    "a golden wheat field under a soft open sky, low horizon",
    "a field of wildflowers under a soft pastel sky, low horizon",
    "a lavender field under a wide soft sky, low horizon",
    "morning mist over a quiet valley under a pale open sky",
    "smooth desert dunes under a wide soft sky, low horizon",
    "a snowy plain under a soft pastel sky, low horizon",
    "a calm lake reflecting distant low mountains under a wide sky",
    "a soft layer of clouds seen from above under an open sky",
    "the milky way and stars over a dark low horizon",
    "soft sunbeams through gentle clouds in a wide open sky",
    "rolling autumn hills under a wide open sky, low horizon",
    "soft pastel sunrise clouds over a calm sea, low horizon",
    "cherry blossom branches against a soft open sky",
    "green rolling meadows under a wide open sky, low horizon",
    "rows of tulips under a soft pastel sky, low horizon",
    "a wide calm river through a low valley under an open sky",
    "terraced green tea fields in soft morning mist",
    "soft golden pampas grass under a wide warm sky, low horizon",
    "an olive grove on a low hillside under a soft sky",
    "the inside of an old stone cathedral looking down the long central aisle, "
        "soft daylight from tall windows, the central aisle empty and open",
    "a wide canyon seen from the rim with open sky above",
    "a gentle aurora over low snowy hills under a starry sky",
    "a quiet stone courtyard with an open empty center and soft daylight",
    "a calm alpine lake reflecting a wide clear sky, low far shore",
    "soft pink twilight clouds over calm water, low horizon",
    "a single tree on a wide plain under a big open sky",
    # Christian / biblical places
    "the old stone walls of Jerusalem at dawn under a soft open sky",
    "ancient olive trees in a quiet garden at golden hour, open sky above",
    "the calm Sea of Galilee at sunrise, very low horizon",
    "a hillside vineyard with neat rows of vines under a soft open sky",
    "the rocky desert wilderness under a wide pale sky, low horizon",
    "weathered ancient stone columns and ruins under a wide open sky",
    "a quiet stone path winding through a wilderness valley under a wide sky",
    "a simple wooden cross on a grassy hill against a soft glowing sky",
    "an old stone well in a quiet sunlit courtyard",
    "terraced hillsides with olive groves under a soft open sky",
    # village / town (no people)
    "a quiet old Mediterranean stone village at dawn under a soft sky",
    "warm terracotta rooftops of an old hillside town under a soft open sky",
    "a small calm harbor at dawn with still water and a wide sky",
    "a quiet empty cobblestone street in an old town, soft morning light",
    # life / season / symbol
    "fresh green spring blossoms and new leaves against a soft open sky",
    "a peaceful garden path among soft flowers in gentle morning light",
    "a gentle rainbow arching over a calm landscape after the rain",
]
REGION = {
    ("center", "middle"): "the central area",
    ("left", "middle"): "the left side",
    ("right", "middle"): "the right side",
}
QUALITY = ("Shot as a real photograph on a full-frame camera with natural light — candid and "
           "true to life, with natural colours, fine grain and natural depth of field. It looks "
           "like a genuine photo, not a render or illustration.")
NOTEXT = ("There are no people anywhere. The image contains absolutely no text, letters, words, "
          "captions, numbers, signs, watermark or logo of any kind.")


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
    """Generate one background → save to `dest`. Clean natural-language prompt (Gemini follows
    prose); the text area is kept clear per `placement`. `full_scene` kept for compatibility."""
    scene = SCENES[index % len(SCENES)]
    region = REGION.get(tuple(placement), REGION[("center", "middle")])
    prompt = (
        f"A real, natural photograph of {scene}. "
        f"Composition: keep {region} of the frame calm, open and uncluttered — clear sky or smooth "
        f"empty space with generous room for two lines of text and a small line below; keep the main "
        f"subject and all detail away from that area, low and toward the edges. "
        f"{QUALITY} {NOTEXT}"
    )

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
