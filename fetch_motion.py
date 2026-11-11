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
#
# 2026-11-11, first attempt (superseded below): the account owner watched actual output and
# called two things out by name — "배경 그림자 움직이는거나 갑자기 반짝이 떠다니는거" (background
# shadow moving, sparkle suddenly floating around) — "너무 가짜같은데" (looks too fake). The fix
# tried then NAMED the two defects and added them to NEG as a ban list ("floating dust, floating
# sparkle, ... shifting shadows, moving shadow patterns, ...") on top of a MOTION that still only
# said "almost still" without saying what WAS allowed to move.
#
# 2026-11-11, same day, corrected: the account owner read that diff and pushed back directly —
# "먼지금지 이런거 넣지 말자 프롬프트 너무 복잡해져. 그냥 '더 진짜처럼'을 구현할수 있는 프롬프트가
# 뭔지 딥리서치해서 프롬프트고슈들이 뭐쓰는지 보고 그거써." Deep research into what working video
# prompt engineers actually do (2026 guides on Veo/Sora/Kling prompting) converges on one point
# that cuts directly against the first attempt: "describe what should happen rather than what
# should be avoided — positive motion instructions work better than long negative lists." The
# first attempt's real flaw was never its wording — it was its SHAPE: MOTION left "what is allowed
# to move" completely unstated, so a long NEG list was doing the job a clear positive instruction
# should have done from the start, growing without bound as each new failure mode got discovered
# and named. Fixed structurally instead: MOTION now states, in one place, the SAME physically real
# motion a nature-documentary tripod shot would actually have (water, cloud, mist, flame, leaves,
# fabric, steam) — naming a concrete positive target gives the model nothing left to invent, so
# grain and shadow no longer need their own ever-growing ban list (removed from NEG below).
MOTION = (
    "A single locked-tripod shot, exactly like one static take from a nature documentary: real "
    "time, 1x speed, never a timelapse, the camera never pans, zooms or moves at all. The ONLY "
    "thing allowed to move is whatever this exact scene would genuinely move on its own across "
    "eight real seconds — water rippling, a cloud or mist drifting, a flame flickering, a leaf or "
    "fabric trembling in air, steam rising — and even that moves barely, like a photograph just "
    "beginning to breathe. Every shadow, every patch of light and all film grain stay fixed to the "
    "surface they are already on, exactly as they would in a real, unedited recording."
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
# 2026-11-11: no longer carries "floating dust / floating sparkle / shifting shadows / ..." — see
# MOTION's comment. That ban list was a SYMPTOM list growing in step with whatever the account
# owner had most recently spotted in a published clip; the fix that actually holds is MOTION
# naming the one thing allowed to move, which leaves nothing else for the model to invent. Kept
# below are only the structural failure modes positive phrasing can't cover on its own (speed,
# camera, cuts, warping) — not an ever-growing catalogue of specific surface artifacts.
#
# Structural review (2026-11-11) caught a real bug in the first draft of this edit: "moving
# clouds", "flowing water" and plain "flickering" were still banned here while MOTION's new
# positive list explicitly ALLOWS "a cloud or mist drifting", "water rippling" and "a flame
# flickering" — the exact COMPOSE/EVENTONE contradiction content_law.py's own docstring warns
# about (one block permits what another forbids, and the model resolves it unpredictably). Fixed
# by keeping only the EXCESS/violent form of each motion here (racing/fast clouds, crashing/
# rushing water, strobing) — the gentle form MOTION now names is no longer also banned by name.
NEG = ("timelapse, sped up, fast-forward, accelerated motion, fast movement, "
       "fast-moving clouds, racing clouds, "
       "rushing water, crashing waves, strong current, rolling waves, churning, turbulence, "
       "busy traffic, energetic movement, "
       "camera pan, camera zoom, camera shake, hard cut, scene change, jump cut, "
       "morphing, warping, sudden changes, popping in, "
       "elements appearing or disappearing, growing, strobing")


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
