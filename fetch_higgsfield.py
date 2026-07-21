#!/usr/bin/env python3
"""
Generate a fresh serene-nature background via the Higgsfield Cloud API (Flux Pro).
Each call returns a unique image — so backgrounds never repeat, no licensing, no Pexels.

Credentials: env HF_API_KEY + HF_API_SECRET, or a local higgsfield_key.txt with those lines.
"""

import base64
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "gemini"        # default backend: Nano Banana Pro (photoreal, clean, respects "no text")
GEMINI_MODEL = "gemini-3-pro-image"
VISION_MODEL = "gemini-2.5-pro"   # vision model that inspects the render for composition flaws
                                  # (flash missed the upright-reflection bug; pro catches it)
FLUX = "flux-pro/kontext/max/text-to-image"   # Higgsfield fallback options
SOUL_APP = "v1/text2image/soul"
SOUL_BASE = "https://platform.higgsfield.ai"

# WIDE-RANGING, dreamy cinematic scenes — deliberately across MANY subjects (water, city streets,
# windows, architecture, weather, coasts, whimsical objects, cozy corners), NOT just fields and
# flowers. Each is chosen to also ANIMATE cleanly in Veo (one clear, simple motion — rippling or
# reflecting water, rain, drifting mist/clouds, gently swaying elements) rather than a busy field of
# many small flowers (which comes out coarse). Each keeps a soft area for the verse. Ordered to
# alternate the subject so the feed never looks the same twice.
# Scenes chosen for WEIGHT, GRAVITY and REALNESS (the user loved a dark, heavy real-sea photo and
# hated a kitschy AI fountain). Lean toward deep, serious, atmospheric, real-looking imagery — dark
# seas, heavy skies, mist, stone, rain — with some quieter serene scenes for tonal range. AVOID
# staged/twee/ornamental subjects (decorative fountains, string-light cafés, flower-basket bicycles,
# umbrellas cradling flowers) — AI renders those as fake CGI. Each still animates cleanly in Veo (or,
# for heavy seas, the motion gate falls it back to a strong still — which is exactly the loved look).
# Scenes are grouped by THEME so we can guarantee variety. Sequential rotation over a flat list
# was clustering (the list happened to start with 8 water scenes in a row → every recent post was
# "village + water below"). Fix: keep the themes in named groups, then ROUND-ROBIN interleave them
# into the flat SCENES list so walking it sequentially alternates themes (sea → forest → street →
# cathedral → mountain → …), never the same theme twice running. `pick_scene()` adds a second guard:
# a category no-repeat ledger, so even a gate rejection / fallback can't collapse two same-theme posts.
SCENE_GROUPS = {
    # ── deep water & sea (WEIGHT / gravity) ──
    "sea": [
        "dark ocean swells rolling under a heavy overcast sky, white foam streaking the deep water",
        "slow heavy waves rolling onto a vast empty shore under a dim grey dawn",
        "a shaft of pale light breaking through dark storm clouds over a wide restless sea",
        "deep still water at dusk, faint ripples under a brooding sky",
    ],
    # ── forest / trees / snow (dry land, no big water) ──
    "forest": [
        "gentle snow drifting down over a dark, silent pine forest at dusk",
        "an autumn forest path in low morning mist, leaves drifting slowly",
        "bare winter trees standing in still, heavy fog, quiet and grey",
        "cherry blossom branches swaying softly against a soft grey sky, a few petals drifting",
    ],
    # ── city / street (real, moody) ──
    "street": [
        "a lone street lamp glowing over wet cobblestones on a rainy night",
        "a narrow old European alley in the rain, warm light pooling on the wet stone",
        "a rainy city crosswalk at night, glowing neon and headlights reflected in the wet street",
    ],
    # ── stone / architecture (reads real, weighty) ──
    "stone": [
        "the tall interior of an old stone cathedral, soft light drifting from high windows",
        "a weathered stone chapel alone on a hill under a heavy drifting sky",
        "an ancient stone archway opening onto a misty valley at dawn",
    ],
    # ── mountains / hills (dry, high, dry-land gravity) ──
    "mountain": [
        "mist drifting slowly through dark pine-covered mountains at first light",
        "low cloud and mist rolling over a lone bare tree on a wide, empty hillside",
        "a calm alpine lake mirroring dark snow peaks at dawn, faint mist on the water",
    ],
    # ── water & reflections (clean motion) ──
    "reflection": [
        "gentle rain rippling a still dark pond that mirrors bare autumn trees and a grey sky",
        "an old town canal reflecting weathered stone buildings, the dark water rippling softly",
        "a wooden rowboat resting on a glassy misty lake at dawn, faint drifting mist",
    ],
    # ── coast / cliffs ──
    "coast": [
        "a lighthouse on a dark cliff under drifting cloud, surf breaking on the rocks below",
        "pale sea cliffs above a deep restless shore under a wide, muted sky",
    ],
    # ── windows / interior ──
    "window": [
        "a rain-speckled window with a blurred grey landscape beyond the wet glass",
        "an open window, sheer curtains drifting gently, a calm pale sky beyond",
    ],
    # ── quiet / still ──
    "quiet": [
        "a lone weathered wooden bench facing a calm, misty field at grey dawn",
        "a single candle-lit stone windowsill at dusk, soft shadow and still air",
    ],
}
# Round-robin interleave: one scene from each theme per pass, so SCENES[i], SCENES[i+1]… cycle
# through DIFFERENT themes. SCENE_CATS[i] is the theme of SCENES[i] (used by the no-repeat ledger).
SCENES, SCENE_CATS = [], []
_round = 0
while any(len(v) > _round for v in SCENE_GROUPS.values()):
    for _cat, _items in SCENE_GROUPS.items():
        if _round < len(_items):
            SCENES.append(_items[_round])
            SCENE_CATS.append(_cat)
    _round += 1


def pick_scene(start, recent_cats, avoid=2):
    """Choose the next scene index, skipping forward past any whose THEME appears in the last
    `avoid` posts — so themes never cluster even if the gate rejects/falls back. Returns
    (index, category). Caller advances scene_i to index+1 and records the category."""
    recent = list(recent_cats)[-avoid:] if avoid else []
    n = len(SCENES)
    for step in range(n):
        i = (start + step) % n
        if SCENE_CATS[i] not in recent:
            return i, SCENE_CATS[i]
    i = start % n
    return i, SCENE_CATS[i]
COMPOSE = {
    ("center", "middle"): "COMPOSITION: compose so the CENTER of the frame — where the verse will sit — "
        "stays soft, open and easy to read text over (open sky, soft mist, calm water or gentle "
        "out-of-focus blur, whatever suits THIS scene). Keep the main subject and any tall elements "
        "(trees, buildings, branches) LOW in the frame or off to the sides, well clear of the centre, so "
        "nothing crosses the middle where the text goes. It must be ONE single natural photograph filling "
        "the whole frame — NEVER a framed picture, inset, border, panel, photo-within-a-photo, polaroid "
        "or collage; the whole image is one continuous scene. Show each subject only ONCE, never "
        "duplicated or mirrored, and never dead-centre.",
    ("left", "middle"): "Leave the left and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the right "
        "and lower part of the photo, keeping the text area clear.",
    ("right", "middle"): "Leave the right and central part of the photo calm and simple for the overlaid "
        "text (soft sky, light, water or a quiet background); place the main subject toward the left "
        "and lower part of the photo, keeping the text area clear.",
}
EVENTONE = ("Render ONE single, continuous, real photograph — one coherent scene with ONE horizon line "
            "only. It must NOT be split or stacked into two scenes: NEVER two horizons, NEVER a second "
            "body of water, second lake, second sky or second landscape above or below the first, NEVER a "
            "mirrored, doubled or repeated view, and never a framed picture, inset, panel, collage, "
            "photo-within-a-photo or any hard horizontal seam. There is only one sky and (if any) one "
            "water surface, in their natural real-world places — sky above, ground or water below, a "
            "single horizon. The TOP of the frame is sky or open space — NEVER an upside-down mirror of "
            "the bottom: no upside-down trees, mountains, cliffs or land hanging down from the top edge, "
            "and no top-bottom kaleidoscope symmetry. "
            "Compose it so the calm, soft, open area where the verse sits (soft sky, "
            "gentle haze, calm water or quiet out-of-focus light) falls naturally across the middle of "
            "this ONE scene — reached organically, never by pasting a second scene into the centre. "
            "If any water (puddle, canal, lake, wet street) reflects something, the reflection MUST be a "
            "physically-correct UPSIDE-DOWN MIRROR image directly below the real object — rooftops and "
            "buildings in the reflection point DOWNWARD, inverted — NEVER a second upright building, town "
            "or scene sitting the right way up in the water.")
COMPOSE_SAFE = ("Keep it a real, natural, uncluttered composition — one continuous photograph. Do not let "
                "any object crowd, block or sit dead-center in the calm middle where the text goes; keep "
                "the main subject and busy detail toward the edges, top or bottom of the frame.")
QUALITY = ("It is a GENUINE real photograph taken with a real camera — richly atmospheric, with real "
           "depth and a quiet sense of WEIGHT, gravity and reverence (holy, still, serious and true — "
           "never cute, kitschy, saccharine, twee or fantastical). Real natural light suited to THIS "
           "scene — often deep, dim, overcast, moody or low-key, not always sunny or golden. Natural "
           "photographic detail, real texture and true-to-life colour with a subtle film grain. It must "
           "look like an ACTUAL photograph a person took — absolutely NOT a glossy 3D render, CGI, a "
           "video-game frame, a digital painting, or a plasticky/artificial AI image. Understated, "
           "grounded and real, with weight — an image that feels honest and quietly moving.")
NOTEXT = ("There are no visible human faces, and absolutely no text, letters, words, captions, numbers, "
          "signs, watermark or logo anywhere. It is a single full-bleed photograph that completely fills "
          "the image, edge to edge.")


def _credentials():
    key, sec = os.environ.get("HF_API_KEY"), os.environ.get("HF_API_SECRET")
    kf = os.path.join(HERE, "higgsfield_key.txt")
    if (not key or not sec) and os.path.exists(kf):
        for line in open(kf):
            if line.startswith("HF_API_KEY="):
                key = line.split("=", 1)[1].strip()
            elif line.startswith("HF_API_SECRET="):
                sec = line.split("=", 1)[1].strip()
    if not (key and sec):
        raise SystemExit("Missing HF_API_KEY / HF_API_SECRET")
    return f"{key}:{sec}"


def generate_background(dest, index=0, placement=("center", "middle"), full_scene=False,
                        model=MODEL, aspect="3:4"):
    """Generate one background → save to `dest`. Clean natural-language prompt (Gemini follows
    prose); the text area is kept clear per `placement`. `aspect` = "3:4" (feed) or "9:16" (reel)."""
    scene = SCENES[index % len(SCENES)]
    compose = COMPOSE.get(tuple(placement), COMPOSE[("center", "middle")])
    prompt = f"A breathtaking, dreamy cinematic photograph of {scene}. {compose} {COMPOSE_SAFE} {EVENTONE} {QUALITY} {NOTEXT}"

    if model == "gemini":
        return _gemini(prompt, dest, aspect=aspect)

    import higgsfield_client as h
    client = h.SyncClient(api_key=_credentials())
    if model == "soul":
        url = _soul(client, prompt)
    else:
        args = {"prompt": prompt, "aspect_ratio": aspect}
        if "flux" in model:
            args["safety_tolerance"] = 2
        url = client.subscribe(model, args)["images"][0]["url"]
    urllib.request.urlretrieve(url, dest)
    return dest


_CHECK_PROMPT = (
    "You are inspecting an AI-GENERATED vertical photo for PHYSICALLY IMPOSSIBLE composition flaws — "
    "the kind an image generator makes. IMPORTANT: a NORMAL photo has sky or open space in the UPPER "
    "part and ground / water / the subject in the LOWER part, meeting at ONE horizon — that is CORRECT "
    "and common, so do NOT flag a normal single-horizon landscape or seascape. Flag ONLY these clear "
    "flaws, and be strict about them:\n"
    "1) VERTICAL MIRROR: the TOP portion is an upside-down mirror of the bottom — trees, mountains, "
    "cliffs, buildings or land hanging UPSIDE-DOWN from the top edge, or an obvious kaleidoscope / "
    "top-bottom mirror symmetry.\n"
    "2) STACKED DUPLICATE: the frame is split into TWO separate scenes — two separate horizons, or two "
    "separate bodies of water with land between them (e.g. one lake high up AND another lake below).\n"
    "3) WRONG REFLECTION: a reflection in water (puddle, canal, lake, wet street) that is NOT a correct "
    "upside-down mirror — e.g. buildings appearing UPRIGHT in the water instead of inverted (a 'second "
    "town' sitting in the water).\n"
    "4) FAKE / CGI: the image clearly looks like a glossy 3D/CGI render, a video-game frame, a digital "
    "painting or a plasticky artificial AI image — including fake, over-perfect ornate man-made objects "
    "— rather than a real photograph. Only flag CLEARLY fake/plastic/CGI, not a real photo with moody "
    "or dim light.\n"
    "5) Obviously impossible, duplicated, melted or badly warped major structures.\n"
    "Do NOT flag: a normal single-horizon landscape/seascape, artistic blur, bokeh, mist, grain, dark "
    "or moody light, or a CORRECT (properly inverted) reflection.\n"
    "Reply ONLY as JSON: {\"ok\": true, \"reason\": \"\"} if it looks physically plausible, or "
    "{\"ok\": false, \"reason\": \"<short reason>\"} if any flaw above is present.")


def check_composition(image_path):
    """Ask a Gemini vision model whether the render has a physically-impossible composition (stacked
    double scene / wrong-way reflection / duplicated structure). Returns (ok: bool, reason: str).
    Best-effort: on ANY error returns (True, ...) so a flaky check never blocks the daily post."""
    try:
        img_b64 = base64.b64encode(open(image_path, "rb").read()).decode()
        body = {"contents": [{"parts": [
                    {"inlineData": {"mimeType": "image/png", "data": img_b64}},
                    {"text": _CHECK_PROMPT}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{VISION_MODEL}:generateContent?key={_gemini_key()}")
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        data = json.load(urllib.request.urlopen(req, timeout=90))
        txt = data["candidates"][0]["content"]["parts"][0]["text"]
        j = json.loads(txt)
        return bool(j.get("ok", True)), str(j.get("reason", ""))[:200]
    except Exception as e:
        return True, f"check skipped ({e})"


def generate_checked(dest, index=0, placement=("center", "middle"), aspect="3:4", attempts=3):
    """Generate a background AND vision-check its composition; regenerate (up to `attempts`) if the
    checker flags a stacked/duplicated scene or a wrong reflection. Returns the last render either
    way (best-effort — never raises just because the checker was unhappy)."""
    for a in range(1, attempts + 1):
        generate_background(dest, index, placement, aspect=aspect)
        ok, reason = check_composition(dest)
        print(f"composition check {a}/{attempts}: ok={ok} :: {reason}")
        if ok:
            return dest
    return dest


def _gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    kf = os.path.join(HERE, "gemini_key.txt")
    if not key and os.path.exists(kf):
        for line in open(kf):
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("Missing GEMINI_API_KEY")
    return key


def _gemini(prompt, dest, aspect="3:4"):
    """Nano Banana Pro (Gemini 3 Pro Image) → save image to dest."""
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"imageConfig": {"aspectRatio": aspect, "imageSize": "2K"}}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={_gemini_key()}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    data = json.load(urllib.request.urlopen(req, timeout=180))
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            with open(dest, "wb") as f:
                f.write(base64.b64decode(part["inlineData"]["data"]))
            return dest
    raise RuntimeError("gemini: no image in response")


def _soul(client, prompt, wh="1536x2048"):
    """Higgsfield Soul (flagship). Its response shape differs from the SDK's, so we call
    the endpoint via the SDK's transport and poll the status ourselves."""
    t = client._transport
    job = t.request("POST", f"{SOUL_BASE}/{SOUL_APP}",
                    json={"params": {"prompt": prompt, "width_and_height": wh}}, timeout=120).json()
    jid = job["id"]
    for _ in range(60):
        st = t.request("GET", f"{SOUL_BASE}/requests/{jid}/status", timeout=30).json()
        if st["status"] == "completed":
            return st["images"][0]["url"]
        if st["status"] in ("failed", "error", "canceled"):
            raise RuntimeError(f"soul {st['status']}")
        time.sleep(3)
    raise RuntimeError("soul timeout")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "hf_bg.png"
    print(generate_background(out, 0))
