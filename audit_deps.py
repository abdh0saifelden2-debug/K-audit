#!/usr/bin/env python3
"""Global AST import audit.

Walks every .py under a root and classifies each import of a known top-level
package (general_two_clocks, atmosphere, glaciers, ocean, closure, subglacial):

  EDGE  - the package does NOT exist at the repo root -> would break if this
          folder were extracted standalone. These are the vendoring targets.
  LOCAL - the package exists at the repo root -> resolves inside the repo, fine.

Usage: python3 audit_deps.py [ROOT] [--all] [--local]
  --all    print every import (including stdlib / third-party)
  --local  also print LOCAL edges (default: EDGEs only)
Exit code: 1 if any EDGE remains (acceptance gate for extracted repos).
"""
import ast
import sys
from pathlib import Path

KNOWN = ("general_two_clocks", "atmosphere", "glaciers", "ocean", "closure", "subglacial")
SKIP = ("__pycache__", ".venv", "venv", ".git", "node_modules", ".pytest_cache")


def local_packages(root: Path) -> set:
    """Top-level names importable from the repo root."""
    names = set()
    for p in root.iterdir():
        if p.is_dir() and (p / "__init__.py").exists():
            names.add(p.name)
        elif p.is_file() and p.suffix == ".py":
            names.add(p.stem)
    return names


def collect(root: Path):
    for p in sorted(root.rglob("*.py")):
        if any(s in p.parts for s in SKIP):
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src, filename=str(p))
        except Exception:
            continue
        yield p.relative_to(root), tree


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    root = Path(args[0]) if args else Path(".")
    show_all = "--all" in flags
    show_local = "--local" in flags

    local = local_packages(root)
    n_edge = n_local = 0
    edge_files = set()

    for f, tree in collect(root):
        rows = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    rows.append((0, "import " + a.name, a.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for a in node.names:
                    rows.append((node.level, f"from {mod}", a.name))

        out = []
        for lvl, head, names in rows:
            if lvl > 0:
                continue  # relative import: always local
            top = head.split()[1].split(".")[0]
            is_known = top in KNOWN
            is_local = top in local
            if not is_known and not show_all:
                continue
            if is_known and not is_local:
                out.append(f"   EDGE  {head} import {names}")
            elif is_known and is_local:
                if show_local or show_all:
                    out.append(f"   LOCAL {head} import {names}")
                n_local += 1
            elif show_all:
                out.append(f"   ok    {head} import {names}")
        if out and any("EDGE" in o for o in out):
            edge_files.add(str(f))
            n_edge += sum(1 for o in out if "EDGE" in o)
        if out:
            print(f)
            for o in sorted(out):
                print(o)

    print(f"\n# root={root}  local_pkgs={sorted(local)}", file=sys.stderr)
    print(f"# EDGE={n_edge} (in {len(edge_files)} files)  LOCAL={n_local}", file=sys.stderr)
    if edge_files:
        print("# files with EDGEs:", file=sys.stderr)
        for fe in sorted(edge_files):
            print(f"#   {fe}", file=sys.stderr)
    sys.exit(1 if n_edge else 0)


if __name__ == "__main__":
    main()
