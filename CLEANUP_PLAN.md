# mk\_torrent — Repository Cleanup Plan & Module Map

**Date:** 2025‑09‑11
**Owner:** Quentin (H2OKing)
**Goal:** Eliminate duplicate/overlapping code, restore a single source of truth, and lock in a clean, future‑proof layout without breaking the CLI or upload workflows.

---

## 0) TL;DR Action Path

1. **Freeze & branch:** create `cleanup/2025-09-module-audit` and tag `pre-cleanup-2025-09-11`.
2. **Evidence pass:** generate a dependency graph, list exact duplicate files (by hash), find dead/unused modules.
3. **Decide canonical layout:** (below) and mark each overlap **Keep / Move / Merge / Delete**.
4. **One subsystem at a time:** trackers → metadata/templates → integrations (AudNexus/qBittorrent) → upload spec → utils.
5. **Ship small PRs:** add shims + deprecation warnings, flip imports to new paths, then delete legacy.

---

## 1) Current Package Map (Roles)

> This is a semantic map (not a literal tree) to clarify intent:

* **`mk_torrent/cli.py`, `__main__.py`** – Entrypoints; should import only the **public API**.
* **`core/`** – Domain‑agnostic core logic: torrent creation, compliance/validation, security, health checks, upload queue.
* **`core/metadata/`** – Domain model and pipelines for metadata: sources, services, processors, validators, templates.
* **`integrations/`** – Thin clients for *external* services (e.g., AudNexus, qBittorrent). No business logic.
* **`trackers/`** – Tracker adapters and API clients (e.g., RED, MAM) + tracker‑specific upload specs/adapters.
* **`features/`** – Optional glue/features (wizards, templates convenience, validation helpers). Candidate for merge into `core`.
* **`utils/`** – Small helper utilities; keep tiny and generic.
* **`workflows/`** – Orchestration/UX flows (wizard, end‑to‑end upload integration) that call into public APIs.

---

## 2) Suspected Overlaps / Duplicates (Initial Hypotheses)

| Area                    | Modules Involved                                                                    | Problem                     | Proposed Canonical                                                                                                             | Next Action                                                                            |
| ----------------------- | ----------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| **Trackers**            | `api/trackers/*` vs `trackers/*`                                                    | Two tracker homes           | **`trackers/*`**                                                                                                               | Migrate unique code from `api/trackers` → `trackers`, add shims, delete `api/trackers` |
| **AudNexus**            | `integrations/audnexus*.py` vs `core/metadata/sources/audnexus.py`                  | Source client logic spread  | **`integrations/audnexus*.py`** for HTTP; `core/metadata/sources/audnexus.py` should *depend on* integrations, not reimplement | Move HTTP/client bits into `integrations`; keep `sources/audnexus.py` as thin adapter  |
| **Templates**           | `features/templates.py` vs `core/metadata/templates/*`                              | Template helpers duplicated | **`core/metadata/templates/*`**                                                                                                | Inline/port helpers from `features/templates.py` and delete that file                  |
| **Upload Spec**         | `core/upload/spec.py` vs `trackers/upload_spec.py` vs `trackers/red/upload_spec.py` | Three specs                 | **`core/upload/spec.py`** as the abstract schema; tracker‑specific deltas live in `trackers/<name>/upload_spec.py`             | Consolidate shared types in `core/upload/spec.py`; adapters import those               |
| **qBittorrent**         | `api/qbittorrent.py` vs `integrations/audnexus/qbittorrent?` (check)                | Ensure a single client      | **`integrations/qbittorrent.py`**                                                                                              | If any other clients exist, merge them here                                            |
| **API vs Integrations** | `api/*` (general) vs `integrations/*`                                               | Two names for same concept  | Prefer **`integrations/*`**                                                                                                    | Move remaining `api/*` clients into `integrations/*` with shims                        |

> NOTE: `__pycache__/` directories are build artifacts; ensure they’re git‑ignored and never committed.

---

## 3) Decision Rubric (Keep / Move / Merge / Delete)

* **Keep** if: imported by CLI/workflows, covered by tests, matches canonical location.
* **Move** if: correct implementation, wrong directory (add deprecation shim for ≥1 release).
* **Merge** if: two modules implement the same idea with diverging bits (create one superset, retire the other).
* **Delete** if: not imported, redundant, stale, or superseded. Stage deletion after a deprecation period if public.

**Shims & Deprecations:**

* Add a file in the old path that re‑exports from the new path and emits `DeprecationWarning`.
* Log once at startup in dev mode to surface moved modules.

---

## 4) Phased Plan & Checklists

### Phase 0 — Safety Net (30–45 min)

* [ ] Create branch: `git checkout -b cleanup/2025-09-module-audit`
* [ ] Tag baseline: `git tag pre-cleanup-2025-09-11`
* [ ] Ensure `.gitignore` includes `**/__pycache__/` and `*.pyc`
* [ ] Ensure CI runs tests and type checks (ruff/mypy) on PRs

### Phase 1 — Evidence Gathering (60–90 min)

**A. Hash‑level duplicate scan**

```bash
# list all python files with hashes
find src/mk_torrent -type f -name "*.py" -not -path "*/__pycache__/*" -print0 | \
  xargs -0 md5sum | sort > /tmp/mk_torrent.hashes

# show duplicate content (same md5, different paths)
awk '{print $1" "$2}' /tmp/mk_torrent.hashes | \
  awk '{arr[$1]=arr[$1]"\n"$2} END {for (h in arr) if (split(arr[h],a,"\n")>2) print h, arr[h]}'
```

**B. Module name collisions**

```bash
# same basename in multiple directories
find src/mk_torrent -type f -name "*.py" -printf '%f\n' | sort | uniq -d
```

**C. Dependency graph & unused code**

```bash
python -m pip install --upgrade ruff vulture deptry pydeps

# dependency graph
pydeps src/mk_torrent --show-deps --max-bacon=4 -T png -o deps.png

# dead code candidates (manual review required)
vulture src/mk_torrent

# unused / missing deps
deptry src

# quick import health
ruff check src
```

**D. Reachability (runtime)**

* [ ] Run the CLI against a **small known dataset**; enable debug logging; capture import warnings.
* [ ] Search import sites for old paths: `rg -n "^from mk_torrent\.(api|features|trackers)" src`

Produce `/tmp/audit_report.md` summarizing duplicates, unused modules, and import sites that point to old paths.

### Phase 2 — Canonical Layout Decision (45–60 min)

Select and lock the canonical structure (proposal below). For each overlap, add a line to **`MIGRATIONS.md`** with: *old path → new path, reason, PR link*.

### Phase 3 — Execute by Subsystem (Iterative PRs)

Order: **Trackers → Templates → Integrations → Upload Spec → Utils**

For each PR:

* [ ] Move files via `git mv <old> <new>`
* [ ] Add shim with `DeprecationWarning` (if public)
* [ ] Update imports across repo (`uvtool`/`ruff --fix`/`sed`)
* [ ] Green tests + smoke run
* [ ] Update docs (this file + `ARCHITECTURE.md` + `MIGRATIONS.md`)

### Phase 4 — Delete Legacy & Tighten Lint (Final)

* [ ] Remove shims after a deprecation window (or immediately if private)
* [ ] Turn lint warnings into errors for import paths
* [ ] Regenerate `deps.png` and commit

---

## 5) Proposed Canonical Layout (Target)

```
src/mk_torrent/
├── __init__.py
├── __main__.py
├── cli.py
├── core/
│   ├── health/
│   │   └── checks.py
│   ├── compliance/
│   │   ├── path_validator.py
│   │   └── path_fixer.py
│   ├── security/
│   │   └── secure_credentials.py
│   ├── torrents/
│   │   └── torrent_creator.py
│   ├── upload/
│   │   ├── queue.py
│   │   └── spec.py            # shared/abstract upload spec types
│   └── metadata/
│       ├── engine.py
│       ├── entities.py
│       ├── exceptions.py
│       ├── processors/
│       │   └── audiobook.py
│       ├── sources/
│       │   ├── audnexus.py   # uses integrations.audnexus client
│       │   ├── embedded.py
│       │   └── pathinfo.py
│       ├── services/
│       │   ├── format_detector.py
│       │   ├── tag_normalizer.py
│       │   ├── html_cleaner.py
│       │   └── merge_audiobook.py
│       ├── templates/
│       │   ├── models.py
│       │   ├── renderer.py
│       │   └── templates/*.jinja
│       └── validators/
│           ├── audiobook_validator.py
│           └── common.py
├── integrations/
│   ├── audnexus.py
│   ├── audnexus_api.py
│   └── qbittorrent.py
├── trackers/
│   ├── base.py
│   ├── red/
│   │   ├── api_client.py
│   │   ├── adapter.py
│   │   └── upload_spec.py    # tracker‑specific fields over core spec
│   └── mam/
│       ├── api_client.py
│       ├── adapter.py
│       └── upload_spec.py
├── utils/
│   ├── async_helpers.py
│   └── api_parser.py
└── workflows/
    ├── wizard.py
    └── upload_integration.py
```

**Naming Rules:**

* `integrations/*` = external IO clients only (HTTP, RPC). No business rules.
* `core/*` = business rules and shared types.
* `trackers/*` = per‑tracker adapters; depend on `core` types.
* `workflows/*` = UX orchestration using public APIs.

---

## 6) Public API & Shims

Define `mk_torrent/public_api.py` exporting **only** stable call sites used by the CLI & workflows. Everything else is internal.

**Example**

```python
# src/mk_torrent/public_api.py
from .core.torrents.torrent_creator import build_torrent
from .core.metadata.engine import extract_audiobook_metadata
__all__ = ["build_torrent", "extract_audiobook_metadata"]
```

Legacy modules should become:

```python
# src/mk_torrent/api/trackers/red.py (shim)
import warnings
warnings.warn(
    "mk_torrent.api.trackers.red is deprecated; use mk_torrent.trackers.red",
    DeprecationWarning, stacklevel=2
)
from mk_torrent.trackers.red import *
```

---

## 7) Tooling & Commands (Copy/Paste)

**Remove caches (local only):**

```bash
find src/mk_torrent -type d -name __pycache__ -prune -exec rm -rf {} +
```

**RegEx audit for old imports:**

```bash
rg -n "from mk_torrent\.(api|features|trackers)" src | sort
```

**Switch imports (example):**

```bash
# review before applying broadly
rg -n "from mk_torrent\.api\.trackers" src
# then carefully replace in small batches
```

**Smoke test script idea:**

```bash
python -m mk_torrent --help
python -m mk_torrent wizard --dry-run --debug
```

---

## 8) Deliverables to Commit in Repo Root

* `CLEANUP_PLAN.md` (this doc)
* `ARCHITECTURE.md` (final layout + module responsibilities)
* `MIGRATIONS.md` (table: old → new + PR link + rationale)
* `DEPRECATIONS.md` (list of shims and planned removal dates)
* `deps.png` (dependency graph snapshot)

---

## 9) Rollback & Risk

* Baseline tag = instant rollback.
* One‑subsystem PRs = limited blast radius.
* Shims with `DeprecationWarning` = safe transition.
* Keep `pre-cleanup-*` tags for at least 60 days.

---

## 10) Working Checklist (Strike as you go)

* [ ] Branch + tag created
* [ ] Hash duplicates listed and triaged
* [ ] Unused/legacy modules identified (vulture/deptry)
* [ ] Canonical layout approved
* [ ] Trackers consolidated
* [ ] Templates consolidated
* [ ] AudNexus source vs integration clarified
* [ ] Upload spec unified
* [ ] Public API exported
* [ ] Shims added + imports flipped
* [ ] Legacy paths deleted
* [ ] Docs & graph regenerated

---

### Notes & Rationale

* **Why prefer `integrations/*` over `api/*`?** “API” is ambiguous; `integrations` signals external IO.
* **Why keep shared spec in `core/upload/spec.py`?** Trackers diverge in fields; a single core schema reduces drift.
* **Why collapse `features/*`?** If features are just helpers, they belong near the domain (`core/metadata`). If they’re UX flows, move them to `workflows/*`.

> Outcome: a clear public API surface, one home per concept, and far fewer mystery imports.
