# 10.5) Recommended Packages & Project Extras

Below are the add-ons that make the refactor sing. Grouped by concern with why they help and how they fit.

**✅ UPDATE: Many of these packages have been implemented in our template system and enhanced requirements.txt**

## Package Categories

### Networking & API (Audnexus, future sources)

* **httpx** — sync+async client, HTTP/2, sane timeouts. *(Future enhancement)*
* **tenacity** ✅ — clean retries with backoff/jitter. **IMPLEMENTED**
* **aiolimiter** — rate limiting if you go async. *(Future enhancement)*
* **respx** — mock `httpx` in tests. *(Future enhancement)*

> Currently using `requests` + `tenacity` + `requests-cache`. Future migration to `httpx` planned for async support.

### Data modeling & config

* **pydantic v2** ✅ — optional strict mirror of `AudiobookMeta`; great validators. **IMPLEMENTED**
* **pydantic-settings** ✅ — typed config (precedence, timeouts, drift rules). **IMPLEMENTED**
* **orjson** ✅ — super-fast JSON for logs/cache/IPC. **IMPLEMENTED**

### HTML & text cleanup

* **nh3** ✅ — modern sanitizer (preferred path). **IMPLEMENTED**
* **beautifulsoup4** ✅ — fallback when `nh3` isn't available. **IMPLEMENTED**
* **python-slugify** ✅ + **Unidecode** — safe filenames, ASCII fallbacks. **IMPLEMENTED**

### Media & file metadata

* **mutagen** ✅ — keep it (tags, duration, chapters). **IMPLEMENTED**
* **Pillow** ✅ — keep it (artwork dimensions/type). **IMPLEMENTED**
* **pymediainfo** ✅ — Advanced media file analysis. **IMPLEMENTED**
* *(Optional)* **python-magic** — MIME sniffing beyond extensions. *(Future enhancement)*

### Template System (NEW - IMPLEMENTED)

* **Jinja2** ✅ — Template engine with BBCode generation. **IMPLEMENTED**
* **bbcode** ✅ — BBCode validation and preview. **IMPLEMENTED**

### Async & concurrency (only if you go async)

* **anyio** — unifies trio/asyncio; `httpx` plays nice. *(Future enhancement)*
* **async-timeout** — explicit time scoping if you want it in addition to `httpx`. *(Future enhancement)*

### Caching & rate limiting

* **requests-cache** ✅ — HTTP response caching. **IMPLEMENTED**
* **diskcache** ✅ — persistent cache for batch runs/warm starts. **IMPLEMENTED**
* **cachetools** — TTL LRU for Audnexus responses, image probes. *(Future enhancement)*

### Logging & CLI UX

* **rich** ✅ — progress bars and pretty errors. **IMPLEMENTED**
* **rich-click** ✅ — Enhanced CLI with rich formatting. **IMPLEMENTED**
* **rich.logging.RichHandler** — readable, structured logs in dev. *(To be implemented)*
* *(Optional)* **structlog** — production JSON logs (pair with `orjson`). *(Future enhancement)*

### Validation & search niceties

* **rapidfuzz** ✅ — fast fuzzy matching when tags are noisy. **IMPLEMENTED**
* **python-dateutil** ✅ — you already have it; keep. **IMPLEMENTED**
* **pathvalidate** ✅ — Path validation and sanitization. **IMPLEMENTED**
* **regex** ✅ — Advanced regex patterns. **IMPLEMENTED**
* **isbnlib** ✅ — ISBN validation and processing. **IMPLEMENTED**
* **pycountry** ✅ — Country/language code handling. **IMPLEMENTED**

### Testing

* **pytest** ✅, **pytest-cov**, **pytest-mock** — baseline. **IMPLEMENTED**
* **freezegun** ✅ — freeze time for year/drift tests. **IMPLEMENTED**
* **pytest-snapshot** ✅ — snapshot testing for templates. **IMPLEMENTED**
* **hypothesis** — property tests for path parser & merge. *(Future enhancement)*
* **respx** — (again) excellent `httpx` mocking. *(Future enhancement)*

## Suggested `pyproject.toml` extras

Keep runtime lean; let users opt into heavy stuff.

```toml
[project.optional-dependencies]
# Core packages - IMPLEMENTED ✅
core = [
  "nh3>=0.3",
  "beautifulsoup4>=4.13",
  "mutagen>=1.47",
  "Pillow>=11.0",
  "python-slugify>=8.0",
  "pathvalidate>=3.2",
  "pymediainfo>=6.1",
  "regex>=2024.5",
  "isbnlib>=3.10",
  "pycountry>=24.6",
  "rapidfuzz>=3.9",
]

# Networking & caching - PARTIALLY IMPLEMENTED ✅
net = [
  "tenacity>=8.5",           # ✅ IMPLEMENTED
  "requests-cache>=1.2",     # ✅ IMPLEMENTED
  "diskcache>=5.6",          # ✅ IMPLEMENTED
  "xxhash>=3.4",             # ✅ IMPLEMENTED
  # Future: httpx, aiolimiter, respx
]

# Data modeling & validation - IMPLEMENTED ✅
strict = [
  "pydantic>=2.8",           # ✅ IMPLEMENTED
  "pydantic-settings>=2.4",  # ✅ IMPLEMENTED
  "orjson>=3.10",            # ✅ IMPLEMENTED
  "fastjsonschema>=2.20",    # ✅ IMPLEMENTED
]

# Template system - IMPLEMENTED ✅ (NEW)
templates = [
  "Jinja2>=3.1",             # ✅ IMPLEMENTED
  "bbcode>=1.1",             # ✅ IMPLEMENTED
]

# CLI & UX - IMPLEMENTED ✅
cli = [
  "rich>=14.1",              # ✅ IMPLEMENTED
  "rich-click>=1.8",         # ✅ IMPLEMENTED
  "typer>=0.17",             # ✅ IMPLEMENTED
  "prompt_toolkit>=3.0.43",  # ✅ IMPLEMENTED
  "tqdm>=4.66.1",            # ✅ IMPLEMENTED
]

# Testing - IMPLEMENTED ✅
test = [
  "pytest>=8.0",            # ✅ IMPLEMENTED
  "freezegun>=1.5",          # ✅ IMPLEMENTED
  "pytest-snapshot>=0.9",   # ✅ IMPLEMENTED
  "codespell>=2.3",          # ✅ IMPLEMENTED
  "bandit>=1.7",             # ✅ IMPLEMENTED
  # Future: pytest-cov, pytest-mock, hypothesis, respx
]

# Development tools - IMPLEMENTED ✅
dev = [
  "black>=24.0",             # ✅ IMPLEMENTED
  "ruff>=0.1.9",             # ✅ IMPLEMENTED
  "pre-commit>=3.6",         # ✅ IMPLEMENTED
]
```

## Install Examples

* **Dev all-in**: `pip install -e .[core,net,strict,templates,cli,test,dev]`
* **Runtime minimal (headless box)**: `pip install -e .[core,net,strict]`
* **Template development**: `pip install -e .[core,strict,templates]`
* **Current implementation**: All packages from requirements.txt (✅ **IMPLEMENTED**)

## What We Actually Implemented ✅

Our enhanced `requirements.txt` includes most recommended packages:

### ✅ **IMPLEMENTED PACKAGES**
- **Template System**: Jinja2, bbcode for professional BBCode generation
- **Data Validation**: Pydantic v2, pydantic-settings, fastjsonschema
- **Text Processing**: nh3, beautifulsoup4, python-slugify, regex
- **Media Handling**: mutagen, Pillow, pymediainfo for comprehensive metadata
- **Validation**: pathvalidate, isbnlib, pycountry, rapidfuzz
- **Performance**: orjson, tenacity, requests-cache, diskcache, xxhash
- **CLI/UX**: rich, rich-click, typer, prompt_toolkit, tqdm
- **Testing**: pytest, freezegun, pytest-snapshot, codespell, bandit
- **Development**: black, ruff, pre-commit

### 🔄 **FUTURE ENHANCEMENTS**
- **Async Support**: httpx, aiolimiter, anyio (when we add async processors)
- **Advanced Testing**: hypothesis, pytest-cov, pytest-mock, respx
- **Enhanced Caching**: cachetools (for TTL/LRU patterns)
- **Advanced Logging**: structlog (for production JSON logs)

## Implementation Patterns

### ✅ **IMPLEMENTED: Template System with Jinja2**

```python
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path

class TemplateRenderer:
    def __init__(self, template_dir: Optional[Path] = None):
        self.env = Environment(
            loader=FileSystemLoader(template_dir or self._default_template_dir()),
            undefined=StrictUndefined,  # Fail on missing variables
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False  # Don't escape BBCode
        )
        self._register_filters()

    def render_description(self, template_data: Dict[str, Any]) -> str:
        template = self.env.get_template('bbcode_desc.jinja')
        return template.render(**template_data)
```

### ✅ **IMPLEMENTED: Pydantic Data Models**

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class BookInfo(BaseModel):
    authors: List[str] = Field(default_factory=list)
    narrators: List[str] = Field(default_factory=list)
    publisher: str = ""
    genre: List[str] = Field(default_factory=list)
    identifiers: Identifiers
    language: str = "en"

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        return v.lower() if v else 'en'
```

### ✅ **IMPLEMENTED: Tenacity + Requests-Cache**

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import requests_cache

# Setup cached session with retries
session = requests_cache.CachedSession(
    cache_name='metadata_cache',
    expire_after=3600,  # 1 hour
    backend='filesystem'
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def fetch_metadata(url: str) -> dict:
    response = session.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

### 🔄 **FUTURE: httpx + tenacity + aiolimiter**

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

### ✅ **IMPLEMENTED: Rich CLI with Progress**

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
import logging

console = Console()

# Rich logging setup
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)

# Progress bars for batch operations
def process_files(files: List[Path]):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        for file in files:
            # Process file
            progress.advance(task)
```

### 🔄 **FUTURE: Cache Audnexus lookups (cachetools)**

```python
from cachetools import TTLCache, cached

_cache = TTLCache(maxsize=2048, ttl=60*60)  # 1h

@cached(_cache)
def normalize_book_payload(raw: dict) -> dict:
    # expensive transforms / HTML cleaning / tag normalization
    ...
    return out
```

## TL;DR picks

### ✅ **IMPLEMENTED & WORKING**
* **Template System**: `Jinja2`, `bbcode` - Professional BBCode generation
* **Data Validation**: `pydantic` v2, `pydantic-settings` - Type-safe models
* **Performance**: `orjson`, `tenacity`, `requests-cache`, `diskcache` - Fast & resilient
* **Text Processing**: `nh3`, `beautifulsoup4`, `python-slugify` - Clean HTML/text
* **Media Handling**: `mutagen`, `Pillow`, `pymediainfo` - Comprehensive metadata
* **Validation**: `rapidfuzz`, `pathvalidate`, `isbnlib`, `pycountry` - Robust validation
* **CLI/UX**: `rich`, `rich-click`, `typer` - Beautiful interface

### 🔄 **FUTURE ENHANCEMENTS**
* **Async Networking**: `httpx`, `aiolimiter` - When we add async processors
* **Advanced Caching**: `cachetools` - TTL/LRU patterns for Audnexus
* **Enhanced Testing**: `hypothesis`, `respx` - Property & async testing
* **Production Logging**: `structlog` - JSON logs for production

### 📦 **CURRENT STATE**
All core recommendations implemented in requirements.txt with 270+ tests passing. Template system operational with professional BBCode generation for RED tracker integration.
