#!/usr/bin/env python3
"""The one command that answers "does the whole thing still work, and what would it actually post."

RULES.md G says `verify.sh` is "이거 하나" — but verify.sh only answers "do the tests and rule
audit pass". It compiles the code, checks cross-references, and runs the unit tests. It has
NEVER ONCE run daily_post.py end to end, so a bug that only shows up when fetch_image /
fetch_motion / fetch_lyria / generate / make_video actually run TOGETHER against a live API can
sit behind a fully green verify.sh indefinitely. Two production bugs are proof: the carousel
centering bug (text_w measured tracked, d.text drew untracked — both functions were individually
correct, so no unit test ever exercised the mismatch) and the weekly carousel eating the Sunday
reel slot (nine green CI runs in a row, the reel just never got built). Both were only found by
looking at the actual picture that shipped.

2026-11-10, the owner: "diff만 보면 안되고 전체 구조도 봐야하고, 전체 돌려도봐야하고, 결과물도
뽑아봐야하고, 지금은 규칙적으로 그게 안되는데 관장하는 부분이 있어야할거같아." This is that part.
It exists because the alternative — backing up the ledgers by hand, running daily_post.py --now
--emit, eyeballing the output, restoring the ledgers by hand — was done ad hoc every few sessions
(see CLAUDE.md 2026-11-09 "전체 다 돌려보고") and once the by-hand backup silently failed (a /tmp
write blocked by the sandbox) and nobody noticed until the next git diff caught it. A script that
does the same three steps every time, and REFUSES to proceed if the backup or the restore does not
verify byte-for-byte, cannot have that near-miss.

This is deliberately NOT wired into control_center.py (RULES.md J-1's "새 진단 스크립트는 여기에도
엮는다"). control_center is read-only and cheap to run often; `--run` here makes real, billed API
calls (Gemini image + motion + Lyria) and takes minutes. Folding it into the passive dashboard
would make "glance at control_center" occasionally cost real money and real wall-clock time
without anyone choosing that — the opposite of what J-1 is for. It is its own command instead.

Usage:
    python3 qa_gate.py                  # tests + rule audit only (free, ~1 min)
    python3 qa_gate.py --run            # + a REAL end-to-end dry run (costs real money,
                                         # several minutes): builds the actual reel that would
                                         # have been posted and leaves it where you can look at it
    python3 qa_gate.py --run --hour 19  # build as the evening slot (affects nothing but the theme)

What --run does NOT do: publish. It calls daily_post.py --now --emit, which returns before the
publish branch (see daily_post.py's own comment at that line). It DOES consume a verse and
advance the scene/music/post rotation counters in state.json — that is the whole point, the real
rotation logic has to run — which is exactly why the ledgers are backed up first and restored
after, and why both of those are verified rather than assumed.
"""
import argparse
import filecmp
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).parent

# Every JSON ledger a pipeline run can mutate. Not just state.json — metrics.record() and the
# story/comment bookkeeping touch several of these too, and a dry run must restore ALL of them,
# not just the one everyone remembers. Kept as a plain list (not re-derived from git ls-files)
# so adding a new ledger is a one-line, visible decision — see check_rules.py's K-1 check, which
# asserts this list still covers every *.json file save_ledger.sh is ever invoked with.
LEDGERS = [
    "state.json", "metrics.json", "comments.json", "account.json",
    "followers.json", "metrics_deleted.json", "reference_study.json",
    "api_support.json", "watch.json",
]

# Files a real run writes under output/ that are worth looking at, not just trusting. Named
# explicitly (not globbed) so a renamed artifact fails loudly here instead of silently vanishing
# from the inspection folder.
ARTIFACTS = ["_bg.png", "_overlay.png", "_meta.json", "_caption.txt", "_comment.txt", "_path.txt"]


class GateError(RuntimeError):
    """Raised when a safety invariant (backup/restore verified) does not hold. Never swallowed —
    see the module docstring: the whole point is refusing to proceed on an unverified backup."""


def backup_ledgers():
    """Copy every existing ledger to a fresh temp dir and verify EACH COPY byte-for-byte before
    trusting it. 2026-11-09's near-miss was a /tmp write that the sandbox silently dropped — the
    code that "backed up" never checked the copy actually landed. tempfile.mkdtemp() honours
    $TMPDIR, which the sandbox allows; the filecmp.cmp() call is what makes the difference between
    "we attempted a backup" and "we have a backup". If any single copy fails to verify, the whole
    temp dir is removed before raising — a half-written backup directory left behind is exactly
    the kind of silent debris this script exists to avoid leaving."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="qa_gate_"))
    saved = {}
    try:
        for name in LEDGERS:
            src = HERE / name
            if not src.exists():
                continue
            dst = tmp / name
            shutil.copy2(src, dst)
            if not filecmp.cmp(src, dst, shallow=False):
                raise GateError(
                    f"backup of {name} did not verify byte-for-byte — refusing to run "
                    f"the pipeline (this is exactly how 2026-11-09's near-miss happened)")
            saved[name] = dst
    except GateError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return tmp, saved


def restore_ledgers(saved):
    """Copy every backed-up ledger back and verify the restore too — a backup that verified but a
    restore that silently fails is the same hole, just on the other side of the run. Also removes
    any ledger the pipeline run created that did NOT exist before (not in `saved`) — a dry run
    must leave no trace, including files it brought into existence, not just files it edited."""
    problems = []
    for name, backup_path in saved.items():
        dst = HERE / name
        shutil.copy2(backup_path, dst)
        if not filecmp.cmp(backup_path, dst, shallow=False):
            problems.append(name)
    if problems:
        # The verified-good backup is deliberately NOT deleted on this path (main()'s rmtree
        # never runs if this raises) — point at it, don't just tell the caller to diff a working
        # tree that may itself now be inconsistent.
        backup_dir = next(iter(saved.values())).parent
        raise GateError(
            f"restore did not verify for: {problems} — ledgers may now be inconsistent. "
            f"The verified-good backup is still at {backup_dir} (not deleted on this failure "
            f"path) — restore from there by hand, then `git diff -- {' '.join(problems)}` "
            f"before touching anything else.")
    for name in LEDGERS:
        if name not in saved and (HERE / name).exists():
            (HERE / name).unlink()


# verify.sh's own PY resolution (its comment: "Pinned to match the workflows (H0-6)"), copied
# here on purpose rather than shared, because the two scripts have no common importable module to
# share it from without inventing one just for this. check_rules.py's H0-6 check compares this
# literal pin against verify.sh/checks.yml/daily-post.yml/weekly-carousel.yml, so a drift here is
# caught the same way a drift in any of those is.
def _py_prefix():
    import importlib.util
    mods = ("yaml", "kiwipiepy", "imageio_ffmpeg", "PIL", "numpy")
    if all(importlib.util.find_spec(m) for m in mods):
        return [sys.executable]
    if shutil.which("uv"):
        return ["uv", "run", "--quiet", "--with", "pyyaml", "--with", "kiwipiepy==0.24.1",
                "--with", "imageio-ffmpeg", "--with", "pillow", "--with", "numpy", "python"]
    return [sys.executable]   # best effort — verify.sh itself already failed loudly on this


def run_verify():
    """verify.sh: compiles, cross-references, rule audit, every test_*.py.

    verify.sh's own step() helper deliberately truncates a FAILING step's output to the lines
    matching FAIL/Error/assert (capped at 8) plus the last 3 lines — that truncation already
    happened to whatever verify.sh printed, before this function ever sees it, so re-printing
    verify.sh's stdout verbatim does NOT show "everything" for a failure. That gap is exactly what
    hid the Ubuntu font-metric failure for 19 days (CLAUDE.md 2026-11-09 밤 2) — the numbers that
    would have explained it were in the part step() discarded. So: print verify.sh's own output
    as-is, AND for every step it reports FAIL, rerun that exact command directly (same PY
    resolution verify.sh uses) and print its full, unfiltered output underneath."""
    r = subprocess.run(["bash", str(HERE / "verify.sh")], cwd=HERE, text=True,
                        capture_output=True)
    print(r.stdout)
    if r.stderr.strip():
        print(r.stderr, file=sys.stderr)

    failed_steps = re.findall(r"^FAIL\s+(\S+)$", r.stdout, re.MULTILINE)
    for name in failed_steps:
        if name == "compiles":
            cmd = ["-m", "compileall", "-q", "."]
        elif name.endswith(".py"):
            cmd = [name]
        else:
            continue   # "cross-references"/"rules" are prefixes of multi-word names, not real
        full = subprocess.run(_py_prefix() + cmd, cwd=HERE, text=True, capture_output=True)
        print(f"\n--- untruncated output for FAILED step {name!r} ---")
        print(full.stdout)
        if full.stderr.strip():
            print(full.stderr, file=sys.stderr)
    # The two multi-word step names ("cross-references resolve", "rules are enforced") verify.sh
    # prints are not single tokens — rerun them by name match against the known full line instead.
    for full_name, cmd in (("cross-references resolve", ["audit_refs.py"]),
                           ("rules are enforced", ["check_rules.py"])):
        if f"FAIL  {full_name}" in r.stdout:
            full = subprocess.run(_py_prefix() + cmd, cwd=HERE, text=True, capture_output=True)
            print(f"\n--- untruncated output for FAILED step {full_name!r} ---")
            print(full.stdout)
            if full.stderr.strip():
                print(full.stderr, file=sys.stderr)
    return r.returncode == 0


def run_pipeline(hour):
    """Actually run daily_post.py --now --emit. Real API calls, real cost, real artifacts.
    Returns (ok, meta_dict, full_log_text)."""
    r = subprocess.run(
        [sys.executable, str(HERE / "daily_post.py"), "--now", "--emit", "--hour", str(hour)],
        cwd=HERE, text=True, capture_output=True)
    log = r.stdout + "\n" + r.stderr
    ok = r.returncode == 0 and "Traceback (most recent call last)" not in r.stderr
    meta = {}
    meta_path = HERE / "output" / "_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return ok, meta, log


def collect_artifacts(dest_dir):
    """Copy the actual produced stills + the actual produced reel into dest_dir, so there is a
    fixed path to open and look at instead of trusting the log. Returns the list of what it
    actually found — an empty list here, after a claimed-ok run, is itself a finding."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for name in ARTIFACTS:
        src = HERE / "output" / name
        if src.exists():
            shutil.copy2(src, dest_dir / name)
            found.append(name)
    posts_dir = HERE / "output" / "posts"
    if posts_dir.exists():
        # the reel just built — newest .mp4, not a hardcoded date string
        mp4s = sorted(posts_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
        if mp4s:
            newest = mp4s[-1]
            shutil.copy2(newest, dest_dir / newest.name)
            found.append(newest.name)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true",
                     help="also run the full pipeline end-to-end (real API calls, real cost)")
    ap.add_argument("--hour", type=int, default=5, help="5=morning, 19=evening (affects theme only)")
    args = ap.parse_args()

    print("=== 1/2 tests + rule audit (verify.sh) ===")
    tests_ok = run_verify()

    if not args.run:
        print("(skipped the full pipeline run — pass --run to actually build and inspect a post)")
        print("\n" + ("PASS" if tests_ok else "FAIL") + " — tests/rules only, pipeline not run")
        return 0 if tests_ok else 1

    print("\n=== 2/2 full pipeline dry run (daily_post.py --now --emit) ===")
    print("backing up ledgers...")
    tmp, saved = backup_ledgers()
    print(f"  {len(saved)} ledger(s) backed up and verified: {sorted(saved)}")
    try:
        ok, meta, log = run_pipeline(args.hour)
    finally:
        print("restoring ledgers...")
        restore_ledgers(saved)
        print("  restored and verified")
        shutil.rmtree(tmp, ignore_errors=True)

    log_path = HERE / "output" / "qa_gate_last_run.log"
    log_path.write_text(log, encoding="utf-8")
    print(f"full run log: {log_path}")

    import time
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    dest_dir = HERE / "output" / "qa_gate" / stamp
    found = collect_artifacts(dest_dir)

    print(f"\n--- pipeline result: {'OK' if ok else 'FAILED — see log above/at ' + str(log_path)} ---")
    if meta:
        for k in ("ref", "segments", "veo_calls", "veo_seconds", "gate_passed", "gate_ran",
                   "gate_skipped", "image_model", "scene", "clip_spoiled", "motion"):
            if k in meta:
                print(f"  {k}: {meta[k]}")
    if found:
        print(f"\nartifacts to actually LOOK AT: {dest_dir}")
        for f in found:
            print(f"  {dest_dir / f}")
    else:
        print("\nNO ARTIFACTS FOUND — a run that claims ok with nothing produced is a finding, "
              "not a pass.")
        ok = False

    overall = tests_ok and ok and bool(found)
    print("\n" + ("PASS" if overall else "FAIL") +
          " — tests" + ("" if tests_ok else "(FAILED)") +
          " + pipeline" + ("" if ok else "(FAILED)") +
          " + artifacts" + ("" if found else "(MISSING)"))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
