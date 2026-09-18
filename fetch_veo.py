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
MOTION = (
    "REAL-TIME at 1x speed, never a timelapse or sped up. The camera is locked — no pan, no zoom, "
    "no move — and the scene is almost still: only the smallest movement that eight real seconds "
    "would actually contain, like a photograph breathing. Nothing enters, leaves, grows or changes."
)

# Prefixed to MOTION when animating the tail frame of an earlier segment, so the segments read as
# ONE continuous shot rather than two takes of the same place. Length has to come from Veo itself
# (CONTENT_RULE 6) — this is the "genuine continuation" that rule allows, as opposed to a loop.
# Retrying with the SAME prompt is three draws from one distribution: if Veo over-animates a given
# image it will do so again. So each retry escalates the demand. Index 0 is the plain prompt.
CALMER = [
    "",
    (" Even less motion than that — about a quarter of what you would normally animate. Sky, cloud "
     "and mist are completely static. Only the smallest surface detail moves, in place, without "
     "travelling across the frame."),
    (" Almost a frozen photograph: the barest trace of life and nothing else. Sky, cloud, mist and "
     "water do not travel at all. A viewer should have to look closely to be sure it moves. If in "
     "doubt, animate LESS."),
]

CONTINUE = ("This is a DIRECT CONTINUATION of one single continuous shot, resuming from the exact "
            "frame provided. The scene, framing, composition, colour and light are already correct "
            "and must stay identical — the motion simply carries on from where it left off. There is "
            "no cut, no new scene, no camera move, no change of subject, no relighting, no shift in "
            "colour grade, and nothing enters or leaves the frame. A viewer must not be able to tell "
            "where the previous footage ended and this begins. ")

# Speed and camera only. What may not APPEAR lives in content_law.NEG_TERMS and is appended at
# send time — naming it in both places is how this string ended up listing "text", "people",
# "watermark" and "logo" twice each.
NEG = ("timelapse, sped up, fast-forward, accelerated motion, fast movement, "
       "fast-moving clouds, racing clouds, moving clouds, "
       "rushing water, crashing waves, flowing water, strong current, rolling waves, churning, "
       "turbulence, busy traffic, energetic movement, "
       "camera pan, camera zoom, camera shake, hard cut, scene change, jump cut, "
       "morphing, warping, sudden changes, popping in, flickering, "
       "elements appearing or disappearing, growing, strobing")


def animate(still_png, dest, aspect="9:16", prompt=MOTION, timeout_s=420, poll_s=10):
    """Submit `still_png` to Veo image-to-video, poll the long-running op, download the mp4
    to `dest`. Raises on error/timeout so callers can fall back to a zoom still."""
    key = hf._gemini_key()
    img_b64 = base64.b64encode(open(still_png, "rb").read()).decode()
    import content_law
    # The still went through every gate and then Veo introduced what the gates forbid — a person
    # walking in, water pouring sideways, the empty upper band dissolving. The motion prompt had
    # never carried the laws at all: no mention of hands, of CGI, of physics, of looking filmed.
    body = {"instances": [{"prompt": content_law.for_video(prompt),
                           "image": {"bytesBase64Encoded": img_b64, "mimeType": "image/png"}}],
            "parameters": {"aspectRatio": aspect,
                           "negativePrompt": NEG + ", " + content_law.NEG_TERMS}}
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
