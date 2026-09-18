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
    "ABSOLUTE RULES, no exceptions:\n"
    "1. NO WRITING of any kind. No letters, words, numbers, handwriting, print, signs, labels, "
    "book spines, clock faces, watermarks or logos, anywhere in the frame, however small or "
    "blurred. Nothing that is merely MEANT to carry writing either.\n"
    "2. NO PEOPLE, and no PART of a person. No face, body, silhouette, hand, arm, leg, foot, or a "
    "person reflected in glass or water. Not at a distance, not out of focus, not turned away, not "
    "cropped at the edge. Nobody. An empty chair, an empty bench or a pair of shoes with no one in "
    "them is correct — the absence of people is the point.\n"
    "3. ONLY WHAT CAN REALLY HAPPEN. Everything in the frame must be an ordinary object or a "
    "phenomenon that genuinely occurs in the physical world, behaving as it really behaves. No "
    "fantasy, no science fiction, no surreal or dreamlike inventions, no impossible structures, no "
    "objects that could not exist. Water falls downward and stays inside what contains it. "
    "Reflections are correct. Light comes from somewhere. Scale and proportion are true.\n"
    "4. IT MUST LOOK FILMED, NOT MADE. Someone seeing this must think a person went to a real "
    "place with a real camera and recorded what was there. They must never think it was generated, "
    "composited or edited. No glossy 3D or CGI look, no digital painting, no plastic surfaces, no "
    "artificial gloss, no impossibly perfect symmetry, no pasted-on panel, band or backdrop, and "
    "no hard straight seam dividing the picture into zones. One continuous photograph, throughout."
)

# Terms for the negativePrompt field, where the model supports one. Same laws, stated as things to
# exclude — a negative prompt is a different lever from an instruction and both are worth using.
NEG_TERMS = (
    "text, letters, words, numbers, handwriting, captions, subtitles, signage, labels, watermark, "
    "logo, "
    "person, people, man, woman, child, face, hands, arms, legs, feet, silhouette, crowd, figure, "
    "reflection of a person, "
    "3d render, cgi, video game, digital painting, illustration, plastic, glossy, artificial, "
    "surreal, fantasy, sci-fi, dreamlike, impossible architecture, floating objects, "
    "collage, photo within a photo, inset, border, panel, backdrop, flat colour band, "
    "hard horizontal seam, split screen, two horizons, mirrored, duplicated"
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
