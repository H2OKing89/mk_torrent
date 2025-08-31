# qBittorrent API for Python — `qBittorrent_api_python.md`

> A overview of the `qbittorrent-api` Python package: what it supports, how to install it, how to use it (both the one-to-one endpoint calls and the ergonomic namespaces), configuration knobs, performance tips, exceptions, and an async-friendly pattern. If qBittorrent is the engine, this client is your well-labeled dashboard.

<details>
<summary><strong>Table of Contents</strong></summary>

* [Introduction](#introduction)
* [Features](#features)
* [Installation](#installation)
* [Getting Started](#getting-started)
* [Usage](#usage)

  * [Namespaces](#namespaces)
  * [Two ways to call the API](#two-ways-to-call-the-api)
* [Behavior & Configuration](#behavior--configuration)

  * [Credentials & Environment Variables](#credentials--environment-variables)
  * [Session Management](#session-management)
  * [Untrusted Certificates](#untrusted-certificates)
  * [Requests/HTTPAdapter Options](#requestshttpadapter-options)
  * [Custom HTTP Headers](#custom-http-headers)
  * [Unimplemented Endpoints & Version Checks](#unimplemented-endpoints--version-checks)
  * [Logging Noise Control](#logging-noise-control)
* [Performance](#performance)
* [Exceptions](#exceptions)
* [Async Support (the safe way)](#async-support-the-safe-way)
* [Production Tips](#production-tips)
* [See Also](#see-also)

</details>

---

## Introduction

Python client for the qBittorrent Web API. As of now it **supports qBittorrent v5.1.2 / Web API v2.11.4 (released July 2, 2025)**. ([qbittorrent-api.readthedocs.io][1])

---

## Features

* Implements the **entire** qBittorrent Web API surface.
* Automatically checks server version/feature support for each endpoint.
* When the auth cookie expires, **re-auth happens automatically** on the next API call. ([qbittorrent-api.readthedocs.io][1])

---

## Installation

```bash
# Latest from PyPI
python -m pip install qbittorrent-api

# Pin a specific release
python -m pip install qbittorrent-api==2024.3.60

# From GitHub main
pip install git+https://github.com/rmartin16/qbittorrent-api.git@main#egg=qbittorrent-api
```

Don’t forget to enable the Web UI in qBittorrent (Tools → Preferences → Web UI). If exposing the API to the internet, follow the upstream hardening recommendations. ([qbittorrent-api.readthedocs.io][1])

---

## Getting Started

```python
import qbittorrentapi

# WebUI connection info
conn_info = dict(
    host="localhost",
    port=8080,
    username="admin",
    password="adminadmin",
)

qbt_client = qbittorrentapi.Client(**conn_info)

# Optional: validate credentials explicitly (not required for normal usage)
try:
    qbt_client.auth_log_in()
except qbittorrentapi.LoginFailed as e:
    print(e)

# If the client won't be long-lived, log out (or use a context manager)
qbt_client.auth_log_out()

# Context manager variant
with qbittorrentapi.Client(**conn_info) as q:
    if q.torrents_add(urls="...") != "Ok.":
        raise Exception("Failed to add torrent.")

# Show basic info
print(f"qBittorrent: {qbt_client.app.version}")
print(f"Web API:     {qbt_client.app.web_api_version}")
for k, v in qbt_client.app.build_info.items():
    print(f"{k}: {v}")

# Iterate torrents
for t in qbt_client.torrents_info():
    print(f"{t.hash[-6:]}: {t.name} ({t.state})")

# Stop everything (yes, everything)
qbt_client.torrents.stop.all()
```

([qbittorrent-api.readthedocs.io][1])

---

## Usage

### Namespaces

Endpoints are grouped in eight namespaces: **auth**, **app**, **log**, **sync**, **transfer**, **torrents**, **rss**, and **search**. ([qbittorrent-api.readthedocs.io][1])

### Two ways to call the API

1. **One-to-one methods** on the client:

```python
q = qbittorrentapi.Client(host="localhost:8080", username="admin", password="adminadmin")
q.app_version()
q.rss_rules()
q.torrents_info()
q.torrents_resume(torrent_hashes="...")
```

2. **Ergonomic namespaces** with properties/helpers:

```python
q = qbittorrentapi.Client(host="localhost:8080", username="admin", password="adminadmin")

# Change a preference (partial update)
is_dht_enabled = q.app.preferences.dht
q.app.preferences = dict(dht=not is_dht_enabled)

# Manage torrents
q.torrents.stop.all()

# Peek different log views
q.log.main.warning()
q.log.main.normal()
```

Many returned objects expose contextual methods, especially torrents:

```python
for t in q.torrents.info.active():
    t.set_location(location="/home/user/torrents/")
    t.reannounce()
    t.upload_limit = -1
```

([qbittorrent-api.readthedocs.io][1])

---

## Behavior & Configuration

### Credentials & Environment Variables

Provide credentials while constructing the `Client`, or later via `auth_log_in()`. You can also set environment variables: `QBITTORRENTAPI_HOST`, `QBITTORRENTAPI_USERNAME`, `QBITTORRENTAPI_PASSWORD`. ([qbittorrent-api.readthedocs.io][2])

### Session Management

The library keeps you logged in automatically, refreshing sessions when cookies expire. **Each new `Client` instance creates a new session**, so prefer a single long-lived instance or a context manager—and do call `auth_log_out()` in bulk-client workflows to avoid extra memory usage in qBittorrent. ([qbittorrent-api.readthedocs.io][2])

### Untrusted Certificates

For lab/self-signed setups you can disable verification with `VERIFY_WEBUI_CERTIFICATE=False` or set env var `QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE`. (Encrypted, yes; trusted, no—use wisely.) ([qbittorrent-api.readthedocs.io][2])

### Requests/HTTPAdapter Options

Pass Requests options globally (e.g., timeouts, proxies) via `REQUESTS_ARGS`, and connection pooling via `HTTPADAPTER_ARGS`. You can also override per call. ([qbittorrent-api.readthedocs.io][2])

```python
q = qbittorrentapi.Client(
    host="https://qbt.local:8080",
    username="admin", password="adminadmin",
    REQUESTS_ARGS={"timeout": (3.1, 30)},
    HTTPADAPTER_ARGS={"pool_connections": 100, "pool_maxsize": 100},
)
# Or per-call:
q.torrents_info(requests_args={"timeout": (3.1, 30)})
```

### Custom HTTP Headers

Add global headers with `EXTRA_HEADERS={...}` or per-request headers when calling endpoints—handy for reverse proxies or extra auditing. ([qbittorrent-api.readthedocs.io][2])

### Unimplemented Endpoints & Version Checks

* Set `RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True` to raise instead of returning `None` when your server lacks a newer endpoint.
* Set `RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True` to raise `UnsupportedQbittorrentVersion` when the server isn’t “fully” supported yet. (You can also probe via the `Version` helper.) ([qbittorrent-api.readthedocs.io][2])

### Logging Noise Control

Lower debug chatter by passing `DISABLE_LOGGING_DEBUG_OUTPUT=True`, or tune loggers for `qbittorrentapi`, `requests`, and `urllib3`. ([qbittorrent-api.readthedocs.io][2])

---

## Performance

By default, some endpoints return **rich objects** (attributes + convenience methods like `start()`/`stop()`), which is great ergonomically but can cost CPU for huge payloads—e.g., `torrents_files()`. To optimize, you can:

* Set `SIMPLE_RESPONSES=True` on the client to always get raw JSON, **or**
* Set `SIMPLE_RESPONSES=True` on heavy individual calls. ([qbittorrent-api.readthedocs.io][3])

```python
# global
q = qbittorrentapi.Client(..., SIMPLE_RESPONSES=True)

# per-call
files = q.torrents.files(torrent_hash="...", SIMPLE_RESPONSES=True)
```

---

## Exceptions

The library exposes a clear hierarchy covering auth, connectivity, and HTTP statuses. Highlights:

* **`APIConnectionError`** — transport-level issues (DNS/TLS/refused).
* **`LoginFailed`** — credentials failed (can bubble up on any call that attempts (re)login).
* **`HTTPError`** → `HTTP4XXError` / `HTTP5XXError`, with fine-grained classes like `Unauthorized401Error`, `Forbidden403Error`, `NotFound404Error`, `Conflict409Error`, `UnsupportedMediaType415Error`, `InternalServerError500Error`, etc.
* **`UnsupportedQbittorrentVersion`** — server not fully supported by this client yet.
* **File/torrent file** errors: `FileError`, `TorrentFileError`, `TorrentFileNotFoundError`, `TorrentFilePermissionError`. ([qbittorrent-api.readthedocs.io][4])

> Pro tip: Treat 4XX as “fix your request or permissions” and 5XX as “server had a moment.” Always log `http_status_code` when catching `HTTPError`.

---

## Async Support (the safe way)

`qbittorrent-api` is synchronous. In async apps, run calls in the event loop’s thread pool using `asyncio.to_thread(...)`. It’s simple and it plays nicely with your coroutines. ([qbittorrent-api.readthedocs.io][5])

```python
import asyncio
import qbittorrentapi

q = qbittorrentapi.Client()

async def fetch_qbt_info():
    return await asyncio.to_thread(q.app_build_info)

print(asyncio.run(fetch_qbt_info()))
```

If you only need a single call’s result (e.g., `torrents_info(category="uploaded")`), wrap **just that** method with `to_thread` so the rest of your async code remains non-blocking. ([qbittorrent-api.readthedocs.io][5])

---

## Production Tips

* **Pin versions** (both qBittorrent and `qbittorrent-api`) to keep behavior deterministic across deployments.
* **Use timeouts** (`REQUESTS_ARGS={"timeout": (3.1, 30)}`) so flaky networks don’t freeze workers. ([qbittorrent-api.readthedocs.io][2])
* **Prefer a single client instance** per process; use the **context manager** for short-lived tasks. ([qbittorrent-api.readthedocs.io][2])
* **Respect TLS**: only set `VERIFY_WEBUI_CERTIFICATE=False` when you understand the risks. ([qbittorrent-api.readthedocs.io][2])
* **Flip on SIMPLE\_RESPONSES** for huge result sets; keep rich objects where they help readability. ([qbittorrent-api.readthedocs.io][3])

---

## See Also

* **Introduction** (features, install, quick start). ([qbittorrent-api.readthedocs.io][1])
* **Behavior & Configuration** (env vars, sessions, TLS, requests/adapter, headers, version checks). ([qbittorrent-api.readthedocs.io][2])
* **Performance** (rich objects vs JSON and `SIMPLE_RESPONSES`). ([qbittorrent-api.readthedocs.io][3])
* **Exceptions** (error taxonomy and meanings). ([qbittorrent-api.readthedocs.io][4])
* **Async Support** (thread-pool pattern). ([qbittorrent-api.readthedocs.io][5])

<sub>Ship it. And may your swarm always be seedy. 🌱</sub>

[1]: https://qbittorrent-api.readthedocs.io/ "qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[2]: https://qbittorrent-api.readthedocs.io/en/latest/behavior%26configuration.html "Behavior & Configuration - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[3]: https://qbittorrent-api.readthedocs.io/en/latest/performance.html "Performance - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[4]: https://qbittorrent-api.readthedocs.io/en/latest/exceptions.html "Exceptions - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[5]: https://qbittorrent-api.readthedocs.io/en/latest/async.html "Async Support - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
