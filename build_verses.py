#!/usr/bin/env python3
"""Rebuild verses.json from the full 개역개정 text — VERBATIM, no edits.

Why this exists: the pool was 98 hand-written verses, and at two posts a day it wrapped every
49 days, so captions repeated word-for-word every seven weeks. On 2026-09-06 Instagram flagged
ten of those repeats as 퍼온 콘텐츠 (duplicated content) and put an account-level reach
restriction on the account — reach fell from ~350 views to ~50 and did not recover.

An audit against the full text also found 27 of the 98 were NOT verbatim 개역개정: words swapped
(잠언 19:21 "굳게" for "완전히"), clauses deleted mid-sentence (시편 34:18 dropped "충심으로"),
and grammar rewritten (예레미야 29:11). For a Bible account that is the worst possible defect, so
this builder never edits, trims or joins: a verse is taken exactly as printed or not at all.

Selection is therefore about CHOOSING, not writing:
  · length that fits the reel overlay at 2-3 lines
  · a complete sentence — the ending test daily_post.py already applies
  · reads standalone, so no dangling connectives and no narrative/genealogy fragments
  · carries one of the nine weekly themes, scored by lexicon
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "data_krv_full.json")

# Same test daily_post.py uses at post time — a verse ending in a connective is half a sentence.
INCOMPLETE_ENDINGS = ("고", "며", "매", "이요", "으며", "하며", "니", "여", "은", "는", "을", "를",
                      "과", "와", "의", "에", "로", "하고", "되고", "지라", "하니", "이며")

# The overlay is sized for the current pool (median 33 chars, max 55). Longer verses are dropped
# rather than trimmed — trimming is exactly what produced the 27 non-verbatim entries.
MIN_LEN, MAX_LEN = 18, 52

# A verse opening with one of these leans on the verse before it and cannot stand alone.
DEPENDENT_START = ("그런즉", "이는", "그리하면", "그러나", "그러므로", "또", "또한", "곧", "이에",
                   "그때에", "그 때에", "그리고", "그가", "그들이", "그들은", "이것은", "그 후에",
                   "이러므로", "그런데", "다만", "무릇", "이와 같이", "그리하여")

# Narrative, legal and genealogical material: true text, but not a devotional line.
NARRATIVE = re.compile(
    r"낳았|자손|족속|지파|아들이라|딸이라|살고|살았더라|죽었더라|장사하|왕이 되|다스리|"
    r"진영|군대|싸우|치니라|멸하|죽이|피를|제물|번제|속죄제|성막|장막|규례|계수|세겔|"
    r"규빗|에봇|제사장이|레위|애굽 땅|바로에게|이스라엘 자손이|말씀하여 이르시되$|하시니라 하|"
    r"하였더라|하더라|이르되|대답하|보내어|올라가|내려가")

# Where a daily devotional line can safely come from. Restricting the source is the single most
# effective filter: the first pass drew from all 66 books and surfaced a battle formation
# (사사기 20:22), a judgment oracle (에스겔 7:25 "패망이 이르리니"), and a lament (시편 10:1
# "어찌하여 멀리 서시며") — all genuine 개역개정, none of them a morning verse. Rule 3 forbids the
# gloomy and the ominous, so the narrative, legal and oracle books are simply not read.
# 욥기 is excluded entirely: most of it is his friends being WRONG, quoted accurately.
DEVOTIONAL_BOOKS = {
    "신", "수",                                   # 강하고 담대하라 and its neighbours
    "시", "잠", "전", "사",                        # wisdom and comfort
    "렘", "호", "욜", "미", "합", "습", "학", "슥", "말",
    "마", "막", "눅", "요", "행",                   # gospels
    "롬", "고전", "고후", "갈", "엡", "빌", "골", "살전", "살후",
    "딤전", "딤후", "딛", "몬", "히", "약", "벧전", "벧후",
    "요일", "요이", "요삼", "유",
}

# Tone gate. A verse can be perfectly translated and still be the wrong thing to wake up to.
DARK = re.compile(
    r"진노|분노하|심판하|형벌|저주|멸망|패망|파멸|재앙|전멸|무찌|죽이|죽으리|피가|칼로|칼이|"
    r"불사르|사르리|원수를 갚|보응하|황폐|폐허|애곡|통곡|슬피 울|음부|지옥|영벌|"
    r"부끄러움을 당|수치를 당|버림받|끊어지리|토하|썩|시체|우상")

# Laments and rhetorical questions read as doubt on their own, out of the psalm that resolves them.
QUESTION = re.compile(r"(까|리요|나이까)[\s.]*$|어찌하여|언제까지")

# Proper nouns pull a verse back into its story; a daily line has to stand outside one.
NAMES = re.compile(
    r"압살롬|다윗|사울|솔로몬|모세|아론|여호수아|사무엘|엘리야|엘리사|바울|베드로|요한이|"
    r"아브라함|이삭|야곱|요셉|바로|애굽|바벨론|앗수르|블레셋|사마리아|고라|발람|"
    r"이스라엘 자손|이스라엘 사람|유다 왕|이스라엘 왕|장로들이|제사장들이")

# Nine weekly themes (THEME_ORDER in daily_post.py). Scored by lexicon; a verse needs a clear
# winner, otherwise it is left out rather than filed under a theme it does not carry.
THEMES = {
    "위로": ("위로", "눈물", "슬픔", "상한", "고난", "환난", "낙심", "근심", "아픔", "지친",
             "수고", "무거운", "쉬게", "싸매", "고치", "회복", "긍휼", "불쌍히", "애통"),
    "평안": ("평안", "평강", "쉼", "안식", "고요", "잔잔", "화평", "두려움이 없", "안전", "평화"),
    "담대": ("담대", "강하", "두려워하지", "놀라지", "용기", "굳세", "이기", "승리", "능히", "힘써"),
    "믿음": ("믿음", "믿는", "믿으", "신뢰", "의지", "바라보", "소망", "구하", "기도", "응답"),
    "감사": ("감사", "찬송", "찬양", "송축", "기쁨", "즐거", "노래", "높이", "영광을 돌리"),
    "사랑": ("사랑", "자비", "인자", "긍휼히", "용서", "친절", "섬기", "이웃", "형제를"),
    "인도": ("인도", "길을", "발걸음", "지키시", "함께 하", "목자", "빛이", "등불", "가르치", "이끄"),
    "은혜": ("은혜", "구원", "속량", "값없이", "선물", "의롭", "거듭", "새롭게", "영생", "십자가"),
    "지혜": ("지혜", "명철", "훈계", "지식", "슬기", "미련", "혀를", "말을", "마음을 지키", "훈련"),
}

BOOKS = {  # abbreviation → full Korean name used in `ref`
    "창": "창세기", "출": "출애굽기", "레": "레위기", "민": "민수기", "신": "신명기",
    "수": "여호수아", "삿": "사사기", "룻": "룻기", "삼상": "사무엘상", "삼하": "사무엘하",
    "왕상": "열왕기상", "왕하": "열왕기하", "대상": "역대상", "대하": "역대하", "스": "에스라",
    "느": "느헤미야", "에": "에스더", "욥": "욥기", "시": "시편", "잠": "잠언", "전": "전도서",
    "아": "아가", "사": "이사야", "렘": "예레미야", "애": "예레미야애가", "겔": "에스겔",
    "단": "다니엘", "호": "호세아", "욜": "요엘", "암": "아모스", "옵": "오바댜", "욘": "요나",
    "미": "미가", "나": "나훔", "합": "하박국", "습": "스바냐", "학": "학개", "슥": "스가랴",
    "말": "말라기", "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음",
    "행": "사도행전", "롬": "로마서", "고전": "고린도전서", "고후": "고린도후서",
    "갈": "갈라디아서", "엡": "에베소서", "빌": "빌립보서", "골": "골로새서",
    "살전": "데살로니가전서", "살후": "데살로니가후서", "딤전": "디모데전서",
    "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서", "히": "히브리서", "약": "야고보서",
    "벧전": "베드로전서", "벧후": "베드로후서", "요일": "요한일서", "요이": "요한이서",
    "요삼": "요한삼서", "유": "유다서", "계": "요한계시록",
}
KEY = re.compile(r"^(" + "|".join(sorted(BOOKS, key=len, reverse=True)) + r")(\d+):(\d+)$")


def theme_of(text):
    """The single theme this verse clearly carries, or None to leave it out."""
    score = {t: sum(w in text for w in words) for t, words in THEMES.items()}
    best = max(score, key=score.get)
    if score[best] == 0:
        return None
    runner = sorted(score.values())[-2]
    return best if score[best] > runner else best   # ties resolve to lexicon order, still one theme


def usable(text):
    if DARK.search(text) or QUESTION.search(text) or NAMES.search(text):
        return False
    if not (MIN_LEN <= len(text) <= MAX_LEN):
        return False
    if text.rstrip().rstrip(".").endswith(INCOMPLETE_ENDINGS):
        return False
    if text.startswith(DEPENDENT_START):
        return False
    if NARRATIVE.search(text):
        return False
    if re.search(r"\d", text):            # counts, ages, measures — not devotional lines
        return False
    return True


def build():
    with open(SOURCE, encoding="utf-8") as f:
        raw = json.load(f)
    out, seen = [], set()
    for key, text in raw.items():
        m = KEY.match(key)
        if not m or m.group(1) not in DEVOTIONAL_BOOKS:
            continue
        text = text.strip()
        if text in seen or not usable(text):
            continue
        theme = theme_of(text)
        if not theme:
            continue
        seen.add(text)
        out.append({"ref": f"{BOOKS[m.group(1)]} {m.group(2)}:{m.group(3)}", "text": text,
                    "theme": theme})
    return out


JUDGE_PROMPT = """당신은 매일 아침·저녁 한 구절을 올리는 한국어 성경 묵상 계정의 편집자입니다.
아래 개역개정 구절들이 그 계정에 **단독으로** 올라갈 수 있는지 하나씩 판정하세요.

받아들일 것: 그 자체로 완결된 약속·권면·찬양·지혜. 앞뒤 문맥을 몰라도 뜻이 통하는 것.

반드시 거절할 것:
- 심판·재앙·저주·전쟁 선언, 원수를 저주하는 기도
- 이야기의 한 조각(누가 어디로 갔다, 무리가 놀랐다 같은 서술)
- 앞 절을 받아야만 뜻이 통하는 것, 문장이 중간에서 끊긴 것
- 특정 인물·지명·사건을 알아야 이해되는 것
- 하나님이 아닌 사람의 잘못된 말을 인용한 것
- 아침에 읽기에 어둡거나 위협적인 것

주제는 다음 아홉 중 하나로 다시 매겨주세요(원래 주제가 틀렸으면 고칠 것):
위로, 평안, 담대, 믿음, 감사, 사랑, 인도, 은혜, 지혜

절대로 본문을 고치지 마세요. 채택 여부와 주제만 판정합니다.

JSON 배열로만 답하세요: [{"i": 번호, "ok": true/false, "theme": "주제"}, ...]

구절:
"""


def judge(batch):
    """Ask Gemini which of these verses can stand alone as a daily devotional line.

    The lexicon gets a verse into the room; this decides whether it belongs there. Keywords cannot
    tell a promise from an oracle — 시편 69:22 ("그들의 평안이 덫이 되게 하소서") scores as 평안 —
    and shipping that to an account already restricted for content quality is not a risk worth
    taking. Returns [(index, theme)] of the ones to keep; on any error keeps NOTHING from the batch,
    because an unverified verse must never reach the pool."""
    import urllib.request
    key = os.environ.get("GEMINI_API_KEY")
    listing = "\n".join(f'{i}. [{v["ref"]}] {v["text"]}' for i, v in enumerate(batch))
    body = {"contents": [{"parts": [{"text": JUDGE_PROMPT + listing}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-pro:generateContent?key={key}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    data = json.load(urllib.request.urlopen(req, timeout=180))
    out = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    keep = []
    for row in out:
        i, theme = row.get("i"), row.get("theme")
        if row.get("ok") and isinstance(i, int) and 0 <= i < len(batch) and theme in THEMES:
            keep.append((i, theme))
    return keep


def verify(verses, size=40):
    kept = []
    for start in range(0, len(verses), size):
        batch = verses[start:start + size]
        try:
            picks = judge(batch)
        except Exception as e:
            print(f"  배치 {start//size + 1}: 검수 실패({e}) — 이 배치는 전부 제외")
            continue
        for i, theme in picks:
            v = dict(batch[i]); v["theme"] = theme
            kept.append(v)
        print(f"  배치 {start//size + 1}: {len(picks)}/{len(batch)} 채택 (누적 {len(kept)})")
    return kept


if __name__ == "__main__":
    import collections
    import sys
    verses = build()
    print(f"1차 선별 {len(verses)}절 / 원문 31089절")
    if "--verify" in sys.argv:
        verses = verify(verses)
        print(f"\nLLM 검수 통과 {len(verses)}절")
    for t, n in collections.Counter(v["theme"] for v in verses).most_common():
        print(f"  {t}: {n}")
    if "--write" in sys.argv:
        out = {"_comment": ("개역개정 verses, VERBATIM — never trimmed, never reworded. Built by "
                            "build_verses.py from the full text and verified one by one; see "
                            "CONTENT_RULE 12."),
               "translation": "개역개정", "verses": verses}
        with open(os.path.join(HERE, "verses.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"verses.json 갱신 — {len(verses)}절")
