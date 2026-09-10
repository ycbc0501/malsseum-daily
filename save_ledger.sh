#!/usr/bin/env bash
# Commit and push machine-written JSON ledgers, without losing them to a concurrent bot.
#
# `git pull --rebase --autostash || true` followed by `git push` is what lost the ledger on
# 2026-08-26: these files are single-line JSON written by several workflows at once, git conflicts
# on that one line, `|| true` swallows the conflict, the repo is left mid-rebase and the push dies.
# The post had already published. The next run read a stale ledger and re-posted the same verse,
# and the account was reach-restricted for duplicate content.
#
# Usage: save_ledger.sh "commit message" file.json [file.json ...]
set -uo pipefail

MSG="$1"; shift
FILES=("$@")

git config user.name "malsseum-bot"
git config user.email "malsseum-bot@users.noreply.github.com"

# Keep our versions aside — a reset would otherwise discard the very thing we are saving.
for f in "${FILES[@]}"; do
  [ -f "$f" ] && cp "$f" "/tmp/ours-$(basename "$f")"
done

for attempt in 1 2 3 4 5; do
  git rebase --abort 2>/dev/null || true
  # If we cannot reach the remote or cannot land on it, STOP. Carrying on would merge our
  # ledger onto an unknown base and then report success — the silent-degradation habit this
  # whole audit exists to remove.
  if ! git fetch origin main; then
    echo "::error::cannot fetch origin/main — not touching the ledger"
    exit 1
  fi
  if ! git reset --hard origin/main; then
    echo "::error::cannot reset onto origin/main — not touching the ledger"
    exit 1
  fi

  for f in "${FILES[@]}"; do
    mine="/tmp/ours-$(basename "$f")"
    # Semantic merge, not textual: dict union, list union, counters take max.
    [ -f "$mine" ] && python3 ledger_merge.py "$mine" "$f" "$f"
  done

  git add "${FILES[@]}" 2>/dev/null || true
  if git diff --cached --quiet; then
    echo "nothing to commit"
    exit 0
  fi
  git commit -m "$MSG"
  if git push; then
    echo "ledger saved (attempt $attempt)"
    exit 0
  fi
  echo "push rejected — remote moved, merging again"
  sleep $((attempt * 5))
done

echo "::error::ledger could not be saved after 5 attempts"
exit 1
