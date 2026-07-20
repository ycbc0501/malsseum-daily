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

# Distinct instrumentation palettes for a WARM, HOPEFUL church hymn → each post sounds different
# in character on top of Lyria's own variation. All gentle, but reassuring and comforting (major
# key, hymn-like) — deliberately NOT the sad/melancholic ambient it drifted toward before.
MOODS = [
    "a warm church pipe organ with soft strings, like a beloved Sunday hymn",
    "a warm grand piano playing a clear, comforting hymn melody, with gentle strings underneath",
    "warm strings and a soft French horn, rich and reassuring, a hymn of praise",
    "a bright acoustic guitar and warm piano, a hopeful, uplifting hymn",
    "a warm harp and soft strings, tender and comforting, a lullaby-like hymn",
    "a warm chapel organ and a soft choir-like pad, peaceful and hopeful",
    "a warm piano with cello and violin in gentle harmony, a heartfelt hymn",
    "soft strings swelling gently under a warm piano hymn melody, comforting",
    "a warm acoustic guitar with piano and light strings, a gentle folk hymn",
    "a music box and warm strings carrying a sweet, hopeful hymn melody",
    "a warm string ensemble playing a rich, comforting traditional hymn",
    "a soft flute and warm organ over gentle strings, a pastoral hymn of peace",
]


def generate(dest, index=0, extra="", timeout_s=180):
    """Generate one WARM, HOPEFUL church HYMN → save mp3 to `dest`. `index` rotates the palette."""
    mood = MOODS[index % len(MOODS)]
    prompt = (f"A warm, comforting and hopeful instrumental church hymn for peaceful Scripture "
              f"reflection — in the spirit of a beloved traditional hymn like 'Amazing Grace' or 'It Is "
              f"Well' (a similar warm, reverent, singable feel, NOT those exact tunes). A clear, gentle, "
              f"singable hymn melody in a MAJOR key with warm, consonant harmony, arranged for {mood}. "
              f"Tender, reverent and reassuring — heartfelt and hopeful, the way a hymn comforts. Keep it "
              f"VERY soft, quiet, small, sparse and intimate — played gently and low, just a few tender "
              f"notes, never full, loud, grand, cinematic or swelling. No vocals, no drums, no beat. It "
              f"must sound like a real CHURCH HYMN, warm and hopeful — absolutely NOT sad, melancholic, "
              f"mournful, dark, tense or like ambient background drone.{extra}")
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
