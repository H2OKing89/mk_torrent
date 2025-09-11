# MIGRATIONS.md — mk\_torrent Module Moves & Renames

**Purpose:** Serve as the single source of truth for path changes during the repo cleanup. Each row maps an **old path → new path**, records the **action**, **rationale**, and **status**, and links to the PR/commit. This file prevents drift, standardizes deprecations, and makes it easy for contributors (and Future‑You) to follow the migration history.

**Effective date:** 2025‑09‑11
**Owner:** Quentin (H2OKing)

---

## Scope & Audience

This document governs **module and path migrations** across the `mk_torrent` package during and after the cleanup initiative. It’s written for:

* Contributors implementing refactors and path moves.
* Reviewers performing code review and CI enforcement.
* Ops/mechanical maintainers validating that shims and warnings are behaving as expected.

If you’re adding brand‑new features that don’t touch imports or paths, you likely don’t need this file—**but** you should still skim the **Dependency Boundaries** section to avoid re‑introducing cycles.

---

## Conventions

* **Action:** `Move`, `Merge`, `Delete`, `Keep+Shim` (re‑export with `DeprecationWarning`).
* **Status:** `planned`, `in‑progress`, `merged`, `removed` (after deprecation window).
* **Removal window:** Target **4 weeks** from first shim warning unless otherwise noted.
* **Scope tags:** `trackers`, `templates`, `integrations`, `core`, `workflows`.
* **Semver note:** Until v1.0, we treat deprecations seriously but allow internal churn. Public CLI behavior remains stable.

### Decision Matrix (when in doubt)

| Situation                                            | Preferred Action                            | Why                                         |
| ---------------------------------------------------- | ------------------------------------------- | ------------------------------------------- |
| Two files implement same concern in different places | **Merge** into canonical home + `Keep+Shim` | Minimizes long‑term drift                   |
| File is correct but in the wrong directory           | **Move** + `Keep+Shim`                      | Preserve imports while flipping callers     |
| File is placeholder/empty or superseded              | **Delete**                                  | Reduce noise; update callers if any         |
| Public path is changing                              | **Keep+Shim** for 2–4 weeks                 | Smooth transition for scripts and workflows |

---

## Dependency Boundaries (must not break)

```
utils → core → {trackers, integrations} → workflows → cli
```

* `core` contains business logic and shared types; it **must not** import from `trackers` or `integrations`.
* `integrations` are IO clients only (HTTP/RPC/FS) and may depend on `utils`.
* `trackers` implement per‑tracker adapters/spec deltas; they depend on `core` types.
* `workflows` orchestrate user flows and call the **public API**.
* `cli` imports **only** from `public_api.py`.

---

## Migration Table

> Update the **PR / Commit** column with the GitHub PR number or short SHA upon merge. Update **Status** accordingly.

| Old Path                                               | New Path                                             |     Action | Rationale                                                            | PR / Commit | Status  | Deprecation removal date | Notes                                       |
| ------------------------------------------------------ | ---------------------------------------------------- | ---------: | -------------------------------------------------------------------- | ----------- | ------- | ------------------------ | ------------------------------------------- |
| `src/mk_torrent/api/trackers/base.py`                  | `src/mk_torrent/trackers/base.py`                    |       Move | One canonical tracker home under `trackers/*`.                       | 23b5b76     | merged  | 2025-10-09               | Phase 2: Complete with shim                |
| `src/mk_torrent/api/trackers/red.py`                   | `src/mk_torrent/trackers/red/adapter.py`             |       Move | Unify tracker adapters; avoid duplicate packages.                    | 23b5b76     | merged  | 2025-10-09               | Phase 2: Complete with shim                |
| `src/mk_torrent/api/trackers/mam.py`                   | `src/mk_torrent/trackers/mam/adapter.py`             |       Move | Same as above for MAM.                                               | 23b5b76     | merged  | 2025-10-09               | Phase 2: Complete with shim                |
| `src/mk_torrent/trackers/upload_spec.py`               | `src/mk_torrent/core/upload/spec.py`                 |      Merge | Centralize shared upload types in `core` to reduce drift.            | TBA         | merged  | 2025-10-09               | Phase 3A.1: Enum consolidation complete    |
| `src/mk_torrent/trackers/red/upload_spec.py`           | `src/mk_torrent/core/upload/spec.py` (shared enums)  | Merge/Keep | Move shared enums to core; keep RED-specific AudioBitrate.           | TBA         | merged  | N/A                      | Phase 3A.1: AudioFormat/MediaType from core |
| `src/mk_torrent/features/templates.py`                 | `src/mk_torrent/core/metadata/templates/renderer.py` | Move/Merge | Consolidate templating with metadata pipeline.                       | TBA         | planned | TBA                      | Phase 3: Different purpose, no action needed |
| `src/mk_torrent/api/qbittorrent.py`                    | `src/mk_torrent/integrations/qbittorrent.py`         |       Move | Single IO client location under `integrations/*`.                    | 23b5b76     | merged  | 2025-10-09               | Phase 2: Complete with shim                |
| `src/mk_torrent/core/upload/spec.py` (empty duplicate) | —                                                    |     Delete | Remove empty duplicate to eliminate confusion.                       | 23b5b76     | merged  | N/A                      | Phase 2: Removed empty duplicate           |
| `src/mk_torrent/api/*` (general)                       | `src/mk_torrent/integrations/*`                      |       Move | Retire ambiguous `api/` in favor of `integrations/` for external IO. | 23b5b76     | merged  | 2025-10-09               | Phase 2: Complete with shims               |

### Completed Migrations (log here after merge)

| Old Path | New Path | Action | PR / Commit | Removal date | Notes |
| -------- | -------- | -----: | ----------- | ------------ | ----- |
| `src/mk_torrent/trackers/red/upload_spec.py` enums | `src/mk_torrent/core/upload/spec.py` | Merge | 5684059 | N/A | Phase 3A.1: AudioFormat/MediaType/ReleaseType consolidated |
| `src/mk_torrent/trackers/upload_spec.py` classes | `src/mk_torrent/core/upload/spec.py` | Merge | 5684059 | 2025-10-09 | Phase 3A.1: Category/UploadSpec/UploadResult consolidated |
| `src/mk_torrent/trackers/red/adapter.py` | `src/mk_torrent/trackers/red_adapter.py` | Unify | 6f4144e | 2025-02-09 | Phase 3A.2: Enhanced red_adapter.py, created deprecation shim |
| N/A | `src/mk_torrent/trackers/factory.py` | Create | e954f1b | N/A | Phase 3A.3: New adapter factory for centralized creation |
| `src/mk_torrent/trackers/mam/adapter.py` | Same (clarified) | Update | e954f1b | N/A | Phase 3A.4: Documented MAM manual upload limitation |

---

## Phase 3A Tracker Consolidation Summary (COMPLETED 2025-01-09)

**Status**: ✅ MERGED — All four sub-phases complete
**Branch**: cleanup/2025-09-module-audit
**Final Commit**: e954f1b

### Achievements
1. **3A.1: Upload Spec Enum Consolidation** — Single source: `core/upload/spec.py`
2. **3A.2: RED Adapter Unification** — Enhanced `red_adapter.py`, deprecated `red/adapter.py`
3. **3A.3: Adapter Factory Pattern** — Centralized creation via `TrackerAdapterFactory`
4. **3A.4: MAM Implementation** — Clarified manual upload requirement

### Key Results
- Resolved enum conflicts across 3 modules (AudioFormat, MediaType, ReleaseType)
- Consolidated duplicate adapter implementations
- Standardized adapter instantiation patterns
- Maintained backward compatibility via deprecation shims
- 4-week deprecation timeline (removal: 2025-02-09)
- All CLI functionality preserved and validated

### Validation
- ✅ CLI still works: `python -m mk_torrent --help`
- ✅ Factory creates adapters: RED, MAM tested
- ✅ Type checking passes across all modules
- ✅ Deprecation warnings trigger correctly
- ✅ Integration tests pass (RED upload workflows)

**Next**: Phase 3B — Integration Layer Consolidation

---

## Shim Inventory (Keep+Shim)

**Pattern:**

```py
# example: src/mk_torrent/api/trackers/red.py
import warnings
warnings.warn(
    "mk_torrent.api.trackers.red is deprecated; use mk_torrent.trackers.red",
    DeprecationWarning, stacklevel=2,
)
from mk_torrent.trackers.red import *  # re-export
```

**Planned shims:**

* `src/mk_torrent/api/trackers/base.py`
* `src/mk_torrent/api/trackers/red.py`
* `src/mk_torrent/api/trackers/mam.py`
* Any other `src/mk_torrent/api/*` modules moved under `integrations/*`

**Removal policy:** Elevate warnings to CI failures after **2 weeks**, remove shims at **4 weeks**.

**Runtime sanity check (optional):**

```py
# tools/check_deprecations.py
import warnings, sys
from contextlib import contextmanager

@contextmanager
def capture_warnings():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("default")
        yield w

if __name__ == "__main__":
    with capture_warnings() as w:
        # import a few common entry points to trigger imports
        import mk_torrent
        import mk_torrent.workflows.upload_integration  # noqa: F401
    found = [str(x.message) for x in w if isinstance(x.message, Warning)]
    if any("deprecated" in m.lower() for m in found):
        print("Deprecations detected:\n" + "\n".join(found))
        sys.exit(1)
```

---

## Import Rewrite Commands

Audit and replace legacy imports that reference deprecated paths.

**Linux/macOS (ripgrep + sed):**

```bash
# Show legacy imports
rg -n "from mk_torrent\.api\.trackers" src | sort

# Replace (review diff before committing!)
rg -l "from mk_torrent\.api\.trackers" src \
  | xargs sed -i 's/from mk_torrent\.api\.trackers/from mk_torrent.trackers/g'
```

**Windows PowerShell:**

```powershell
# Show legacy imports
rg -n "from mk_torrent\.api\.trackers" src | sort

# Replace in-place (creates a .bak by default if you choose -Backup)
Get-ChildItem -Recurse src -Filter *.py | ForEach-Object {
  (Get-Content $_.FullName) -replace 'from mk_torrent\.api\.trackers','from mk_torrent.trackers' \
    | Set-Content $_.FullName
}
```

Update tracker‑specific spec imports:

```bash
rg -n "from mk_torrent\.trackers\.upload_spec" src | sort
# then replace with
# from mk_torrent.core.upload.spec import ...
```

**Verify after rewrites:**

```bash
python -m compileall -q src && ruff check src && pytest -q
```

---

## Validation Checklist (per PR)

* [ ] All imports updated to new path(s)
* [ ] Shim added (if public) and warning logs once in dev
* [ ] Unit tests pass; snapshot tests for Jinja outputs (if templates)
* [ ] `ruff` + `ruff-format` clean; `mypy` clean on changed modules
* [ ] Wizard/CLI smoke tests pass
* [ ] This file updated (row status + PR/Commit), and `DEPRECATIONS.md` entry added
* [ ] ADR added/updated if boundaries changed (see ADR section)

### Test Matrix (recommended minimum)

| Area               | Tests                                                                                         |
| ------------------ | --------------------------------------------------------------------------------------------- |
| Trackers (RED/MAM) | Adapter unit tests; spec round‑trip (build → serialize → validate); golden fixtures unchanged |
| Templates          | Snapshot test for Jinja output; HTML cleaning idempotence                                     |
| Integrations       | Client happy‑path and error mapping; timeouts/retries mocked                                  |
| Core               | Validator accepts/declines expected cases; no IO in pure services                             |
| Workflows          | Wizard dry‑run; upload integration end‑to‑end under `--dry-run`                               |

---

## Timeline & Status Gates

* **Week 0:** Merge PR with shims and import rewrites; CI allows deprecations.
* **Week 2:** CI treats `DeprecationWarning` as failure in new PRs.
* **Week 4:** Remove shim, delete legacy path. Add entry to `CHANGELOG.md`.

**Metrics to watch:**

* Count of `DeprecationWarning` at startup (should drop to 0 by Week 2).
* Number of files under `src/mk_torrent/api/**` (should hit 0 by Week 4).
* `deps.png` acyclicity (no back‑edges introduced by moves).

---

## ADR Index (Architecture Decision Records)

Store ADRs under `docs/adr/`. Suggested IDs:

* **ADR‑0001:** Use `integrations/*` for external IO, retire `api/*`.
* **ADR‑0002:** Centralize shared upload spec in `core/upload/spec.py`.
* **ADR‑0003:** Enforce `public_api.py` as the only CLI/workflow import surface.

**ADR template**

```md
# ADR-XXXX: Title
Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded
Context: Why this decision matters
Decision: What we chose
Consequences: Trade-offs, risks, follow-ups
```

---

## CI/Pre‑commit Enforcement

**.pre-commit-config.yaml (snippet):**

```yaml
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
* custom job: fail if any file exists under `src/mk_torrent/api/**` after deprecation window
* custom job: run `tools/check_deprecations.py` and fail on warnings after Week 2

**Makefile targets (quality):**

```makefile
lint:
    ruff check src
    mypy src/mk_torrent

test:
    pytest -q

smoke:
    python -m mk_torrent --help
    python -m mk_torrent wizard --dry-run --debug
```

---

## Rollback Plan

* Every migration PR must be **reversible**: moves via `git mv`, shims in separate commits, import rewrites isolated.
* Keep a tag per phase milestone (e.g., `pre-cleanup-2025-09-11`).
* If rollback needed, revert the import‑rewrite commit first, then revert file moves. Remove shims last.

---

## FAQ

**Q: Why keep shims if we control all call sites?**
A: Hidden import paths (scripts, notebooks, external callers) happen. Shims de‑risk.

**Q: Can we shorten the 4‑week window?**
A: Yes—if CI shows 0 deprecations across two consecutive weeks and we’ve updated all internal callers.

**Q: What about third‑party plugins?**
A: Treat as external callers: announce in release notes and keep shims for a full cycle.

**Q: How do I add a new tracker post‑cleanup?**
A: Create `trackers/<name>/{api_client.py,adapter.py,upload_spec.py}`; depend on `core.upload.spec` and **do not** put IO in `core`.

---

## Row Template (copy/paste)

```md
| `old/path.py` | `new/path.py` | Move | Short rationale | #123 | in-progress | 2025-10-09 | Notes about shims/tests |
```

---

## Change Log

* **2025‑09‑11:** Initial draft created with planned moves for `trackers`, `templates`, `integrations`, and `core` upload spec.
* **2025‑09‑11:** Expanded with boundaries, ADR index, test matrix, Windows rewrite commands, metrics, and rollback plan.
