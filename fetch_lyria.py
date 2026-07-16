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

# Distinct instrumentation palettes for an instrumental HYMN → each post sounds different in
# character on top of Lyria's own variation. All calm, reverent, wordless church-hymn arrangements.
MOODS = [
    "solo felt piano, like a quiet church hymn",
    "warm strings and piano, a soft hymn arrangement",
    "a soft, distant pipe organ, gentle and hymnal",
    "acoustic fingerstyle guitar, a warm intimate hymn",
    "harp and soft strings, a serene hymn",
    "felt piano with a warm string pad, a tender hymn",
    "cello and piano, a slow reverent hymn",
    "warm organ and strings, a slow sacred hymn",
    "soft acoustic guitar and light strings, a gentle hymn",
    "delicate music box and strings, a calm hymn",
    "warm strings and soft brass, a stately gentle hymn",
    "soft flute and strings, a pastoral hymn",
]


def generate(dest, index=0, extra="", timeout_s=180):
    """Generate one instrumental HYMN track → save mp3 to `dest`. `index` rotates the palette."""
    mood = MOODS[index % len(MOODS)]
    prompt = (f"A calm, reverent, instrumental HYMN for quiet Scripture reflection, in the style of a "
              f"traditional Christian church hymn: a warm, singable, worshipful melody with gentle "
              f"sacred harmony, arranged for {mood}. Slow, peaceful and tender, no vocals, no drums, "
              f"no beat — just a soft hymn melody.{extra}")
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
