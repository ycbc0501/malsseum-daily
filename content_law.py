#!/usr/bin/env python3
"""The law of content making — ONE source, used by every prompt we send.

Why this file exists: the image prompt had four separate blocks (COMPOSE, COMPOSE_SAFE, EVENTONE,
QUALITY) saying overlapping things in different words, and they contradicted each other. COMPOSE
demanded "one single flat even tone, no texture" across the upper half while EVENTONE forbade "any
hard horizontal seam". A model resolving that contradiction paints a flat panel onto the photo and
butts it against the scene — which is exactly what shipped on 09-14 and 09-17. Meanwhile the VIDEO
prompt had never been given the same laws at all: no mention of hands, of CGI, of physics, or of
looking like a real photograph. So Veo walked people into frame and poured water sideways.

The rules live here, once. `fetch_higgsfield` (the still) and `fetch_veo` (the motion) both build
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
    "3. NATURE ONLY, obeying its own laws — only what occurs naturally and behaves as it really "
    "does, consistent with ordinary physics. Nothing invented, impossible or fantastical; nothing "
    "that could not simply be found and filmed.\n"
    "4. FILMED, NOT MADE — it must read as an unedited recording of a real place, never generated, "
    "composited or retouched. No CGI or digital-painting look, and nothing laid on top of the "
    "picture: no panel, band or backdrop, no straight edge cutting it into zones."
)

# Terms for the negativePrompt field, where the model supports one. Same laws, stated as things to
# exclude — a negative prompt is a different lever from an instruction and both are worth using.
# For the negativePrompt field. Kept short and non-overlapping: this used to be concatenated onto
# fetch_veo.NEG and the two listed "text, people, watermark, logo" twice over.
NEG_TERMS = (
    "text, letters, numbers, signage, watermark, logo, "
    "person, people, face, hands, limbs, silhouette, crowd, reflection of a person, "
    "3d render, cgi, digital painting, illustration, plastic, glossy, surreal, fantasy, "
    "collage, inset, border, panel, backdrop, flat colour band, hard seam, split screen, "
    "two horizons, mirrored, duplicated"
)


def for_image(scene, variation, framing):
    """The complete still prompt: what to photograph, how it is lit, how it is framed, and the law."""
    return (f"A genuine photograph, taken on a real camera in a real place: {scene}, {variation}.\n\n"
            f"{framing}\n\n{LAW}")


def for_video(motion, extra=""):
    """The complete motion prompt. The law applies to every frame of the clip, not just the first —
    the still passed every gate and then Veo introduced what the law forbids."""
    return (f"{motion}{extra}\n\n{LAW}\n"
            "These rules apply to EVERY FRAME. Nothing that breaks them may appear at any point "
            "during the clip, including anything that enters, grows or is revealed as it plays.")
