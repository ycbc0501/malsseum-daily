#!/usr/bin/env python3
"""Every module attribute referenced across files must actually exist.

Three times in one day I deleted a constant while editing the file around it — NOTEXT, COMPOSE and
CALMER — and each time the code still compiled, because Python resolves `module.NAME` at runtime.
Two of the three reached a commit. compileall cannot see this class of break; only something that
walks the references can.
"""
import ast
import importlib
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
SKIP = ("sync-conflict", "audit_refs")
LOCAL = {p.stem for p in HERE.glob("*.py") if not any(s in p.name for s in SKIP)}


def references():
    """(file, line, module, attribute) for every `module.ATTR` where module is one of ours."""
    for path in sorted(HERE.glob("*.py")):
        if any(s in path.name for s in SKIP):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as e:
            yield path.name, e.lineno, "<syntax>", str(e)
            continue
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in LOCAL:
                        aliases[a.asname or a.name] = a.name
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                mod = aliases.get(node.value.id)
                if mod and mod != path.stem:
                    yield path.name, node.lineno, mod, node.attr


def shadowed_imports():
    """(file, function, use line, import line, module) where a function uses a module BEFORE
    importing it locally.

    Python binds a name for the WHOLE function body, so an `import x` anywhere inside makes
    every earlier `x.attr` an UnboundLocalError — even when `x` is imported at module level and
    the code reads perfectly. This is invisible to compileall and to the reference check above:
    the attribute exists, the module imports, the file compiles. Only running that exact line
    finds it.

    It cost four consecutive posts on 2026-09-18/19: daily_post.main() imported fetch_higgsfield
    ninety lines below its first use, so every run built the whole reel — image, Veo, music —
    and then died before publishing."""
    for path in sorted(HERE.glob("*.py")):
        if any(s in path.name for s in SKIP):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef,
                                                               ast.AsyncFunctionDef))):
            bound = {}                       # name → line of the local import that binds it
            for node in ast.walk(fn):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for a in node.names:
                        bound.setdefault(a.asname or a.name.split(".")[0], node.lineno)
            if not bound:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    at = bound.get(node.id)
                    if at and node.lineno < at:
                        yield path.name, fn.name, node.lineno, at, node.id


def main():
    missing = []
    for file, fn, used, imported, name in shadowed_imports():
        missing.append((file, used,
                        f"{fn}() uses {name} at line {used} but imports it at line {imported} "
                        f"— the local import makes it UnboundLocalError"))
    for file, line, mod, attr in references():
        if mod == "<syntax>":
            missing.append((file, line, attr))
            continue
        try:
            m = importlib.import_module(mod)
        except Exception as e:
            missing.append((file, line, f"cannot import {mod}: {e}"))
            continue
        if not hasattr(m, attr):
            missing.append((file, line, f"{mod}.{attr} does not exist"))
    for f, l, why in missing:
        print(f"  {f}:{l}  {why}")
    print(f"\n교차 참조 {'전부 유효 ✅' if not missing else f'{len(missing)}건 깨짐 ❌'}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
