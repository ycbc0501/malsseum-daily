#!/usr/bin/env python3
"""
Animate a still image into a short cinematic clip.

Was Google Veo (predictLongRunning on generativelanguage.googleapis.com). On 2026-10-23 Google
pulled the model out from under us without warning: every call started returning
"models/veo-3.1-fast-generate-preview is no longer available", and NOT A SINGLE model exposed by
this API key still supported predictLongRunning (checked by listing all 60 models on 2026-10-31).
The error was never loud: daily_post.py's existing except-and-fall-back-to-a-zoom-still swallowed
it cleanly, so 15 reels in a row shipped as motionless stills with nobody told (STRATEGY.md §18).

Patched 2026-10-31 onto Higgsfield — the SAME account already used for the still backgrounds
(fetch_image.py). That was only ever meant as a stopgap ("already have the credentials") taken
days after fetch_image.py's OWN default had just moved to Gemini for stills precisely because
Higgsfield was being retired as a cost/trust concern (double billing, over-spec for what a still
background needs). Nobody recognised reusing it for motion as un-reversing that decision — it
read as "reuse an existing credential", not "un-retire a vendor" — until the account's credits
ran out on 2026-11-08 (`not_enough_credits`) and the account owner asked why Higgsfield was still
being paid for at all (CLAUDE.md 2026-11-08/09).

Replaced 2026-11-09 with Gemini Omni 1.2 Flash (GA 2026-11-05) via the Interactions API — a
DIFFERENT door from generateContent, which is the one the 2026-10-31 "Omni can't make video"
finding actually knocked on (generateContent genuinely never serves video; this model only takes
requests through POST .../v1beta/interactions). Verified live against the real account before
being wired in here — 9 billed image-to-video generations total: 7 raw-protocol probes (to pin
down the request/response shape and test two HTTP clients) plus 2 through this file's actual
animate(), chained end to end exactly as daily_post.py would (opening segment, then a real
continuation generated from the opening's own last frame via make_video.last_frame(), then
make_video.chain_clips() joining the two) — the 15.6s joined clip held one locked composition
start to end, measured (make_video.structure_drift = 9.33, limit 20) and eyeballed frame-by-frame
at the seam. What that testing found:
  - synchronous: the HTTP response itself carries status:"completed" and the finished clip —
    there is no job id to poll, unlike Veo's and Higgsfield's long-running-operation shape.
  - 8.0-8.04s / 720x1280 every time, with aspect_ratio="9:16" accepted explicitly in
    response_format (so, unlike Wan 2.7, this provider DOES have a real aspect control).
  - ships an AAC audio track on every clip with no field to suppress it. NOT stripped here —
    make_video.chain_clips() (`-map "[v]" -an`) and make_video.build_reel_native()
    (`-map "[v]" -map "2:a"`, where input 2 is this pipeline's own Lyria music, RULES.md E-6)
    both select video-only from this file's output by explicit stream index, so the model's own
    audio is already discarded downstream however many segments ship. An early strip here was
    tried and removed in code review (2026-11-09) as redundant work with its own failure surface
    (an extra ffmpeg subprocess + temp file per clip for a guarantee two call sites already gave).
  - no dedicated negative-prompt field exists on this endpoint (same absence fetch_image.py's
    plain Gemini stills already work around) — what must not appear is folded into the one text
    prompt as "avoid", not sent as a separate parameter.
  - plain urllib.request.urlopen() dropped the connection mid-transfer on 1 of 3 tries
    (http.client.IncompleteRead, ~20KB short of a ~4.5MB body) — the `requests` library completed
    3/3. The clip generates and bills either way; only the client-side download differs. So this
    file uses `requests`, imported lazily inside animate() the same way `higgsfield_client` used
    to be, to keep `import fetch_motion` cheap for callers that only read its constants
    (check_rules.py does exactly that).

SAME GEMINI_API_KEY already used for the stills (fetch_image.py) — no new credential, no new
account, no new secret to register.

    python3 fetch_motion.py still.png out.mp4
"""

import base64
import sys

import content_law
import fetch_image as gm   # reuse _gemini_key() -- same Gemini account as the stills

MODEL = "gemini-omni-1.2-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

# Locked camera + BARELY-THERE motion, so the composition (and the clear center band the verse
# sits on) never shifts AND the scene never looks frantic. Fast video models tend to over-animate,
# so the prompt pushes hard toward "a living photograph that only breathes" — the fast waves /
# rushing traffic came from asking for too much motion, not from any speed bug downstream.
# 2026-11-11: the account owner watched actual output and called two things out by name —
# "배경 그림자 움직이는거나 갑자기 반짝이 떠다니는거" (background shadow moving, sparkle suddenly
# floating around) — "너무 가짜같은데" (looks too fake). Neither was ever asked for; MOTION already
# pushed toward near-stillness. The likely mechanism: the still image already carries its own light
# and shadow pattern and film grain (fetch_image.QUALITY — "subtle grain", "a soft filmic quality"),
# and an image-to-video model given only "breathe a little" with no instruction about what NOT to
# animate will readily reinterpret that grain as floating dust/sparkle and that shadow edge as
# something sliding across the wall, because both already look like texture waiting to move. Fixed
# by naming the failure mode directly instead of only asking for less motion in general — "less"
# doesn't tell the model WHICH surface details must hold still.
MOTION = (
    "REAL-TIME at 1x speed, never a timelapse or sped up. The camera is locked — no pan, no zoom, "
    "no move — and the scene is almost still: only the smallest movement that eight real seconds "
    "would actually contain, like a photograph breathing. Nothing enters, leaves, grows or changes. "
    "Every shadow and patch of light stays exactly where it already is in the frame — nothing "
    "slides, crawls, sweeps or drifts across any surface. Film grain and surface texture are fixed "
    "to the surface they belong to, like grain on a photograph, never floating specks, dust or "
    "sparkle drifting through the air."
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

# Speed and camera only. What may not APPEAR lives in content_law.NEG_TERMS. Neither Higgsfield's
# negative_prompt field nor a Gemini Omni equivalent exists any more on this provider — there is no
# dedicated field at all — so both of these are folded straight into the one text prompt in
# animate() below, under "AVOID ENTIRELY". Naming the same thing in both strings is how this list
# ended up listing "text", "people", "watermark" and "logo" twice each; kept apart on purpose.
NEG = ("timelapse, sped up, fast-forward, accelerated motion, fast movement, "
       "fast-moving clouds, racing clouds, moving clouds, "
       "rushing water, crashing waves, flowing water, strong current, rolling waves, churning, "
       "turbulence, busy traffic, energetic movement, "
       "camera pan, camera zoom, camera shake, hard cut, scene change, jump cut, "
       "morphing, warping, sudden changes, popping in, flickering, "
       "elements appearing or disappearing, growing, strobing, "
       # 2026-11-11 — named directly, see MOTION's comment: the two defects the account owner
       # actually saw in a published clip, not a generic "less motion" that doesn't say which
       # surface detail must hold still.
       "floating dust, floating sparkle, drifting light motes, glinting specks in the air, "
       "shifting shadows, moving shadow patterns, dappled light sliding across a surface, "
       "grain or texture moving like floating particles")


# Billed per generated second whether the take is used or not, and it is the dominant cost line.
# Counting calls here makes the bill a number in metrics.json rather than an estimate
# reconstructed from logs after the fact.
CALLS = [0]
SECONDS_PER_CALL = 8.0


def animate(still_png, dest, aspect="9:16", prompt=MOTION, timeout_s=180):
    """Submit `still_png` for image-to-video, save the mp4 to `dest`.
    Raises on error/timeout so callers can fall back to a zoom still.

    Synchronous: the Interactions API returns the finished clip in the HTTP response itself
    (confirmed live 2026-11-09 — `status` is already "completed" when the request returns, no
    job id to poll), unlike the submit-then-poll shape Higgsfield and Veo both used. Measured
    latency for one 8s/720p clip was 37-44s across 7 live calls, so 180s leaves ample margin
    without reviving the old unbounded-poll risk this file used to guard against explicitly.

    `aspect` is a REAL parameter here (response_format.aspect_ratio) — unlike the Higgsfield
    Wan 2.7 call this replaced, which had no aspect-ratio field of its own and simply inherited
    whatever the input image already was.
    """
    CALLS[0] += 1
    import requests   # lazy — see module docstring: keeps `import fetch_motion` dependency-light

    with open(still_png, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    text = (content_law.for_video(prompt) + "\n\nAVOID ENTIRELY, at any point in the clip: "
            + NEG + ", " + content_law.NEG_TERMS + ".")
    body = {
        "model": MODEL,
        "input": [
            {"type": "image", "data": img_b64, "mime_type": "image/png"},
            {"type": "text", "text": text},
        ],
        "response_format": {"type": "video", "resolution": "720p", "aspect_ratio": aspect},
    }
    resp = requests.post(f"{API_URL}?key={gm._gemini_key()}", json=body, timeout=timeout_s)
    if resp.status_code != 200:
        raise RuntimeError(f"gemini-omni: HTTP {resp.status_code} ({resp.text[:500]})")
    data = resp.json()

    status = data.get("status")
    if status != "completed":
        raise RuntimeError(f"gemini-omni: status={status} ({data.get('error') or data})")

    video_b64 = None
    for step in data.get("steps", []):
        for part in step.get("content", []):
            if part.get("type") == "video":
                video_b64 = part.get("data")
    if not video_b64:
        raise RuntimeError(f"gemini-omni: no video in response (id={data.get('id')})")

    with open(dest, "wb") as f:
        f.write(base64.b64decode(video_b64))
    return dest


if __name__ == "__main__":
    still, out = sys.argv[1], sys.argv[2]
    print(animate(still, out))
