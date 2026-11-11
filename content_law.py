#!/usr/bin/env python3
"""The law of content making — ONE source, used by every prompt we send.

Why this file exists: the image prompt had four separate blocks (COMPOSE, COMPOSE_SAFE, EVENTONE,
QUALITY) saying overlapping things in different words, and they contradicted each other. COMPOSE
demanded "one single flat even tone, no texture" across the upper half while EVENTONE forbade "any
hard horizontal seam". A model resolving that contradiction paints a flat panel onto the photo and
butts it against the scene — which is exactly what shipped on 09-14 and 09-17. Meanwhile the VIDEO
prompt had never been given the same laws at all: no mention of hands, of CGI, of physics, or of
looking like a real photograph. So Veo walked people into frame and poured water sideways.

The rules live here, once. `fetch_image` (the still) and `fetch_motion` (the motion) both build
their prompts from LAW, so a rule added here reaches both. The human-readable statement of the same
laws is RULES.md section A; check_rules.py asserts the two agree.
"""

# The absolute laws. Every prompt carries these verbatim, image and video alike.
LAW = (
    "ABSOLUTE RULES:\n"
    "1. NO WRITING anywhere in frame — no letters, numbers, signs, labels, watermarks or logos, "
    "however small or blurred, and nothing that is merely meant to carry writing.\n"
    "2. NO PEOPLE and no part of one — no face, body, silhouette, hand, limb or reflection of a "
    "person, at any distance, however blurred or cropped. An empty chair or empty shoes are right; "
    "the absence of people is the point.\n"
    "3. REAL THINGS ONLY, behaving as they really do — an ordinary place or object that exists in "
    "the world, obeying ordinary physics: gravity, light, motion, reflection, scale. Nothing "
    "invented, impossible or fantastical; nothing that could not simply be found and filmed.\n"
    "4. FILMED, NOT MADE — it must read as an unedited recording of a real place, never generated, "
    "composited or retouched. No CGI or digital-painting look, and nothing laid on top of the "
    "picture: no panel, band or backdrop, no straight edge cutting it into zones."
)

# Terms for the negativePrompt field, where the model supports one. Same laws, stated as things to
# exclude — a negative prompt is a different lever from an instruction and both are worth using.
# For the negativePrompt field. Kept short and non-overlapping: this used to be concatenated onto
# fetch_motion.NEG and the two listed "text, people, watermark, logo" twice over.
NEG_TERMS = (
    "text, letters, numbers, signage, watermark, logo, "
    "person, people, face, hands, limbs, silhouette, crowd, reflection of a person, "
    "3d render, cgi, digital painting, illustration, plastic, glossy, surreal, fantasy, "
    "collage, inset, border, panel, backdrop, flat colour band, hard seam, split screen, "
    "two horizons, mirrored, duplicated"
)


# 2026-11-11: when real reference photographs are available (fetch_image.STYLE_REF_DIR,
# populated by reference_study.py), they are now attached to the image-generation call directly
# instead of being reduced to a bucket count. The account owner's correction to that
# categorise-then-discard approach: "걔네 이미지를 제미나이에 통째로 넣어서 이런 룩앤필로
# 만들어달라하고 우리가 장소나 이런걸 지금처럼 단어들로 입력해주는게 좋을듯해." Real photographs
# steer grain, light and colour grade far more directly than describing them in words ever could —
# but the attached photos must not become the SUBJECT of the new picture: the scene is still named
# in words (`scene`, below), and this note tells the model which job each input has.
STYLE_REF_NOTE = (
    "The attached reference photographs are a LOOK AND FEEL guide only — match their colour "
    "grade, light quality, mood, grain and overall photographic character. Do NOT copy their "
    "subject, composition or layout: the actual scene for THIS photograph is the one described "
    "in words below."
)


def for_image(scene, variation, framing, style_ref=False):
    """The complete still prompt: what to photograph, how it is lit, how it is framed, and the law.
    `style_ref=True` only when reference photographs are actually attached alongside this text
    (see STYLE_REF_NOTE) — default False so a caller with nothing to attach gets the exact prompt
    this function always produced; style_ref never needs a special "no references" sentence."""
    look = variation.strip().rstrip(".")
    note = f"\n\n{STYLE_REF_NOTE}" if style_ref else ""
    return (f"A genuine photograph, taken on a real camera in a real place: {scene}, {look}.\n\n"
            f"{framing}{note}\n\n{LAW}")


def for_video(motion, extra=""):
    """The complete motion prompt. The law applies to every frame of the clip, not just the first —
    the still passed every gate and then Veo introduced what the law forbids."""
    return (f"{motion}{extra}\n\n{LAW}\n"
            "These rules apply to EVERY FRAME. Nothing that breaks them may appear at any point "
            "during the clip, including anything that enters, grows or is revealed as it plays.")
