#!/usr/bin/env python3
"""Check that every workflow step passes the environment its code actually reads.

This is the single most expensive bug class in this repo, because it fails SILENTLY. Code that
reads a missing token gets None, the API returns "Cannot parse access token", a broad except
catches it, the guard falls back — and the log says nothing useful. The duplicate guards in
daily_post.py and carousel_post.py were both dead this way for their entire lives, so the
protection I kept reporting as working had never once run.

An AST walk collects every os.environ key a module reads, transitively through its imports, and
compares that against the env the workflow step provides. Run from check_rules.py.
"""
import ast, os, re, sys, pathlib, yaml
HERE = pathlib.Path(".")
MODS = {p.stem: p for p in HERE.glob("*.py")}

def reads(mod, seen=None):
    """이 모듈이 (임포트 포함) 읽는 os.environ 키 전부."""
    seen = seen if seen is not None else set()
    if mod in seen or mod not in MODS: return set()
    seen.add(mod)
    tree = ast.parse(MODS[mod].read_text())
    keys, imports = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in ("get", "__getitem__"):
                v = f.value
                if isinstance(v, ast.Attribute) and v.attr == "environ":
                    if n.args and isinstance(n.args[0], ast.Constant): keys.add(n.args[0].value)
        if isinstance(n, ast.Subscript):
            v = n.value
            if isinstance(v, ast.Attribute) and v.attr == "environ":
                s = n.slice
                if isinstance(s, ast.Constant): keys.add(s.value)
        if isinstance(n, ast.Import):
            for a in n.names: imports.add(a.name.split(".")[0])
        if isinstance(n, ast.ImportFrom) and n.module:
            imports.add(n.module.split(".")[0])
    for i in imports: keys |= reads(i, seen)
    return keys

# Genuinely optional, with a working fallback in the code — not a missing configuration.
ALLOWED = {
    ("comment-reply.yml", "IG_USERNAME"),      # falls back to the API, then to cached state
}

problems = []
for wf in sorted(HERE.glob(".github/workflows/*.yml")):
    d = yaml.safe_load(wf.read_text())
    for job in (d.get("jobs") or {}).values():
        for step in job.get("steps", []):
            run = step.get("run") or ""
            given = set((step.get("env") or {}) | (job.get("env") or {}) | (d.get("env") or {}))
            # Only what the step actually EXECUTES — `python x.py` at the start of a line or after
            # a shell separator. Matching anywhere caught filenames quoted inside issue bodies.
            for m in re.findall(r"(?:^|[|&;]\s*|\n\s*)python3?\s+(?:-m\s+)?([a-z_]+)\.py", run):
                need = reads(m)
                missing = {k for k in need if k not in given and k.startswith(("IG_","GEMINI","HF_","PEXELS","TELEGRAM","GH_"))}
                missing -= {k for k in missing if (wf.name, k) in ALLOWED}
                if missing:
                    problems.append((wf.name, (step.get("name") or "?")[:38], m, sorted(missing)))
print(f"{'워크플로':22}{'단계':40}{'실행':16}빠진 env")
for w,s,m,miss in problems:
    print(f"{w:22}{s:40}{m+'.py':16}{', '.join(miss)}")
print(f"\n총 {len(problems)}건")
raise SystemExit(1 if problems else 0)
