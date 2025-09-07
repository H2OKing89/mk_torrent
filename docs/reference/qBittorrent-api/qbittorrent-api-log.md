# qBittorrent Log API (Python) — `qBittorrent_api_log.md`

> Read and filter qBittorrent’s daemon and peer logs via the `qbittorrent-api` Python client. This doc covers both the low-level mixin methods and the ergonomic `client.log` interface, plus patterns for tailing, severity filtering, and incremental reads.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Area" src="https://img.shields.io/badge/API-Log-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `LogAPIMixIn`](#class-logapimixin)
  * [Class: `Log`](#class-log)
  * [Class: `Main`](#class-main)
  * [Return Types](#return-types)
* [Method Reference](#method-reference)

  * [`log_main`](#log_main)
  * [`log_peers`](#log_peers)
* [Usage Patterns](#usage-patterns)

  * [Filter by severity](#filter-by-severity)
  * [Incremental reads with `last_known_id`](#incremental-reads-with-last_known_id)
  * [“Tail -f” style polling](#tail--f-style-polling)
  * [Peer log basics](#peer-log-basics)
* [Tips](#tips)
* [See Also](#see-also)

</details>

---

## Overview

The **Log** endpoints provide two streams:

1. **Main log** — qBittorrent’s own log messages (normal/info/warning/critical).
2. **Peer log** — events related to peers (connections, bans, etc).

`qbittorrent-api` exposes these via:

* Direct methods on the client (`client.log_main(...)`, `client.log_peers(...)`)
* A namespaced, chainable interface (`client.log.main.*`, `client.log.peers(...)`)

updated: 2025-09-06T19:00:01-05:00
---

## Quick Start

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Get all severities from the main log
entries = client.log_main()
for e in entries:
    # entries behave like objects with attribute-style access (dict-like too)
    print(e)

# Peer log
peers = client.log_peers()
for p in peers:
    print(p)
```

Object-style:

```python
log_list   = client.log.main()              # same as client.log_main()
peers_list = client.log.peers()             # same as client.log_peers()

# Pre-filter by severity using helpers
only_info     = client.log.main.info()
only_warnings = client.log.main.warning()
only_crit     = client.log.main.critical()
```

---

## API Surface

### Class: `LogAPIMixIn`

**Bases:** `AppAPIMixIn`
Implements all Log API methods:

* `log_main(normal=None, info=None, warning=None, critical=None, last_known_id=None, **kwargs) -> LogMainList`
* `log_peers(last_known_id=None, **kwargs) -> LogPeersList`

---

### Class: `Log`

High-level, attribute-friendly interface:

```python
log_list = client.log.main()
peers    = client.log.peers(last_known_id="...")

# Pre-filtered variants
log_info    = client.log.main.info(last_known_id=1)
log_warning = client.log.main.warning(last_known_id=1)
log_crit    = client.log.main.critical(last_known_id=1)
```

Properties / methods:

* `main: Main` — callable plus helpers for severity filters
* `peers(last_known_id=None, **kwargs) -> LogPeersList` — peer log

---

### Class: `Main`

Implements `log_main()` and severity-filtered helpers.

* `__call__(normal=True, info=True, warning=True, critical=True, last_known_id=None, **kwargs) -> LogMainList`
* `info(last_known_id=None, **kwargs) -> LogMainList`
* `normal(last_known_id=None, **kwargs) -> LogMainList` *(sets `info=False`)*
* `warning(last_known_id=None, **kwargs) -> LogMainList` *(sets `info=False`, `normal=False`)*
* `critical(last_known_id=None, **kwargs) -> LogMainList` *(sets `info=False`, `normal=False`, `warning=False`)*

---

### Return Types

* `LogMainList (List[LogEntry])` — main log lines
* `LogPeersList (List[LogPeer])` — peer log lines
* `LogEntry` / `LogPeer` — list entries (dict-like with attribute access)

> Field shapes can vary by qBittorrent/Web API version. Treat items as dict-like (`entry["message"]`) and attribute-like (`entry.message`). Common fields typically include an **id**, **timestamp**, **type/severity**, and a **message** string.

---

## Method Reference

### `log_main`

Retrieve daemon log entries.

**Signature:**
`log_main(normal=None, info=None, warning=None, critical=None, last_known_id=None, **kwargs) -> LogMainList`

**Parameters**

* `normal: bool | None` — `False` to exclude *normal* entries
* `info: bool | None` — `False` to exclude *info* entries
* `warning: bool | None` — `False` to exclude *warning* entries
* `critical: bool | None` — `False` to exclude *critical* entries
* `last_known_id: str | int | None` — return only entries with `id > last_known_id`

**Returns:** `LogMainList`

---

### `log_peers`

Retrieve peer log entries.

**Signature:**
`log_peers(last_known_id=None, **kwargs) -> LogPeersList`

**Parameters**

* `last_known_id: str | int | None` — return only entries with `id > last_known_id`

**Returns:** `LogPeersList`

---

## Usage Patterns

### Filter by severity

```python
# Only warnings
warnings = client.log.main.warning()

# Only critical
crit = client.log.main.critical()

# Everything except 'normal' lines
no_normal = client.log_main(normal=False)
```

### Incremental reads with `last_known_id`

Keep track of the highest `id` you’ve seen to fetch only new lines next time—great for UIs and background jobs.

```python
last_id = 0

def fetch_new():
    global last_id
    new = client.log_main(last_known_id=last_id)
    if new:
        last_id = max(entry.id for entry in new)  # id is typically numeric
    return new
```

> If your storage is per-severity, use the same `last_known_id` scheme for `warning()`, `critical()`, etc.

### “Tail -f” style polling

```python
import time

last = 0
while True:
    batch = client.log.main(last_known_id=last)
    if batch:
        last = max(e.id for e in batch)
        for e in batch:
            # Print with a safe fallback for fields that may vary by version
            msg  = getattr(e, "message", str(e))
            lvl  = getattr(e, "type", getattr(e, "severity", ""))
            when = getattr(e, "timestamp", "")
            print(f"[{when}] {lvl}: {msg}")
    time.sleep(1.0)
```

### Peer log basics

```python
peer_last = 0
while True:
    peers = client.log_peers(last_known_id=peer_last)
    if peers:
        peer_last = max(p.id for p in peers)
        for p in peers:
            # Common fields often include id, timestamp, ip, message
            print(p)
    time.sleep(2.0)
```

---

## Tips

* **Prefer the object interface** for readability:

  * `client.log.main.warning(last_known_id=123)` reads nicely and sets the right filters.
* **Use `last_known_id`** for efficient polling; it saves bandwidth and avoids reprocessing.
* **Treat entries as flexible**: different qBittorrent versions may add/change fields. Code defensively with `.get()`/`getattr()`.
* **SIMPLE\_RESPONSES**: if you only need raw JSON for heavy volumes, consider initializing your `Client` with `SIMPLE_RESPONSES=True` or pass it per-call for big bursts.

---

## See Also

* **Authentication & Application** docs for session/version handling.
* **Client** doc for constructor options (`REQUESTS_ARGS`, TLS, proxies).
* **Exceptions** doc for handling HTTP and auth errors when reading logs.
