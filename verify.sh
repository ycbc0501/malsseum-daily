#!/usr/bin/env bash
# The ONE thing to run. CI runs exactly this, so "did I check everything" has one answer.
#
# It exists because the checks kept being written and then not wired in: five tests in the repo
# and CI ran one of them, three audits and CI ran one. One of the unrun tests had been broken for
# days. Everything here is discovered by glob, so a new test or audit is picked up without anyone
# remembering to add it anywhere.
set -uo pipefail
cd "$(dirname "$0")"

# audit_env.py parses the workflows, so pyyaml is required. Without it the audit reports
# CANNOT VERIFY and this script fails — deliberately. "I could not check" is not "it is fine".
# audit_env.py parses the workflows, so it needs a YAML parser. Prefer a python that has one:
# uv can supply it without touching the system install. CI installs it directly.
PY=python3
if ! $PY -c "import yaml" 2>/dev/null; then
  if command -v uv >/dev/null 2>&1; then
    PY="uv run --quiet --with pyyaml python"
  else
    echo "FAIL  no YAML parser — run: pip install pyyaml  (the workflow audit cannot run without it)"
    exit 1
  fi
fi
fail=0
step() {                       # step <name> <command...>
  local name="$1"; shift
  if out=$("$@" 2>&1); then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    # Show the lines that FAILED, not the tail — a passing tail hides the reason above it.
    { echo "$out" | grep -E "FAIL|CANNOT VERIFY|Error|error:|Traceback|assert" | head -8
      echo "$out" | tail -3; } | sed 's/^/        /'
    fail=1
  fi
}

step "compiles" $PY -m compileall -q .
step "cross-references resolve" $PY audit_refs.py
step "rules are enforced" $PY check_rules.py     # runs audit_env.py itself

for t in test_*.py; do
  [ -e "$t" ] || continue
  step "$t" $PY "$t"
done

echo
if [ "$fail" -eq 0 ]; then echo "everything holds"; else echo "SOMETHING IS BROKEN"; fi
exit $fail
