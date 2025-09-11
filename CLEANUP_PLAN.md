# mk\_torrent — Repository Cleanup Plan & Module Map

**Date:** 2025‑09‑11
**Owner:** Quentin (H2OKing)
**Goal:** Eliminate duplicate/overlapping code, restore a single source of truth, and lock in a clean, future‑proof layout without breaking the CLI or upload workflows.

---

## 0) TL;DR Action Path

1. **Freeze & branch:** create `cleanup/2025-09-module-audit` and tag `pre-cleanup-2025-09-11`.
2. **Evidence pass:** generate a dependency graph, list exact duplicate files (by hash), find dead/unused modules, and surface import‑path drift.
3. **Decide canonical layout:** (below) and mark each overlap **Keep / Move / Merge / Delete** with rationale.
4. **One subsystem at a time:** trackers → metadata/templates → integrations (AudNexus/qBittorrent) → upload spec → utils → workflows.
5. **Ship small PRs:** add shims + deprecation warnings, flip imports to new paths, green CI, then delete legacy.
6. **Enforce:** turn deprecations into errors, lock layering rules in CI, and document the final architecture.

**Success criteria**

* No duplicate modules by path **or** purpose.
* All imports align to the canonical layout.
* CLI and `wizard` smoke tests pass end‑to‑end.
* A clean `deps.png` graph with acyclic core dependencies.

---

## 1) Current Package Map (Roles)

> This is a semantic map (not a literal tree) to clarify intent:

* **`mk_torrent/cli.py`, `__main__.py`** – Entrypoints; should import only the **public API**.
* **`core/`** – Domain‑agnostic core logic: torrent creation, compliance/validation, security, health checks, upload queue.
* **`core/metadata/`** – Domain model and pipelines for metadata: sources, services, processors, validators, templates.
* **`integrations/`** – Thin clients for *external* services (e.g., AudNexus, qBittorrent). No business logic.
* **`trackers/`** – Tracker adapters and API clients (e.g., RED, MAM) + tracker‑specific upload specs/adapters.
* **`features/`** – Optional glue/features (wizards, templates convenience, validation helpers). Candidate for merge into `core` or `workflows`.
* **`utils/`** – Small helper utilities; keep tiny and generic.
* **`workflows/`** – Orchestration/UX flows (wizard, end‑to‑end upload integration) that call into public APIs.

**Layering rule (import direction only):**

```
utils → core → {trackers, integrations} → workflows → cli
```

* Lower layers **must not** import from higher layers. Trackers & integrations may import `core` & `utils`. The CLI only touches the public API.

---

## 2) Suspected Overlaps / Duplicates (Initial Hypotheses)

| Area                    | Modules Involved                                                                    | Problem                     | Proposed Canonical                                                                                                             | Next Action                                                                            |
| ----------------------- | ----------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| **Trackers**            | `api/trackers/*` vs `trackers/*`                                                    | Two tracker homes           | **`trackers/*`**                                                                                                               | Migrate unique code from `api/trackers` → `trackers`, add shims, delete `api/trackers` |
| **AudNexus**            | `integrations/audnexus*.py` vs `core/metadata/sources/audnexus.py`                  | Source client logic spread  | **`integrations/audnexus*.py`** for HTTP; `core/metadata/sources/audnexus.py` should *depend on* integrations, not reimplement | Move HTTP/client bits into `integrations`; keep `sources/audnexus.py` as thin adapter  |
| **Templates**           | `features/templates.py` vs `core/metadata/templates/*`                              | Template helpers duplicated | **`core/metadata/templates/*`**                                                                                                | Inline/port helpers from `features/templates.py` and delete that file                  |
| **Upload Spec**         | `core/upload/spec.py` vs `trackers/upload_spec.py` vs `trackers/red/upload_spec.py` | Three specs                 | **`core/upload/spec.py`** as the abstract schema; tracker‑specific deltas live in `trackers/<name>/upload_spec.py`             | Consolidate shared types in `core/upload/spec.py`; adapters import those               |
| **qBittorrent**         | `api/qbittorrent.py` vs any other client                                            | Ensure a single client      | **`integrations/qbittorrent.py`**                                                                                              | Merge all client variants here                                                         |
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
* Document every shim in `DEPRECATIONS.md` with a planned removal date.

**Acceptance criteria for each migration PR:**

* CI green on `ruff`, `mypy` (or pyright), unit tests, and smoke tests.
* No references to the old path remain (enforced with `rg` check + ruff rule).
* `MIGRATIONS.md` updated with old→new mapping and rationale.

---

## 4) Phased Plan & Checklists

### Phase 0 — Safety Net (30–45 min) ✅ COMPLETE

* [x] Create branch: `git checkout -b cleanup/2025-09-module-audit`
* [x] Tag baseline: `git tag pre-cleanup-2025-09-11`
* [x] Ensure `.gitignore` includes `**/__pycache__/`, `*.pyc`, `.coverage/`, `.pytest_cache/`
* [ ] Ensure CI runs tests and type checks (ruff/mypy) on PRs
* [ ] Freeze dependency versions (lockfile) to reduce drift during refactor

### Phase 1 — Evidence Gathering (60–120 min) ✅ COMPLETE

**A. Hash‑level duplicate scan** ✅

* **Found:** 2 empty files with identical hashes (`core/upload/__init__.py` and `core/upload/spec.py`)
* **Status:** Empty placeholders - spec.py needs implementation per plan

**B. Module name collisions** ✅

* **Found:** 5 basename conflicts: `audnexus.py`, `base.py`, `red.py`, `upload_spec.py`, `__init__.py`
* **Status:** All match predicted overlaps in cleanup plan table

**C. Dependency graph & unused code** ✅

* **Tools installed:** ruff, vulture, deptry, pydeps, radon
* **Reports generated:** deps.png, vulture report, deptry analysis
* **Status:** Ruff clean, other reports need review

**D. Reachability (runtime)** ✅

* [x] Search import sites for old paths: found 2 violations requiring migration
* [x] Capture `ImportError`/`DeprecationWarning` lines to `/tmp/audit_report.md`

**E. Public API surfacing** ✅

* [x] Audit report produced with collision analysis
* [x] Old import paths identified: 2 files using legacy patterns

### Phase 2 — Canonical Layout Decision (45–60 min) ✅ COMPLETE

**A. Documentation Infrastructure** ✅

* **Created:** `MIGRATIONS.md` with comprehensive migration tracking
* **Created:** `docs/adr/0001-integrations-vs-api.md` documenting architectural decisions
* **Status:** Documentation foundation established for systematic migration

**B. Core Upload Spec Implementation** ✅

* **Implemented:** `core/upload/spec.py` with shared base classes and types
* **Foundation:** BaseUploadSpec, Artist, RemasterInfo, AudioFormat, MediaType enums
* **Status:** Shared types ready for tracker-specific extensions in Phase 3

**C. Systematic File Moves (git mv)** ✅

* **Completed:** api/trackers/base.py → trackers/base.py
* **Completed:** api/trackers/red.py → trackers/red/adapter.py
* **Completed:** api/trackers/mam.py → trackers/mam/adapter.py
* **Completed:** api/qbittorrent.py → integrations/qbittorrent.py
* **Status:** All file moves preserve git history

**D. Deprecation Shims** ✅

* **Created:** Shims at all old api/trackers/* paths with DeprecationWarning
* **Created:** api/qbittorrent.py shim pointing to integrations/qbittorrent.py
* **Status:** Backward compatibility maintained with 4-week deprecation timeline

**E. Architecture Decisions** ✅

* **Decision:** features/templates.py serves different purpose than core/metadata/templates/ (no consolidation needed)
* **Decision:** AudNexus already properly separated (integrations/* for HTTP, core/metadata/sources/* for adapters)
* **Decision:** Upload spec consolidation deferred to Phase 3 (requires careful RED compatibility work)
* **Status:** Canonical layout locked in, migrations documented

**F. Cleanup & Validation** ✅

* **Removed:** Empty duplicate core/upload/__init__.py
* **Verified:** No legacy import paths remain in codebase
* **Tested:** CLI functionality unchanged (python -m mk_torrent --help works)
* **Status:** Clean working state ready for Phase 3

### Phase 3 — Execute by Subsystem (Iterative PRs) 🚧 IN PROGRESS

**Status:** Planning complete, ready for systematic execution
**Order:** Trackers → Integrations → Upload Specs → Utils → Workflows

#### Phase 3A: Trackers Consolidation

**Goal:** Consolidate tracker specs and update adapters for consistency

* [ ] **Audit current tracker structure** - map RED/MAM spec overlaps and adapter patterns
* [ ] **Consolidate RED upload specs** - merge redundant spec definitions, extend core/upload/spec.py
* [ ] **Update MAM adapter** - align with RED patterns, ensure consistent interface
* [ ] **Create tracker factory pattern** - standardize adapter instantiation and configuration
* [ ] **Add tracker validation suite** - comprehensive tests for spec round-trip and API compatibility
* [ ] **Update tracker documentation** - clear examples and integration patterns

#### Phase 3B: Integrations Cleanup

**Goal:** Clean up AudNexus/qBittorrent integrations, eliminate redundancy

* [ ] **Audit AudNexus integration points** - ensure clean separation between HTTP client and metadata adapter
* [ ] **Review qBittorrent client** - verify single canonical implementation in integrations/
* [ ] **Consolidate external API patterns** - consistent error handling, retry logic, timeout management
* [ ] **Add integration testing framework** - mock external services for reliable testing
* [ ] **Document integration boundaries** - clear contracts between core and external services

#### Phase 3C: Upload Specs Completion

**Goal:** Complete shared upload specification system

* [ ] **Extend core upload spec** - add remaining common fields and validation patterns
* [ ] **Implement tracker-specific extensions** - RED/MAM specific fields as clean extensions
* [ ] **Create spec validation framework** - comprehensive validation with clear error messages
* [ ] **Add spec serialization/deserialization** - JSON/YAML round-trip with schema validation
* [ ] **Build spec migration tools** - helpers to convert between spec versions
* [ ] **Document spec architecture** - clear examples and extension patterns

#### Phase 3D: Utils Consolidation

**Goal:** Consolidate helper functions and eliminate duplicates

* [ ] **Audit utils/* modules** - identify duplicate functions and consolidation opportunities
* [ ] **Merge common patterns** - file handling, string processing, validation helpers
* [ ] **Create focused utility modules** - clear separation of concerns (io, validation, formatting)
* [ ] **Add comprehensive utils tests** - ensure all utility functions are well-tested
* [ ] **Document utility patterns** - clear guidelines for when to add new utilities

#### Phase 3E: Workflows Streamlining

**Goal:** Streamline end-to-end workflow processes

* [ ] **Map workflow dependencies** - understand current wizard and upload integration flows
* [ ] **Eliminate workflow redundancy** - consolidate duplicate orchestration logic
* [ ] **Standardize error handling** - consistent error propagation and user feedback
* [ ] **Add workflow testing** - end-to-end testing with mocked external dependencies
* [ ] **Document workflow architecture** - clear separation between orchestration and business logic

**Per-Subsystem PR Template:**

* [ ] Move files via `git mv <old> <new>` (preserve history)
* [ ] Add shim with `DeprecationWarning` (if public API)
* [ ] Update imports across repo (`ruff --fix` + manual verification)
* [ ] Green tests + smoke run (`pytest` + CLI validation)
* [ ] Update docs (`MIGRATIONS.md` + subsystem-specific docs)
* [ ] Add deprecation timeline entry (30-day standard window)

**Smoke tests (per subsystem):**

```bash
# Core functionality
python -m mk_torrent --help
python -m mk_torrent wizard --dry-run --debug

# Specific subsystem validation
python -c "import mk_torrent.trackers.red.adapter; print('✅ RED adapter')"
python -c "import mk_torrent.integrations.qbittorrent; print('✅ qBittorrent')"
python -c "from mk_torrent.core.upload.spec import BaseUploadSpec; print('✅ Upload spec')"
```

### Phase 4 — Delete Legacy & Tighten Lint (Final)

* [ ] Remove shims after the deprecation window
* [ ] Turn lint warnings into errors for import paths (ruff rule or custom check)
* [ ] Regenerate `deps.png` and commit
* [ ] Enable CI gate that asserts **no files** under deprecated paths

---

## 5) Proposed Canonical Layout (Target)

```
src/mk_torrent/
├── __init__.py
├── __main__.py
├── cli.py
├── public_api.py                # curated, stable surface for CLI/workflows
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
* `public_api.py` = the only import surface used by CLI & workflows.

**Dependency boundaries:**

* `core` MUST NOT import from `integrations` or `trackers`.
* `trackers` SHOULD import `core.upload.spec` and provide tracker deltas.
* `sources/*.py` SHOULD depend on `integrations/*` for IO.

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

**Deprecation timeline example**

* **Week 0:** Add shim + warnings. CI allows but surfaces warnings.
* **Week 2:** Warnings elevated to CI failures for new PRs.
* **Week 4:** Remove shim and delete legacy paths.

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

**Optional pre‑commit hooks:**

```bash
# .pre-commit-config.yaml snippet
- repo: https://github.com/charliermarsh/ruff-pre-commit
  rev: v0.6.0
  hooks:
    - id: ruff
    - id: ruff-format
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.11.0
  hooks:
    - id: mypy
```

**CI gates (suggested):**

* ruff + ruff‑format
* mypy (or pyright)
* pytest (unit + smoke)
* custom check: fail if `src/mk_torrent/api/**` exists after Phase 4

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
* `docs/adr/*` (decision log)

**`MIGRATIONS.md` example rows**

```
mk_torrent/api/trackers/red.py → mk_torrent/trackers/red/adapter.py | unify tracker adapters | PR #123
mk_torrent/features/templates.py → mk_torrent/core/metadata/templates/renderer.py | consolidate templating | PR #124
mk_torrent/api/qbittorrent.py → mk_torrent/integrations/qbittorrent.py | single client | PR #125
```

---

## 9) Rollback & Risk

* Baseline tag = instant rollback.
* One‑subsystem PRs = limited blast radius.
* Shims with `DeprecationWarning` = safe transition.
* Keep `pre-cleanup-*` tags for at least 60 days.

**Risks & mitigations**

* *Risk:* Hidden runtime imports from legacy paths.
  *Mitigation:* runtime log sniffer that fails CI on `DeprecationWarning` after grace period.
* *Risk:* Tracker behavior divergence after merge.
  *Mitigation:* record golden fixtures for RED/MAM upload specs; assert unchanged JSON after refactor.
* *Risk:* Template rendering regressions.
  *Mitigation:* snapshot tests for Jinja output; compare against committed `*.snap` files.

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

**Progress tracker (labels suggested)**

* `status/triage`, `status/in-progress`, `status/review`, `status/blocked`
* `scope/trackers`, `scope/templates`, `scope/integrations`, `scope/core`, `scope/workflows`

---

## 11) Coding Standards (Enforcement‑Ready)

* **Style & lint:** ruff + ruff‑format; no `flake8` overlap.
* **Typing:** aim for `from __future__ import annotations`; mypy strict on `core/*` and `trackers/*`.
* **Logging:** `logging.getLogger(__name__)`; no `print()` in library code.
* **Errors:** prefer explicit exceptions; no bare `except:`.
* **Imports:** absolute within package; no reaching across layers (see layering rule).
* **I/O boundaries:** network and filesystem confined to `integrations/*` and top‑level workflows.

---

## 12) Tracker‑Specific Guardrails (RED/MAM)

* Keep a shared base in `trackers/base.py` for reusable behaviors (rate‑limit backoff, auth refresh).
* Encode per‑tracker constraints as dataclasses layered over `core.upload.spec`.
* Maintain fixtures under `tests/fixtures/trackers/{red,mam}/` to snapshot requests & responses.

**Example spec layering (conceptual)**

```
core.upload.spec.Release → trackers.red.upload_spec.RedRelease
                             └─ adds: ripper, media_format, lineage, tags
```

---

## 13) Metadata Pipeline Notes

**Flow (high‑level)**

```
pathinfo → format_detector → embedded/audnexus sources → processors.audiobook →
validators → templates.renderer → upload_spec builder
```

* `sources.audnexus` **uses** `integrations.audnexus_api` for IO.
* `services.tag_normalizer` should be pure (no IO) and unit tested with fixtures.

**Common pitfalls**

* Duplicated HTML cleaning across `services` and `features`; consolidate under `services/html_cleaner.py`.
* Throw away partial metadata merges; use a `merge_audiobook.py` strategy that preserves provenance.

---

## 14) Migration Cheat‑Sheet

**Move + shim**

```bash
git mv src/mk_torrent/api/trackers/red.py src/mk_torrent/trackers/red/adapter.py
cat > src/mk_torrent/api/trackers/red.py <<'PY'
import warnings
warnings.warn("mk_torrent.api.trackers.red is deprecated; use mk_torrent.trackers.red",
              DeprecationWarning, stacklevel=2)
from mk_torrent.trackers.red import *
PY
```

**Flip imports**

```bash
rg -l "from mk_torrent\.api\.trackers" src | xargs sed -i 's/from mk_torrent\.api\.trackers/from mk_torrent.trackers/g'
```

**Verify**

```bash
pytest -q && ruff check src && mypy src/mk_torrent
```

---

## 15) Post‑Cleanup Enforcement

* Add a CI job that fails if any path under `src/mk_torrent/api/**` or `features/templates.py` exists.
* Add a custom `ruff` rule (or `pytest` check) that forbids imports against deprecated modules.
* Document in `ARCHITECTURE.md` and link to ADRs.

---

## 16) Glossary

* **Canonical layout** – The authoritative directory structure and module placement.
* **Shim** – A thin compatibility layer re‑exporting from a new module while warning.
* **Public API** – The stable set of functions imported by the CLI and workflows.
* **Integration** – Code that talks to external systems (HTTP/RPC), kept separate from business logic.

---

### Notes & Rationale

* **Why prefer `integrations/*` over `api/*`?** “API” is ambiguous; `integrations` signals external IO.
* **Why keep shared spec in `core/upload/spec.py`?** Trackers diverge in fields; a single core schema reduces drift.
* **Why collapse `features/*`?** If features are just helpers, they belong near the domain (`core/metadata`). If they’re UX flows, move them to `workflows/*`.

> Outcome: a clear public API surface, one home per concept, and far fewer mystery imports.
