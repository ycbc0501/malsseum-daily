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

# Locked camera + BARELY-THERE motion, so the composition (and the clear center band the verse
# sits on) never shifts AND the scene never looks frantic. Veo's fast tier tends to over-animate,
# so the prompt pushes hard toward "a living photograph that only breathes" — the fast waves /
# rushing traffic came from asking for too much motion, not from any speed bug downstream.
MOTION = ("Animate this photograph with EXTREMELY subtle, minimal, slow motion — it should look almost "
          "exactly like a STILL photograph that is only faintly breathing, a calm living wallpaper. The "
          "camera is completely locked: no pan, no zoom, no camera move at all. Allow only the faintest, "
          "slowest, gentlest movement — a soft shimmer on water, an almost-imperceptible drift of mist or "
          "cloud, a tiny glimmer of light. Keep EVERY movement very slow, very small and calm. Absolutely "
          "NO fast, energetic or busy motion: no crashing or rushing waves, no fast-moving or speeding "
          "cars or traffic, no fast water, no timelapse, no sped-up anything. Everything already in the "
          "frame stays present the whole time — nothing appears, grows, pops in, flickers or morphs. "
          "Serene, peaceful, barely-moving — like a photograph gently coming to life.")
NEG = ("fast motion, fast movement, rushing water, crashing waves, choppy water, fast-moving cars, "
       "speeding cars, busy traffic, timelapse, sped up, energetic movement, churning, turbulence, "
       "text, letters, words, watermark, logo, people, person, camera pan, camera zoom, camera shake, "
       "hard cut, scene change, morphing, warping, distortion, sudden changes, popping in, flickering, "
       "elements appearing or disappearing, growing, blooming, jump cut, strobing")


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
