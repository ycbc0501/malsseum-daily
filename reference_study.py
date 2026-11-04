#!/usr/bin/env python3
"""Study a reference account's grid every ~2 weeks, so the pool's variety is checked against
something outside our own code rather than only against itself.

Why this exists (2026-11-04): the account owner looked at the live grid and said it directly —
"같은구조의 방 바다 들판 좀 따분한거같은데" (room/ocean/field, same structure, repeating). Looking at
@dailymayim's grid side by side makes the gap concrete: night skies, fireworks, a piano room,
windows-as-frame, architecture (a rooftop, a house exterior, an archway) — structure our own
SCENE_GROUPS pool already HAS (fetch_image.py has 70 categories / 140 scenes) but that the recent
rotation was not reaching, because pick_scene()'s no-repeat window only checked exact category, not
visual structure (fixed the same day — see RULES.md D-1, fetch_image.SCENE_STRUCTURE).

This script is the forward-looking half of that fix: a recurring check against an outside
reference, on a cadence (~14 days), so the next time the rotation drifts narrow it is caught by
comparison instead of by the account owner noticing the grid looks boring.

Two fetch paths:
  - API (business_discovery): tried first. Needs `instagram_basic` + `pages_read_engagement` on
    the token AND the app's "Instagram Public Content Access" feature enabled — confirmed BLOCKED
    as of 2026-11-04 (`(#10) Application does not have permission for this action`, the SAME token
    that publishes fine). The real Meta error is always surfaced, never swallowed (RULES.md H0) —
    so the day this starts working shows up in the log, not as a guess.
  - Manual: when the API path is blocked, the cron job sends a Telegram reminder asking for grid
    screenshots — the same thing the account owner already did by hand on 2026-11-04. Screenshots
    get classified (Gemini vision, or a human eye reading the same taxonomy — this script does not
    care which) and fed back in with --manual DIR.

What this file NEVER does: edit fetch_image.py. A gap report only SUGGESTS candidate scene
categories — whether to add one, and what the actual prompt text should say (it still has to pass
content_law.LAW and get registered in INTERIOR_CATS/SCENE_STRUCTURE), is a reviewed code change,
not something this script writes for itself. check_rules.py asserts this file never opens
fetch_image.py for writing.
"""
import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, timedelta

import fetch_image as hf
import notify
import post_instagram

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "reference_study.json")
REPORT_DIR = os.path.join(HERE, "notes", "reference-study")

# The account this project's visual aesthetic has been benchmarked against since the 2026-07-30
# reversal (verse-first, quiet, muted, everyday — see the visual-aesthetic memory note). Extend
# this list rather than replacing it if a second reference becomes useful.
REFERENCE_ACCOUNTS = ["dailymayim"]

STUDY_INTERVAL_DAYS = 14


def _today():
    return date.today().isoformat()


def load_ledger(path=None):
    try:
        with open(path or LEDGER_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"history": [], "last_run": None, "next_due": None}


def save_ledger(d, path=None):
    with open(path or LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def due(ledger=None, today=None):
    """True if a study is due: no run has ever completed, or STUDY_INTERVAL_DAYS have passed
    since the last one advanced next_due. Pure function of the ledger + a date, so it is testable
    without touching the clock or the real ledger file."""
    ledger = ledger if ledger is not None else load_ledger()
    today = today or _today()
    nd = ledger.get("next_due")
    return not nd or today >= nd


def advance(ledger, today=None, days=STUDY_INTERVAL_DAYS):
    today = today or _today()
    ledger["last_run"] = today
    ledger["next_due"] = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
    return ledger


# ---------------------------------------------------------------------------------------------
# Fetch — API path (documented BLOCKED 2026-11-04; kept so the day it starts working needs only
# a permission grant, not a code change — RULES.md H0: never swallow the API's own reason).
# ---------------------------------------------------------------------------------------------
def try_api_fetch(handle, limit=12, ig_user_id=None, token=None):
    """Business Discovery: pull a reference account's recent public media via OUR OWN token.
    Raises RuntimeError carrying Meta's actual error body on failure — never swallowed."""
    ig_user_id = ig_user_id or os.environ.get("IG_USER_ID")
    token = token or os.environ.get("IG_ACCESS_TOKEN")
    if not ig_user_id or not token:
        raise RuntimeError("IG_USER_ID / IG_ACCESS_TOKEN not set")
    fields = (f"business_discovery.username({handle})"
              f"{{username,media_count,followers_count,"
              f"media.limit({limit}){{media_type,media_url,permalink,timestamp}}}}")
    url = (f"{post_instagram.GRAPH}/{ig_user_id}?fields={urllib.parse.quote(fields)}"
           f"&access_token={urllib.parse.quote(token)}")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"business_discovery({handle}) failed: HTTP {e.code} {body}") from None
    media = data.get("business_discovery", {}).get("media", {}).get("data", [])
    return [m for m in media if m.get("media_type") in ("IMAGE", "CAROUSEL_ALBUM")]


# ---------------------------------------------------------------------------------------------
# Classify — Gemini vision, the SAME model/credential path as fetch_image.check_composition, on
# purpose (RULES.md H0-4: one implementation of a thing, not a second one that can drift).
# ---------------------------------------------------------------------------------------------
TAXONOMY_PROMPT = (
    "You are studying an Instagram grid for VISUAL STRUCTURE variety — not content, not text, not "
    "quality. Classify what this single picture reads as AT A GLANCE, using ONLY one of these "
    "buckets if it genuinely fits: {buckets}. If none of them fit the picture's structure, answer "
    "with \"NEW: <a short 2-4 word label>\" instead of forcing a bad fit. "
    "Reply ONLY as JSON: {{\"bucket\": \"<one of the above, or a NEW: label>\", "
    "\"why\": \"<one short phrase>\"}}")


def classify_image(image_path, taxonomy=None):
    """Ask Gemini vision which structural bucket a reference picture falls into (or propose a new
    one, outside our existing taxonomy). Never edits anything — returns a label only."""
    taxonomy = taxonomy or sorted(set(hf.SCENE_STRUCTURE.values()))
    img_b64 = base64.b64encode(open(image_path, "rb").read()).decode()
    prompt = TAXONOMY_PROMPT.format(buckets=", ".join(taxonomy))
    body = {"contents": [{"parts": [
                {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
                {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{hf.VISION_MODEL}:generateContent?key={hf._gemini_key()}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    data = json.load(urllib.request.urlopen(req, timeout=90))
    txt = data["candidates"][0]["content"]["parts"][0]["text"]
    j = json.loads(txt)
    return {"bucket": str(j.get("bucket", "?"))[:60], "why": str(j.get("why", ""))[:200]}


# ---------------------------------------------------------------------------------------------
# Compare — pure function, no network, fully testable without touching Gemini or Instagram.
# ---------------------------------------------------------------------------------------------
def gap_report(ref_buckets, our_recent_cats, catalog_structure=None):
    """ref_buckets: list of bucket labels already classified (an existing taxonomy name, or a
    "NEW: ..." label). our_recent_cats: the tail of state["used_scene_cats"]. Returns a dict
    comparing distributions. Never edits anything — report only."""
    catalog_structure = catalog_structure or hf.SCENE_STRUCTURE
    ref_dist = Counter(ref_buckets)
    our_recent_dist = Counter(catalog_structure.get(c, "?") for c in our_recent_cats)
    catalog_dist = Counter(catalog_structure.values())
    new_candidates = sorted({b for b in ref_buckets if b.startswith("NEW:")})
    known_ref = [b for b in ref_buckets if not b.startswith("NEW:")]
    # A bucket the reference leans on but we have not used at all lately, even though our own
    # catalog already has it — that gap is in ROTATION (pick_scene reach), not in the prompt pool.
    underused = sorted(
        b for b in set(known_ref)
        if ref_dist[b] >= 2 and our_recent_dist.get(b, 0) == 0 and catalog_dist.get(b, 0) > 0)
    return {
        "ref_dist": dict(ref_dist),
        "our_recent_dist": dict(our_recent_dist),
        "catalog_dist": dict(catalog_dist),
        "new_candidates": new_candidates,
        "underused_in_rotation": underused,
    }


def write_report(accounts, mode, gap, today=None, path=None):
    today = today or _today()
    path = path or os.path.join(REPORT_DIR, f"{today}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# 레퍼런스 스터디 — {today}",
        "",
        f"대상: {', '.join('@' + a for a in accounts)} · 수집 방식: {mode}",
        "",
        "이 보고서는 fetch_image.py를 자동으로 바꾸지 않습니다. 후보는 검토 후 사람/다음 세션이",
        "직접 추가합니다 — 프롬프트는 content_law.LAW(인물 없음·글자 없음·실사·실필름)를 통과해야",
        "하고, 실내라면 INTERIOR_CATS·SCENE_STRUCTURE에도 같이 등록해야 합니다 (RULES.md D).",
        "",
        "## 레퍼런스 구조 분포",
    ]
    for b, n in sorted(gap["ref_dist"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- {b}: {n}")
    lines += ["", "## 우리 최근 로테이션 분포 (state.used_scene_cats 꼬리)"]
    for b, n in sorted(gap["our_recent_dist"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- {b}: {n}")
    lines += ["", "## 레퍼런스엔 있는데 최근 우리 로테이션엔 없는 버킷 (카탈로그엔 있음 — 회전 문제)"]
    lines += [f"- {b}" for b in gap["underused_in_rotation"]] or ["- (없음)"]
    lines += ["", "## 기존 7개 구조 버킷 어디에도 안 맞는 신규 후보 (검토 필요)"]
    lines += [f"- {b}" for b in gap["new_candidates"]] or ["- (없음)"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def record_run(accounts, mode, gap, report_path, ledger=None, today=None, path=None):
    """Append a history entry and advance due(). Writes to `path` (LEDGER_PATH by default) —
    NOT wherever `ledger` happened to come from. Passing an in-memory `ledger` dict without ALSO
    passing a throwaway `path` used to still write the real reference_study.json: that clobbered
    the genuine first manual study with test fixture data the moment test_reference_study.py ran
    (caught 2026-11-04, same day this file was written — see RULES.md D-2/H0-4, "원장은 한
    구현만 씁니다" cuts both ways: shared code must still take an explicit target, not assume one)."""
    ledger = ledger if ledger is not None else load_ledger(path)
    today = today or _today()
    ledger.setdefault("history", []).append({
        "date": today, "accounts": list(accounts), "mode": mode,
        "report": os.path.relpath(report_path, HERE),
        "new_candidates": gap["new_candidates"],
        "underused_in_rotation": gap["underused_in_rotation"],
    })
    advance(ledger, today)
    save_ledger(ledger, path)
    return ledger


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------
def _recent_cats():
    try:
        return json.load(open(os.path.join(HERE, "state.json"))).get("used_scene_cats", [])
    except Exception:
        return []


def send_reminder(reason=""):
    accounts = ", ".join("@" + a for a in REFERENCE_ACCOUNTS)
    msg = (f"\U0001F4CE 레퍼런스 스터디 때입니다 — {accounts} 그리드 스크린샷을 보내주세요.\n"
           f"(자동 수집이 아직 막혀 있습니다: {reason[:200]})" if reason else
           f"\U0001F4CE 레퍼런스 스터디 때입니다 — {accounts} 그리드 스크린샷을 보내주세요.")
    notify.send(msg)


def run_try_fetch():
    """Try the API for every configured account; classify whatever comes back. If EVERY account
    fails, fall back to a Telegram reminder and still record the attempt (so `due()` moves on —
    retrying a blocked permission daily would just be the same failure every day)."""
    errors, all_buckets, ok_accounts = [], [], []
    for h in REFERENCE_ACCOUNTS:
        try:
            media = try_api_fetch(h)
        except Exception as e:
            print(f"reference_study: {h} unavailable — {e}")
            errors.append(str(e))
            continue
        ok_accounts.append(h)
        for m in media:
            url = m.get("media_url")
            if not url:
                continue
            tmp = f"/tmp/refstudy_{h}_{m.get('timestamp', '')[:10]}.jpg"
            try:
                urllib.request.urlretrieve(url, tmp)
                all_buckets.append(classify_image(tmp)["bucket"])
            except Exception as e:
                print(f"reference_study: classify failed for one {h} image — {e}")
    if not ok_accounts:
        print("reference_study: API path unavailable for every account — sending a reminder instead")
        send_reminder(reason="; ".join(errors))
        gap = gap_report([], _recent_cats())
        path = write_report(REFERENCE_ACCOUNTS, "unavailable", gap)
        record_run(REFERENCE_ACCOUNTS, "unavailable", gap, path)
        return 1
    gap = gap_report(all_buckets, _recent_cats())
    path = write_report(ok_accounts, "api", gap)
    record_run(ok_accounts, "api", gap, path)
    print(f"reference_study: report written to {path}")
    return 0


def run_manual(dirpath, accounts):
    files = sorted(
        os.path.join(dirpath, n) for n in os.listdir(dirpath)
        if n.lower().endswith((".jpg", ".jpeg", ".png")))
    if not files:
        print(f"reference_study: no images found in {dirpath}")
        return 1
    buckets = [classify_image(p)["bucket"] for p in files]
    gap = gap_report(buckets, _recent_cats())
    path = write_report(accounts, "manual", gap)
    record_run(accounts, "manual", gap, path)
    print(f"reference_study: report written to {path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true", help="print + exit 0 if a study is due, else 1")
    ap.add_argument("--run", action="store_true",
                     help="if due: try the API, fall back to a Telegram reminder; no-op otherwise")
    ap.add_argument("--remind", action="store_true")
    ap.add_argument("--manual", metavar="DIR", help="classify local screenshots in DIR")
    ap.add_argument("--account", action="append", default=[])
    args = ap.parse_args()
    if args.due:
        d = due()
        print("due" if d else f"not due (next: {load_ledger().get('next_due')})")
        return 0 if d else 1
    if args.remind:
        send_reminder()
        return 0
    if args.manual:
        return run_manual(args.manual, args.account or REFERENCE_ACCOUNTS)
    if args.run:
        if not due():
            print(f"not due yet (next: {load_ledger().get('next_due')})")
            return 0
        return run_try_fetch()
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
