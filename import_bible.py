#!/usr/bin/env python3
"""
Import a full Bible text file into verses.json.

YOU provide the data — a translation you have the right to use (e.g. licensed 개역개정
from 대한성서공회). Save it as `bible_source.json` in this folder, then run this.

Supported input shapes (auto-detected):
  1) [{"book": "시편"|"Psalms"|"Ps", "chapter": 23, "verse": 1, "text": "..."}, ...]
  2) {"verses": [ ...same objects... ]}

It keeps only verses that read well as standalone cards:
  • a COMPLETE thought (drops ones ending mid-clause: 고/며/매/…)
  • short enough for the 2–3 line layout (≤ MAX_CHARS)
and writes them to verses.json as [{"ref": "시편 23:1", "text": "..."}].

    python3 import_bible.py            # import bible_source.json → verses.json
    python3 import_bible.py --append   # add to the existing curated verses instead of replacing
"""

import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_CHARS = 55                       # fits the fixed-size 2–3 line layout
INCOMPLETE = ("고", "며", "매", "이요", "으며", "하며")

# English / abbreviation → 개역개정 Korean book names (so any common dataset works)
EN2KO = {
    "genesis": "창세기", "gen": "창세기", "exodus": "출애굽기", "exo": "출애굽기",
    "leviticus": "레위기", "lev": "레위기", "numbers": "민수기", "num": "민수기",
    "deuteronomy": "신명기", "deu": "신명기", "joshua": "여호수아", "jos": "여호수아",
    "judges": "사사기", "jdg": "사사기", "ruth": "룻기", "rut": "룻기",
    "1 samuel": "사무엘상", "2 samuel": "사무엘하", "1 kings": "열왕기상", "2 kings": "열왕기하",
    "1 chronicles": "역대상", "2 chronicles": "역대하", "ezra": "에스라", "nehemiah": "느헤미야",
    "esther": "에스더", "job": "욥기", "psalms": "시편", "psalm": "시편", "psa": "시편",
    "proverbs": "잠언", "pro": "잠언", "ecclesiastes": "전도서", "ecc": "전도서",
    "song of solomon": "아가", "isaiah": "이사야", "isa": "이사야", "jeremiah": "예레미야",
    "jer": "예레미야", "lamentations": "예레미야애가", "ezekiel": "에스겔", "daniel": "다니엘",
    "hosea": "호세아", "joel": "요엘", "amos": "아모스", "obadiah": "오바댜", "jonah": "요나",
    "micah": "미가", "nahum": "나훔", "habakkuk": "하박국", "zephaniah": "스바냐",
    "haggai": "학개", "zechariah": "스가랴", "malachi": "말라기",
    "matthew": "마태복음", "mat": "마태복음", "mark": "마가복음", "mrk": "마가복음",
    "luke": "누가복음", "luk": "누가복음", "john": "요한복음", "jhn": "요한복음",
    "acts": "사도행전", "romans": "로마서", "rom": "로마서",
    "1 corinthians": "고린도전서", "2 corinthians": "고린도후서", "galatians": "갈라디아서",
    "ephesians": "에베소서", "philippians": "빌립보서", "colossians": "골로새서",
    "1 thessalonians": "데살로니가전서", "2 thessalonians": "데살로니가후서",
    "1 timothy": "디모데전서", "2 timothy": "디모데후서", "titus": "디도서", "philemon": "빌레몬서",
    "hebrews": "히브리서", "james": "야고보서", "1 peter": "베드로전서", "2 peter": "베드로후서",
    "1 john": "요한일서", "2 john": "요한이서", "3 john": "요한삼서", "jude": "유다서",
    "revelation": "요한계시록", "rev": "요한계시록",
}


def book_ko(book):
    b = str(book).strip()
    return EN2KO.get(b.lower(), b)   # already-Korean names pass through unchanged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--source", default="bible_source.json")
    args = ap.parse_args()

    src = os.path.join(HERE, args.source)
    if not os.path.exists(src):
        raise SystemExit(f"missing {args.source} — put your Bible data file here first.")
    raw = json.load(open(src, encoding="utf-8"))
    rows = raw.get("verses", raw) if isinstance(raw, dict) else raw

    out, seen = [], set()
    kept = dropped_incomplete = dropped_long = 0
    for r in rows:
        text = " ".join(str(r["text"]).split())
        ref = f"{book_ko(r['book'])} {r['chapter']}:{r['verse']}"
        if ref in seen:
            continue
        if text.rstrip().rstrip(".").endswith(INCOMPLETE):
            dropped_incomplete += 1
            continue
        if len(text) > MAX_CHARS:
            dropped_long += 1
            continue
        seen.add(ref)
        out.append({"ref": ref, "text": text})
        kept += 1

    vpath = os.path.join(HERE, "verses.json")
    if args.append and os.path.exists(vpath):
        existing = json.load(open(vpath, encoding="utf-8"))
        have = {v["ref"] for v in existing["verses"]}
        existing["verses"].extend(v for v in out if v["ref"] not in have)
        data = existing
    else:
        data = {"_comment": "Imported via import_bible.py. Verify text + license before scaling.",
                "translation": raw.get("translation", "개역개정") if isinstance(raw, dict) else "개역개정",
                "verses": out}

    json.dump(data, open(vpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"kept {kept}  (dropped: {dropped_incomplete} incomplete, {dropped_long} too long)")
    print(f"verses.json now has {len(data['verses'])} verses")


if __name__ == "__main__":
    main()
