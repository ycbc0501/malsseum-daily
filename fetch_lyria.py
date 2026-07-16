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

# Distinct instrumentation palettes for a VERY GENTLE instrumental hymn → each post sounds
# different in character on top of Lyria's own variation. All soft, quiet, sparse and soothing.
MOODS = [
    "soft solo felt piano, played very quietly and slowly",
    "warm strings, gentle and hushed, played softly",
    "a very soft, distant pipe organ, pianissimo and airy",
    "delicate acoustic fingerstyle guitar, intimate and quiet",
    "a gentle harp with faint soft strings, delicate",
    "quiet felt piano with a soft warm pad underneath",
    "a soft, slow cello with faint piano, tender",
    "an airy soft ambient pad with faint distant piano",
    "light acoustic guitar with a whisper of strings",
    "a delicate music box with soft strings, faint and calm",
    "a soft warm string pad, slow and barely-there",
    "a soft flute over gentle strings, hushed and pastoral",
]


def generate(dest, index=0, extra="", timeout_s=180):
    """Generate one VERY GENTLE instrumental HYMN → save mp3 to `dest`. `index` rotates the palette."""
    mood = MOODS[index % len(MOODS)]
    prompt = (f"A very gentle, soft and quiet instrumental hymn for peaceful Scripture reflection, in "
              f"the style of a tender traditional church hymn: a slow, delicate, sparse melody with soft "
              f"warm harmony, arranged for {mood}. Extremely calm, unhurried and soothing, minimal and "
              f"understated, played softly and low, no vocals, no drums, no beat, no big swells or loud "
              f"moments — just a soft, quiet, peaceful hymn.{extra}")
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
