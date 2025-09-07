# qBittorrent Client (Python) — `qBittorrent_api_client.md`

> A practical, guide to the `qbittorrent-api` **Client**: constructor options, connection patterns, performance knobs, version/compat checks, session lifecycle, and battle-tested recipes (timeouts, proxies, reverse proxies, headers). Everything here is safe to paste into your repo’s docs.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Web API coverage" src="https://img.shields.io/badge/qBittorrent%20Web%20API-2.x-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [Constructor & Options](#constructor--options)
* [SIMPLE\_RESPONSES and Performance](#simple_responses-and-performance)
* [Requests/HTTPAdapter/Headers](#requestshttpadapterheaders)
* [Certificates & HTTPS](#certificates--https)
* [Sessions & Context Manager](#sessions--context-manager)
* [Version/Feature Compatibility](#versionfeature-compatibility)
* [Mixins & Surface Area](#mixins--surface-area)
* [Reverse Proxy & Host Format](#reverse-proxy--host-format)
* [Error Handling Cheatsheet](#error-handling-cheatsheet)
* [Full Example: hardened client factory](#full-example-hardened-client-factory)
* [See Also](#see-also)

</details>

---

## Overview

`Client` is the main entry point to qBittorrent’s Web API in Python. It aggregates major endpoint groups (torrents, transfer, search, RSS, torrent creator, logs/sync) and exposes ergonomic helpers plus lower-level controls for HTTP behavior, TLS validation, headers, and more. (See mixins list below.)

updated: 2025-09-06T19:00:01-05:00
---

## Quick Start

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")
torrents = client.torrents_info()
for t in torrents:
    print(t.name, t.state)
```

* If you pass `username` and `password` at construction, an explicit `auth_log_in()` call isn’t required; the client authenticates when needed. ([qbittorrent-api.readthedocs.io][1])

---

## Constructor & Options

```text
Client(
  host='', port=None, username=None, password=None, *,
  EXTRA_HEADERS=None, REQUESTS_ARGS=None, HTTPADAPTER_ARGS=None,
  VERIFY_WEBUI_CERTIFICATE=True, FORCE_SCHEME_FROM_HOST=False,
  RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
  RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
  VERBOSE_RESPONSE_LOGGING=False, SIMPLE_RESPONSES=False,
  DISABLE_LOGGING_DEBUG_OUTPUT=False
)
```

* **host**: `"[http[s]://]hostname[:port][/path]"` (path is allowed; useful for reverse proxies).
* **SIMPLE\_RESPONSES**: return bare JSON vs richer objects.
* **VERIFY\_WEBUI\_CERTIFICATE**: set `False` only when you truly accept untrusted TLS.
* **EXTRA\_HEADERS / REQUESTS\_ARGS / HTTPADAPTER\_ARGS**: per-session HTTP behavior (timeouts, proxies, pools).
* **FORCE\_SCHEME\_FROM\_HOST**: trust your `http/https` scheme even if auto-detect disagrees.
* **RAISE\_NOTIMPLEMENTEDERROR\_FOR\_UNIMPLEMENTED\_API\_ENDPOINTS**: raise instead of returning `None` for endpoints your qBittorrent doesn’t support.
* **RAISE\_ERROR\_FOR\_UNSUPPORTED\_QBITTORRENT\_VERSIONS**: raise if your qBittorrent isn’t fully supported.
* **DISABLE\_LOGGING\_DEBUG\_OUTPUT**: globally quiet debug logs (client + requests + urllib3). ([qbittorrent-api.readthedocs.io][1])

---

## SIMPLE\_RESPONSES and Performance

Richer response objects are convenient (attributes + contextual methods) but carry conversion overhead on large payloads like `torrents_files()`. You can globally set `SIMPLE_RESPONSES=True`, or enable it per call (recommended for big lists/files). ([qbittorrent-api.readthedocs.io][2])

```python
# global
client = Client(..., SIMPLE_RESPONSES=True)

# per-call
files = client.torrents_files(torrent_hash="...", SIMPLE_RESPONSES=True)
```

---

## Requests/HTTPAdapter/Headers

The client uses **Requests** under the hood and lets you thread through configuration:

```python
client = Client(
    host="https://qbt.example.com",
    username="admin", password="adminadmin",
    REQUESTS_ARGS={"timeout": (3.1, 30), "proxies": {"https": "http://proxy:3128"}},
    HTTPADAPTER_ARGS={"pool_connections": 100, "pool_maxsize": 100},
    EXTRA_HEADERS={"X-My-Header": "value"},
)
```

You can also pass these per endpoint call if you only need them sometimes (e.g., a longer timeout for a heavy request). ([qbittorrent-api.readthedocs.io][3])

---

## Certificates & HTTPS

For self-signed certs in test labs, you can disable verification:

```python
Client(..., VERIFY_WEBUI_CERTIFICATE=False)
```

Prefer real certificates in production—verification is your MITM safety net. An environment flag is also supported: `QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE`. ([qbittorrent-api.readthedocs.io][3])

---

## Sessions & Context Manager

* The library manages login sessions automatically and will re-authenticate when needed.
* Each **new** `Client` instance creates a **new** session in qBittorrent; if you spin up many clients, either use a **context manager** or call `auth_log_out()` so you don’t bloat the daemon’s memory. ([qbittorrent-api.readthedocs.io][3])

```python
from qbittorrentapi import Client

with Client(host="localhost:8080", username="admin", password="adminadmin") as qbt:
    if qbt.torrents_add(urls="...") != "Ok.":
        raise RuntimeError("Failed to add torrent.")
```

---

## Version/Feature Compatibility

Two knobs for safer automation:

* `RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True` → raise `NotImplementedError` if you call endpoints your server version doesn’t expose (e.g., very old Web API).
* `RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True` → raise `UnsupportedQbittorrentVersion` when the client doesn’t fully support the connected qBittorrent. You can also inspect support via the `Version` helper. ([qbittorrent-api.readthedocs.io][3])

---

## Mixins & Surface Area

`Client` composes multiple API areas via mixins, including:

* `LogAPIMixIn`, `SyncAPIMixIn`, `TransferAPIMixIn`, `TorrentsAPIMixIn`, `TorrentCreatorAPIMixIn`, `RSSAPIMixIn`, `SearchAPIMixIn`.
  This is why you can call methods like `torrents_info()`, `transfer_info()`, `search_start()`, `rss_add_feed()`, and the Torrent Creator endpoints directly from the client. ([qbittorrent-api.readthedocs.io][1])

> Tip: Application and Authentication endpoints are also exposed via convenient namespaces—see your `client.application` and `client.auth` docs for details.

---

## Reverse Proxy & Host Format

The `host` accepts a base path—handy behind Nginx/Traefik:

```python
# qBittorrent is reverse-proxied at https://example.com/qbt/
client = Client(host="https://example.com/qbt/", username="...", password="...")
```

If the scheme detection ever misfires in unusual setups, set `FORCE_SCHEME_FROM_HOST=True` to trust the scheme you provided. ([qbittorrent-api.readthedocs.io][1])

---

## Error Handling Cheatsheet

Common exceptions you’ll want to catch:

* **APIConnectionError** — connectivity (DNS, TLS, refused), and base class for HTTP errors.
* **LoginFailed** — authentication failed (can occur on any call if refresh-login fails).
* **Forbidden403Error / Unauthorized401Error** — session not authorized (banned IP, bad cookie, XSS/host header).
* **NotFound404Error** — resource not found (e.g., torrent hash missing).
* **Conflict409Error** — arguments don’t make sense for the endpoint (e.g., invalid state).
* **UnsupportedQbittorrentVersion** — server not fully supported by the client. ([qbittorrent-api.readthedocs.io][4])

---

## Full Example: hardened client factory

```python
from qbittorrentapi import Client, exceptions as qba_exc

def make_client(host, user, pwd, *, simple=False, verify=True):
    return Client(
        host=host,
        username=user,
        password=pwd,
        SIMPLE_RESPONSES=simple,
        VERIFY_WEBUI_CERTIFICATE=verify,
        REQUESTS_ARGS={"timeout": (3.1, 30)},
        HTTPADAPTER_ARGS={"pool_connections": 50, "pool_maxsize": 50},
        RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
        RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
        DISABLE_LOGGING_DEBUG_OUTPUT=True,
    )

try:
    qbt = make_client("https://qbt.example.com/api/", "admin", "adminadmin",
                      simple=True, verify=False)
    print("Web UI:", qbt.app_web_api_version())
    print("# Torrents:", len(qbt.torrents_info()))
except qba_exc.LoginFailed:
    print("Invalid credentials.")
except qba_exc.APIConnectionError as e:
    print("Cannot reach qBittorrent:", e)
finally:
    try:
        qbt.auth_log_out()
    except Exception:
        pass
```

---

## See Also

* **Client reference (official docs):** constructor, parameters, and mixins. ([qbittorrent-api.readthedocs.io][1])
* **Behavior & Configuration:** sessions, env vars (`QBITTORRENTAPI_HOST/USERNAME/PASSWORD`, `QBITTORRENTAPI_DO_NOT_VERIFY_WEBUI_CERTIFICATE`), requests/adapter settings, logging, version checks. ([qbittorrent-api.readthedocs.io][3])
* **Performance:** guidance on `SIMPLE_RESPONSES`. ([qbittorrent-api.readthedocs.io][2])
* **Exceptions:** full error taxonomy and meanings. ([qbittorrent-api.readthedocs.io][4])

> *Pin your qBittorrent and `qbittorrent-api` versions in production CI to avoid accidental breaking changes. Add health checks that hit `app_version()` and `app_web_api_version()` on startup so you fail fast if a reverse proxy or TLS setting regressed.*

[1]: https://qbittorrent-api.readthedocs.io/en/latest/apidoc/client.html "Client - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[2]: https://qbittorrent-api.readthedocs.io/en/latest/performance.html "Performance - qbittorrent-api 2025.5.1.dev12+gc1103a2 documentation"
[3]: https://qbittorrent-api.readthedocs.io/en/latest/behavior%26configuration.html "Behavior & Configuration - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
[4]: https://qbittorrent-api.readthedocs.io/en/latest/exceptions.html "Exceptions - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
