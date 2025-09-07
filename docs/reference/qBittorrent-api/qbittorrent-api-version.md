# qBittorrent Version Helpers (Python) — `qBittorrent_api_version.md`

> Sanity-check your qBittorrent **app** and **Web API** versions against what the `qbittorrent-api` library officially supports. Use these helpers to fail fast, gate features, and keep your automation from stepping on rakes.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Module" src="https://img.shields.io/badge/API-Version-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [Method Reference](#method-reference)

  * [`is_api_version_supported(api_version) → bool`](#is_api_version_supportedapi_version--bool)
  * [`is_app_version_supported(app_version) → bool`](#is_app_version_supportedapp_version--bool)
  * [`latest_supported_api_version() → str`](#latest_supported_api_version--str)
  * [`latest_supported_app_version() → str`](#latest_supported_app_version--str)
  * [`supported_api_versions() → set[str]`](#supported_api_versions--setstr)
  * [`supported_app_versions() → set[str]`](#supported_app_versions--setstr)
* [Practical Recipes](#practical-recipes)

  * [Fail fast at startup](#fail-fast-at-startup)
  * [Gate a feature by Web API version](#gate-a-feature-by-web-api-version)
  * [Soft-warn on “unknown but probably fine” versions](#soft-warn-on-unknown-but-probably-fine-versions)
* [Notes & Gotchas](#notes--gotchas)
* [See Also](#see-also)

</details>

---

## Overview

`Version` is a tiny utility class that answers one question: *“Does this Python client claim to fully support that qBittorrent **app**/**Web API** version?”*

* **Supported** here means the library has explicit knowledge of that version’s behavior and endpoints.
* **Reality check:** even if a version isn’t listed as “supported,” **most methods often still work**—the Web API is largely backward/forward compatible, with occasional exceptions.

updated: 2025-09-06T19:09:40-05:00
---

## Quick Start

```python
from qbittorrentapi import Client, Version

qbt = Client(host="localhost:8080", username="admin", password="adminadmin")

app_v = qbt.app.version            # e.g. "v5.1.2"
api_v = qbt.app.web_api_version    # e.g. "2.11.4"

print("App supported? ", Version.is_app_version_supported(app_v))
print("API supported? ", Version.is_api_version_supported(api_v))

print("Latest app known to client: ", Version.latest_supported_app_version())
print("Latest API known to client: ", Version.latest_supported_api_version())
```

---

## Method Reference

### `is_api_version_supported(api_version) → bool`

Return **True/False** for whether a Web API version (e.g., `"2.11.4"`) is fully supported by this client.

* **Param:** `api_version: str`
* **Return:** `bool`

---

### `is_app_version_supported(app_version) → bool`

Return **True/False** for whether an application version (e.g., `"v5.1.2"` or `"5.1.2"`) is fully supported by this client.

* **Param:** `app_version: str`
* **Return:** `bool`

---

### `latest_supported_api_version() → str`

Return the most recent **Web API** version that this client declares full support for.

---

### `latest_supported_app_version() → str`

Return the most recent **qBittorrent app** version that this client declares full support for.

---

### `supported_api_versions() → set[str]`

Return the full **set** of Web API versions this client supports.

---

### `supported_app_versions() → set[str]`

Return the full **set** of app versions this client supports.

---

## Practical Recipes

### Fail fast at startup

If you prefer strictness, make the process loudly refuse unknown versions:

```python
from qbittorrentapi import Client, Version, exceptions as qba_exc

qbt = Client(host="...", username="...", password="...")

app_v = qbt.app.version
api_v = qbt.app.web_api_version

if not Version.is_app_version_supported(app_v):
    raise qba_exc.UnsupportedQbittorrentVersion(
        f"qBittorrent {app_v} not fully supported by this client."
    )
if not Version.is_api_version_supported(api_v):
    raise qba_exc.UnsupportedQbittorrentVersion(
        f"Web API {api_v} not fully supported by this client."
    )
```

> Alternative: set `RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True` on the `Client` to have the library do this for you globally.

---

### Gate a feature by Web API version

When using endpoints introduced in newer Web API releases, guard the call:

```python
from qbittorrentapi import Client, Version

qbt = Client(host="...", username="...", password="...")
api_v = qbt.app.web_api_version

def _ver_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))

if _ver_tuple(api_v) >= (2, 11, 0):
    # Safe to call an endpoint introduced in 2.11.0+
    qbt.search_download_torrent(url="magnet:...", plugin="example")
else:
    print("Your Web API is older than 2.11.0; skipping this call.")
```

> The `Version` class tells you what the **client** supports; comparing version tuples tells you what the **server** actually is.

---

### Soft-warn on “unknown but probably fine” versions

Prefer a friendly message while still proceeding:

```python
from qbittorrentapi import Client, Version

qbt = Client(host="...", username="...", password="...")
app_v = qbt.app.version
if not Version.is_app_version_supported(app_v):
    print(f"Warning: This client doesn’t list app {app_v} as fully supported. "
          "Most features may still work, but keep an eye on edge cases.")
```

---

## Notes & Gotchas

* **Prefix handling:** App versions often include a leading `"v"` (e.g., `"v5.1.2"`). The helpers handle both `"v5.1.2"` and `"5.1.2"`.
* **Support vs. compatibility:** “Not supported” here means “the client hasn’t pinned behavior for that exact version.” In practice, many calls still succeed thanks to API stability.
* **Be explicit in CI:** Pin both qBittorrent and `qbittorrent-api` versions for reproducible builds, and check support at service startup.
* **Global strict mode:** `Client(..., RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=True)` flips the library into “don’t guess” mode.

---

## See Also

* **Client configuration** for strict version gating and other behavior flags.
* **Search / Torrent Creator** docs for examples of endpoints introduced in specific Web API releases.
* **Exceptions** for handling `UnsupportedQbittorrentVersion` and friends.

<sub>Version drift happens. Check it, gate it, ship it. 🚀</sub>
