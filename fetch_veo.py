#!/usr/bin/env python3
"""
Animate a still image into a short cinematic clip via Google Veo 3.1 (image-to-video),
using the SAME Gemini API key as the Nano Banana stills — no new account or SDK. This turns
a grand background still into REAL motion (drifting clouds, shifting light) for the Reel,
instead of a Ken Burns zoom on a frozen picture.

    python3 fetch_veo.py still.png out.mp4
"""

import base64
import json
import sys
import time
import urllib.request

import fetch_higgsfield as hf   # reuse _gemini_key()

VEO_MODEL = "veo-3.1-fast-generate-preview"   # "fast" tier: good motion, lower cost than full
API = "https://generativelanguage.googleapis.com/v1beta"

# Locked camera + gentle scene motion only, so the composition (and the clear center band the
# verse sits on) never shifts. Anything more energetic would slide the text off its calm area.
MOTION = ("The camera stays locked and still — no pan, no zoom, no camera move — so the composition "
          "never shifts. The scene comes alive gently and CONTINUOUSLY from the very first frame: water "
          "ripples and reflections shimmer, mist and clouds drift slowly, flowers and tall grass sway "
          "softly in a light breeze, leaves flutter subtly. EVERYTHING already in the frame stays "
          "present the whole time and moves only softly and steadily — nothing suddenly appears, grows, "
          "pops in, flickers, blooms or morphs; no timelapse. The motion is smooth, subtle and "
          "consistent from start to finish. Serene, dreamy, cinematic, natural slow motion.")
NEG = ("text, letters, words, watermark, logo, people, person, camera pan, camera zoom, camera shake, "
       "hard cut, scene change, morphing, warping, distortion, sudden changes, popping in, flickering, "
       "elements appearing or disappearing, growing, blooming, timelapse, jump cut, strobing")


def animate(still_png, dest, aspect="9:16", prompt=MOTION, timeout_s=420, poll_s=10):
    """Submit `still_png` to Veo image-to-video, poll the long-running op, download the mp4
    to `dest`. Raises on error/timeout so callers can fall back to a zoom still."""
    key = hf._gemini_key()
    img_b64 = base64.b64encode(open(still_png, "rb").read()).decode()
    body = {"instances": [{"prompt": prompt,
                           "image": {"bytesBase64Encoded": img_b64, "mimeType": "image/png"}}],
            "parameters": {"aspectRatio": aspect, "negativePrompt": NEG}}
    url = f"{API}/models/{VEO_MODEL}:predictLongRunning?key={key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    op = json.load(urllib.request.urlopen(req, timeout=120))["name"]

    status_url = f"{API}/{op}?key={key}"
    waited = 0
    while waited < timeout_s:
        d = json.load(urllib.request.urlopen(status_url, timeout=30))
        if d.get("done"):
            if "error" in d:
                raise RuntimeError(f"veo error: {d['error']}")
            uri = d["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
            dl = uri + ("&" if "?" in uri else "?") + "key=" + key
            urllib.request.urlretrieve(dl, dest)
            return dest
        time.sleep(poll_s)
        waited += poll_s
    raise RuntimeError(f"veo: timed out after {timeout_s}s")


if __name__ == "__main__":
    still, out = sys.argv[1], sys.argv[2]
    print(animate(still, out))
