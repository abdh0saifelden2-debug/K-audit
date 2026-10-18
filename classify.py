"""Classify every file in a per-repo split against the pristine monorepo.

Usage:
    python3 classify.py --mono /path/to/K <split-repo>

Every file in <split-repo> is matched against the monorepo by SHA-256, then by
same relpath, then by basename, and reported as one of:

    SAME-PATH   identical bytes at the same relative path
    VENDORED    identical bytes at a different monorepo path
    MODIFIED    content differs from the monorepo copy (same relpath/basename)
    MODIFIED?   content differs and the basename is ambiguous
    NEW         no monorepo counterpart

Exit code 0 always; the report is the output.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

SKIP = {".git", ".github", "__pycache__", ".pytest_cache", ".venv", "*.pyc"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mono", default=os.environ.get("K_MONO", "K"),
                    help="path to the pristine K monorepo clone "
                         "(default: $K_MONO or ./K)")
    ap.add_argument("repo", help="path to the split repo to classify")
    args = ap.parse_args()

    mono = Path(args.mono)
    if not mono.is_dir():
        sys.exit(f"monorepo not found: {mono} (pass --mono /path/to/K)")

    by_hash, by_name = {}, {}
    for p in mono.rglob("*"):
        if any(s in p.parts for s in SKIP) or p.is_dir():
            continue
        if p.name == ".DS_Store":
            continue
        try:
            d = sha(p)
        except OSError:
            continue
        rel = str(p.relative_to(mono))
        by_hash.setdefault(d, []).append(rel)
        by_name.setdefault(p.name, []).append(rel)

    repo = Path(args.repo)
    if not repo.is_dir():
        sys.exit(f"repo not found: {repo}")

    report = []
    for p in sorted(repo.rglob("*")):
        if any(s in p.parts for s in SKIP) or p.is_dir() or p.suffix == ".pyc":
            continue
        rel = str(p.relative_to(repo))
        if rel in ("AUDIT.md",):
            continue
        d = sha(p)
        cands = by_hash.get(d, [])
        if any(c == rel for c in cands):
            report.append(("SAME-PATH", rel, ""))
        elif cands:
            report.append(("VENDORED", rel, cands[0]))
        else:
            if (mono / rel).exists():
                report.append(("MODIFIED", rel, rel))
            elif len(by_name.get(p.name, [])) == 1:
                report.append(("MODIFIED", rel, by_name[p.name][0]))
            elif by_name.get(p.name):
                report.append(("MODIFIED?", rel, ",".join(by_name[p.name][:3])))
            else:
                report.append(("NEW", rel, ""))

    from collections import Counter
    print(repo.name, dict(Counter(r[0] for r in report)))
    for tag, rel, src in report:
        if tag != "SAME-PATH":
            print(f"  {tag:9} {rel}   <- {src}")


if __name__ == "__main__":
    main()
