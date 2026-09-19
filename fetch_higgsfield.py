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


class MissingCredential(RuntimeError):
    """A key or secret is not configured.

    A LIBRARY function must never raise SystemExit. Callers wrap these in
    `except Exception` and document themselves as best-effort — check_composition says
    "on ANY error returns (True, ...)" — but SystemExit is not an Exception, so a missing
    key sailed straight through the handler and killed the post. Same shape as the story
    error that failed a run after the feed post had already published (2026-09-10).
    SystemExit belongs in main(), nowhere else."""

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
        "a plain wooden desk beside a window, a single cup left on it",
        "a bare writing desk with nothing on it, a chair pushed in",
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
    # ── everyday & intimate (expanded 2026-09-06) ──
    # The pool was 36 themes / 72 sentences, so the SAME scene description came back every 36 days
    # while the verse pool now lasts a year. @dailymayim (34k followers, bio "일상에 흐르는 하나님
    # 말씀") is built on ordinary objects — a dessert on a table at night, a window, a cup — not on
    # landscapes, and that is the half we were thinnest in. Rule 3's 고요함 still governs: quiet,
    # muted, everyday, never grand.
    "tea_cup": [
        "a plain cup of tea on a bare table, steam rising slowly",
        "a single mug left on a wooden table, the drink still warm",
    ],
    "bread_table": [
        "a small loaf of bread on a plain board, nothing else on the table",
        "a simple plate with a piece of bread, left on a bare table",
    ],
    "morning_table": [
        "a bare breakfast table by a window, one plate set and untouched",
        "an empty kitchen table with a single bowl, early light across it",
    ],
    "folded_laundry": [
        "a neat stack of folded white linen on a plain surface",
        "clean folded cloth resting on the corner of a quiet table",
    ],
    "doorway": [
        "a simple open doorway with a still room beyond it",
        "a plain door standing ajar, the room past it quiet and bare",
    ],
    # A clock face is numerals, and numerals come out mangled. Dropped for a candle, which is the
    # same quiet mark of passing time with nothing to misprint.
    "candle_still": [
        "a single unlit candle standing on a bare surface, the wall behind it plain",
        "one short candle resting on a quiet shelf, nothing else around it",
    ],
    "coat_hook": [
        "a single coat hanging on a hook against a plain wall",
        "one scarf left on a hook, the wall beside it bare",
    ],
    "key_bowl": [
        "a small dish holding a set of keys on a bare surface",
        "a shallow bowl with a few coins, left on a quiet table",
    ],
    # No paper of any kind, in any state. Paper is the surface the model writes on.
    "small_dish": [
        "a small empty ceramic dish resting on a bare table",
        "one shallow plain bowl left on a quiet wooden surface",
    ],
    "sparrow": [
        "a small sparrow resting on a bare branch, perfectly still",
        "one small bird sitting quietly on a plain railing",
    ],
    "cat_window": [
        "a cat curled asleep on a windowsill, the room quiet",
        "a small animal resting still beside a plain window",
    ],
    "stone_path": [
        "a narrow stone path running between low quiet grass",
        "a simple worn footpath leading gently away",
    ],
    "wooden_bench": [
        "an empty wooden bench standing alone in a quiet place",
        "a plain bench with no one on it, the ground bare around it",
    ],
    "hanging_lamp": [
        "a single pendant lamp hanging low over an empty table",
        "one bare bulb glowing softly above a quiet room",
    ],
    "potted_plant": [
        "a small potted plant on a plain sill, its leaves still",
        "one modest green plant standing alone on a bare surface",
    ],
    "wool_blanket": [
        "a folded wool blanket draped over the arm of a quiet chair",
        "a soft throw left neatly over the back of a plain seat",
    ],
    "bowl_of_fruit": [
        "a few pieces of fruit resting in a plain bowl on a bare table",
        "a single apple left on a wooden surface, nothing else near",
    ],
    "washed_dishes": [
        "clean dishes stacked to dry beside a quiet sink",
        "a single washed bowl resting on a plain draining board",
    ],
    "sewing": [
        "a spool of thread and a folded cloth on a quiet table",
        "simple needlework left resting on a bare surface",
    ],
    "shoes_by_door": [
        "a pair of plain shoes set neatly beside a quiet doorway",
        "one pair of worn shoes resting on a bare floor",
    ],
    "umbrella_stand": [
        "a single closed umbrella leaning in a quiet entryway",
        "one folded umbrella resting against a plain wall",
    ],
    # Paper of any kind — sheets, notebooks, books — is dropped entirely. Even blank or closed it
    # is the surface the model most wants to write on, and a book adds nothing a cloth or a cup
    # does not already say.
    "linen_cloth": [
        "a plain folded cloth resting on a quiet table, nothing else near it",
        "a soft square of linen left on a bare wooden surface",
    ],
    "water_glass": [
        "a single glass of water standing on a plain table",
        "one clear glass left on a quiet wooden surface",
    ],
    "basket": [
        "a simple woven basket resting empty on a bare floor",
        "one plain basket set quietly in the corner of a room",
    ],

    # ── quiet outdoors, everyday scale (not monumental) ──
    "garden_gate": [
        "a low wooden gate standing open onto a quiet garden",
        "a simple gate at the end of a plain path",
    ],
    "clothesline": [
        "white cloth hanging still on a line in quiet air",
        "plain laundry drying motionless on a simple line",
    ],
    "picket_fence": [
        "a low fence running along a quiet grass verge",
        "a plain wooden fence with still fields beyond it",
    ],
    "well": [
        "an old stone well standing quietly in an open space",
        "a simple water well with nothing moving around it",
    ],
    "stepping_stones": [
        "flat stepping stones crossing very shallow still water",
        "a few stones set across a quiet, barely moving stream",
    ],
    "hedgerow": [
        "a low green hedge running beside a quiet lane",
        "a simple hedgerow with an empty path along it",
    ],
    "orchard": [
        "a few fruit trees standing quietly in an open orchard",
        "an orchard row with still grass beneath the trees",
    ],
    "haystack": [
        "a single round bale resting in a quiet cut field",
        "one haystack standing alone in an open meadow",
    ],
    "boat_moored": [
        "a small wooden boat moored still at a quiet bank",
        "one rowing boat resting motionless against a low jetty",
    ],
    "bridge_small": [
        "a small stone footbridge over very still water",
        "a simple wooden bridge crossing a quiet narrow stream",
    ],
    "still_water": [
        "a wide expanse of perfectly flat water meeting a low horizon",
        "shallow still water reaching away toward a distant shoreline",
    ],
}

# Round-robin interleave: one scene from each theme per pass, so SCENES[i], SCENES[i+1]… cycle
# through DIFFERENT themes. SCENE_CATS[i] is the theme of SCENES[i] (used by the no-repeat ledger).
# Walking SCENE_GROUPS in dict order put every interior together, because the 30 everyday scenes
# were appended as one block: the sequence held FOURTEEN interiors in a row, which is a week of
# nothing but rooms. The account owner saw it immediately — "다 무슨 방에서 우울한 벽만".
#
# So the order is woven instead of listed: OUTDOOR_PER_INDOOR outdoor scenes between every indoor
# one. That fixes the run length and the balance in the same place. The reference account this
# aesthetic came from is mostly sky, water and weather with the everyday as accent, and the pool
# had drifted to 40% interiors.
# Scene families that happen INDOORS. They need different composition language: an interior has
# no sky and no horizon, and asking for "a clear cloudless sky" in the upper half of a bedroom is
# a contradiction the image model resolves by GRAFTING AN OUTDOOR SKY ABOVE THE ROOM — a
# physically impossible composite (published 2026-08-2x, 에베소서 2:8). The instruction caused the
# defect; the gate could not catch it because every clause there was written for landscapes.
# cafe_table is deliberately NOT here — a terrace and a garden lawn are OUTDOORS, and telling
# them "there is no sky" would break the one thing that scene needs.
INTERIOR_CATS = {
    "window_light", "bedroom", "lamp_room", "desk",
    # Added with the 2026-09-06 everyday expansion. Every one of these sits INSIDE a room, so the
    # same trap applies: tell a tea cup on a table that the upper half should be "a clear cloudless
    # sky" and the model puts a sky above the kitchen. Adding scenes without adding them here is
    # how the 에베소서 2:8 composite happened in the first place.
    "tea_cup", "bread_table", "morning_table", "folded_laundry",
    "doorway", "candle_still", "coat_hook", "key_bowl", "small_dish", "cat_window",
    "hanging_lamp",
    "potted_plant", "wool_blanket", "bowl_of_fruit", "washed_dishes", "sewing", "shoes_by_door",
    "umbrella_stand", "linen_cloth", "water_glass",
    "basket",
}

def _weave():
    """Spread the indoor scenes evenly through the outdoor ones, whatever the counts.

    A fixed ratio does not work: with 90 outdoor and 60 indoor a 3:1 weave exhausts the outdoor
    queue and leaves thirty rooms piled at the end. Placing each indoor scene at its proportional
    position keeps them apart no matter how the pool changes.
    """
    rounds = {c: list(v) for c, v in SCENE_GROUPS.items()}
    out_q, in_q = [], []
    for _r in range(max(len(v) for v in rounds.values())):
        for cat, items in rounds.items():
            if _r < len(items):
                (in_q if cat in INTERIOR_CATS else out_q).append((items[_r], cat))
    total = len(out_q) + len(in_q)
    # Fractional positions the indoor scenes should land on, evenly spaced across the whole run.
    slots = {round((i + 0.5) * total / len(in_q)) for i in range(len(in_q))} if in_q else set()
    scenes, cats = [], []
    oi = ii = 0
    for pos in range(total):
        take_in = pos in slots and ii < len(in_q)
        if not take_in and oi >= len(out_q):
            take_in = ii < len(in_q)
        q, i = (in_q, ii) if take_in else (out_q, oi)
        if i >= len(q):
            continue
        scenes.append(q[i][0]); cats.append(q[i][1])
        if take_in:
            ii += 1
        else:
            oi += 1
    return scenes, cats


SCENES, SCENE_CATS = _weave()

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
# Indoors uses only LIGHT[:INDOOR_LIGHT_CUTOFF] — the daylight half. See scene_variation().
INDOOR_LIGHT_CUTOFF = 5

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


def scene_variation(t, indoors=False):
    """A rotating light + vantage phrase, so the same scene looks different each time it recurs.

    Indoors the darkest entries are skipped. Dark is on brand — the account owner confirmed that
    outright — but dark means EVENING outdoors and ABANDONED in an empty room, and a run of dim
    bare walls is what they saw and called 우울한. Sunset and after-dark stay for scenes that have
    a sky; a room gets the daylight half of the palette and reads as quiet rather than forsaken.
    """
    light_pool = LIGHT[:INDOOR_LIGHT_CUTOFF] if indoors else LIGHT
    light = light_pool[t % len(light_pool)]
    vi = (t // len(light_pool)) % len(VANTAGE)
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

# What the empty upper half IS, per scene type — substituted into COMPOSE.
EMPTY_AREA = {
    False: "open sky",
    True: "a tall expanse of the room's own wall",
}
# Only an outdoor frame has a horizon. Saying "one horizon only" to an interior contradicts the
# same sentence's "there is NO horizon" — the interior prompt was carrying both.
# What the open expanse must look like, in a photographer's terms. It has to be decisively light
# or decisively dark for the verse to separate from it — but that is about the LIGHT, never about
# flattening the surface, which is the distinction the old wording lost.
TONE = {
    False: "an overcast sky that reads as one soft luminous field, or a clear sky at dusk gone "
           "deep and dark — bright or dark, never a middling grey, and always real sky with its "
           "own cloud and gradation. ",
    True: "the wall evenly lit and either pale and bright or deep in shadow — never a middling "
          "grey — with its own plaster texture, marks and falloff. This is an interior: no sky, "
          "no horizon, nothing outdoors above the room. ",
}

ANCHOR = {
    # Named objects used to be listed here — furniture, flowers, rooftops — and they were sent with
    # EVERY scene, so an open seascape was being told to put furniture along its bottom edge. Say
    # where things go, never what things are; the scene sentence is the only place that decides.
    False: "the horizon sits low and whatever the scene contains rests along the bottom edge",
    True: "whatever the room contains rests along the bottom edge, with the bare wall of that same "
          "room rising behind it",
}


# No zones, and no template shared between a field and a kitchen. The old text described an upper
# half that holds the verse and a lower part that holds the scene — which IS a two-zone
# composition, and the law then had to forbid the band that description produces. These are the
# words a photographer would use about the shot itself. Whether the result can carry the verse is
# decided by MEASURING it (generate.text_area_ok) and regenerating, never by asking for a space.
OUTDOOR_TOP = (
    "COMPOSITION: a wide, unhurried frame with the horizon LOW, roughly a third of the way up, so "
    "that open sky fills most of the picture above it — the sky is the subject. Everything with "
    "detail or texture sits along the bottom and nothing rises into the sky. The light must be "
    "decisive: either an overcast sky reading as one soft luminous field, or a clear sky at dusk "
    "gone deep and dark. Never a middling grey, and always real sky with its own cloud and "
    "gradation. Simple and unhurried, with a lot of quiet space."
)
INDOOR_TOP = (
    "COMPOSITION: photographed straight on from low down, so a tall expanse of the room's own wall "
    "rises above the subject and fills most of the frame. Whatever the room contains rests along "
    "the bottom. The wall is evenly lit and decisively pale or deep in shadow — never a middling "
    "grey — keeping its own plaster texture, marks and falloff. This is an interior: no sky, no "
    "horizon, nothing outdoors above the room. Simple and unhurried, with a lot of quiet space."
)

COMPOSE = {
    ("center", "top"): None,          # chosen per scene in generate_background
    ("center", "middle"):
        "COMPOSITION: a simple, open frame with the subject low or to one side and a wide, calm "
        "expanse through the middle. Quiet and restrained, with plenty of space.",
    ("left", "middle"):
        "COMPOSITION: the subject sits low and to the right; the left and centre of the frame open "
        "out quietly. Simple and restrained.",
    ("right", "middle"):
        "COMPOSITION: the subject sits low and to the left; the right and centre of the frame open "
        "out quietly. Simple and restrained.",
}
QUALITY = (
    "The mood is QUIET and STILL, with a sense of hope and reverence — peaceful and true, never "
    "cute, kitschy or saccharine. Natural light belonging to THIS scene at whatever hour it is: "
    "soft daylight, late dusk or faint light after dark are all welcome and dim is fine, but never "
    "gloomy, ominous, oppressive, bleak or sorrowful. Colour is MUTED and gentle, slightly "
    "desaturated, low in contrast, with a soft filmic quality and subtle grain — restrained, like a "
    "quiet film photograph, not vivid, glossy or dramatic. Understated and simple: "
    "few elements, nothing showy. Shot on a full-frame camera with a normal prime "
    "lens — natural depth of field with the far distance falling gently out of focus, believable "
    "lens character, and the slight imperfection of a real photograph. Detail is UNEVEN and organic "
    "the way nature actually is: grass and foliage vary in height, colour and density, never a "
    "uniform repeating carpet, with no airbrushed smoothness and no halo around edges."
)


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
        raise MissingCredential("Missing HF_API_KEY / HF_API_SECRET")
    return f"{key}:{sec}"


def generate_background(dest, index=0, placement=("center", "middle"), full_scene=False,
                        model=MODEL, aspect="3:4", var_t=None):
    """Generate one background → save to `dest`. Clean natural-language prompt (Gemini follows
    prose); the text area is kept clear per `placement`. `aspect` = "3:4" (feed) or "9:16" (reel)."""
    scene = SCENES[index % len(SCENES)]
    indoors = SCENE_CATS[index % len(SCENES)] in INTERIOR_CATS
    variation = scene_variation(index if var_t is None else var_t, indoors=indoors)
    compose = COMPOSE.get(tuple(placement), COMPOSE[("center", "middle")])
    # An interior has no sky and no horizon. Filling the same landscape wording for a bedroom is
    # what produced the room-with-a-sky-above composite, so the empty area and the anchor are
    # chosen by scene family, not assumed.
    indoors = SCENE_CATS[index % len(SCENES)] in INTERIOR_CATS
    if tuple(placement) == ("center", "top"):
        compose = INDOOR_TOP if indoors else OUTDOOR_TOP
    # Built from content_law, which is the ONE place the prohibitions live. Four separate blocks
    # used to repeat them in different words and contradict each other — COMPOSE demanded a flat
    # even tone across the upper half while EVENTONE forbade any hard seam, and the model resolved
    # that by painting a panel onto the photograph (RULES.md A).
    import content_law
    prompt = content_law.for_image(scene, f"{variation}. {QUALITY}", compose)

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
    "4) FAKE / CGI: the image looks like a glossy 3D/CGI render, a video-game frame, a digital "
    "painting or a plasticky artificial AI image — including fake, over-perfect ornate man-made objects "
    "— rather than a real photograph. Judge this by the usual AI tells: over-saturated or candy-like "
    "colour, an unnatural glow or halo, airbrushed plastic smoothness, uniformly repeating grass or "
    "foliage texture, everything equally sharp from front to back with no real depth of field, or "
    "light that comes from nowhere. Be STRICTEST on plain, simple scenes — an open field, a bare "
    "hillside, a plain sky have no detail to hide behind, so if such a scene looks even somewhat "
    "artificial or 'rendered' rather than photographed, flag it. Do not flag a real photo merely for "
    "moody or dim light.\n"
    "5) Obviously impossible, duplicated, melted or badly warped major structures.\n"
    "6) IMPOSSIBLE INDOOR/OUTDOOR COMPOSITE: the lower part is clearly an INTERIOR (a room, "
    "furniture, a bed, a desk, a table, a floor) while the upper part is an OUTDOOR sky, clouds, "
    "landscape or open air that could not physically be there — i.e. open sky sitting directly "
    "above a room with no ceiling, wall or window to justify it. A window or open door showing a "
    "view is CORRECT and must not be flagged; what is wrong is outdoors appearing where the room's "
    "own wall or ceiling should be.\n"
    "7) A LINE CUTS THE FRAME IN TWO. A straight, level line runs the full width of the picture "
    "and the area above it differs in tone, colour or brightness from the area below, so the eye "
    "reads two stacked rectangles instead of one photograph. REJECT IT EVEN IF THE LINE COULD BE "
    "SOMETHING REAL — a painted dado or picture rail, a change of wall colour, the edge of a "
    "shadow, a field boundary. Plausibility is not the test; whether the frame looks halved is. "
    "It applies whether or not the upper area has texture: a dark even band above a lit wall is as "
    "wrong as a blank panel. ONLY TWO EXCEPTIONS: a true horizon where sky meets land or water, "
    "and the line where a wall meets a floor. Everything else that rules a line across the frame "
    "is rejected.\n"
    "8) ANY PERSON: a face, a body, a silhouette, a hand, an arm, a leg, or a person reflected in "
    "glass or water — anywhere in the frame, at any distance, however blurred, cropped or turned "
    "away. AI-made faces and hands look wrong and break the stillness the post depends on. An "
    "empty chair, an empty bench or empty shoes are CORRECT — the absence of people is the point; "
    "what is wrong is a person being in the picture at all.\n"
    "9) ANY WRITING: letters, words, numbers, handwriting, print on a page, a shop sign, a label, "
    "a book spine, a clock face, a watermark or a logo — ANYWHERE in the frame, however small, "
    "blurred or partial. Image models render writing as broken nonsense, and one line of garbled "
    "text tells a viewer instantly that nobody made this. Reject even if it is tiny or out of "
    "focus. Reject a page or a sign that is clearly MEANT to carry writing even when the marks are "
    "illegible smudges.\n"
    "Do NOT flag: a normal single-horizon landscape/seascape, artistic blur, bokeh, mist, grain, dark "
    "or moody light, or a CORRECT (properly inverted) reflection.\n"
    "Reply ONLY as JSON: {\"ok\": true, \"reason\": \"\"} if it looks physically plausible, or "
    "{\"ok\": false, \"reason\": \"<short reason>\"} if any flaw above is present.")


# Counts how often the gate actually reached the model, so a run where every check quietly failed
# is a number rather than a line in a log nobody reads. Reset by generate_checked per render.
GATE_RAN = [0, 0]      # [ran, skipped]


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
        GATE_RAN[0] += 1
        return bool(j.get("ok", True)), str(j.get("reason", ""))[:200]
    except Exception as e:
        GATE_RAN[1] += 1
        return True, f"check skipped ({e})"


SEAM_JUMP = 7.0      # brightness levels (0-255) between two adjacent rows
SEAM_RATIO = 30.0    # …and that many times the image's own typical row-to-row change


def seam_score(image_path):
    """(jump, ratio, y) for the worst horizontal edge in the image — a MEASUREMENT, not a question.

    Nano Banana sometimes returns a stacked composite: a dark wall filling the top two thirds
    and a lit scene pasted below it, joined by a hard line running the full width. The vision
    checker is supposed to catch exactly this ("stacked double scene" is in its own prompt) and
    on 2026-09-14 it looked at one and answered `ok=True` with no reason given. The reel shipped,
    and it is one of the ten Instagram flagged.

    This is the motion-gate lesson again: a model asked "does this look wrong?" will say no, while
    a number does not get to have an opinion. A real photograph's brightness drifts row to row;
    a paste has one row where it jumps. The 09-14 render jumped 16.5 levels at 67% height against
    a median row-to-row change of 0.05 — 356×. A clean render from the same week: 4.5 and 10×.

    Both thresholds must trip: the ratio alone fires on very flat images where the median is
    near zero, and the jump alone fires on high-contrast scenes where a bright window edge is
    the subject rather than a defect. The top and bottom 5% are ignored (frame edges) and so is
    the band the verse sits in — white text on a dark wall IS a brightness cliff."""
    from PIL import Image
    import statistics
    im = Image.open(image_path).convert("L")
    w, h = im.size
    rows = [statistics.mean(im.crop((0, y, w, y + 1)).getdata()) for y in range(h)]
    deltas = [(abs(rows[y + 1] - rows[y]), y) for y in range(int(0.05 * h), int(0.95 * h) - 1)
              if not (0.18 * h < y < 0.45 * h)]
    if not deltas:
        return 0.0, 0.0, 0
    median = statistics.median(d for d, _ in deltas) or 0.001
    jump, y = max(deltas)
    return jump, jump / median, y


def has_seam(image_path):
    """True if the render looks pasted together. Never raises — a gate that cannot run must not
    be able to stop a post (rule 0-3)."""
    try:
        jump, ratio, y = seam_score(image_path)
    except Exception as e:
        print(f"seam check skipped ({e})")
        return False
    bad = jump >= SEAM_JUMP and ratio >= SEAM_RATIO
    print(f"seam: jump {jump:.1f} (limit {SEAM_JUMP}), {ratio:.0f}x typical "
          f"(limit {SEAM_RATIO}x) at {y}px → {'STACKED' if bad else 'ok'}")
    return bad


def generate_checked(dest, index=0, placement=("center", "middle"), aspect="3:4", attempts=3,
                     var_t=None, deadline_s=None):
    """Generate until the gate PASSES. Returns (path, index_used, passed).

    This used to try three times and return the third render whether it passed or not, so a frame
    the gate had rejected could still be published — and one was: a picture split into two tonal
    zones by a ruled line shipped on 09-14 and 09-17. The bar is now that what goes out has
    passed, so the loop keeps going until it does or the clock stops it. At roughly 35 seconds a
    render a ten-minute budget is around fifteen attempts, and the measured first-attempt
    rejection rate is about one in five, so running out is a remote case rather than the norm.

    Each retry also moves to the NEXT scene: a café terrace puts a shop sign in frame every time,
    and redrawing the same prompt just fails the same way. The scene that actually shipped is
    reported back so the ledger records what was published, not what was requested.
    """
    import time as _t
    started = _t.monotonic()
    budget = deadline_s if deadline_s is not None else attempts * 120
    used = index
    for a in range(1, 200):
        used = (index + a - 1) % len(SCENES)
        generate_background(dest, used, placement, aspect=aspect,
                            var_t=(var_t if var_t is None else var_t + a - 1))
        ok, reason = check_composition(dest)
        # The measurement runs even when the model said yes — on 09-14 it said yes to a stacked
        # composite. Two independent gates, and the cheap deterministic one is not the junior.
        if ok and has_seam(dest):
            ok, reason = False, "stacked composite (measured)"
        print(f"composition check {a} (scene {used} {SCENE_CATS[used]}): ok={ok} :: {reason}")
        if ok:
            return dest, used, True
        if _t.monotonic() - started > budget:
            print(f"WARNING: no render passed the gate within {budget:.0f}s after {a} attempts — "
                  f"publishing the last one, which the gate REJECTED")
            return dest, used, False
    return dest, used, False

def _gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    kf = os.path.join(HERE, "gemini_key.txt")
    if not key and os.path.exists(kf):
        for line in open(kf):
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise MissingCredential("Missing GEMINI_API_KEY")
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
