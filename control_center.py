#!/usr/bin/env python3
"""The one place to ask "is everything okay" — instead of five.

    python3 control_center.py            # print the full status report
    python3 control_center.py --notify    # also send it as ONE Telegram message

Why this exists (2026-11-09, asked directly: "다 감독하는 센터를 만들어 여기저기 뿌리지 말고")
-----------------------------------------------------------------------------------------------
By the time this was asked, "supervision" already meant five unrelated commands, each answering
one question and silent about the other four:

    watch.py          — operational alerts (engagement, missed slots, motion, cron liveness)
    check_rules.py     — does the CODE still match RULES.md (via verify.sh, push-triggered CI)
    ig_doctor.py       — does our TOKEN actually have the scope it needs
    ig_probe.py        — is that scope map still fresh, or probed 25+ days ago
    reference_study.py — is the external-comparison study overdue

A human (or an agent starting a session with no memory of the last one) had to know all five
names and run all five to get the full picture. Worse: `checks.yml` runs on every push and, if it
goes RED, says so only on GitHub's own Actions page — which nothing in this repo ever pings
anyone about, because the operational alert channel (watch.py → Telegram) and the static
verification layer (verify.sh → GitHub Actions UI) have never talked to each other. A broken rule
could sit red for days exactly the way a broken test sat unrun for days before verify.sh existed
(see verify.sh's own docstring) — the same shape of problem, one level up.

This file does not reimplement any of the five. It imports each one and asks it the question it
already knows how to answer, then prints one report. Nothing here makes a billed API call test
cannot afford to run often (the only live calls are `debug_token`, once, and one GitHub Actions
run lookup — both free and read-only); the expensive single-metric probing `ig_doctor.py` does at
the end of its own `main()` is deliberately NOT called here.

RULES.md §J: a new standalone supervisory script must be wired in here too, or it is the sixth
name nobody remembers to run — check_rules.py enforces that this file actually imports each of
the five by name, not just that the five files still exist.
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KST = datetime.timezone(datetime.timedelta(hours=9))


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ------------------------------------------------------------------------------------------- ops
def ops_section():
    """watch.py's own findings() — already the union of operational alerts AND cron liveness
    (cron_health is folded in there, RULES.md I-1). Read-only: `prev` is passed so the checks that
    need history (scene-freeze, reply-divergence) see it, but this never writes watch.json — that
    remains watch.py's job, run on its own schedule."""
    import watch
    prev = _load_json(os.path.join(HERE, "watch.json"), {})
    try:
        found = watch.findings(prev)
    except Exception as e:
        return {"ok": None, "detail": f"watch.findings() 자체가 실패했습니다 ({e})", "items": []}
    return {"ok": not found, "detail": None, "items": [msg.splitlines()[0] for _, msg in found]}


# -------------------------------------------------------------------------------------------- ci
def ci_section():
    """The latest production run of checks.yml — the push-triggered test+rule suite. This is the
    ONE thing that previously had NO alert path at all: a red run sits on GitHub's Actions page
    and nothing in this repo has ever pinged anyone about it. Reuses cron_health's own GitHub API
    helper rather than a second urllib implementation — checks.yml has no `schedule:` trigger so
    cron_health's own WATCHLIST machinery (which only watches scheduled runs) does not cover it;
    this asks the same API for the most recent run of any kind instead."""
    import cron_health
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not (repo and token):
        return {"ok": None, "detail": "GITHUB_REPOSITORY/GITHUB_TOKEN 없음 — 조회 불가", "url": None}
    try:
        runs = cron_health._gh(f"/repos/{repo}/actions/workflows/checks.yml/runs?per_page=1", token)
    except Exception as e:
        return {"ok": None, "detail": f"조회 실패 ({e})", "url": None}
    latest = (runs.get("workflow_runs") or [None])[0]
    if not latest:
        return {"ok": None, "detail": "실행 기록 없음", "url": None}
    conclusion = latest.get("conclusion")
    ok = conclusion in (None, "success", "skipped")
    return {"ok": ok, "detail": conclusion or latest.get("status"), "url": latest.get("html_url")}


# ----------------------------------------------------------------------------------------- token
def token_section():
    """What our tokens are allowed to do. Reuses ig_doctor.verdict() rather than re-reading
    describe()/NEEDED on its own — that second reading is exactly what broke this section:
    IG_INSIGHTS_TOKEN is an Instagram-Login token, debug_token structurally cannot read it
    (confirmed 2026-11-10 with every app id/secret combination — see ig_doctor.py's module
    docstring), so a describe()-only check reports it dead on EVERY run forever, correctly
    debug_token-wise and incorrectly in every way that matters. verdict() already carries the
    live-probe fallback that makes this call right; this just asks it instead of asking twice."""
    import ig_doctor
    s = ig_doctor.secrets()
    app_id, app_secret = s.get("META_APP_ID"), s.get("META_APP_SECRET")
    if not (app_id and app_secret):
        return {"ok": None, "detail": "META_APP_ID/META_APP_SECRET 없음 — 조회 불가", "ok_tokens": []}
    v = ig_doctor.verdict(s)
    errors = [f"{key}: {err.get('message')}" for key, err in v["errors"].items()
              if key not in v["ok_tokens"]]
    return {"ok": bool(v["ok_tokens"]), "detail": "; ".join(errors) or None,
            "ok_tokens": v["ok_tokens"]}


# ------------------------------------------------------------------------------------ freshness
def freshness_section():
    """Is the scope map (ig_probe.py) and the external-comparison study (reference_study.py)
    still fresh, or overdue for a re-measurement. Neither is urgent on its own — both drift over
    weeks, not hours — which is exactly why nobody remembers to check them without one place that
    lists every slow-moving thing next to the fast-moving ones."""
    import ig_probe
    import reference_study
    stale, probe_detail = ig_probe.is_stale()
    ledger = reference_study.load_ledger()
    due = reference_study.due(ledger)
    return {
        "probe_stale": stale, "probe_detail": probe_detail,
        "study_due": due, "study_next": ledger.get("next_due"),
    }


SECTIONS = ("ops", "ci", "token", "freshness")


def report(now=None):
    """Everything above, in one dict. A plain function, not just a CLI, so an agent (or a test)
    can read the status without parsing printed text."""
    now = now or datetime.datetime.now(KST)
    return {
        "generated": now.isoformat(),
        "ops": ops_section(),
        "ci": ci_section(),
        "token": token_section(),
        "freshness": freshness_section(),
    }


def _mark(ok):
    return "✅" if ok else ("❓" if ok is None else "⚠️")


def render(r):
    lines = [f"🏛 컨트롤 센터 — {r['generated'][:16].replace('T', ' ')} KST"]

    ops = r["ops"]
    lines.append(f"\n{_mark(ops['ok'])} 운영 알림 (watch.py — 크론 생존 포함)")
    if ops["detail"]:
        lines.append(f"   {ops['detail']}")
    elif ops["items"]:
        for item in ops["items"]:
            lines.append(f"   · {item}")
    else:
        lines.append("   전부 정상")

    ci = r["ci"]
    lines.append(f"\n{_mark(ci['ok'])} 코드/규칙 검증 (checks.yml 최신 실행)")
    lines.append(f"   {ci['detail']}" + (f" — {ci['url']}" if ci.get("url") else ""))

    token = r["token"]
    lines.append(f"\n{_mark(token['ok'])} 토큰/권한")
    if token["ok_tokens"]:
        lines.append(f"   인사이트 권한 있음: {token['ok_tokens']}")
    elif token["ok"] is False:
        lines.append("   인사이트 권한을 가진 토큰이 없습니다 — notes/insights-token-2026-10-07.md")
    if token["detail"]:
        lines.append(f"   {token['detail']}")

    fresh = r["freshness"]
    lines.append("\nℹ️ 진단 최신성")
    lines.append(f"   api_support.json: {'재측정 필요 — ' if fresh['probe_stale'] else ''}"
                 f"{fresh['probe_detail']}")
    lines.append(f"   레퍼런스 스터디: {'기한 지남' if fresh['study_due'] else '아직 안 됨'}"
                 f" (다음 {fresh['study_next'] or '미정'})")

    return "\n".join(lines)


def main():
    r = report()
    text = render(r)
    print(text)
    if "--notify" in sys.argv:
        import notify
        ok = notify.send(text)
        print("telegram: sent" if ok else "telegram: NOT sent")
    # Exit non-zero when something is CONFIRMED broken (ok is False anywhere) — None ("could not
    # check") is deliberately not treated as failure, the same distinction cron_health draws:
    # a lookup that could not run is not evidence of either health or breakage.
    broken = any(r[s].get("ok") is False for s in ("ops", "ci", "token"))
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
