# mk\_torrent — Metadata Architecture Refactor (v1)

> **Conductor Document**: This is the master index for the metadata core architecture. Each section links to detailed specifications.

> Scope: **metadata core only** (how we extract, normalize, validate, and present metadata), wired to, but separate from, `qbittorrent` (torrent creation) and `trackers` (upload flows like RED).

---

## Architecture Overview

This document serves as the conductor for the metadata architecture refactor. Each numbered section below has a corresponding detailed specification document.

## 📋 Table of Contents

### Foundation & Design
1. **[Goals](./1%20—%20Goals.md)** - Core objectives and design principles
2. **[High-level Architecture](./2%20—%20High-level%20Architecture.md)** - System overview and component responsibilities
3. **[Proposed Directory Layout](./3%20—%20Proposed%20Directory%20Layout.md)** - File structure and module organization
4. **[Canonical Data Model](./4%20—%20Canonical%20Data%20Model.md)** - Primary data structures and normalization rules

### Core Components
5. **[Interfaces & Dependency Injection](./5%20—%20Interfaces%20&%20Dependency%20Injection.md)** - Protocols, DI patterns, and component wiring
6. **[Engine Pipeline](./6%20—%20Engine%20Pipeline.md)** - Processing flow and data transformation steps
7. **[Services Details](./7%20—%20Services%20Details.md)** - Generic utilities and service modules
   - **[Field Merger Specification](./7.5%20—%20Audiobook%20Metadata%20Field%20Merger.md)** - Detailed merge logic and precedence rules
8. **[Validators](./8%20—%20Validators.md)** - Quality assurance and completeness scoring

### Integration & Output
9. **[Tracker Mapping](./9%20—%20Tracker%20Mapping.md)** - Output formatting for tracker APIs
10. **[Configuration](./10%20—%20Configuration.md)** - Settings, precedence rules, and runtime behavior
10.5. **[Recommended Packages & Project Extras](./10.5%20—%20Recommended%20Packages%20&%20Project%20Extras.md)** - Dependencies and optional enhancements

### Development & Deployment
11. **[Testing Strategy](./11%20—%20Testing%20Strategy.md)** - Test architecture and quality assurance
12. **[Migration Plan](./12%20—%20Migration%20Plan.md)** - Low-risk incremental implementation steps
13. **[Error Handling & Logging](./13%20—%20Error%20Handling%20&%20Logging.md)** - Exception hierarchy and monitoring
14. **[Example: Processor Skeleton](./14%20—%20Example%20Processor%20Skeleton.md)** - Implementation patterns and examples

### Extensibility & Future
15. **[Extension Guide](./15%20—%20Extension%20Guide.md)** - Adding new sources, content types, and trackers
16. **[Next Steps](./16%20—%20Next%20Steps.md)** - Implementation checklist and current priorities

---

## Quick Reference

### Current Implementation Status
- ✅ Validation system (audiobook_validator.py) - completed and lint-compliant
- ✅ Architecture cleanup - legacy code removed, modern structure in place
- ✅ Documentation organization - detailed specifications created
- 🎯 **Next Priority**: Implement field merger (`services/merge.py`) per [dedicated specification](./7.5%20—%20Audiobook%20Metadata%20Field%20Merger.md)

### Key Architectural Decisions
- **Primary Data Model**: Dataclass (fast, zero deps) with optional Pydantic mirror
- **Dependency Injection**: Constructor-based DI for easy testing and flexibility
- **Declarative Merging**: Configuration-driven precedence rules per field
- **Modular Services**: Composable utilities for HTML cleaning, format detection, etc.
- **Tracker Isolation**: Mappers handle tracker-specific transformations

### Essential Components
- **Engine**: Orchestrates the entire pipeline
- **Processors**: Content-type specific handlers (audiobook, music, video)
- **Sources**: Metadata extractors (embedded tags, APIs, path parsing)
- **Services**: Generic utilities (cleaning, merging, validation)
- **Mappers**: Tracker-specific output formatters

---

## Result Vision

**A crisp, plug-and-play metadata core** that's easy to reason about, test, and extend—without surprising knock-on effects in trackers or torrent creation.

---

For complete details on each component, please refer to the individual specification documents linked above. This conductor document provides the high-level overview and navigation structure for the entire metadata architecture.

---

### Suggested `pyproject.toml` extras

Keep runtime lean; let users opt into heavy stuff.

```toml
[project.optional-dependencies]
core = [
  "nh3>=0.2",
  "beautifulsoup4>=4.12",
  "mutagen>=1.47",
  "Pillow>=10.0",
  "python-slugify>=8.0",
  "Unidecode>=1.3",
  "cachetools>=5.3",
]

net = [
  "httpx>=0.27",
  "tenacity>=9.0",
  "aiolimiter>=1.1",
]

strict = [
  "pydantic>=2.7",
  "pydantic-settings>=2.4",
  "orjson>=3.10",
]

cli = [
  "rich>=13.7",
]

test = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "pytest-mock>=3.14",
  "freezegun>=1.5",
  "hypothesis>=6.100",
  "respx>=0.21",
]
```

**Install examples**

* Dev all-in: `pip install -e .[core,net,strict,cli,test]`
* Runtime minimal (headless box): `pip install -e .[core,net]`

---

### Tiny patterns to copy-paste

**httpx + tenacity + aiolimiter**

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from aiolimiter import AsyncLimiter

rate = AsyncLimiter(5, 1)  # 5 req/sec

class AudnexusAPI:
    def __init__(self, base_url: str, timeout=10.0):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        wait=wait_exponential(multiplier=0.3, min=0.5, max=5),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def get_book(self, asin: str) -> dict:
        async with rate:
            r = await self.client.get(f"/lookup/{asin}")
            r.raise_for_status()
            return r.json()
```

**Cache Audnexus lookups (cachetools)**

```python
from cachetools import TTLCache, cached

_cache = TTLCache(maxsize=2048, ttl=60*60)  # 1h

@cached(_cache)
def normalize_book_payload(raw: dict) -> dict:
    # expensive transforms / HTML cleaning / tag normalization
    ...
    return out
```

**Rich logging handler**

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)
log = logging.getLogger("mk_torrent")
```

**pydantic strict model (optional mirror)**

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class AudiobookMetaModel(BaseModel):
    title: str
    author: str
    album: str
    year: Optional[int] = Field(None, ge=1800, le=2100)
    genres: List[str] = []
    # ...

    @field_validator("genres", mode="before")
    @classmethod
    def norm_genres(cls, v):
        return sorted(set([g.strip().lower() for g in (v or []) if g]))
```

---

### TL;DR picks

* **Must-haves:** `httpx`, `tenacity`, `cachetools`, `nh3`, `rich`
* **Great optional adds:** `pydantic` + `pydantic-settings`, `aiolimiter`, `respx`, `rapidfuzz`, `orjson`
* **Keep:** `mutagen`, `Pillow`, `beautifulsoup4`, `python-dateutil`

---

## 11) Testing strategy

```
tests/
  unit/
    core/metadata/
      services/
        test_html_cleaner.py
        test_format_detector.py
      sources/
        test_pathinfo.py
        test_audnexus_normalize.py
      processors/
        test_audiobook_extract_path.py
        test_audiobook_enhance_merge.py
      validators/
        test_audiobook_validator.py
      test_engine_detect_and_registry.py
  integration/
    test_engine_audiobook_e2e.py  # tmpdir with an .m4b + fake audnexus
```

* Heavy use of fixtures & mocks; no real network.
* Add parameterized cases for path variants (`vol_` missing, weird parens, ASIN absent, unicode).

---

## 12) Migration plan (low-risk, incremental)

1. **Introduce `core/metadata/base.py`** and switch both `engine.py` & `audiobook.py` to import the single Protocol/dataclass.
2. **Extract services & sources** from `features/metadata_engine.py` into `core/metadata/services/*` and `sources/*`.
3. **Wire DI** in `core/metadata/engine.py` and register `audiobook` with these services.
4. **Implement `services/merge.py`** and move any hard-coded precedence to config.
5. **Add mappers/red.py**; update `api/trackers/red.py` to consume mapped payloads.
6. **Refactor tests**: split current monolithic test into unit suites; keep integration test for e2e sanity.
7. **Compatibility shim**: if needed, re-export `MetadataEngine` from `features/__init__.py` for one release.
8. **Delete old monolith** once downstream imports are migrated.

---

## 13) Error handling & logging

* Use `exceptions.py` for typed failures: `SourceUnavailable`, `MetadataConflict`, `ValidationError`.
* Structured logging (JSON-friendly): engine stages, chosen source for each field, validation summary, mapper output size.

---

## 14) Example: Processor skeleton

```python
# processors/audiobook.py
from typing import Dict, Any
from pathlib import Path
from ..base import AudiobookMeta

class AudiobookMetadata:
    def __init__(self, cleaner, detector, aud, pathinfo, merger):
        self.cleaner = cleaner
        self.detector = detector
        self.aud = aud
        self.pathinfo = pathinfo
        self.merger = merger

    def extract(self, source: Path) -> Dict[str, Any]:
        parts = []
        parts.append({"_src": "path", **self.pathinfo.parse(source)})
        parts.append({"_src": "embedded", **self.detector.tags(source)})  # optional
        asin = parts[0].get("asin") or parts[-1].get("asin")
        if asin:
            parts.append({"_src": "api", **self.aud.lookup(asin)})

        merged = self.merger.merge(parts)
        normalized = self.cleaner.sanitize(merged)
        # album fallback
        if not normalized.get("album"):
            normalized["album"] = normalized.get("title", "")
        return normalized

    def validate(self, md: Dict[str, Any]) -> Dict[str, Any]:
        # delegate to validators/audiobook_validator
        from ..validators.audiobook_validator import validate_audiobook
        return validate_audiobook(md)

    def enhance(self, md: Dict[str, Any]) -> Dict[str, Any]:
        # lightweight derived fields (display_name, zero-pad volume, etc.)
        out = dict(md)
        t, a = out.get("title", ""), out.get("author", "")
        if t and a:
            out["display_name"] = f"{t} by {a}"
        return out
```

---

## 15) Extension guide

* **Add a new source**: drop a file in `sources/`, expose a `lookup(...)` or `extract(...)`, register via DI in `engine.py`, then add to precedence in config.
* **Add a new content type**: create `processors/<type>.py`, reuse services, create `<type>_validator.py`, and update engine registry.
* **Support a new tracker**: implement `mappers/<tracker>.py` and keep `api/trackers/<tracker>.py` focused on HTTP/form mechanics.

---

## 16) Next steps (for this repo)

* [ ] Create `core/metadata/base.py` and port both engine & audiobook to it.
* [ ] Extract `HTMLCleaner`, `FormatDetector`, `PathInfo`, `Audnexus` into `services/` & `sources/`.
* [ ] Implement `services/merge.py` + `validators/audiobook_validator.py`.
* [ ] Add `mappers/red.py` and flip `api/trackers/red.py` to consume it.
* [ ] Split tests as per structure; keep one e2e.
* [ ] Remove dead code & typos in existing `audiobook.py`.

---

**Result**: A crisp, plug-and-play metadata core that’s easy to reason about, test, and extend—without surprising knock-on effects in trackers or torrent creation.
