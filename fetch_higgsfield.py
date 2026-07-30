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
# AESTHETIC = 고요함 (QUIET), not brightness (user direction 2026-07-30, superseding the bright-only
# direction of 2026-07-23). Bright dawn and a lamp-lit room after dark are BOTH on brand; what is
# banned is gloom, dread, despair and heaviness — a quiet dark is peaceful, a gloomy dark is not.
# Still HYPERREALISTIC, real and reverent, and still anti-kitsch — AVOID staged/twee/ornamental
# subjects (decorative fountains, string-light cafés, flower-basket bicycles, umbrellas cradling
# flowers) which AI renders as fake CGI.
# The verse LEADS: the frame is the accompaniment, so scenes stay simple and under-stated. A frame
# with a lot to say competes with the 말씀 and wins.
# Scenes are grouped by THEME so we can guarantee variety. Sequential rotation over a flat list was
# clustering, so we keep themes in named groups then ROUND-ROBIN interleave them into the flat SCENES
# list so walking it sequentially alternates themes (sea → window → street → …), never the same theme
# twice running. `pick_scene()` adds a category no-repeat ledger too.
#
# Base prompts name the SUBJECT and weather ONLY — never the time of day, never the brightness. Tone
# comes from the rotating LIGHT palette, which is now free to be quiet and dark as well as bright.
# (This rule was always documented here but never followed: the prompts used to carry 109 hardcoded
# tone words — "bright" 46×, "sunlit" 22×, "sunlight" 20× — which is the real reason the account
# could only ever look bright. A dark LIGHT palette would have contradicted the scene itself.)
#
# Two families, deliberately:
#   · QUIET NATURE / ARCHITECTURE — the wide, calm scenes.
#   · EVERYDAY & INTIMATE — a window, a lamp, a made bed, stems in a glass. This family is what the
#     @dailymayim reference is mostly made of, and it is the one that lets the 말씀 lead: an ordinary
#     room has far less to say than a monumental landscape, so the verse becomes the subject.
SCENE_GROUPS = {
    # ── quiet nature & architecture ──
    "sea": [
        "the open sea rolling in long gentle swells under a wide empty sky",
        "the open sea far from shore, low swells moving slowly beneath a broad sky",
    ],
    "forest_path": [
        "a narrow path winding into a green forest between tall slender trees",
        "a woodland trail with fresh leaves overhead and soft ground underfoot",
    ],
    "cathedral": [
        "the tall stone interior of an old cathedral, light falling from high windows",
        "the long nave of an old church, stone columns receding toward the far end",
    ],
    "mist_mountain": [
        "green mountain ridges layered one behind another, soft mist settled between them",
        "a single peak rising above a low sea of cloud",
    ],
    "rainy_street": [
        "a cobblestone lane freshly washed by rain, wet stones and pastel houses",
        "a quiet old-town lane still glistening after rain, water beading on the stone",
    ],
    "wheat_field": [
        "a wide field of wheat bending slowly under an open sky",
        "an open plain of grain rolling away toward a low far horizon",
    ],
    "reflection_lake": [
        "a still lake holding a correct upside-down reflection of the mountains behind it",
        "a calm mountain lake mirroring the ridge above in a clean inverted reflection",
    ],
    "lighthouse": [
        "a white lighthouse standing on a green headland above the sea",
        "a lighthouse above low cliffs, the sea stretching away to the horizon",
    ],
    "snowfall": [
        "soft snow drifting down through a quiet forest",
        "gentle snow falling across an open field of clean untouched white",
    ],
    "canal_town": [
        "an old town beside a canal, the buildings reflected correctly upside-down in the calm water",
        "a narrow canal between pastel stone houses, the water holding a clean inverted reflection",
    ],
    "chapel": [
        "a small white chapel alone on a green hill",
        "a plain country chapel standing at the edge of an open meadow",
    ],
    "wilderness": [
        "a vast open landscape of bare hills and distant ridges",
        "a wide canyon of weathered rock under an empty sky",
    ],
    "river": [
        "a broad river winding slowly through a green valley",
        "a calm river flowing between low grassy banks",
    ],
    "archway": [
        "a worn stone archway among old ruins, open sky beyond it",
        "the arches of an old stone ruin, the land visible through them",
    ],
    "blossom": [
        "branches of spring blossom against an open sky, a few petals drifting",
        "a single flowering tree standing alone on an open lawn",
    ],
    "starfield": [
        "a field of stars arching over low gentle hills, the Milky Way faintly visible",
        "a deep night sky full of stars above a soft low horizon",
    ],
    "harbor": [
        "small wooden boats resting on the calm water of a quiet harbor",
        "a few moored boats sitting still on flat harbor water",
    ],
    "winter_trees": [
        "bare winter trees standing in still air, frost on their branches",
        "a row of leafless winter trees along the edge of an open field",
    ],
    "storm_sky": [
        "broad shafts of light breaking through parting cloud over the sea",
        "heavy cloud opening over the water, beams falling through the gap",
    ],
    "rain_pond": [
        "gentle rain dimpling a still pond, the trees reflected correctly upside-down",
        "raindrops rippling the surface of a quiet pond, a clean inverted reflection below",
    ],
    "shore": [
        "small waves sliding up a wide empty shore over clean pale sand",
        "a long empty beach, shallow water running up the flat sand",
    ],
    "waterfall": [
        "a waterfall spilling down a mossy rock face into a clear pool, mist hanging in the air",
        "water falling from a high cliff into a still pool, spray drifting at its base",
    ],
    "dusk_sky": [
        "a wide sky grading from deep overhead down to soft colour at the horizon, a thin crescent moon, a low silhouette of hills and a town with scattered lights along the bottom",
        "a broad evening sky above a low horizon, a faint crescent moon, the land beneath it a soft silhouette",
    ],
    "candle": [
        "a single candle standing on a stone windowsill, its small flame steady",
        "one candle burning quietly in a bare stone interior",
    ],

    # ── everyday & intimate: the reference's signature. Small, ordinary, quiet — the frame has
    #    little to say on its own, so the verse carries the post. ──
    "window_light": [
        "a plain window with a sheer curtain and an empty sill, a calm view beyond",
        "a simple window standing open, the air still, a quiet view outside",
    ],
    "bedroom": [
        "a simply made bed beside a window in a quiet bare room, soft folded linen",
        "a plain bed with rumpled white sheets in an empty room, a window nearby",
    ],
    "lamp_room": [
        "a small table lamp beside an armchair in a quiet, sparsely furnished room",
        "a single lamp on a side table in an otherwise empty room, its shade warm",
    ],
    "flowers_vase": [
        "a few slender stems in a clear glass vase on a windowsill",
        "one small bunch of flowers in a plain glass jar on a bare table",
    ],
    "curtain": [
        "a long sheer curtain drifting slowly at an open window",
        "pale linen curtains hanging still across a tall window",
    ],
    "desk": [
        "a plain wooden desk beside a window, an open book and a cup left on it",
        "a bare writing desk with a single notebook, a chair pushed in",
    ],
    "cafe_table": [
        "two simple chairs and a small round table on a quiet empty terrace",
        "a pair of metal chairs at a little table on an empty garden lawn",
    ],
    "alley": [
        "a narrow quiet lane between old walls, a few potted plants along one side",
        "a long empty stone alley, plants spilling from the walls",
    ],
    "city_night": [
        "a wide city skyline seen from high above, scattered windows lit across it",
        "a broad view over a sleeping city, streets threading between the buildings",
    ],
    "field_flowers": [
        "a patch of wildflowers standing in a meadow, stems leaning slightly",
        "poppies scattered across an open field of grass",
    ],
    "country_road": [
        "an empty road curving away between fields toward a far horizon",
        "a quiet lane running between hedgerows into open country",
    ],
    "still_water": [
        "a wide expanse of perfectly flat water meeting a low horizon",
        "shallow still water reaching away toward a distant shoreline",
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

# VARIATION — so even the SAME theme looks substantially different each time it recurs. LIGHT sets a
# colour/light palette (not a strict clock-time, so it never contradicts a scene, e.g. stars or a
# candle), VANTAGE sets the camera angle/distance. Keyed on a MONOTONIC per-post counter, not the
# scene index. LIGHT has 5 entries deliberately: a theme comes round every ~24 posts, and 5 does not
# divide 24, so a theme's light palette cycles through all five across successive appearances (a 6th
# palette would divide 24 and lock each theme to the same light every time).
LIGHT = [
    "in clear early-morning light",
    "in soft, even daylight",
    "in warm, low afternoon light",
    "in the pale quiet light of dawn",
    "in the last quiet light of dusk, the sky still holding colour",
    "in the cool blue stillness just after sunset",
    "in low light after dark — the scene only faintly lit, calm and very quiet",
]
VANTAGE = [
    "from a wide, distant vantage with deep open space",
    "from a low, grounded eye-level view",
    "from a high vantage looking out over it",
    "in an intimate, close and quiet framing",
]
# RETIRED 2026-07-30: the SCALE / 웅장함 axis ("monumental scale", "vast atmospheric depth", "a small
# element dwarfed to reveal scale"). It was the instrument of an image-first post, and the account is
# verse-first now: a monumental frame competes with the 말씀 for attention and wins. The @dailymayim
# reference carries almost no monumental imagery — it is windows, lamps, made beds, stems in a glass —
# and that is exactly why the verse reads as the subject there. Grandeur is not a variation axis any
# more; the everyday/intimate scene family in SCENE_GROUPS replaces it.

# SCALE — the 웅장함 (grandeur) axis. The hard constraint: COMPOSE keeps the CENTRE soft and open for
# the verse and pushes tall subjects low or to the sides, so we can NOT get grandeur the usual way (a
# huge subject filling the middle) — the two instructions would fight and the render comes out
# muddled. So every phrase below builds scale OUTSIDE the centre: receding depth, atmospheric
# perspective, immensity at the frame edges, and a small element that reveals how big everything else
# is. Each stays scene-agnostic ("whatever suits THIS scene") because this string is appended to all
# 25 themes, from open sea to a candle-lit interior.


def scene_variation(t):
    """A rotating 'light palette + camera angle' phrase, keyed on the monotonic post counter `t`, so
    successive appearances of the same theme differ in tone, colour and angle.

    LIGHT now spans BRIGHT THROUGH DARK (clear morning → faint light after dark). The account's
    criterion is 고요함 (quiet), not brightness: a lamp-lit room at night and a pale dawn are both on
    brand, while gloom, dread and despair are not — QUALITY and NEG carry that line.

    Periods stay coprime: LIGHT advances every post (7), VANTAGE every 7 posts (4), so a theme meets
    a fresh light+angle pairing for 28 posts before any combination recurs. 7 is prime and divides
    neither 36 (themes) nor 72 (scenes), so a theme never locks onto one tone."""
    light = LIGHT[t % len(LIGHT)]
    vi = (t // len(LIGHT)) % len(VANTAGE)
    return ", ".join([light, VANTAGE[vi]])


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
    ("center", "top"): "COMPOSITION: the UPPER HALF of the frame must be genuinely EMPTY — open sky, "
        "still water, a plain wall or soft haze, whatever suits THIS scene — because the verse sits "
        "there and must read with nothing behind it. Anchor the subject and every detailed or textured "
        "element in the LOWER THIRD: a low horizon, the ground, the furniture, the flowers, the "
        "rooftops all sit along the bottom edge, and NOTHING (no branch, no tree, no post, no "
        "building, no bird) reaches up into the empty upper half. Aim for a lot of plain negative "
        "space — an under-stated, quiet, restrained photograph rather than an impressive one. It must "
        "be ONE single natural photograph filling the whole frame — NEVER a framed picture, inset, "
        "border, panel, photo-within-a-photo, polaroid or collage; the whole image is one continuous "
        "scene. Show each subject only ONCE, never duplicated or mirrored.",
    # Kept so an older call site can't crash, but production uses ("center", "top") — see rule 9.
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
COMPOSE_SAFE = ("Keep it a real, natural, uncluttered composition — one continuous photograph, simple and "
                "restrained, with only a few elements. Do not let any object crowd or reach into the open "
                "upper part of the frame where the text goes; keep the subject and all busy detail along "
                "the BOTTOM of the frame.")
QUALITY = ("It is HYPERREALISTIC — completely indistinguishable from a GENUINE real photograph taken "
           "with a real camera — with real depth and a quiet sense of hope, grace and reverence "
           "(peaceful and true — never cute, kitschy, saccharine, twee or fantastical). "
           # 고요함, not brightness: the criterion is whether the frame is CALM. A dim lamp-lit room is
           # on brand; a gloomy or foreboding one is not. Understatement is required, because the verse
           # is the subject and a spectacular photograph steals the post.
           "The mood is QUIET and STILL. Natural light suited to THIS scene at whatever hour it "
           "belongs to — soft daylight, late dusk or faint light after dark are all welcome, and dim "
           "is fine — but it is never gloomy, ominous, oppressive, bleak, sorrowful or frightening. "
           "Colour is MUTED and gentle, slightly desaturated, low in contrast, with a soft filmic "
           "quality and a subtle grain — restrained, like a quiet film photograph, NOT vivid, "
           "saturated, glossy, dramatic or spectacular. Understated and simple: plenty of plain empty "
           "space, few elements, nothing showy. Natural photographic detail, real texture and "
           "true-to-life colour. It must look like an ACTUAL photograph a person took — absolutely NOT "
           "a glossy 3D render, CGI, a video-game frame, a digital painting, or a plasticky/artificial "
           "AI image. Real and quietly moving — an image that feels honest and calm.")
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
                        model=MODEL, aspect="3:4", var_t=None):
    """Generate one background → save to `dest`. Clean natural-language prompt (Gemini follows
    prose); the text area is kept clear per `placement`. `aspect` = "3:4" (feed) or "9:16" (reel)."""
    scene = SCENES[index % len(SCENES)]
    variation = scene_variation(index if var_t is None else var_t)
    compose = COMPOSE.get(tuple(placement), COMPOSE[("center", "middle")])
    prompt = f"A cinematic, genuine real photograph of {scene}, {variation}. {compose} {COMPOSE_SAFE} {EVENTONE} {QUALITY} {NOTEXT}"

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


def generate_checked(dest, index=0, placement=("center", "middle"), aspect="3:4", attempts=3, var_t=None):
    """Generate a background AND vision-check its composition; regenerate (up to `attempts`) if the
    checker flags a stacked/duplicated scene or a wrong reflection. Returns the last render either
    way (best-effort — never raises just because the checker was unhappy)."""
    for a in range(1, attempts + 1):
        generate_background(dest, index, placement, aspect=aspect, var_t=var_t)
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
