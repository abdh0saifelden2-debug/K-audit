# K-audit

Split-audit tooling for the **K** monorepo and its five claim-cluster
repositories (`K1-two-clocks-theory`, `K2-subglacial-cavity`,
`K3-scallop-migration`, `K4-swirl-vortex`, `K5-ocean-probes`).

Each split repo ships an `AUDIT.md` describing how it was carved out of the
pristine monorepo. These two tools are the reproducible checks behind those
documents.

## Tools

### `classify.py` — content map

```bash
git clone https://github.com/abdh0saifelden2-debug/K K
python3 classify.py --mono K /path/to/K2-subglacial-cavity
```

Every file in the split repo is matched against the monorepo by SHA-256, then
by same relative path, then by basename, and reported as `SAME-PATH`,
`VENDORED`, `MODIFIED`, `MODIFIED?` or `NEW`.

### `verify_repo.py` — import-edge gate (load-bearing)

```bash
python3 verify_repo.py --mono K /path/to/K2-subglacial-cavity
```

Builds the set of top-level module names that exist anywhere in the monorepo,
resolves every non-relative import in the split repo against its local names,
and fails (exit 1) if any import resolves only outside the repository. The
`OK <repo>: no external edges` line is the self-containment acceptance gate
quoted in each `AUDIT.md`.

### `audit_deps.py` — coarse package audit

```bash
python3 audit_deps.py /path/to/K2-subglacial-cavity --local
```

Classifies imports of the known monorepo packages as `EDGE` (package not at
the repo root) or `LOCAL`. Exit 1 if any `EDGE` remains.

## Environment

Both monorepo-aware tools take `--mono PATH` (or the `K_MONO` environment
variable, default `./K`). Clone the public monorepo first:

```bash
git clone https://github.com/abdh0saifelden2-debug/K K
```

## Release

`v1.0` — first published revision, used by the `AUDIT.md` files of the five
split repositories. Cite the tag permalink:

<https://github.com/abdh0saifelden2-debug/K-audit/tree/v1.0>
