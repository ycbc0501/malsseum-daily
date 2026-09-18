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


def main():
    missing = []
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
