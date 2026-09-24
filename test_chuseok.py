#!/usr/bin/env python3
"""Rule B-5b — the 명절 greeting is caption text only, date-gated, and sits under the 출처.

Run the pre-fix daily_post.py against this and cases 1, 3, 4 and 5 fail: there was no greeting
at all. Case 2 is the one that keeps the feature honest after the holiday — an unlisted date
must produce the exact bytes the caption always had.

    python3 test_chuseok.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("CAPTION_REFLECTION", None)   # the reflection line is measured in test_reflection

import daily_post

VERSE = {"text": "네가 먹어서 배부르고 네 하나님 여호와께서 옥토를 네게 주셨음으로 말미암아 그를 찬송하리라",
         "ref": "신명기 8:10"}
PLAIN = f"{VERSE['text']}\n[{VERSE['ref']}]"
HELLO = "풍성한 한가위 보내세요."


def main():
    fails = []

    # 1. 추석 당일 — the greeting is there, and the 말씀 is still first and topmost.
    cap = daily_post.build_caption(VERSE, "", today="2026-09-25")
    if not cap.startswith(PLAIN):
        fails.append("the greeting displaced the 말씀 from the top of the caption")
    if HELLO not in cap:
        fails.append("no greeting on 2026-09-25")

    # 2. Any other day — byte-identical to the caption this account has always sent. This is what
    #    makes the greeting expire by itself instead of lingering into March.
    for day in ("2026-01-01", "2026-03-01", "2026-09-23", "2026-09-27", "2027-09-25"):
        if daily_post.build_caption(VERSE, "", today=day) != PLAIN:
            fails.append(f"{day} is not in GREETINGS but changed the caption")
        if daily_post.greeting(day) is not None:
            fails.append(f"greeting({day}) is not None")

    # 3. The whole 연휴 window we decided to greet, and only that.
    want = {"2026-09-24", "2026-09-25", "2026-09-26"}
    if set(daily_post.GREETINGS) != want:
        fails.append(f"GREETINGS covers {sorted(daily_post.GREETINGS)}, expected {sorted(want)}")

    # 4. Position: under the 출처 but ABOVE the reflection line. Instagram folds the caption at
    #    ~125 chars and the 08-01 measurement put that cut just after the reference, so a greeting
    #    below a 60-char reflection ships folded away. Stub the line so this needs no network.
    import reflection
    real = reflection.line
    try:
        reflection.line = lambda v: "상은 차려졌고, 그 상을 낸 땅은 주신 것입니다."
        cap = daily_post.build_caption(VERSE, "", today="2026-09-25")
        # Report, don't raise: a missing greeting must read as a named failure, not a traceback
        # from .index(). The whole point of this file is to say WHAT broke.
        if HELLO not in cap:
            fails.append("no greeting once the reflection line is present")
        elif cap.index(HELLO) > cap.index("상은 차려졌고"):
            fails.append("the greeting sits BELOW the reflection line (it would be truncated)")
        if not cap.startswith(PLAIN):
            fails.append("the 말씀 is no longer first once the reflection line is present")
    finally:
        reflection.line = real

    # 5. Caption only. Not one prompt or render module may carry the string — LAW rule 1 forbids
    #    writing in frame, and this feature must not have quietly become an exception to it.
    here = os.path.dirname(os.path.abspath(__file__))
    for f in ("generate.py", "content_law.py", "fetch_veo.py", "fetch_higgsfield.py",
              "make_video.py", "carousel.py"):
        p = os.path.join(here, f)
        if os.path.exists(p) and any(g in open(p, encoding="utf-8").read()
                                     for g in set(daily_post.GREETINGS.values())):
            fails.append(f"a greeting string reached {f} — it must never enter the frame")

    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}  (test_chuseok)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
