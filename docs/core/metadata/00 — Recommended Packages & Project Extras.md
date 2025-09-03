# 10.5) Recommended Packages & Project Extras

Below are the add-ons that make the refactor sing. Grouped by concern with why they help and how they fit.

## Package Categories

### Networking & API (Audnexus, future sources)

* **httpx** — sync+async client, HTTP/2, sane timeouts.
* **tenacity** — clean retries with backoff/jitter.
* **aiolimiter** — rate limiting if you go async.
* **respx** — mock `httpx` in tests.

> Standardize on `httpx` across the metadata core. Keep a tiny adapter for `requests` only if something upstream can't move yet.

### Data modeling & config

* **pydantic v2** — optional strict mirror of `AudiobookMeta`; great validators.
* **pydantic-settings** — typed config (precedence, timeouts, drift rules).
* **orjson** — super-fast JSON for logs/cache/IPC.

### HTML & text cleanup

* **nh3** — modern sanitizer (preferred path).
* **beautifulsoup4** — fallback when `nh3` isn't available.
* **python-slugify** + **Unidecode** — safe filenames, ASCII fallbacks.

### Media & file metadata

* **mutagen** — keep it (tags, duration, chapters).
* **Pillow** — keep it (artwork dimensions/type).
* *(Optional)* **python-magic** — MIME sniffing beyond extensions.

### Async & concurrency (only if you go async)

* **anyio** — unifies trio/asyncio; `httpx` plays nice.
* **async-timeout** — explicit time scoping if you want it in addition to `httpx`.

### Caching & rate limiting

* **cachetools** — TTL LRU for Audnexus responses, image probes.
* *(Optional)* **diskcache** — persistent cache for batch runs/warm starts.

### Logging & CLI UX

* **rich** — progress bars and pretty errors.
* **rich.logging.RichHandler** — readable, structured logs in dev.
* *(Optional)* **structlog** — production JSON logs (pair with `orjson`).

### Validation & search niceties

* **rapidfuzz** — fast fuzzy matching when tags are noisy.
* **python-dateutil** — you already have it; keep.

### Testing

* **pytest**, **pytest-cov**, **pytest-mock** — baseline.
* **freezegun** — freeze time for year/drift tests.
* **hypothesis** — property tests for path parser & merge.
* **respx** — (again) excellent `httpx` mocking.

## Suggested `pyproject.toml` extras

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

## Install Examples

* Dev all-in: `pip install -e .[core,net,strict,cli,test]`
* Runtime minimal (headless box): `pip install -e .[core,net]`

## Implementation Patterns

### httpx + tenacity + aiolimiter

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

### Cache Audnexus lookups (cachetools)

```python
from cachetools import TTLCache, cached

_cache = TTLCache(maxsize=2048, ttl=60*60)  # 1h

@cached(_cache)
def normalize_book_payload(raw: dict) -> dict:
    # expensive transforms / HTML cleaning / tag normalization
    ...
    return out
```

### Rich logging handler

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

### pydantic strict model (optional mirror)

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

## TL;DR picks

* **Must-haves:** `httpx`, `tenacity`, `cachetools`, `nh3`, `rich`
* **Great optional adds:** `pydantic` + `pydantic-settings`, `aiolimiter`, `respx`, `rapidfuzz`, `orjson`
* **Keep:** `mutagen`, `Pillow`, `beautifulsoup4`, `python-dateutil`
