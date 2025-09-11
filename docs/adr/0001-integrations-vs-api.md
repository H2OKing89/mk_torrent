# ADR-0001: Use `integrations/*` for external IO, retire `api/*`

**Date:** 2025-09-11
**Status:** Accepted
**Owner:** Quentin (H2OKing)

---

## Context

The `mk_torrent` package currently has modules under both `api/*` and `integrations/*` directories that handle external service communication (HTTP, RPC, filesystem). This creates confusion about where new external clients should be placed and leads to scattered functionality:

- `api/trackers/*` contains RED and MAM tracker clients
- `api/qbittorrent.py` contains qBittorrent RPC client
- `integrations/audnexus*.py` contains AudNexus HTTP clients
- Some HTTP client logic exists within `core/metadata/sources/`

The duplication violates the single source of truth principle and makes maintenance difficult. Contributors are unclear which directory to use for new external service integrations.

**Problem Statement:** We need a clear, consistent naming convention and location for all external service clients to eliminate confusion and reduce code drift.

---

## Decision

We will **standardize on `integrations/*`** as the canonical location for all external service clients and **retire `api/*`** through a systematic migration with deprecation shims.

**Specific actions:**

1. **Move all external IO clients to `integrations/*`:**
   - `api/trackers/*` → `trackers/*` (tracker-specific clients)
   - `api/qbittorrent.py` → `integrations/qbittorrent.py`
   - HTTP/client code in `core/metadata/sources/` → `integrations/`

2. **Enforce clear separation of concerns:**
   - `integrations/*` = **IO-only clients** (HTTP, RPC, filesystem)
   - `core/*` = **business logic and shared types**
   - `trackers/*` = **per-tracker adapters** that depend on core types

3. **Add deprecation shims** at old `api/*` paths that:
   - Re-export from new locations
   - Emit `DeprecationWarning` with clear migration path
   - Maintain backward compatibility for 4-week transition period

---

## Rationale

### Why `integrations` over `api`?

- **"API" is ambiguous:** Could mean our public API, REST endpoints, or external clients
- **"Integrations" is precise:** Clearly signals external system communication
- **Industry convention:** Many codebases use "integrations" for external service clients
- **Future-proof:** Room for different integration types (webhooks, message queues, etc.)

### Why move tracker clients to `trackers/*` instead of `integrations/*`?

- **Domain-specific:** Tracker clients are core to the application's purpose
- **Adapter pattern:** Each tracker needs business logic adapters beyond just HTTP clients
- **Clean layering:** `trackers/` can depend on `core/upload/spec.py` for shared types
- **Logical grouping:** Tracker API clients, adapters, and specs belong together

### Dependency boundaries (enforced)

```
utils → core → {trackers, integrations} → workflows → cli
```

- `core` contains business logic; **must not** import from `integrations` or `trackers`
- `integrations` are pure IO clients; may depend on `utils` for common helpers
- `trackers` implement domain adapters; depend on `core` types and `utils`
- `workflows` orchestrate user flows using the public API
- `cli` imports **only** from `public_api.py`

---

## Consequences

### Benefits

✅ **Single source of truth:** One clear location for each type of external client
✅ **Reduced confusion:** Contributors know exactly where external clients belong
✅ **Better separation of concerns:** IO isolated from business logic
✅ **Easier testing:** Mock boundaries are clearer
✅ **Future extensibility:** Room for new integration types without path conflicts

### Trade-offs

⚠️ **Migration effort:** Requires systematic file moves and import path updates
⚠️ **Temporary complexity:** 4-week deprecation period with shims and warnings
⚠️ **Potential breakage:** External scripts importing `api/*` modules will need updates

### Risks and Mitigations

**Risk:** Hidden runtime imports from legacy paths
**Mitigation:** Runtime log sniffer that fails CI on `DeprecationWarning` after grace period

**Risk:** Import cycles introduced during migration
**Mitigation:** Strict dependency boundary enforcement in CI; `deps.png` regeneration

**Risk:** Tracker behavior divergence after consolidation
**Mitigation:** Golden fixtures for upload specs; assert unchanged JSON after refactor

---

## Implementation Plan

1. **Phase 2A:** Move files with `git mv` to preserve history
2. **Phase 2B:** Add deprecation shims at old paths
3. **Phase 2C:** Batch update import statements across codebase
4. **Phase 2D:** Update tests and run smoke tests
5. **Phase 3:** Remove shims after 4-week deprecation window

**Success Criteria:**

- All external IO clients located in appropriate `integrations/*` or `trackers/*` directories
- No files remain under `src/mk_torrent/api/**` after migration
- All tests pass; CLI and wizard functionality unchanged
- Dependency graph (`deps.png`) remains acyclic

---

## Monitoring

- **Week 0:** Merge migration with shims; CI allows deprecations
- **Week 2:** CI treats `DeprecationWarning` as failure for new PRs
- **Week 4:** Remove shims; assert no `api/*` paths exist

**Metrics:**

- Count of `DeprecationWarning` at startup (target: 0 by Week 2)
- Number of files under `src/mk_torrent/api/**` (target: 0 by Week 4)

---

## Related Decisions

- **ADR-0002:** (Planned) Centralize shared upload spec in `core/upload/spec.py`
- **ADR-0003:** (Planned) Enforce `public_api.py` as only CLI/workflow import surface

---

## References

- Phase 1 Evidence: 5 basename collisions found matching predictions
- `MIGRATIONS.md`: Detailed migration table with timelines
- `CLEANUP_PLAN.md`: Overall repository cleanup strategy
