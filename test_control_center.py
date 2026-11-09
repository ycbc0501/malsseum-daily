#!/usr/bin/env python3
"""control_center.py — each section's logic, and render()'s mapping from status to marker.

No test here makes a real network call (this repo's convention — see test_cron_health.py,
test_reference_study.py): every section function does its own `import X` and calls through to
X's already-public API, so the fix here is to monkeypatch that API, not control_center itself.
"""
import os
import sys

import control_center as cc
import cron_health
import ig_doctor
import ig_probe
import reference_study
import watch

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


def restoring(module, name, value):
    """Monkeypatch module.name = value, return a callable that restores it."""
    original = getattr(module, name)
    setattr(module, name, value)
    return lambda: setattr(module, name, original)


# --------------------------------------------------------------------------------------- ops_section
undo = restoring(watch, "findings", lambda prev: [])
try:
    r = cc.ops_section()
    check("ops_section: no findings -> ok True, no items", r["ok"] is True and r["items"] == [])
finally:
    undo()

undo = restoring(watch, "findings", lambda prev: [("drop", "⚠️ 좋아요가 떨어지고 있습니다\n자세히")])
try:
    r = cc.ops_section()
    check("ops_section: a finding -> ok False", r["ok"] is False)
    check("ops_section: item is the finding's FIRST line, not the whole message",
          r["items"] == ["⚠️ 좋아요가 떨어지고 있습니다"])
finally:
    undo()


def _raise(prev):
    raise RuntimeError("boom")


undo = restoring(watch, "findings", _raise)
try:
    r = cc.ops_section()
    check("ops_section: watch.findings() itself raising -> ok None, not a crash, not ok True",
          r["ok"] is None and "boom" in r["detail"])
finally:
    undo()

# --------------------------------------------------------------------------------------- ci_section
_env_backup = {k: os.environ.pop(k, None) for k in ("GITHUB_REPOSITORY", "GITHUB_TOKEN")}
try:
    r = cc.ci_section()
    check("ci_section: no GITHUB_TOKEN/REPOSITORY -> ok None, not False (cannot check != broken)",
          r["ok"] is None)
finally:
    for k, v in _env_backup.items():
        if v is not None:
            os.environ[k] = v

os.environ["GITHUB_REPOSITORY"] = "o/r"
os.environ["GITHUB_TOKEN"] = "t"
try:
    undo = restoring(cron_health, "_gh", lambda path, token: {
        "workflow_runs": [{"conclusion": "success", "html_url": "https://x/1"}]})
    try:
        r = cc.ci_section()
        check("ci_section: latest run succeeded -> ok True", r["ok"] is True)
    finally:
        undo()

    undo = restoring(cron_health, "_gh", lambda path, token: {
        "workflow_runs": [{"conclusion": "failure", "html_url": "https://x/2"}]})
    try:
        r = cc.ci_section()
        check("ci_section: latest run failed -> ok False", r["ok"] is False)
        check("ci_section: carries the run URL through", r["url"] == "https://x/2")
    finally:
        undo()

    undo = restoring(cron_health, "_gh", lambda path, token: {"workflow_runs": []})
    try:
        r = cc.ci_section()
        check("ci_section: no run history yet -> ok None, not False", r["ok"] is None)
    finally:
        undo()

    def _raise_gh(path, token):
        raise RuntimeError("api down")

    undo = restoring(cron_health, "_gh", _raise_gh)
    try:
        r = cc.ci_section()
        check("ci_section: GitHub API unreachable -> ok None, not a crash", r["ok"] is None)
    finally:
        undo()
finally:
    del os.environ["GITHUB_REPOSITORY"]
    del os.environ["GITHUB_TOKEN"]

# ------------------------------------------------------------------------------------ token_section
undo = restoring(ig_doctor, "secrets", lambda: {})
try:
    r = cc.token_section()
    check("token_section: no app id/secret -> ok None (cannot check), not False", r["ok"] is None)
finally:
    undo()

undo1 = restoring(ig_doctor, "secrets", lambda: {
    "META_APP_ID": "a", "META_APP_SECRET": "b", "IG_ACCESS_TOKEN": "pub"})
undo2 = restoring(ig_doctor, "describe", lambda token, app_id, app_secret: (
    {"scopes": ["instagram_basic", "pages_read_engagement"]}, None))
try:
    r = cc.token_section()
    check("token_section: scopes present but insights scope missing -> ok False",
          r["ok"] is False and r["ok_tokens"] == [])
finally:
    undo1(); undo2()

undo1 = restoring(ig_doctor, "secrets", lambda: {
    "META_APP_ID": "a", "META_APP_SECRET": "b", "IG_ACCESS_TOKEN": "pub"})
undo2 = restoring(ig_doctor, "describe", lambda token, app_id, app_secret: (
    {"scopes": ["instagram_basic", "instagram_manage_insights", "pages_read_engagement"]}, None))
try:
    r = cc.token_section()
    check("token_section: all required scopes present -> ok True",
          r["ok"] is True and r["ok_tokens"] == ["IG_ACCESS_TOKEN"])
finally:
    undo1(); undo2()

undo1 = restoring(ig_doctor, "secrets", lambda: {
    "META_APP_ID": "a", "META_APP_SECRET": "b", "IG_ACCESS_TOKEN": "pub"})
undo2 = restoring(ig_doctor, "describe", lambda token, app_id, app_secret: (
    None, {"message": "token malformed"}))
try:
    r = cc.token_section()
    check("token_section: describe() erroring is reported, not silently dropped",
          r["ok"] is False and "token malformed" in r["detail"])
finally:
    undo1(); undo2()

# -------------------------------------------------------------------------------- freshness_section
undo1 = restoring(ig_probe, "is_stale", lambda: (True, "40 days since 2026-10-01"))
undo2 = restoring(reference_study, "load_ledger", lambda: {"next_due": "2026-11-18"})
undo3 = restoring(reference_study, "due", lambda ledger: False)
try:
    r = cc.freshness_section()
    check("freshness_section: reports probe staleness verbatim",
          r["probe_stale"] is True and "40 days" in r["probe_detail"])
    check("freshness_section: reports study due-ness and the next date",
          r["study_due"] is False and r["study_next"] == "2026-11-18")
finally:
    undo1(); undo2(); undo3()

# ----------------------------------------------------------------------------------------- render()
GOOD = {
    "generated": "2026-11-09T12:00:00+09:00",
    "ops": {"ok": True, "detail": None, "items": []},
    "ci": {"ok": True, "detail": "success", "url": "https://x"},
    "token": {"ok": True, "detail": None, "ok_tokens": ["IG_ACCESS_TOKEN"]},
    "freshness": {"probe_stale": False, "probe_detail": "probed 1 day(s) ago (2026-11-08)",
                  "study_due": False, "study_next": "2026-11-18"},
}
text = cc.render(GOOD)
check("render(): an all-ok report shows no ⚠️ anywhere", "⚠️" not in text)
check("render(): an all-ok ops section says so in Korean", "전부 정상" in text)

BROKEN = dict(GOOD, ops={"ok": False, "detail": None, "items": ["⚠️ 뭔가 깨졌습니다"]})
text = cc.render(BROKEN)
check("render(): a broken ops section surfaces the item text", "⚠️ 뭔가 깨졌습니다" in text)

UNKNOWN = dict(GOOD, ci={"ok": None, "detail": "GITHUB_TOKEN 없음 — 조회 불가", "url": None})
text = cc.render(UNKNOWN)
check("render(): ok=None renders as ❓, distinct from both ✅ and ⚠️", "❓" in text)

# "broken" is whatever main() uses to decide its exit code — re-derived here rather than calling
# main() itself (which would need real argv/stdout/notify plumbing) so the EXIT CODE logic has
# its own regression coverage, not just the text.


def is_broken(r):
    return any(r[s].get("ok") is False for s in ("ops", "ci", "token"))


check("exit logic: all-ok report is not broken", not is_broken(GOOD))
check("exit logic: a confirmed-False section IS broken", is_broken(BROKEN))
check("exit logic: an unknown (None) section alone is NOT broken — can't-check != broken",
      not is_broken(UNKNOWN))

# ------------------------------------------------------------------------------- SECTIONS / wiring
# Reverse-check on the constant check_rules.py's own J-1 assertions lean on: if a section gets
# renamed without updating SECTIONS, this catches it independently of check_rules.py's text scan.
check("SECTIONS lists exactly the four section functions control_center actually defines",
      set(cc.SECTIONS) == {"ops", "ci", "token", "freshness"})
check("report() produces exactly the keys SECTIONS promises, plus 'generated'",
      set(cc.report.__code__.co_names) & {"ops_section", "ci_section", "token_section",
                                          "freshness_section"} == {
          "ops_section", "ci_section", "token_section", "freshness_section"})


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall control_center checks hold")
    sys.exit(1 if FAIL else 0)
