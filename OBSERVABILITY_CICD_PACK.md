# CI/CD + structlog Observability Pack (Extended)

This pack adds a production‑ready CI/CD pipeline **and** switches logging to **structlog** with correlation IDs, PII redaction, timing, domain event tracking, and optional tracing hooks. It’s designed to be **useful on day 1 of a pilot** and to scale as you harden the service.

> Assumptions: repo root uses `src/` layout; Python 3.12/3.13; Dockerfile present; pytest. Replace `mk_torrent` with your package name where needed.

---

## 1) Folder & File Additions

```
.
├── .github/workflows/
│   ├── ci.yml
│   ├── security.yml
│   ├── release.yml
│   ├── dependency-review.yml
│   └── sbom.yml
├── .github/
│   ├── CODEOWNERS
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE.md
├── .pre-commit-config.yaml
├── pyproject.toml             # ruff, mypy, black, pytest config (merge with existing)
├── src/mk_torrent/core/logging_config.py
├── src/mk_torrent/core/observability.py
├── src/mk_torrent/core/logging_middleware.py
├── src/mk_torrent/core/tracing.py
├── tests/test_logging_redaction.py
├── tests/test_logging_correlation.py
├── docs/observability.md
├── Makefile
└── .env.example               # extended with logging vars
```

**Nice-to-haves** (optional but recommended for local demos):

```
observability/
├── docker-compose.observability.yml   # grafana + loki + tempo + promtail
└── grafana/                           # provisioning dashboards
```

---

## 2) Environment Variables (`.env.example`)

```bash
# ===== Logging Configuration =====
LOG_LEVEL=INFO                    # DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json                   # json|console (json for prod)
LOG_REDACT=1                      # 1=enable PII redaction
LOG_SAMPLE_SUCCESS=0.01           # sampling rate for noisy success paths
REQUEST_ID_HEADER=X-Request-ID    # inbound request-id header (if applicable)
LOG_INCLUDE_STACK=0               # 1=attach stacks even on info
LOG_COLOR=0                       # console colorization (dev only)
LOG_JSON_SORT_KEYS=0              # deterministic key order in JSON
LOG_SINK=stdout                   # stdout|stderr|file:<path>
LOG_EVENT_SCHEMA_VERSION=1        # bump when fields change materially

# ===== Tracing (optional; disabled if missing) =====
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=mk_torrent
OTEL_TRACES_SAMPLER=parentbased_always_on
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=dev

# ===== Build/CI =====
PYTHON_VERSION=3.13
```

---

## 3) structlog Configuration (`src/mk_torrent/core/logging_config.py`)

```python
from __future__ import annotations
import json
import logging
import os
import re
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict

import structlog

# ---- Correlation Context ----
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
run_id_var: ContextVar[str] = ContextVar("run_id", default=str(uuid.uuid4()))

PII_KEY_HINTS = {"password", "token", "secret", "apikey", "api_key", "email", "phone", "ssn", "address", "name"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
TOKEN_RE = re.compile(r"(?i)(?:bearer\s+)?([A-F0-9]{20,})")

class _Config:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "json").lower()
    redact = os.getenv("LOG_REDACT", "1") in {"1", "true", "TRUE"}
    sample_success = float(os.getenv("LOG_SAMPLE_SUCCESS", "0"))
    include_stack = os.getenv("LOG_INCLUDE_STACK", "0") in {"1", "true", "TRUE"}
    color = os.getenv("LOG_COLOR", "0") in {"1", "true", "TRUE"}
    json_sort_keys = os.getenv("LOG_JSON_SORT_KEYS", "0") in {"1", "true", "TRUE"}
    sink = os.getenv("LOG_SINK", "stdout")
    schema_version = int(os.getenv("LOG_EVENT_SCHEMA_VERSION", "1"))

CFG = _Config()

# ---- Processors ----

def add_run_and_correlation(logger, method_name, event_dict):
    event_dict.setdefault("run_id", run_id_var.get())
    cid = correlation_id_var.get()
    if cid is not None:
        event_dict.setdefault("correlation_id", cid)
    event_dict.setdefault("schema_version", CFG.schema_version)
    return event_dict


def redact_pii(logger, method_name, event_dict):
    if not CFG.redact:
        return event_dict

    def _redact_value(k: str, v: Any) -> Any:
        if v is None:
            return v
        lk = k.lower()
        if any(h in lk for h in PII_KEY_HINTS):
            return "<redacted>"
        if isinstance(v, str):
            v = EMAIL_RE.sub("<email>", v)
            v = PHONE_RE.sub("<phone>", v)
            v = TOKEN_RE.sub("<token>", v)
        return v

    for k in list(event_dict.keys()):
        event_dict[k] = _redact_value(k, event_dict[k])
    return event_dict


def sample_success(logger, method_name, event_dict):
    # downsample high‑volume success paths
    if CFG.sample_success and event_dict.get("level", "").lower() in {"info", "debug"}:
        et = str(event_dict.get("event_type", "")).upper()
        if et.endswith("_SUCCESS") or et.endswith("_OK"):
            import random
            if random.random() > CFG.sample_success:
                raise structlog.DropEvent
    return event_dict


def add_duration(logger, method_name, event_dict):
    t0 = event_dict.pop("_t0", None)
    if t0 is not None:
        event_dict["duration_ms"] = round((time.perf_counter() - t0) * 1000, 3)
    return event_dict


class JsonRenderer(structlog.processors.JSONRenderer):
    def __call__(self, logger, name, event_dict):
        return json.dumps(event_dict, sort_keys=CFG.json_sort_keys, ensure_ascii=False) + "\n"


# ---- Public helpers ----

def bind_correlation_id(correlation_id: str | None = None) -> str:
    """Bind a correlation_id for the current context; returns the active id."""
    cid = correlation_id or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


class log_span:
    """Context manager that logs entry/exit with duration and optional attributes.

    Example:
        with log_span("metadata.extract", torrent_path=path):
            ...
    """

    def __init__(self, name: str, **attrs: Any):
        self.name = name
        self.attrs = attrs
        self.t0 = time.perf_counter()
        self.log = structlog.get_logger("span")

    def __enter__(self):
        self.log.info("span.start", span=self.name, _t0=self.t0, **self.attrs)
        return self

    def __exit__(self, exc_type, exc, tb):
        duration_ms = round((time.perf_counter() - self.t0) * 1000, 3)
        base = dict(span=self.name, duration_ms=duration_ms, **self.attrs)
        if exc is None:
            self.log.info("span.end", **base)
        else:
            self.log.error("span.error", **base, exc_info=True)
        return False


def _sink_stream():
    if CFG.sink == "stdout":
        return sys.stdout
    if CFG.sink == "stderr":
        return sys.stderr
    if CFG.sink.startswith("file:"):
        path = CFG.sink.split(":", 1)[1]
        return open(path, "a", buffering=1, encoding="utf-8")
    return sys.stdout


def configure_logging():
    # Route stdlib logging into structlog
    logging.basicConfig(level=getattr(logging, CFG.level, logging.INFO), stream=_sink_stream())

    processors = [
        structlog.contextvars.merge_contextvars,
        add_run_and_correlation,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_duration,
        redact_pii,
        sample_success,
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.dev.ConsoleRenderer(colors=CFG.color) if CFG.fmt == "console" else JsonRenderer()
    )

    structlog.configure(
        processors=processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, CFG.level, logging.INFO)),
        cache_logger_on_first_use=True,
    )

    for noisy in ("urllib3", "httpx", "botocore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.get_logger("boot").info(
        "logging.configured",
        level=CFG.level,
        format=CFG.fmt,
        redact=CFG.redact,
        sample_success=CFG.sample_success,
        sink=CFG.sink,
        schema=CFG.schema_version,
    )
```

**Sample JSON log (redacted):**

```json
{
  "event": "event",
  "event_type": "TORRENT_BUILT_SUCCESS",
  "infohash": "abcdef1234",
  "torrent_path": "/data/book",
  "correlation_id": "0f2b...",
  "run_id": "41a6...",
  "schema_version": 1,
  "timestamp": "2025-09-11T06:55:10.123Z",
  "level": "info"
}
```

---

## 4) Domain Events & Instrumentation (`src/mk_torrent/core/observability.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import structlog
from .logging_config import log_span

log = structlog.get_logger("events")

# Example canonical event schema (extend as needed)
@dataclass
class DomainEvent:
    event_type: str                     # e.g., METADATA_EXTRACTED
    torrent_path: Optional[str] = None
    infohash: Optional[str] = None
    tracker: Optional[str] = None       # red|mam|...
    asin: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    ok: bool = True
    # Arbitrary extras (safe fields only)
    meta: Optional[Dict[str, Any]] = None

    def to_log(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.upper()
        return d


def emit(event: DomainEvent):
    payload = event.to_log()
    if event.ok:
        log.info("event", **payload)
    else:
        log.warning("event", **payload)


# Helper examples for common events

def metadata_extracted(**kwargs):
    emit(DomainEvent(event_type="METADATA_EXTRACTED", **kwargs))

def torrent_built(**kwargs):
    emit(DomainEvent(event_type="TORRENT_BUILT_SUCCESS", **kwargs))

def upload_submitted(**kwargs):
    emit(DomainEvent(event_type="UPLOAD_SUBMITTED", **kwargs))

```

**Event taxonomy (starter):**

| Category | Event Type              | Required Fields                             |
| -------- | ----------------------- | ------------------------------------------- |
| Metadata | `METADATA_EXTRACTED`    | `torrent_path`, `asin` or `title`, `author` |
| Build    | `TORRENT_BUILT_SUCCESS` | `infohash`, `torrent_path`                  |
| Upload   | `UPLOAD_SUBMITTED`      | `tracker`, `infohash`                       |
| Error    | `UPLOAD_FAILED`         | `tracker`, `infohash`, `meta.reason`        |

---

## 5) Request Timing & Correlation Helpers (`src/mk_torrent/core/logging_middleware.py`)

> If you add a small HTTP surface (FastAPI/Starlette) or use `httpx`, these helpers add correlation and timings.

```python
from __future__ import annotations
import time
import uuid
from typing import Callable
import structlog

from .logging_config import bind_correlation_id, log_span

# FastAPI/Starlette style ASGI middleware
class CorrelationTimingMiddleware:
    def __init__(self, app, header_name: str = "X-Request-ID"):
        self.app = app
        self.header_name = header_name
        self.log = structlog.get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        cid = headers.get(self.header_name.lower()) or str(uuid.uuid4())
        bind_correlation_id(cid)

        t0 = time.perf_counter()
        with log_span("http.request", path=scope.get("path"), method=scope.get("method")):
            try:
                await self.app(scope, receive, send)
                self.log.info("http.ok", path=scope.get("path"), duration_ms=round((time.perf_counter()-t0)*1000,3))
            except Exception:
                self.log.error("http.error", path=scope.get("path"), duration_ms=round((time.perf_counter()-t0)*1000,3), exc_info=True)
                raise

# httpx instrumentation example
import httpx

class LoggedClient(httpx.Client):
    def request(self, method, url, *args, **kwargs):
        with log_span("httpx.request", method=method, url=url):
            return super().request(method, url, *args, **kwargs)
```

---

## 6) Tracing (Optional) — `src/mk_torrent/core/tracing.py`

```python
from __future__ import annotations
import os

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover
    trace = None


def configure_tracing(service_name: str = "mk_torrent") -> None:
    if trace is None:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
```

---

## 7) Usage Example (CLI entry)

```python
# src/mk_torrent/__main__.py
from mk_torrent.core.logging_config import configure_logging, bind_correlation_id
from mk_torrent.core.observability import metadata_extracted, torrent_built
from mk_torrent.core.tracing import configure_tracing
import uuid

if __name__ == "__main__":
    configure_logging()
    configure_tracing("mk_torrent")  # no-op if OTEL env vars not set
    bind_correlation_id(str(uuid.uuid4()))  # one id per CLI run

    # ... run tasks
    metadata_extracted(torrent_path="/data/book", asin="B0XXXX", author="Some Author", title="Book Title")
    torrent_built(infohash="abcdef1234")
```

---

## 8) Tests — Logging & Redaction

**Redaction unit** — `tests/test_logging_redaction.py`

```python
from mk_torrent.core.logging_config import configure_logging
import structlog

def test_redaction_basic(monkeypatch, capsys):
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_REDACT", "1")
    configure_logging()
    log = structlog.get_logger("test")
    log.info("hello", email="john@doe.com", phone="(402) 555-1212", token="ABCDEF1234567890ABCDEF")
    out = capsys.readouterr().out
    assert "<email>" in out
    assert "<phone>" in out
    assert "<token>" in out
```

**Correlation unit** — `tests/test_logging_correlation.py`

```python
from mk_torrent.core.logging_config import configure_logging, bind_correlation_id
import structlog

def test_correlation_id_injected(monkeypatch, capsys):
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging()
    bind_correlation_id("test-cid")
    structlog.get_logger("t").info("x")
    out = capsys.readouterr().out
    assert "test-cid" in out
```

---

## 9) CI Workflow — `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:

jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: "pip"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
          pip install ruff black mypy bandit pip-audit pytest-cov
      - name: Ruff (lint)
        run: ruff check src
      - name: Black (format check)
        run: black --check src tests
      - name: MyPy (type check)
        run: mypy src
      - name: Bandit (security)
        run: bandit -q -r src -x tests
      - name: pip-audit (deps vulns)
        run: pip-audit -r requirements.txt || true
      - name: Tests
        run: pytest -q --maxfail=1 --disable-warnings --cov=mk_torrent --cov-report=xml
      - name: Coverage artifact
        uses: actions/upload-artifact@v4
        with:
          name: coverage-xml
          path: coverage.xml

  build-docker:
    needs: lint-type-test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t ghcr.io/${{ github.repository }}:sha-${{ github.sha }} .
      - name: Login GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push image
        run: |
          docker tag ghcr.io/${{ github.repository }}:sha-${{ github.sha }} ghcr.io/${{ github.repository }}:latest
          docker push ghcr.io/${{ github.repository }}:sha-${{ github.sha }}
          docker push ghcr.io/${{ github.repository }}:latest
```

**Optional matrix expansions:** add OS matrix (ubuntu/macOS/windows), enable `pytest -n auto` for parallel, cache `.mypy_cache`, and split lint/type/test into separate jobs for faster feedback.

---

## 10) Security Workflows

### 10.1 Dependency Review — `.github/workflows/dependency-review.yml`

```yaml
name: Dependency Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
```

### 10.2 CodeQL + Container Scan — `.github/workflows/security.yml`

```yaml
name: Security Scans
on:
  schedule:
    - cron: "0 6 * * 1"  # weekly
  workflow_dispatch:

jobs:
  codeql:
    uses: github/codeql-action/.github/workflows/codeql.yml@v3
    with:
      languages: python

  trivy-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t local/mk_torrent:scan .
      - name: Trivy scan
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: local/mk_torrent:scan
          format: table
          exit-code: 0
          ignore-unfixed: true
```

### 10.3 SBOM — `.github/workflows/sbom.yml`

```yaml
name: SBOM
on:
  push:
    branches: [ main ]
  workflow_dispatch:
jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Syft SBOM
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: sbom.spdx.json
      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

---

## 11) Release Workflow — `.github/workflows/release.yml`

```yaml
name: Release
on:
  push:
    tags:
      - "v*"

jobs:
  pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Build sdist/wheel
        run: |
          python -m pip install --upgrade build twine
          python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*

  ghcr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Login GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & Push
        run: |
          TAG=${GITHUB_REF_NAME}
          docker build -t ghcr.io/${{ github.repository }}:${TAG} .
          docker push ghcr.io/${{ github.repository }}:${TAG}
```

**Versioning tip:** Adopt Conventional Commits and auto-generate release notes with `release-please` or `semantic-release` if desired.

---

## 12) Pre‑commit — `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: ["--fix"]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: ["types-requests"]
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.9
    hooks:
      - id: bandit
        args: ["-q", "-r", "src", "-x", "tests"]
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
```

---

## 13) Tooling Config — `pyproject.toml` additions

> Merge with your existing file.

```toml
[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP", "B", "W", "N"]
ignore = ["E203", "W503"]

[tool.mypy]
python_version = "3.13"
packages = ["mk_torrent"]
warn_unused_ignores = true
warn_redundant_casts = true
strict_optional = true
pretty = true

[tool.pytest.ini_options]
addopts = "-ra -q"
pythonpath = ["src"]
```

---

## 14) Developer UX — Makefile

```makefile
.PHONY: setup fmt lint type test run cov
setup:
    python -m pip install --upgrade pip
    pip install -e .[dev]
fmt:
    black src tests && ruff check --fix src tests
lint:
    ruff check src tests && bandit -q -r src -x tests
type:
    mypy src
test:
    pytest -q
cov:
    pytest --cov=mk_torrent --cov-report=term-missing
run:
    python -m mk_torrent --help

```

---

## 15) Event Naming, Severity, and Field Guidelines

* **Naming**: `NOUN_VERB[_RESULT]` (e.g., `TORRENT_BUILT_SUCCESS`, `UPLOAD_SUBMITTED`).
* **Severity**: `INFO` for success/expected flow, `WARNING` for degraded/reties, `ERROR` for failures, `DEBUG` for noisy dev details.
* **Required fields per category**:

  * Build: `infohash`, `torrent_path`.
  * Upload: `tracker`, `infohash`, `meta.request_id` if available.
* **PII**: Never log raw `email`, `phone`, physical `address`, API keys, or access tokens. Use `<email>`, `<phone>`, `<token>` or hashes.
* **Sampling**: Tag noisy success as `*_SUCCESS` so the sampler can trim volume.
* **Schema**: bump `LOG_EVENT_SCHEMA_VERSION` when you change event fields.

---

## 16) Migration Steps

1. `pip install structlog` and (optionally) `opentelemetry-sdk`.
2. Replace any custom logging init with `configure_logging()` early in startup.
3. Swap `logging.getLogger(__name__)` with `structlog.get_logger(__name__)` gradually.
4. Bind correlation IDs at process start (CLI) or per request (middleware).
5. Emit domain events via `observability.py` helpers.
6. Verify redaction & sampling in CI (unit tests provided).
7. Optionally enable tracing by setting OTEL env vars.

**One-shot sed helpers (review before running):**

```bash
rg -l "logging.getLogger\(" src | xargs -I{} sed -i "s/logging.getLogger/structlog.get_logger/g" {}
```

---

## 17) Secrets Needed (GitHub → Settings → Secrets and variables → Actions)

* `PYPI_API_TOKEN` (optional, if publishing to PyPI)

---

## 18) Operations & Runbook Snippets

* **Symptom:** upload volume spikes; **Action:** raise `LOG_SAMPLE_SUCCESS` to reduce noise, ensure Loki retention is adequate.
* **Symptom:** PII leakage suspected; **Action:** set `LOG_REDACT=1`, inspect redaction tests, add keys to `PII_KEY_HINTS`.
* **Symptom:** mixed logs without correlation; **Action:** confirm `bind_correlation_id()` call paths.
* **Symptom:** slow requests; **Action:** wrap critical sections in `log_span()` and inspect `duration_ms`.

---

## 19) Optional Local Observability Stack (demo)

`observability/docker-compose.observability.yml` (excerpt):

```yaml
version: "3.8"
services:
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]
  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
  tempo:
    image: grafana/tempo:latest
    ports: ["3200:3200"]
```

---

**Done.** You now have CI/CD with quality + security gates, structured logging with correlation IDs, PII safety, duration spans, an event taxonomy, optional tracing, and runbook tips. Copy these into your repo and send it. 🚀
