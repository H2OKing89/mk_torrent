# qBittorrent Transfer API (Python) — `qBittorrent_api_transfer.md`

> Read and control **global transfer state** in qBittorrent using `qbittorrent-api`: bandwidth limits, alt-speed mode, global stats, and peer banning. This page covers the raw endpoints and the ergonomic `client.transfer` interface.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Area" src="https://img.shields.io/badge/API-Transfer-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `TransferAPIMixIn`](#class-transferapimixin)
  * [Class: `Transfer`](#class-transfer)
  * [Return Types](#return-types)
* [Method Reference](#method-reference)

  * [`transfer_info`](#transfer_info)
  * [`transfer_download_limit` / `transfer_set_download_limit`](#transfer_download_limit--transfer_set_download_limit)
  * [`transfer_upload_limit` / `transfer_set_upload_limit`](#transfer_upload_limit--transfer_set_upload_limit)
  * [`transfer_speed_limits_mode` / `transfer_set_speed_limits_mode` / `transfer_toggle_speed_limits_mode`](#transfer_speed_limits_mode--transfer_set_speed_limits_mode--transfer_toggle_speed_limits_mode)
  * [`transfer_ban_peers`](#transfer_ban_peers)
* [Usage Patterns](#usage-patterns)

  * [Read & set speed limits (bytes/sec)](#read--set-speed-limits-bytessec)
  * [Using alternative speed limits mode](#using-alternative-speed-limits-mode)
  * [Banning one or more peers](#banning-one-or-more-peers)
  * [Polling global transfer info](#polling-global-transfer-info)
* [Tips, Units & Edge Cases](#tips-units--edge-cases)
* [Appendix: Property vs Method Mapping](#appendix-property-vs-method-mapping)

</details>

---

## Overview

The **Transfer** endpoints expose global status from the qBittorrent status bar (current speeds, totals, DHT nodes, etc.) and let you **set bandwidth limits**, **toggle “alt speed” mode**, and **ban peers**. You can call methods directly (e.g., `client.transfer_info()`) or use the object-style wrapper (`client.transfer.*`) with properties that read/write live values.

updated: 2025-09-06T19:09:40-05:00
---

## Quick Start

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Global transfer snapshot (what the status bar shows)
info = client.transfer_info()
print("DL:", info.get("dl_info_speed"), "UL:", info.get("up_info_speed"))

# Get current limits (0 means unlimited)
print("DL limit:", client.transfer_download_limit())
print("UL limit:", client.transfer_upload_limit())

# Set limits to ~1 MiB/s down and ~512 KiB/s up
client.transfer_set_download_limit(1_048_576)
client.transfer_set_upload_limit(524_288)

# Enable alt-speed mode
client.transfer_set_speed_limits_mode(True)

# Ban a noisy peer
client.transfer_ban_peers(peers=["203.0.113.10:51413"])
```

Object-style (ergonomic) interface:

```python
# Properties mirror the methods and update qBittorrent in real-time
dl_limit = client.transfer.download_limit
client.transfer.download_limit = 1_048_576

# Toggle alt-speed via property/methods
_ = client.transfer.speed_limits_mode        # "1" or "0"
client.transfer.set_speed_limits_mode(True)
client.transfer.toggle_speed_limits_mode()   # flips current state
```

---

## API Surface

### Class: `TransferAPIMixIn`

**Bases:** `AppAPIMixIn` — Implements all Transfer endpoints:

* `transfer_info() -> TransferInfoDictionary`
* `transfer_download_limit() -> int`
* `transfer_set_download_limit(limit=None) -> None`
* `transfer_upload_limit() -> int`
* `transfer_set_upload_limit(limit=None) -> None`
* `transfer_speed_limits_mode() -> str` *(returns `"1"` or `"0"`)*
* `transfer_set_speed_limits_mode(intended_state=None) -> None` *(explicit set; `None` toggles)*
* `transfer_toggle_speed_limits_mode(intended_state=None) -> None` *(alias; also accepts `None` to toggle)*
* `transfer_ban_peers(peers=None) -> None` *(introduced qBittorrent v4.2.0 / Web API v2.3.0)*

> Some codebases also expose `transfer_setSpeedLimitsMode(...)` as a legacy/camelCase alias.

---

### Class: `Transfer`

High-level, attribute-friendly wrapper:

```python
transfer_info = client.transfer.info                 # property
dl_limit      = client.transfer.download_limit       # property
client.transfer.download_limit = 1_000_000           # setter → updates qBittorrent
client.transfer.set_upload_limit(750_000)            # method

# Speed limits mode helpers
mode = client.transfer.speed_limits_mode             # "1" = enabled, "0" = disabled
client.transfer.set_speed_limits_mode(True)
client.transfer.toggle_speed_limits_mode()

# Moderation
client.transfer.ban_peers(["hostA:6881", "hostB:51413"])
```

**Implements:**

* `info: TransferInfoDictionary` (property)
* `download_limit: int` / `set_download_limit(limit)`
* `upload_limit: int` / `set_upload_limit(limit)`
* `speed_limits_mode: str` / `set_speed_limits_mode(intended_state)` / `toggle_speed_limits_mode(intended_state=None)`
* `ban_peers(peers) -> None`

---

### Return Types

* **`TransferInfoDictionary`** — dict-like wrapper of the **global transfer info** (speeds, totals, rates, DHT, cache stats, etc.).
* Integer limits are **bytes per second**; `0` (or `-1` on setters) means **unlimited**.

---

## Method Reference

### `transfer_info`

**Signature:** `transfer_info(**kwargs) -> TransferInfoDictionary`
Retrieve global transfer info (status-bar data).

---

### `transfer_download_limit` / `transfer_set_download_limit`

* **Get:** `transfer_download_limit(**kwargs) -> int`
  Returns current **download** limit in **bytes/second**; `0` means unlimited.

* **Set:** `transfer_set_download_limit(limit=None, **kwargs) -> None`
  Set global **download** limit (bytes/second). Use `0` or `-1` to remove the cap.

---

### `transfer_upload_limit` / `transfer_set_upload_limit`

* **Get:** `transfer_upload_limit(**kwargs) -> int`
  Returns current **upload** limit in **bytes/second**; `0` means unlimited.

* **Set:** `transfer_set_upload_limit(limit=None, **kwargs) -> None`
  Set global **upload** limit (bytes/second). Use `0` or `-1` for unlimited.

---

### `transfer_speed_limits_mode` / `transfer_set_speed_limits_mode` / `transfer_toggle_speed_limits_mode`

* **Read:** `transfer_speed_limits_mode(**kwargs) -> str`
  Returns `"1"` if **alternative speed limits** are enabled, `"0"` otherwise.

* **Write:**

  * `transfer_set_speed_limits_mode(intended_state=None, **kwargs) -> None`
  * `transfer_toggle_speed_limits_mode(intended_state=None, **kwargs) -> None`
    Pass `True` to enable, `False` to disable, or **omit / pass `None` to toggle** current state.

> A camelCase form `transfer_setSpeedLimitsMode(...)` may also exist.

---

### `transfer_ban_peers`

**Signature:** `transfer_ban_peers(peers=None, **kwargs) -> None`
Ban one or more peers.
**Params:** `peers: str | Iterable[str] | None` — values formatted as `"host:port"`.

---

## Usage Patterns

### Read & set speed limits (bytes/sec)

```python
# Read current limits
dl = client.transfer_download_limit()
ul = client.transfer_upload_limit()
print("limits:", dl, ul)

# Set to ~5 MiB/s down, ~2 MiB/s up
client.transfer_set_download_limit(5 * 1024 * 1024)
client.transfer_set_upload_limit(2 * 1024 * 1024)

# Remove limits
client.transfer_set_download_limit(0)  # or -1
client.transfer_set_upload_limit(-1)
```

### Using alternative speed limits mode

```python
# Check state ("1" / "0")
print("alt-speed:", client.transfer_speed_limits_mode())

# Force enable
client.transfer_set_speed_limits_mode(True)

# Toggle (flip current)
client.transfer_toggle_speed_limits_mode()
```

> You can pass `intended_state=None` to either setter/toggler to “just toggle”.

### Banning one or more peers

```python
# Single
client.transfer_ban_peers("198.51.100.2:51413")

# Multiple
client.transfer_ban_peers(["203.0.113.10:6881", "203.0.113.11:51413"])
```

### Polling global transfer info

```python
stats = client.transfer_info()
print("Down:", stats.get("dl_info_speed"), "Up:", stats.get("up_info_speed"))
print("DHT:", stats.get("dht_nodes"), "Conn:", stats.get("connection_status"))
```

---

## Tips, Units & Edge Cases

* **Units:** limits are **bytes per second** (B/s), not bits. Multiply by `1024**2` for MiB/s conversions.
* **Unlimited:** `0` (and setter `-1`) means **no cap**.
* **Alt-speed mode reading:** `transfer_speed_limits_mode()` returns a **string** `"1"` or `"0"`—convert to `bool(int(...))` if you need a boolean.
* **Immediate effect:** property setters like `client.transfer.download_limit = 1_000_000` **update the daemon immediately**.
* **Peer format:** Always pass peers as `"host:port"`; invalid entries are ignored server-side.

---

## Appendix: Property vs Method Mapping

| Object-style (`client.transfer`)         | Method-style (`client.transfer_*`)                                | Notes                    |
| ---------------------------------------- | ----------------------------------------------------------------- | ------------------------ |
| `info` (property)                        | `transfer_info()`                                                 | Global transfer snapshot |
| `download_limit` (get/set)               | `transfer_download_limit()`, `transfer_set_download_limit(limit)` | Bytes/sec                |
| `upload_limit` (get/set)                 | `transfer_upload_limit()`, `transfer_set_upload_limit(limit)`     | Bytes/sec                |
| `speed_limits_mode` (get)                | `transfer_speed_limits_mode()`                                    | `"1"` or `"0"`           |
| `set_speed_limits_mode(True/False/None)` | `transfer_set_speed_limits_mode(...)`                             | `None` toggles           |
| `toggle_speed_limits_mode()`             | `transfer_toggle_speed_limits_mode(...)`                          | Flip state               |
| `ban_peers(peers)`                       | `transfer_ban_peers(peers)`                                       | `"host:port"` strings    |

---

*Dial in your bandwidth, keep things civilized with a peer ban or two, and let the swarm sing.*
