#!/usr/bin/env python3
"""
Animate a still image into a short cinematic clip.

Was Google Veo (predictLongRunning on generativelanguage.googleapis.com). On 2026-10-23 Google
pulled the model out from under us without warning: every call started returning
"models/veo-3.1-fast-generate-preview is no longer available", and NOT A SINGLE model exposed by
this API key still supports predictLongRunning (checked by listing all 60 models on 2026-10-31 —
zero have any video-generation method; Google's suggested replacement, gemini-omni-1.1-flash, only
supports generateContent and cannot make video at all). The error was never loud: daily_post.py's
existing except-and-fall-back-to-a-zoom-still swallowed it cleanly, so 15 reels in a row shipped as
motionless stills with nobody told (STRATEGY.md §18).

Now Higgsfield — the SAME account already used for the still backgrounds (fetch_higgsfield.py),
same HF_API_KEY/HF_API_SECRET, no new credential. Their Wan 2.7 image-to-video model
(api.higgsfield.ai/wan/v2.7/image-to-video) takes the still, a motion prompt and a negative
prompt, and returns an mp4 — verified for real on 2026-10-31 with output/_bg.png: 8.03s,
720x1280 (the input's own 9:16 kept automatically — there is no aspect-ratio field to set), camera
locked, composition unchanged frame 0 → 4 → 7. $0.05/s pay-as-you-go, no subscription — about half
of Veo's ₩138/s (metrics.VEO_WON_PER_SECOND; update that constant once a real invoice replaces the
quoted rate).

    python3 fetch_veo.py still.png out.mp4
"""

import sys
import time

import fetch_higgsfield as hf   # reuse _credentials() — same Higgsfield account as the stills

APPLICATION = "wan/v2.7/image-to-video"

# Locked camera + BARELY-THERE motion, so the composition (and the clear center band the verse
# sits on) never shifts AND the scene never looks frantic. Fast video models tend to over-animate,
# so the prompt pushes hard toward "a living photograph that only breathes" — the fast waves /
# rushing traffic came from asking for too much motion, not from any speed bug downstream.
MOTION = (
    "REAL-TIME at 1x speed, never a timelapse or sped up. The camera is locked — no pan, no zoom, "
    "no move — and the scene is almost still: only the smallest movement that eight real seconds "
    "would actually contain, like a photograph breathing. Nothing enters, leaves, grows or changes."
)

# Prefixed to MOTION when animating the tail frame of an earlier segment, so the segments read as
# ONE continuous shot rather than two takes of the same place. Length has to come from the model
# itself (CONTENT_RULE 6) — this is the "genuine continuation" that rule allows, as opposed to a
# loop. Retrying with the SAME prompt is three draws from one distribution: if the model
# over-animates a given image it will do so again. So each retry escalates the demand. Index 0 is
# the plain prompt.
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


# Billed per generated second whether the take is used or not, and it is the dominant cost line.
# Counting calls here makes the bill a number in metrics.json rather than an estimate
# reconstructed from logs after the fact.
CALLS = [0]
SECONDS_PER_CALL = 8.0


def animate(still_png, dest, aspect="9:16", prompt=MOTION, timeout_s=420, poll_s=5):
    """Submit `still_png` for image-to-video, poll the request, download the mp4 to `dest`.
    Raises on error/timeout so callers can fall back to a zoom still.

    `aspect` is accepted for call-site compatibility but unused: Wan 2.7 has no aspect-ratio
    parameter and simply keeps the input image's own ratio, which is already 9:16 (generate.REEL)
    for every still this pipeline makes."""
    CALLS[0] += 1
    import content_law
    import higgsfield_client as h
    from PIL import Image

    client = h.SyncClient(api_key=hf._credentials())
    img = Image.open(still_png)
    img_url = client.upload_image(img, format="png")

    args = {
        "image_url": img_url,
        "prompt": content_law.for_video(prompt),
        "negative_prompt": NEG + ", " + content_law.NEG_TERMS,
        "duration": int(SECONDS_PER_CALL),
        "resolution": "720p",
    }
    ctrl = client.submit(APPLICATION, args)

    # client.submit()/.get() poll forever with no ceiling (confirmed in higgsfield_client's
    # poll_request_status: `while True`) — the same unbounded-hang shape the old Google poll loop
    # was written to avoid, so this keeps that same explicit timeout rather than trusting the SDK.
    waited = 0
    status = ctrl.status()
    while not isinstance(status, h.DONE_STATUSES):
        if waited >= timeout_s:
            raise RuntimeError(f"higgsfield: timed out after {timeout_s}s")
        time.sleep(poll_s)
        waited += poll_s
        status = ctrl.status()

    if isinstance(status, h.NSFW):
        raise RuntimeError("higgsfield: flagged NSFW")
    if isinstance(status, (h.Failed, h.Cancelled)):
        raise RuntimeError(f"higgsfield: request {type(status).__name__.lower()}")

    result = ctrl.get()
    video = result.get("video") or {}
    url = video.get("url")
    if not url:
        raise RuntimeError(f"higgsfield: no video in response ({result})")
    import urllib.request
    urllib.request.urlretrieve(url, dest)
    return dest


if __name__ == "__main__":
    still, out = sys.argv[1], sys.argv[2]
    print(animate(still, out))
