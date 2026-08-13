#!/usr/bin/env python3
"""
The post's FIRST COMMENT — five hashtags fixed per theme, plus the one quiet line about
the account (`first_comment`). The caption itself carries only the reference and the verse.

Instagram capped posts and reels at **5 hashtags** in December 2025, and the cap counts
caption and comments together (the first-comment placement buys no extra slots), so five
is the account's entire budget. Over the cap Instagram strips the excess or refuses the
publish.

Hashtags no longer drive reach — Instagram's own position is that they label a topic
rather than distribute content — so the only job here is to say accurately what the post
is about. That makes this a lookup table and not an algorithm: one reviewable set per
theme, no counter, no rotation. Rotating them would add moving parts for no reader-visible
benefit, since nobody experiences hashtag sameness the way they experience a repeated
image or hymn (which is what the no-repeat ledgers in CONTENT_RULE §11 are actually for).

    python3 hashtags.py            # print the table
"""

MAX = 5                       # Instagram's hard cap (Dec 2025). Never raise this.

SETS = {
    "위로": "#오늘의말씀 #성경말씀 #위로 #위로의말씀 #쉼",
    "평안": "#오늘의말씀 #성경말씀 #평안 #평안의말씀 #기도",
    "담대": "#오늘의말씀 #성경말씀 #담대 #용기 #믿음생활",
    "믿음": "#오늘의말씀 #성경말씀 #믿음 #믿음생활 #신앙",
    "감사": "#오늘의말씀 #성경말씀 #감사 #감사일기 #감사의말씀",
    "사랑": "#오늘의말씀 #성경말씀 #사랑 #하나님의사랑 #은혜",
    "인도": "#오늘의말씀 #성경말씀 #인도하심 #순종 #기도",
    "은혜": "#오늘의말씀 #성경말씀 #은혜 #은혜의말씀 #신앙",
    "지혜": "#오늘의말씀 #성경말씀 #지혜 #잠언 #묵상",
}

# The cap is a hard external constraint, so the table is checked once at import rather
# than trusted: a set that grew a sixth tag would otherwise fail silently on Instagram.
for _theme, _set in SETS.items():
    _tags = _set.split()
    assert all(t.startswith("#") for t in _tags), _theme
    assert len(_tags) == len(set(_tags)) == MAX, f"{_theme}: {len(_tags)} tags, need {MAX}"


# Moved out of the caption 2026-08-01. Two reasons, one of them evidence:
#   · It was already invisible. Instagram truncates the caption at ~125 chars behind "더 보기", and on
#     a real post the cut landed right after the reference — so the CTA shipped folded away. Putting
#     it in the first comment is therefore closer to RETIRING it than relocating it, and that is the
#     honest description of this change.
#   · It contradicted the account. The constitution says the 말씀 leads and rule 10b says the DM asks
#     for nothing; selling in the caption was the one place that still did.
# Kept (rather than deleted) so the account still states what it is to anyone who does look, and so
# `follows` / `profile_visits` in metrics.json can show whether removing it cost anything.
FOLLOW_CTA = "매일 아침·저녁, 마음에 닿는 말씀을 전합니다 🕊"


def build(theme):
    """The five hashtags for a `theme` verse."""
    return SETS.get(theme) or SETS["믿음"]


def first_comment(theme):
    """Everything that goes in the post's first comment: the quiet line about the account,
    then the five tags. The caption itself carries ONLY the reference and the verse."""
    return f"{FOLLOW_CTA}\n\n{build(theme)}"


if __name__ == "__main__":
    for theme in SETS:
        print(f"{theme}  {build(theme)}")
    print("\n--- first comment ---")
    print(first_comment("감사"))
