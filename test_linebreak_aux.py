#!/usr/bin/env python3
"""A verb and its auxiliary are one predicate — never two lines.

    python3 test_linebreak_aux.py

하박국 2:4 shipped on 2026-09-21 broken as "…정직하지 / 못하나 …". That was not a near miss on
balance: "정직하지" ends in a connective ending (EC), so the scorer counted the break as a
PREFERRED clause end. It is the middle of a verb. Kiwi tags the auxiliary VX, which is the
signal — but only when the ending before it is one that actually takes an auxiliary, because
kiwi reads the 주 of "주는" (Lord) as the auxiliary 주다.
"""
import sys
from PIL import Image, ImageDraw

import generate

FAIL = []
D = ImageDraw.Draw(Image.new("RGB", (1080, 1350)))


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


def split_of(text, size=44, max_w=900):
    return generate.fit_verse(D, text, max_w=max_w, size=size)[1]


def joined_pairs(lines):
    """The word pair straddling each break."""
    return [(lines[i].split()[-1], lines[i + 1].split()[0]) for i in range(len(lines) - 1)]


print("auxiliary verbs stay whole")

CASES = [
    ("보라 그의 마음은 교만하며 그 속에서 정직하지 못하나 의인은 그의 믿음으로 말미암아 살리라",
     ("정직하지", "못하나")),
    ("내가 너희에게 말하기를 그들을 무서워하지 말라 두려워하지 말라", ("무서워하지", "말라")),
    ("내 손이 그와 함께 하여 견고하게 하고 내 팔이 그를 힘이 있게 하리로다", ("견고하게", "하고")),
    ("내가 평생토록 여호와께 노래하며 내가 살아 있는 동안 내 하나님을 찬양하리로다", ("살아", "있는")),
    ("여호와를 의지하는 자는 시온 산이 흔들리지 아니하고 영원히 있음 같도다", ("흔들리지", "아니하고")),
]
for text, pair in CASES:
    for size in (44, 35):
        got = joined_pairs(split_of(text, size))
        check(f"{pair[0]}│{pair[1]} not split at {size}px", pair not in got)

# The account owner's actual instruction: 하박국 2:4's first line must run through 못하나.
first = split_of("보라 그의 마음은 교만하며 그 속에서 정직하지 못하나 의인은 그의 믿음으로 말미암아 살리라")[0]
check("하박국 2:4 first line ends at 못하나", first.endswith("못하나"))

# A tagger mistake must not become a layout bug: kiwi calls the 주 of "주는" an auxiliary (VX),
# but "감사하리이다" is not an ending that takes one, so the break stays legal.
p = "주는 나의 하나님이시라 내가 주께 감사하리이다 주는 나의 하나님이시라 내가 주를 높이리이다"
check("시편 118:28 still fits two lines", len(split_of(p)) <= 2)

# The rule must not quietly cost line count across the corpus — that bill came due once already
# when the object particle was added and three-line verses went 3 → 7.
import json
rows = json.load(open("verses.json"))
rows = rows if isinstance(rows, list) else rows.get("verses", rows)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    three = sum(1 for x in rows if x.get("text") and len(split_of(x["text"])) > 2)
print(f"  ({len(rows)} verses, {three} need three lines)")
check("three-line verses stay at or below the shipped 3", three <= 3)


# ---- leftward-binding forms (2026-10-15) -------------------------------------
# Reported: 저는 다리로│하여금 (히브리서 12:13) and 이제는 주│안에서 (에베소서 5:8). Neither is a
# tagger signal — kiwi calls 하여금 an adverb and the 안 of "주 안에서" a common noun — so the rule
# has to be about what binds LEFT, the mirror of _FWD_NOUN.
for _text, _orphan in [
    ("너희 발을 위하여 곧은 길을 만들어 저는 다리로 하여금 어그러지지 않고 고침을 받게 하라", "하여금"),
    ("너희가 전에는 어둠이더니 이제는 주 안에서 빛이라 빛의 자녀들처럼 행하라", "안에서"),
    ("하나님이여 주의 인자하심이 어찌 그리 보배로우신지요 사람들이 주의 날개 그늘 아래에 피하나이다", "아래에"),
]:
    for _size in (44, 35):
        _lines = split_of(_text, _size)
        check(f"{_orphan} never starts a line at {_size}px",
              _orphan not in [l.split()[0] for l in _lines[1:]])

# A positional noun with nothing before it must still be allowed to open the verse.
check("a positional noun may open the verse",
      split_of("앞에 있는 것을 잡으려고 좇아가노라")[0].startswith("앞에"))

print(f"\n{len(FAIL)} failure(s)" if FAIL else "\nall good")
sys.exit(1 if FAIL else 0)

