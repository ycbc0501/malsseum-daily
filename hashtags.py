#!/usr/bin/env python3
"""
The post's hashtag set — FIVE tags, chosen for the verse's theme.

Instagram capped hashtags at **5 per post/reel** in December 2025, and the cap counts
caption and comments together: putting them in the first comment buys no extra slots.
Over the cap, Instagram strips the excess or refuses the publish. So five is the account's
entire hashtag budget and `build()` enforces it as a hard invariant.

Hashtags no longer drive reach — Instagram's own position is that they label topics rather
than distribute content. These five are therefore chosen to say accurately what the post is
about (this verse, this theme), not to fish. One anchor that never changes, two broad tags
and two theme tags that rotate on the post counter at coprime steps, so consecutive posts
never carry an identical set.

    python3 hashtags.py            # print a few posts' worth
"""

MAX = 5                       # Instagram's hard cap (Dec 2025). Never raise this.

ANCHOR = "#오늘의말씀"          # the one constant: what this account is

BROAD = ["#말씀", "#성경말씀", "#큐티", "#말씀묵상", "#말씀스타그램"]

THEME = {
    "위로": ["#위로", "#위로의말씀", "#쉼"],
    "평안": ["#평안", "#평안의말씀", "#기도"],
    "담대": ["#담대", "#용기", "#믿음생활"],
    "믿음": ["#믿음", "#믿음생활", "#신앙"],
    "감사": ["#감사", "#감사일기", "#감사의말씀"],
    "사랑": ["#사랑", "#하나님의사랑", "#은혜"],
    "인도": ["#인도하심", "#순종", "#기도"],
    "은혜": ["#은혜", "#은혜의말씀", "#신앙"],
    "지혜": ["#지혜", "#잠언", "#묵상"],
}


def build(theme, i):
    """The five tags for a `theme` verse on post `i` (the monotonic post counter).

    Steps are coprime with the list lengths so the set keeps moving instead of settling
    into a repeat: broad tags step 1 and 2 through a list of 5, theme tags 1 and 2
    through a list of 3."""
    broad = [BROAD[i % len(BROAD)], BROAD[(i + 2) % len(BROAD)]]
    tt = THEME.get(theme) or THEME["믿음"]
    theme_tags = [tt[i % len(tt)], tt[(i + 1) % len(tt)]]
    tags = []
    for t in [ANCHOR] + broad + theme_tags:      # dedupe, keep order
        if t not in tags:
            tags.append(t)
    return " ".join(tags[:MAX])                  # the cap is not negotiable


if __name__ == "__main__":
    for theme in THEME:
        print(f"{theme:4s}  " + "\n      ".join(build(theme, i) for i in range(3)))
