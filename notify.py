#!/usr/bin/env python3
"""Send a short Telegram message about what the pipeline just did.

Until now the only signal a post had failed was a GitHub issue, which nobody reads, so a missed
post stayed invisible until it showed up as a gap on the feed days later. This puts it where the
account owner actually is.

Best-effort by construction: no token, no chat id, or a Telegram outage all return quietly. An
alerting channel must never be able to fail a post — that would be the alert causing the outage
it exists to report.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.telegram.org"


def send(text, token=None, chat_id=None):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("telegram: not configured — skipping")
        return False
    body = urllib.parse.urlencode({
        "chat_id": chat_id, "text": text,
        "disable_web_page_preview": "true",
    }).encode()
    try:
        req = urllib.request.Request(f"{API}/bot{token}/sendMessage", data=body, method="POST")
        urllib.request.urlopen(req, timeout=20)
        print("telegram: sent")
        return True
    except Exception as e:
        print(f"telegram: failed ({e}) — ignoring, an alert must never fail a post")
        return False


def posted(meta_path, run_url=""):
    """Message describing the post that just went out, from _meta.json."""
    try:
        with open(meta_path, encoding="utf-8") as f:
            m = json.load(f)
    except Exception as e:
        return f"게시 완료 (메타 읽기 실패: {e})\n{run_url}"
    motion = m.get("motion")
    sky = m.get("motion_sky")
    tries = m.get("motion_attempts")
    lines = [
        f"✅ 게시 완료 — {m.get('ref', '?')}",
        f"[{m.get('theme', '?')}] {m.get('duration', '?')}초 · {m.get('segments', '?')}세그먼트",
    ]
    if motion is not None:
        # The number the owner has been judging by eye for weeks — see RULES.md E8.
        lines.append(f"모션 {motion} / 하늘 {sky} (목표 1.5 / 0.35, {tries}회 시도)")
    if run_url:
        lines.append(run_url)
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--posted":
        raise SystemExit(0 if send(posted(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")) else 0)
    raise SystemExit(0 if send(" ".join(sys.argv[1:])) else 0)
