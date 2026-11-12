#!/usr/bin/env python3
"""Notice when a SCHEDULED WORKFLOW itself has stopped firing or started failing.

Every other check in this repo watches an OUTCOME (a post went out, likes held up, motion
rendered). This one watches the INFRASTRUCTURE that produces those outcomes — because an outcome
check can only speak once something downstream has visibly broken, and some crons have no visible
downstream at all. comment-reply.yml, insights.yml, refresh-token.yml and reference-study.yml can
each silently stop running for weeks with nothing else in this repo noticing — refresh-token.yml
is the most dangerous: if it stops, the long-lived token eventually expires and EVERY workflow in
this repo stops publishing at once, discovered only when the account goes dark.

Why this exists (2026-11-09): asked to watch "everything, down to crons dying," a direct check of
GitHub's own run history (not a theory about what the cron expression SHOULD do) turned up a
currently-live, unreported failure: weekly-carousel.yml's most recent scheduled run (2026-11-08)
built the carousel slides and then died with "HTTP Error 400: Bad Request" publishing them —
Meta's actual reason was swallowed by a code path this fix also closes (post_instagram._post(),
see RULES.md H0 history). The carousel never asked for a human to look, and nothing else in this
repo would ever have noticed a single weekly post silently failing to go out. See RULES.md I-1.

THRESHOLDS ARE MEASURED, NOT ASSUMED. "comment-reply.yml runs every 10 minutes" is what the cron
expression SAYS; what GitHub actually does with a sub-hourly schedule is throttle it hard under
load. Pulled on 2026-11-09 (`gh api .../runs?event=schedule --paginate`): 1000 runs over 86 days,
median gap 48 MINUTES (not 10), p99 7.8 hours, worst observed gap 12.3 hours. A threshold written
from the cron expression would have paged someone every single day for something GitHub does
constantly and harmlessly. Every number in WATCHLIST below is "worst observed gap, times a safety
margin" — recalibrate with the same query if this ever starts crying wolf or, worse, goes quiet
on a real outage.

What this does NOT cover: if GitHub Actions stops running ANYTHING for this repo — not one
workflow but the whole scheduler — this check dies with everything else, because it also only
runs on a GitHub Actions schedule. That blind spot cannot be closed by code living inside the
thing it is watching; see RULES.md I-2 for the external dead-man's-switch this needs (a one-time
human signup, same shape as the IG insights token).
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"

# file: the workflow's path under .github/workflows/
# label: shown in the alert
# max_gap_h: alert if MORE than this many hours have passed since the workflow was last known to
#   be alive (its most recent event=schedule run, or — if it has never had one yet — the moment
#   GitHub registered/last edited the workflow file, so a just-added workflow does not trip this
#   before it has had a chance to fire even once).
WATCHLIST = [
    {
        "file": "comment-reply.yml",
        "label": "댓글 답글 (시간당, 2026-11-12 이전엔 10분 간격 선언)",
        # Measured 2026-11-09 against the OLD "*/10 * * * *" declaration: 1000 runs / 86 days,
        # median gap 48min, max observed 12.3h. The cron itself changed to hourly 2026-11-12
        # (RULES.md G-1) because GitHub was throttling the sub-hourly declaration anyway — this
        # ceiling is left unchanged since 24h was already far looser than even that worst case.
        "max_gap_h": 24,
    },
    {
        "file": "insights.yml",
        "label": "지표 백필 (매일)",
        # Measured 2026-11-09: 96 runs / 95 days, max observed gap 30.1h.
        "max_gap_h": 36,
    },
    {
        "file": "refresh-token.yml",
        "label": "토큰 갱신 (매주, 가장 중요 — 끊기면 전체 발행이 멈춥니다)",
        # Measured 2026-11-09: 12 runs / 77 days, max observed gap 171.1h (~7.1 days).
        "max_gap_h": 24 * 9,
    },
    {
        "file": "weekly-carousel.yml",
        "label": "주간 캐러셀 (매주)",
        # Measured 2026-11-09: 19 runs / 126 days, max observed gap 177.6h (~7.4 days).
        "max_gap_h": 24 * 9,
    },
    {
        "file": "reference-study.yml",
        "label": "레퍼런스 스터디 (2주마다, RULES.md D-2)",
        # The cron itself fires on the 1st/15th regardless of due(); worst steady-state gap
        # between those two dates is 17 days (15th of a 31-day month → 1st). 24 days covers that
        # with margin without waiting so long a real outage goes unnoticed for a month.
        "max_gap_h": 24 * 24,
    },
]

# Every OTHER workflow with a `schedule:` trigger must be listed here, with why it is NOT in
# WATCHLIST — otherwise a 6th scheduled workflow added later (or one simply forgotten on
# 2026-11-09) sails past this watchdog exactly the way weekly-carousel.yml sailed past every
# OTHER check that existed before this file. check_rules.py enforces that
# WATCHLIST ∪ DELIBERATELY_UNWATCHED covers every workflow file with a schedule: trigger.
DELIBERATELY_UNWATCHED = {
    "daily-post.yml": (
        "watch.py's own missed-slot check asks Instagram directly whether a reel went out — a "
        "better oracle than 'did the workflow fire', because it is immune to a chain that fires "
        "on schedule but fails every retry, or fires and quietly skips for an unrelated reason."),
    "watch.yml": (
        "this IS the watchdog — it cannot certify its own pulse from inside itself. RULES.md I-2 "
        "covers this with an external dead-man's-switch (HEALTHCHECK_URL), not a self-check."),
}

# A run that finished in any of these states is NOT a failure worth paging about — "skipped" is
# a legitimate no-op (a job-level `if:` that chose not to run), not a crash.
OK_CONCLUSIONS = (None, "success", "skipped")


def _gh(path, token):
    """GET the GitHub API, with Meta's own H0 lesson applied to GitHub's API too: a dropped
    error body is a dropped reason. Raises RuntimeError carrying the body on failure."""
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"GET {path} failed: HTTP {e.code} {body}") from None


def _gh_post(path, token, body):
    """POST the GitHub API — same H0 lesson as _gh(): keep the error body, don't drop it."""
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode(), method="POST",
                                  headers={
                                      "Authorization": f"Bearer {token}",
                                      "Accept": "application/vnd.github+json",
                                      "X-GitHub-Api-Version": "2022-11-28",
                                      "Content-Type": "application/json",
                                  })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"POST {path} failed: HTTP {e.code} {body_text}") from None


def dispatch_workflow(workflow_file, repo=None, token=None, ref="main", inputs=None):
    """Fire `workflow_dispatch` on `workflow_file` via the REST API → (ok, detail). Never raises.

    Why the API and not `gh workflow run`: this has no dependency on the gh CLI existing on
    whatever runner calls it. Why GITHUB_TOKEN works here at all when it can't trigger most
    other events: GitHub's own docs carve out `workflow_dispatch` and `repository_dispatch` as
    the two exceptions to "actions taken by GITHUB_TOKEN don't trigger new workflow runs" (the
    anti-recursion guard) — confirmed 2026-11-12 specifically because this function exists to
    let watch.yml's own GITHUB_TOKEN fire a daily-post.yml catch-up. It still needs the calling
    job's `permissions:` to grant `actions: write`, or GitHub answers 403.

    `inputs` is sent only if given (an empty dict is a valid GitHub payload, but omitting the key
    entirely when the caller passed nothing keeps the request identical to before `inputs`
    existed). watch.py uses this to pass {"hour": "5"/"19"} — see its auto_retry_missed_slots()
    docstring for why dispatching with no hour at all was a real bug (it let daily-post.yml's own
    wall-clock fallback silently retry the WRONG slot).

    Catches Exception broadly, not just the RuntimeError _gh_post raises for an HTTP error — a
    structural review (2026-11-12) found that a plain network failure (URLError, timeout, DNS)
    is not a RuntimeError and used to propagate straight out of this function, through
    watch.auto_retry_missed_slots(), and crash watch.py's main() before it could save ANY of this
    run's state — one flaky POST silently disabling the whole alert pipeline's bookkeeping, not
    just this one feature. A caller that truly needs to tell network/API failures apart from
    "not configured" still can, from the detail string; nothing here invents a fake success."""
    repo = repo or os.environ.get("GITHUB_REPOSITORY")
    token = token or os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return False, "GITHUB_REPOSITORY / GITHUB_TOKEN not set"
    body = {"ref": ref}
    if inputs:
        body["inputs"] = inputs
    try:
        _gh_post(f"/repos/{repo}/actions/workflows/{workflow_file}/dispatches", token, body)
        return True, "dispatched"
    except Exception as e:                            # noqa: BLE001 — see docstring
        return False, str(e)


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def evaluate(entry, workflow_info, last_run, now):
    """Pure — no network, so this is testable without mocking GitHub. workflow_info is GitHub's
    `/actions/workflows/<file>` response (or None if that call failed). last_run is the single
    most recent event=schedule run (or None, meaning no scheduled run has EVER completed — which
    is normal for a workflow younger than its own cadence, not a fault).

    Returns (ok, detail): ok is True (healthy), False (alert), or None (cannot judge — a lookup
    failed upstream; findings() escalates that separately and must never read it as "fine").

    workflow_info's created_at/updated_at are used ONLY when there is no last_run at all — the
    "too new to have fired yet" case. An earlier version of this function folded them into the
    baseline unconditionally (max of everything), which meant an unrelated same-day edit to a
    workflow file (a comment tweak, anything) bumps updated_at and silently RESETS the staleness
    clock even while the schedule itself has been dead for weeks — masking exactly the failure
    mode this function exists to catch, and worst on refresh-token.yml, the one entry whose own
    label calls it the most dangerous to miss. Caught by a reverse test in test_cron_health.py:
    a stale last_run plus a fresh updated_at must still alert."""
    if last_run:
        baseline = _parse(last_run["created_at"])
    else:
        candidates = [workflow_info.get(k) for k in ("created_at", "updated_at")] \
            if workflow_info else []
        candidates = [c for c in candidates if c]
        if not candidates:
            return None, "판정 불가 — created_at 을 읽을 수 없습니다"
        baseline = max(_parse(c) for c in candidates)
    gap_h = (now - baseline).total_seconds() / 3600
    if gap_h > entry["max_gap_h"]:
        return False, (f"{gap_h:.0f}시간째 스케줄 실행이 없습니다 "
                        f"(한계 {entry['max_gap_h']}시간)")
    if last_run and last_run.get("conclusion") not in OK_CONCLUSIONS:
        return False, (f"가장 최근 스케줄 실행이 실패했습니다 ({last_run.get('conclusion')}) "
                        f"— {last_run.get('html_url', '(링크 없음)')}")
    return True, None


def fetch_and_evaluate(entry, repo, token, now=None):
    """Network wrapper around evaluate(). Never raises — a monitor that crashes on a bad API
    response goes silent exactly when something is already wrong, which is worse than one check
    quietly reporting 'cannot judge' while the rest keep working."""
    now = now or datetime.now(timezone.utc)
    try:
        info = _gh(f"/repos/{repo}/actions/workflows/{entry['file']}", token)
        runs = _gh(f"/repos/{repo}/actions/workflows/{entry['file']}/runs"
                   f"?event=schedule&per_page=1", token)
    except Exception as e:
        print(f"cron_health: {entry['file']} unreachable — {e}")
        return None, f"조회 실패 ({e})"
    last_run = (runs.get("workflow_runs") or [None])[0]
    return evaluate(entry, info, last_run, now)


def findings(repo=None, token=None, now=None, watchlist=None):
    """[(key, message)] in the same shape watch.py's own findings() returns, so main() there can
    fold this straight into its existing send/cooldown/clear machinery without a second path."""
    repo = repo or os.environ.get("GITHUB_REPOSITORY")
    token = token or os.environ.get("GITHUB_TOKEN")
    out = []
    if not repo or not token:
        print("cron_health: GITHUB_REPOSITORY / GITHUB_TOKEN not set — skipping")
        return out
    watchlist = watchlist if watchlist is not None else WATCHLIST
    results = [(entry, fetch_and_evaluate(entry, repo, token, now)) for entry in watchlist]
    # evaluate()'s docstring promises ok=None is "reported separately, never read as fine" — this
    # is that separate report. Every entry failing to even be judged, all at once, is itself a
    # strong signal (a broken GITHUB_TOKEN scope or a renamed repo breaks ALL of them identically,
    # not one at a time), so it fires on the first run, the same way a single publish failure is
    # trusted immediately elsewhere in this file — waiting for N consecutive runs would mean days
    # of this watchdog being silently blind before anyone heard about it.
    if results and all(ok is None for _, (ok, _) in results):
        out.append(("cron-health-unreachable",
                    "⚠️ cron_health 가 워크플로를 하나도 판정하지 못했습니다 (GitHub API 접근 실패)\n"
                    "watch.yml의 GITHUB_TOKEN 권한(actions: read)과 GITHUB_REPOSITORY 를 확인하세요"))
        return out
    for entry, (ok, detail) in results:
        if ok is False:
            out.append((f"cron-{entry['file']}",
                        f"⚠️ {entry['label']} 가 멈췄을 수 있습니다 — {detail}\n"
                        f".github/workflows/{entry['file']} 의 Actions 로그를 확인하세요"))
    return out


if __name__ == "__main__":
    results = findings()
    for key, message in results:
        print(f"{key}: {message}")
    if not results:
        print("cron_health: all scheduled workflows look alive")
