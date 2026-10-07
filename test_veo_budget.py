#!/usr/bin/env python3
"""The Veo bill must have a CEILING, and the ceiling must fit the monthly cap.

This is the test that would have caught the thing nobody caught for six weeks. Between
2026-09-23 and 2026-10-06 the pipeline bought 1,008 billed Veo seconds and shipped 376 of
them — 62.7% of the money was thrown away — and the posts that retried MOST shipped the
SHORTEST reels (6 calls → one 7.7s segment, in 12 of 25 posts). Nothing failed. Every gate
behaved exactly as written. The cost simply had no upper bound that anyone had computed:
VEO_TRIES=3 on the opening plus VEO_TRIES=3 on each of two continuations is NINE calls, and
nine calls is 72 billed seconds, and 72 seconds twice a day is ₩597,000 a month against a
₩260,000 cap.

So this file does not test that the code runs. It tests the ARITHMETIC OF THE WORST CASE,
read out of the shipped source, against RULES.md E-0b/E-0c. A future change that reopens the
leak — raising CHAIN_TRIES, dropping the chain_ok gate, adding a fourth segment — fails here
with the monthly figure printed next to the cap, in won.

    python3 test_veo_budget.py
"""

import pathlib
import re

import daily_post

SRC = pathlib.Path(__file__).with_name("daily_post.py").read_text()

# RULES.md E-0b. Veo is ~80% of spend; the rest (images, vision gates, Lyria) measured ~₩60,000.
MONTHLY_CAP_WON = 260_000
NON_VEO_WON = 60_000
VEO_BUDGET_WON = MONTHLY_CAP_WON - NON_VEO_WON
POSTS_PER_DAY = 2
SECONDS_PER_CALL = 8.0
# Derived from the September invoice, same constant metrics.py prices the ledger with.
WON_PER_SECOND = 193659 / 1400

bad = 0


def fails(msg):
    print(f"  FAIL  {msg}")
    return 1


def const(name):
    """Read a retry ceiling out of the shipped source.

    VEO_TRIES and CHAIN_TRIES are locals inside run(), so they cannot be imported. Reading them
    from the text is the point: the test must see what the file actually says, not a copy of it
    kept in sync by hand — a copy is how the old comment claiming "one take" survived next to a
    loop that took three.
    """
    m = re.search(rf"^\s*{name} = (\d+)$", SRC, re.M)
    if not m:
        raise AssertionError(f"{name} is not a plain integer constant in daily_post.py any more")
    return int(m.group(1))


VEO_TRIES = const("VEO_TRIES")
CHAIN_TRIES = const("CHAIN_TRIES")
SEGMENTS = daily_post.SEGMENTS

# ── 1. The chain gate is the shipped expression, not a paraphrase of it ──────────────────────
# Evaluate the ACTUAL range() bound from the source under both branches. If someone deletes the
# chain_ok gate, this stops finding the expression and the test fails rather than quietly
# passing on a copy that still has it.
m = re.search(r"for seg in range\(2, (.+?)\):", SRC)
if not m:
    bad += fails("the continuation loop bound is no longer a readable range() expression")
else:
    expr = m.group(1)
    env = {"SEGMENTS": SEGMENTS}
    missed = list(range(2, eval(expr, {}, dict(env, chain_ok=False))))
    clean = list(range(2, eval(expr, {}, dict(env, chain_ok=True))))
    if missed:
        bad += fails(f"E-0c: an opening that missed still chains {len(missed)} segment(s) — "
                     f"the continuations would be built from a scene Veo already failed")
    if len(clean) != SEGMENTS - 1:
        bad += fails(f"a clean opening chains {len(clean)} segment(s), expected {SEGMENTS - 1}")
    print(f"1. chain gate: clean opening → {len(clean)} continuation(s), "
          f"opening that missed → {len(missed)}")

if "chain_ok = (motion_attempts == 1 and not spoiled)" not in SRC:
    bad += fails("E-0c: the gate no longer requires the opening to pass on the FIRST take")

# ── 2. Worst case per post, in calls ─────────────────────────────────────────────────────────
# Two mutually exclusive branches, because the gate makes them exclusive:
#   (a) the opening misses → up to VEO_TRIES calls and NO chain
#   (b) the opening is clean first try → 1 call plus CHAIN_TRIES per continuation
worst_calls = max(VEO_TRIES, 1 + (SEGMENTS - 1) * CHAIN_TRIES)
worst_seconds = worst_calls * SECONDS_PER_CALL
worst_month = worst_seconds * WON_PER_SECOND * POSTS_PER_DAY * 30
print(f"2. worst case: {worst_calls} calls = {worst_seconds:.0f}s/post "
      f"→ ₩{worst_month:,.0f}/month at {POSTS_PER_DAY}/day   (Veo budget ₩{VEO_BUDGET_WON:,})")
if worst_month > VEO_BUDGET_WON:
    bad += fails(f"E-0b: the WORST case costs ₩{worst_month:,.0f}/month, over the ₩"
                 f"{VEO_BUDGET_WON:,} Veo budget. Lower SEGMENTS, VEO_TRIES or CHAIN_TRIES, "
                 f"or cut the posting frequency — do not just hope the worst case is rare.")

# The regression this file exists for: the pre-2026-10-07 shape had no gate and retried
# continuations, so its worst case was VEO_TRIES on every segment.
old_worst = VEO_TRIES * SEGMENTS * SECONDS_PER_CALL * WON_PER_SECOND * POSTS_PER_DAY * 30
print(f"3. the shape this replaced: {VEO_TRIES * SEGMENTS} calls = ₩{old_worst:,.0f}/month "
      f"({old_worst / worst_month:.1f}x) — unbounded in practice, which is what happened")

# ── 3. A continuation gets one take ──────────────────────────────────────────────────────────
if CHAIN_TRIES != 1:
    bad += fails(f"E-0c: CHAIN_TRIES is {CHAIN_TRIES}. A continuation that misses its one take "
                 f"stops the chain; buying more takes of a drifting scene never rescued it in "
                 f"the 25 posts measured.")

# ── 4. The per-segment ledger, so the next cost question is read and not reconstructed ───────
if '"veo_attempts"' not in SRC or "veo_attempts.append" not in SRC:
    bad += fails("E-0d: takes per segment are not recorded — the saving above had to be "
                 "reconstructed from totals once already, and was an estimate because of it")

# ── 5. What the ledger says we are actually paying now ───────────────────────────────────────
# Not a pass/fail: the ceiling is enforced above, this is the measured reality next to it.
try:
    import metrics
    rows = [e for e in metrics.load().values() if e.get("veo_seconds")]
    if rows:
        recent = sorted(rows, key=lambda e: e.get("published_at") or "")[-25:]
        avg = sum(e["veo_seconds"] for e in recent) / len(recent)
        print(f"4. measured: last {len(recent)} post(s) averaged {avg:.1f}s "
              f"→ ₩{avg * WON_PER_SECOND * POSTS_PER_DAY * 30:,.0f}/month at this rate "
              f"(ceiling above is {worst_seconds:.0f}s)")
except Exception as e:
    print(f"4. measured: ledger unavailable ({e})")

print()
print("all veo-budget checks passed" if not bad else f"{bad} CHECK(S) FAILED")
raise SystemExit(1 if bad else 0)
