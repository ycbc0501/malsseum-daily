#!/usr/bin/env python3
"""
Generate a UNIQUE instrumental music track per post with Google Lyria 3 (text-to-music),
using the same Gemini API key as the images. Every call produces a fresh, never-before-heard
piece — so no two posts ever share music — and because it is generated, there is zero
Content-ID / copyright-takedown risk (the reason we only ever used vetted instrumentals).

    python3 fetch_lyria.py out.mp3 3      # generate with mood #3
"""

import base64
import json
import sys
import urllib.request

import fetch_higgsfield as hf   # reuse _gemini_key()

MODEL = "lyria-3-clip-preview"   # 30s instrumental clip
API = "https://generativelanguage.googleapis.com/v1beta"

# Distinct instrumentation/mood palettes → each post sounds different in character, on top of
# Lyria's own variation. All calm, reverent, wordless — fitting a Scripture reflection.
MOODS = [
    "soft solo felt piano, slow and tender, reflective",
    "warm strings and gentle piano, peaceful and hopeful, softly cinematic",
    "ethereal ambient worship pads, slow swells, calm and spacious",
    "gentle acoustic fingerstyle guitar, warm and intimate",
    "delicate harp and soft strings, serene and heavenly",
    "quiet felt piano with a subtle warm pad, contemplative",
    "tender cello and piano duet, reverent and slow",
    "airy ambient synth pad with faint piano, dreamy and still",
    "soft acoustic guitar and light strings, gentle sunrise mood",
    "music box and soft strings, innocent and calm",
    "warm analog pad and slow piano chords, meditative",
    "soft flute and warm strings, pastoral and gentle",
]


def generate(dest, index=0, extra="", timeout_s=180):
    """Generate one instrumental track → save mp3 to `dest`. `index` rotates the mood palette."""
    mood = MOODS[index % len(MOODS)]
    prompt = (f"A calm, gentle, reverent instrumental piece for quiet Scripture reflection: {mood}. "
              f"Slow, peaceful, worshipful, tasteful and understated, no vocals, no heavy drums.{extra}")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    url = f"{API}/models/{MODEL}:generateContent?key={hf._gemini_key()}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    data = json.load(urllib.request.urlopen(req, timeout=timeout_s))
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            with open(dest, "wb") as f:
                f.write(base64.b64decode(part["inlineData"]["data"]))
            return dest
    raise RuntimeError("lyria: no audio in response")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "lyria.mp3"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(generate(out, idx))
