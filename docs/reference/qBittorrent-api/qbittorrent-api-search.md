# qBittorrent Search API (Python) — `qBittorrent_api_search.md`

> Manage search plugins and run meta-searches directly from Python using `qbittorrent-api`. This doc covers starting/stopping jobs, paging through results, plugin lifecycle (install/enable/update/uninstall), and version quirks.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Area" src="https://img.shields.io/badge/API-Search-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `SearchAPIMixIn`](#class-searchapimixin)
  * [Class: `Search`](#class-search)
  * [Return Types](#return-types)
* [Method Reference](#method-reference)

  * [`search_start`](#search_start)
  * [`search_status`](#search_status)
  * [`search_results`](#search_results)
  * [`search_stop`](#search_stop)
  * [`search_delete`](#search_delete)
  * [`search_plugins`](#search_plugins)
  * [`search_enable_plugin`](#search_enable_plugin)
  * [`search_install_plugin`](#search_install_plugin)
  * [`search_uninstall_plugin`](#search_uninstall_plugin)
  * [`search_update_plugins`](#search_update_plugins)
  * [`search_download_torrent`](#search_download_torrent)
  * [`search_categories` (deprecated/removed)](#search_categories-deprecatedremoved)
* [Usage Patterns](#usage-patterns)

  * [Run a search and page through results](#run-a-search-and-page-through-results)
  * [Polling status until finished](#polling-status-until-finished)
  * [Download a result via URL or magnet](#download-a-result-via-url-or-magnet)
  * [Plugin management workflow](#plugin-management-workflow)
  * [SIMPLE\_RESPONSES for large result sets](#simple_responses-for-large-result-sets)
* [Errors & Edge Cases](#errors--edge-cases)
* [Appendix: Property vs Method Mapping](#appendix-property-vs-method-mapping)

</details>

---

## Overview

The **Search** endpoints expose qBittorrent’s plugin-based meta-search. A search job fans out to any enabled search plugins and aggregates results. This requires Python on the qBittorrent host (for the plugin system). Host settings may limit concurrent searches.

You can use either:

* **Method-style** calls (e.g., `client.search_start(...)`)
* The **object-style** namespace (e.g., `client.search.start(...)`)

updated: 2025-09-06T19:14:05-05:00
---

## Quick Start

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Start a search across all enabled plugins in all categories
job = client.search.start(pattern="Ubuntu", plugins="enabled", category="all")

# Peek status
print(job.status())

# Fetch first page of results
page = job.results(limit=50, offset=0)
for r in page.get("results", []):
    print(r.get("fileName") or r.get("descrLink"), r.get("seeders"))

# Stop & delete when done (courteous!)
job.stop()
job.delete()
```

---

## API Surface

### Class: `SearchAPIMixIn`

**Bases:** `AppAPIMixIn`
Implementation of all Search API methods:

* `search_start(...) -> SearchJobDictionary`
* `search_status(...) -> SearchStatusesList`
* `search_results(...) -> SearchResultsDictionary`
* `search_stop(...) -> None`
* `search_delete(...) -> None`
* `search_plugins(...) -> SearchPluginsList`
* `search_enable_plugin(...) -> None`
* `search_install_plugin(...) -> None`
* `search_uninstall_plugin(...) -> None`
* `search_update_plugins(...) -> None`
* `search_categories(...) -> SearchCategoriesList` *(introduced v4.1.4 / removed v4.3.0)*
* `search_download_torrent(...) -> None` *(introduced v5.0.0 / Web API v2.11)*

---

### Class: `Search`

High-level, attribute-friendly interface:

```python
search_job = client.search.start(pattern="Ubuntu", plugins="all", category="all")
status     = search_job.status()
results    = search_job.results(limit=100, offset=0)
search_job.stop()
search_job.delete()

plugins = client.search.plugins
# categories were removed in qBittorrent v4.3.0
client.search.install_plugin(sources=["https://example.com/plugin.zip"])
client.search.enable_plugin(plugins=["myplugin"], enable=True)
client.search.update_plugins()
```

**Implements:**

* `categories(plugin_name=None) -> SearchCategoriesList`
* `delete(search_id=None) -> None`
* `download_torrent(url=None, plugin=None) -> None`
* `enable_plugin(plugins=None, enable=None) -> None`
* `install_plugin(sources=None) -> None`
* `plugins: SearchPluginsList`
* `results(search_id=None, limit=None, offset=None) -> SearchResultsDictionary`
* `start(pattern=None, plugins=None, category=None) -> SearchJobDictionary`
* `status(search_id=None) -> SearchStatusesList`
* `stop(search_id=None) -> None`
* `uninstall_plugin(sources=None) -> None`
* `update_plugins() -> None`

---

### Return Types

* **`SearchJobDictionary`** — returned by `start(...)`; includes the job ID and convenience methods:

  * `status() -> SearchStatusesList`
  * `results(limit=None, offset=None) -> SearchResultsDictionary`
  * `stop() -> None`, `delete() -> None`

* **`SearchResultsDictionary`** — result payload for `search_results(...)`.
  *(Upstream wiki details the schema; typically includes `results`, `total`, `status`, etc.)*

* **`SearchStatusesList`** with items **`SearchStatus`** — status for one/all jobs.

* **`SearchPluginsList`** with items **`SearchPlugin`** — installed plugins.

* **`SearchCategoriesList`** *(removed in v4.3.0)* with items **`SearchCategory`**.

---

## Method Reference

### `search_start`

Start a new search job.

```python
search_start(pattern=None, plugins=None, category=None, **kwargs) -> SearchJobDictionary
```

* **Requires**: Python installed on the qBittorrent host
* **Raises**: `Conflict409Error` (e.g., too many concurrent jobs)
* **Params**:

  * `pattern: str | None` — search term
  * `plugins: str | Iterable[str] | None` — list of plugin names, or `"all"` / `"enabled"`
  * `category: str | None` — plugin-dependent category, or `"all"`

---

### `search_status`

Get the status of one or all search jobs.

```python
search_status(search_id=None, **kwargs) -> SearchStatusesList
```

* **Raises**: `NotFound404Error` (invalid ID)
* `search_id=None` → status for **all** jobs

---

### `search_results`

Retrieve results for a job (paged).

```python
search_results(search_id=None, limit=None, offset=None, **kwargs) -> SearchResultsDictionary
```

* **Raises**: `NotFound404Error`, `Conflict409Error`
* **Params**:

  * `search_id: str | int | None`
  * `limit: str | int | None` — page size
  * `offset: str | int | None` — starting index

---

### `search_stop`

Stop a running search.

```python
search_stop(search_id=None, **kwargs) -> None
```

* **Raises**: `NotFound404Error`

---

### `search_delete`

Delete a search job (cleanup).

```python
search_delete(search_id=None, **kwargs) -> None
```

* **Raises**: `NotFound404Error`

---

### `search_plugins`

List installed search plugins.

```python
search_plugins(**kwargs) -> SearchPluginsList
```

---

### `search_enable_plugin`

Enable or disable plugins.

```python
search_enable_plugin(plugins=None, enable=None, **kwargs) -> None
```

* `plugins: str | Iterable[str] | None` (names)
* `enable: bool | None` (`True` by default)

---

### `search_install_plugin`

Install plugins from URLs or local files.

```python
search_install_plugin(sources=None, **kwargs) -> None
```

* `sources: str | Iterable[str] | None` — URLs or file paths

---

### `search_uninstall_plugin`

Uninstall plugins by name.

```python
search_uninstall_plugin(names=None, **kwargs) -> None
```

* `names: str | Iterable[str] | None`

---

### `search_update_plugins`

Auto-update search plugins.

```python
search_update_plugins(**kwargs) -> None
```

---

### `search_download_torrent`

Download a `.torrent` or magnet reported by a search plugin.

```python
search_download_torrent(url=None, plugin=None, **kwargs) -> None
```

* **Introduced**: qBittorrent **v5.0.0** (Web API **v2.11**)
* **Params**:

  * `url: str | None` — direct .torrent URL or magnet
  * `plugin: str | None` — plugin name (when required)

---

### `search_categories` (deprecated/removed)

```python
search_categories(plugin_name=None, **kwargs) -> SearchCategoriesList
```

* **Introduced**: v4.1.4 (Web API v2.1.1)
* **Removed**: v4.3.0 (Web API v2.6)
* `plugin_name: str | None` — limit by plugin (`"all"` / `"enabled"` also supported historically)

---

## Usage Patterns

### Run a search and page through results

```python
job = client.search.start(pattern="debian iso", plugins="enabled", category="all")

# First 50
res = job.results(limit=50, offset=0)
for item in res.get("results", []):
    name = item.get("fileName") or item.get("title") or item.get("descrLink")
    seeds = item.get("seeders")
    size  = item.get("size")
    print(f"{name}  |  seeds={seeds}  |  size={size}")

# Next page
res2 = job.results(limit=50, offset=50)
```

### Polling status until finished

```python
import time

job = client.search.start(pattern="Ubuntu 24.04", plugins="all", category="all")

while True:
    stats = job.status()
    # Typically a list with a single status for this job ID
    s = stats[0] if stats else None
    state = getattr(s, "status", None)  # e.g., "Running", "Stopped", "Finished"
    if state in {"Stopped", "Finished"}:
        break
    time.sleep(0.5)

final = job.results(limit=100, offset=0)
```

### Download a result via URL or magnet

If your result entries include a `.torrent` URL or magnet link, and the plugin requires routing through qBittorrent:

```python
url = "magnet:?xt=urn:btih:..."
client.search.download_torrent(url=url, plugin="some_plugin")
```

> Depending on the plugin, `plugin` may be optional for direct magnets.

### Plugin management workflow

```python
# See what's installed
for p in client.search.plugins:
    print(getattr(p, "name", p))

# Install from URL or local path
client.search.install_plugin(sources=[
    "https://example.com/qbt_search_plugin.zip",
    "/path/to/local_plugin.zip",
])

# Enable a subset
client.search.enable_plugin(plugins=["myplugin", "another"], enable=True)

# Update all
client.search.update_plugins()

# Remove a plugin
client.search.uninstall_plugin(names=["another"])
```

### SIMPLE\_RESPONSES for large result sets

Search results can be chunky. If you’re post-processing thousands of rows and care about speed:

```python
client = Client(..., SIMPLE_RESPONSES=True)
bulk = client.search_results(search_id=123, limit=500, offset=0)
# or per-call:
bulk = client.search.results(search_id=123, limit=500, offset=0, SIMPLE_RESPONSES=True)
```

---

## Errors & Edge Cases

* **`Conflict409Error`** — starting too many jobs, or conflicting parameters.
* **`NotFound404Error`** — status/results/stop/delete for an unknown `search_id`.
* **Python not installed on host** — searches won’t run; install Python on the qBittorrent box/container.
* **Categories** — the `search_categories` endpoint existed only up to qBittorrent **v4.3.0**.

> Always guard your loops with timeouts/backoffs, and clean up with `stop()`/`delete()` for good neighbor etiquette.

---

## Appendix: Property vs Method Mapping

| Object-style (`client.search`)        | Method-style (`client.search_*`) | Notes                         |
| ------------------------------------- | -------------------------------- | ----------------------------- |
| `start(pattern, plugins, category)`   | `search_start(...)`              | Returns `SearchJobDictionary` |
| `status(search_id=None)`              | `search_status(...)`             | Status for one/all jobs       |
| `results(search_id, limit, offset)`   | `search_results(...)`            | Paged results                 |
| `stop(search_id)`                     | `search_stop(...)`               | Stop a job                    |
| `delete(search_id)`                   | `search_delete(...)`             | Remove job                    |
| `plugins` (property)                  | `search_plugins()`               | List plugins                  |
| `enable_plugin(plugins, enable)`      | `search_enable_plugin(...)`      | Enable/disable                |
| `install_plugin(sources)`             | `search_install_plugin(...)`     | Add plugins                   |
| `uninstall_plugin(names)`             | `search_uninstall_plugin(...)`   | Remove plugins                |
| `update_plugins()`                    | `search_update_plugins()`        | Auto-update                   |
| *(removed)* `categories(plugin_name)` | `search_categories(...)`         | Removed in v4.3.0             |

---

*Happy hunting. May your queries be precise and your seeders plentiful.*
