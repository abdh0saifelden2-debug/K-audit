#!/usr/bin/env python3
"""Verify an extracted repo has no imports reaching back into the monorepo.

Method: build the set of top-level module names that exist anywhere in the
source monorepo (directories with __init__.py, and root-level .py files).
For every import in the target repo, if the top-level name is an internal
name but is NOT resolvable from the repo root -> EDGE (leak).

Usage:
    python3 verify_repo.py --mono /path/to/K <split-repo>

Exit code 1 if any EDGE (this is the acceptance gate).
"""
import argparse
import ast
import os
import sys
from pathlib import Path

SKIP = ("__pycache__", ".venv", "venv", ".git", "node_modules", ".pytest_cache")


def internal_names(mono: Path) -> set:
    """Top-level module/package names that exist somewhere in the monorepo."""
    names = set()
    for p in mono.rglob("*"):
        if any(s in p.parts for s in SKIP):
            continue
        if p.is_dir() and (p / "__init__.py").exists():
            names.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            names.add(p.stem)
    return names


def local_names(root: Path) -> set:
    """Every name resolvable from anywhere in the repo (tests use sys.path
    inserts into subfolders, so root-level-only checking gives false leaks)."""
    names = set()
    for p in root.rglob("*"):
        if any(s in p.parts for s in SKIP):
            continue
        if p.is_dir() and ((p / "__init__.py").exists() or any(p.glob("*.py"))):
            names.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            names.add(p.stem)
    return names


def imports_of(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.append((0, a.name.split(".")[0], path))
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                continue  # relative -> local
            if n.module:
                out.append((0, n.module.split(".")[0], path))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mono", default=os.environ.get("K_MONO", "K"),
                    help="path to the pristine K monorepo clone "
                         "(default: $K_MONO or ./K)")
    ap.add_argument("repo", help="path to the split repo to verify")
    args = ap.parse_args()

    mono = Path(args.mono)
    if not mono.is_dir():
        sys.exit(f"monorepo not found: {mono} (pass --mono /path/to/K)")
    root = Path(args.repo)
    if not root.is_dir():
        sys.exit(f"repo not found: {root}")

    internal = internal_names(mono)
    local = local_names(root)
    edges = []
    for f in sorted(root.rglob("*.py")):
        if any(s in f.parts for s in SKIP):
            continue
        for _lvl, top, path in imports_of(f):
            if top in internal and top not in local:
                edges.append((str(f.relative_to(root)), top))
    if edges:
        print(f"EDGES in {root}: {len(edges)}")
        for f, t in sorted(set(edges)):
            print(f"  {f}  ->  {t}")
        sys.exit(1)
    print(f"OK {root}: no external edges "
          f"(local_pkgs={sorted(p for p in local if p in internal)})")


if __name__ == "__main__":
    main()
