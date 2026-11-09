#!/usr/bin/env python3
"""Tell the same Telegram channel watch.py uses that `checks.yml` just went red.

RULES.md J-2: a push CI failure used to be visible only on GitHub's own Actions page, because the
operational alert channel (watch.py) and this static-verification layer (verify.sh via checks.yml)
had never spoken to each other. Called as a dedicated step with `if: failure()`, not inlined as a
`python3 -c "..."` one-liner — an earlier version tried that and a folded YAML block scalar mixed
with ${{ }} expression substitution inside a Python string produced a leading-space IndentationError
that would only have shown up the day it actually needed to fire. A real file is testable; an
inline string spanning YAML folding rules is not.

Every value here is a GitHub-provided environment variable already present on any step — no
${{ }} expression needed, so there is nothing for YAML's templating and Python's string quoting to
collide over.
"""
import os


def message():
    repo = os.environ.get("GITHUB_REPOSITORY", "?")
    sha = os.environ.get("GITHUB_SHA", "?")[:12]
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID", "?")
    return (f"🔴 검증 실패 (checks.yml) — {repo}@{sha}\n"
            f"{server}/{repo}/actions/runs/{run_id}")


def main():
    import notify
    ok = notify.send(message())
    print("telegram: sent" if ok else "telegram: NOT sent")
    return 0          # best-effort — a failed alert must not fail this already-failing job harder


if __name__ == "__main__":
    raise SystemExit(main())
