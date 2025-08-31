# qBittorrent Sync API (Python) — `qBittorrent_api_sync.md`

> Incremental, low-latency updates for your UI or automation: fetch only what changed in qBittorrent since the last call. This guide covers the `qbittorrent-api` Sync endpoints, the `rid` mechanism, and handy `delta()` helpers.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Area" src="https://img.shields.io/badge/API-Sync-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `SyncAPIMixIn`](#class-syncapimixin)
  * [Class: `Sync`](#class-sync)
  * [Return Types](#return-types)
* [Method Reference](#method-reference)

  * [`sync_maindata`](#sync_maindata)
  * [`sync_torrent_peers`](#sync_torrent_peers)
* [Usage Patterns](#usage-patterns)

  * [Polling with `rid` (manual)](#polling-with-rid-manual)
  * [Zero-boilerplate diffs with `delta()`](#zero-boilerplate-diffs-with-delta)
  * [Forcing a full refresh with `reset_rid()`](#forcing-a-full-refresh-with-reset_rid)
  * [Merging partial updates](#merging-partial-updates)
* [Tips & Edge Cases](#tips--edge-cases)
* [See Also](#see-also)

</details>

---

## Overview

The **Sync** API provides *partial* updates based on a **response ID** (aka `rid`). Each call returns either a **full snapshot** or a **diff** since the last `rid`. Responses include flags/fields like `full_update`, `torrents` (changed), `torrents_removed`, `categories[_removed]`, `tags[_removed]`, and `server_state`, letting you update a UI efficiently without re-pulling everything. ([GitHub][1])

---

## Quick Start

```python
from qbittorrentapi import Client

qbt = Client(host="localhost:8080", username="admin", password="adminadmin")

# Manual, one-off fetch
snap = qbt.sync_maindata(rid=0)   # full snapshot (rid=0)
print(snap.get("server_state", {}))

# Peers for a specific torrent (sync-style)
peers = qbt.sync_torrent_peers(torrent_hash="...", rid=0)
```

Ergonomic, stateful helpers:

```python
# Automatically request deltas since the last call:
md = qbt.sync.maindata.delta()

# Sync torrent peers deltas for a given hash:
pd = qbt.sync.torrent_peers.delta(torrent_hash="...")

# Reset and force next call to return a full snapshot:
qbt.sync.maindata.reset_rid()
qbt.sync.torrent_peers.reset_rid()
```

(Helper methods & properties shown above are part of the `qbittorrent-api` client’s Sync namespace.) ([qbittorrent-api.readthedocs.io][2])

---

## API Surface

### Class: `SyncAPIMixIn`

**Bases:** `AppAPIMixIn` — Implements the Sync endpoints:

* `sync_maindata(rid=0, **kwargs) -> SyncMainDataDictionary`
* `sync_torrent_peers(torrent_hash=None, rid=0, **kwargs) -> SyncTorrentPeersDictionary` ([qbittorrent-api.readthedocs.io][3])

---

### Class: `Sync`

High-level, attribute-friendly interface with convenient *stateful* helpers:

```python
# Same underlying endpoints, object-style:
maindata      = qbt.sync.maindata(rid="...")
maindata_diff = qbt.sync.maindata.delta()     # fetch only changes since last call
qbt.sync.maindata.reset_rid()                 # next call returns a full snapshot

torrent_peers      = qbt.sync.torrent_peers(torrent_hash="...", rid="...")
torrent_peers_diff = qbt.sync.torrent_peers.delta(torrent_hash="...")
qbt.sync.torrent_peers.reset_rid()
```

These call the same wire endpoints and manage `rid` for you. ([qbittorrent-api.readthedocs.io][2])

---

### Return Types

* **`SyncMainDataDictionary`** — response to `sync_maindata()`. Upstream wiki documents the JSON shape, including `rid`, `full_update`, `torrents`, `torrents_removed`, `categories`, `categories_removed`, `tags`, `tags_removed`, and `server_state`. ([GitHub][1])
* **`SyncTorrentPeersDictionary`** — response to `sync_torrent_peers()`. Wiki documents parameters and `rid` semantics for torrent peers sync calls. ([GitHub][1])

---

## Method Reference

### `sync_maindata`

```python
sync_maindata(rid=0, **kwargs) -> SyncMainDataDictionary
```

Retrieves **main** sync data. Pass the previous `rid` to receive either a full snapshot or only changes since that `rid` (see `full_update` and per-section deltas in the response). If `rid` is omitted, `0` is assumed. ([GitHub][1])

---

### `sync_torrent_peers`

```python
sync_torrent_peers(torrent_hash=None, rid=0, **kwargs) -> SyncTorrentPeersDictionary
```

Retrieves **torrent peer** sync data for a specific torrent. Requires `torrent_hash`. Like `maindata`, the `rid` indicates incremental vs full updates. If `torrent_hash` is invalid, the endpoint returns 404. ([GitHub][1])

---

## Usage Patterns

### Polling with `rid` (manual)

```python
rid = 0
while True:
    data = qbt.sync_maindata(rid=rid)
    # Server returns next rid; stash it for the next loop
    rid = data.get("rid", rid)
    if data.get("full_update", False):
        # Replace your entire local cache with this snapshot
        rebuild_cache_from(data)
    else:
        # Merge only the diffs: torrents, removed lists, categories/tags, server_state
        apply_partial_update(data)
    # sleep/backoff as appropriate for your UI
```

The wiki clarifies that if your request’s `rid` does not match the last server reply, `full_update` will be `true`—use that as your “replace cache” signal. ([GitHub][1])

---

### Zero-boilerplate diffs with `delta()`

Let the client track `rid` for you:

```python
# Only the changes since the previous call
diff = qbt.sync.maindata.delta()

# For torrent peers:
peer_diff = qbt.sync.torrent_peers.delta(torrent_hash="...")
```

These helpers persist the last seen `rid` within the object wrapper, so you don’t have to. ([qbittorrent-api.readthedocs.io][2])

---

### Forcing a full refresh with `reset_rid()`

If your UI lost state or a previous `rid` is suspect, reset and fetch fresh:

```python
qbt.sync.maindata.reset_rid()
full = qbt.sync.maindata()   # next call returns full snapshot

qbt.sync.torrent_peers.reset_rid()
peers_full = qbt.sync.torrent_peers(torrent_hash="...")
```

The `reset_rid()` methods ensure the next call behaves like `rid=0`. ([qbittorrent-api.readthedocs.io][2])

---

### Merging partial updates

A typical `maindata` response includes:

* `torrents` — **only changed** torrents keyed by hash (merge into your map)
* `torrents_removed` — list of hashes to **delete** from your map
* `{categories|tags}` & `{categories_removed|tags_removed}` — add/remove these in your UI
* `server_state` — global transfer info (rates, limits, DHT nodes, etc.)

This schema is defined in the official WebUI API wiki. ([GitHub][1])

---

## Tips & Edge Cases

* **Missed a tick?** If your client `rid` drifts (e.g., process restart), the server marks `full_update=true`. Treat that as a signal to reload your entire local cache. ([GitHub][1])
* **Peers endpoint requires a hash**; a bad hash returns 404 (`NotFound404Error` at the Python layer). ([GitHub][1])
* **Performance**: Because Sync is incremental, you usually don’t need `SIMPLE_RESPONSES=True`. Save that for massive lists like full torrent file dumps.
* **Two spellings for peers property**: the object interface exposes both `torrentPeers` and `torrent_peers` entries for convenience; use either. ([qbittorrent-api.readthedocs.io][2])

---

## See Also

* **Sync API (client docs):** signatures, usage, and helpers. ([qbittorrent-api.readthedocs.io][3])
* **Upstream WebUI API (wiki):** response schema for `maindata` and `torrentPeers`, `rid` semantics. ([GitHub][1])
* **Latest package docs (PDF):** current release notes and method listings. ([qbittorrent-api.readthedocs.io][4])

> TL;DR — keep the `rid`, merge the diffs, refresh on `full_update`. Your UI stays snappy; your daemon stays happy.

[1]: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-%28qBittorrent-4.1%29 "WebUI API (qBittorrent 4.1) · qbittorrent/qBittorrent Wiki · GitHub"
[2]: https://qbittorrent-api.readthedocs.io/en/v2024.8.65/apidoc/sync.html?utm_source=chatgpt.com "Sync - qbittorrent-api 2024.8.65 documentation"
[3]: https://qbittorrent-api.readthedocs.io/en/latest/apidoc/sync.html?utm_source=chatgpt.com "Sync - qbittorrent-api 2025.5.1.dev12+gc1103a2 documentation"
[4]: https://qbittorrent-api.readthedocs.io/_/downloads/en/latest/pdf/?utm_source=chatgpt.com "Release 2025.7.1.dev4+g4fc2ae4"
