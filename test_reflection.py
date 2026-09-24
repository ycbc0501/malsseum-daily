#!/usr/bin/env python3
"""
The caption line must be OFF until rule B-5 is changed, and when it is on it must never be
able to put a sermon — or a sales pitch — under the 말씀.

    python3 test_reflection.py
"""

import os
import sys

import reflection

# (line the model produced, should it publish?)
CASES = [
    ("좋다.", False),                                     # too short to be a thought
    ("오늘도 힘내세요.", False),                            # imperative — "하세요" list missed this
    ("이 말씀을 붙들고 오늘을 삽시다.", False),               # propositive hidden inside 삽
    ("우리 함께 걸어가자.", False),                         # plain propositive
    ("함께 나누어 보세요.", False),
    ("정말 놀랍지 않나요?", False),                         # question
    ("오늘 하루도 평안하시길!", False),                      # exclamation
    ("좋아요와 공유 부탁드립니다.", False),                   # sells
    ("지금 팔로우 하고 매일 받아보시길.", False),
    ("#오늘의말씀 과 함께합니다.", False),                    # hashtag
    ("x" * 80, False),                                    # over MAX_CHARS
    ("두려움이 사라져서가 아니라, 먼저 가시는 분이 계셔서 건너갑니다.", True),
    ("하나 됨은 만드는 것이 아니라, 이미 주신 것을 지키는 일입니다.", True),
    ("무엇을 생각하며 하루를 보내는지가, 그 하루가 어디로 가는지를 정합니다.", True),
    ("나의 만족은 소유가 아니라 소속에 달려 있습니다.", True),   # real output, 2026-09-14
]


def main():
    fails = []

    for raw, want in CASES:
        got = reflection._clean(raw) is not None
        if got != want:
            fails.append(f"_clean({raw[:30]!r}) → {'accept' if got else 'reject'}, "
                         f"expected {'accept' if want else 'reject'}")

    # The switch is off unless explicitly set. This is the whole safety story: rule B-5 belongs
    # to the account owner, so the default must produce today's caption byte for byte.
    for value, want in (("", False), ("0", False), ("no", False),
                        ("1", True), ("true", True), ("on", True)):
        os.environ["CAPTION_REFLECTION"] = value
        if reflection.enabled() != want:
            fails.append(f"enabled() with CAPTION_REFLECTION={value!r} → {not want}")
    os.environ.pop("CAPTION_REFLECTION", None)

    # Off → line() must not even try to reach the network.
    if reflection.line({"text": "…", "ref": "시편 1:1"}) is not None:
        fails.append("line() returned something while disabled")

    # And the caption itself is unchanged.
    import daily_post
    verse = {"text": "여호와는 나의 목자시니 내게 부족함이 없으리로다", "ref": "시편 23:1"}
    # An ordinary day — a date with no 명절 greeting (rule B-5b), so this still measures the one
    # thing it is here for: the reflection flag off means the caption is the verse and nothing else.
    if daily_post.build_caption(verse, "", today="2026-01-01") != f"{verse['text']}\n[{verse['ref']}]":
        fails.append("build_caption() is not byte-identical with the flag off")

    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{len(CASES) + 7 - len(fails)}/{len(CASES) + 7} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
