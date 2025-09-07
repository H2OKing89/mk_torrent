# qBittorrent API – Definitions & Core Types (`qBittorrent_api_definitions.md`)

> A compact-but-complete reference for the foundational types, enums, and containers used across `qbittorrent-api`. Think of this as the *type toolbox*—everything other docs silently rely on.

<p align="center">
  <img alt="Scope" src="https://img.shields.io/badge/scope-core%20types-blue">
  <img alt="Audience" src="https://img.shields.io/badge/audience-developers-success">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Type Aliases](#type-aliases)

  * [`APIKwargsT`](#apikwargst)
  * [`FilesToSendT`](#filestosendt)
  * [`JsonValueT`](#jsonvaluet)
  * [`ClientT`](#clientt)
  * [`ListEntryT`](#listentryt)
  * [`ListInputT`](#listinputt)
* [Base Containers](#base-containers)

  * [`Dictionary`](#dictionary)
  * [`List`](#list)
  * [`ListEntry`](#listentry)
  * [`ClientCache`](#clientcache)
* [API Namespaces](#api-namespaces)

  * [`APINames` enum](#apiname-enum)
* [Torrent State Model](#torrent-state-model)

  * [`TorrentState` enum](#torrentstate-enum)
  * [State helpers](#state-helpers)
  * [State value changes (v5+ / Web API v2.11+)](#state-value-changes-v5--web-api-v211)
  * [Usage examples](#usage-examples)
* [Tracker Status Model](#tracker-status-model)

  * [`TrackerStatus` enum](#trackerstatus-enum)
  * [Usage example](#usage-example)

</details>

---

## Overview

The `qbittorrent-api` client wraps responses in ergonomic containers and enums. These definitions give you:

* Stronger semantics than raw JSON
* Enum-ified states/tracker statuses with human-friendly helpers
* Typed list/dict wrappers that still behave like native Python containers
* Lightweight “client-aware” wrappers so objects can call back into the API when it makes sense

updated: 2025-09-07T04:23:39-05:00
---

## Type Aliases

### `APIKwargsT`

> “kwarg catch-all” for API method signatures.

* **Type:** `Any`
* **Use it when:** your function forwards arbitrary keyword arguments into the request layer.

### `FilesToSendT`

> The shape expected by endpoints that upload files.

* **Type:** `Mapping[str, bytes | tuple[str, bytes]]`
* **Examples:**

  ```python
  files = {"torrents": b"...raw .torrent bytes..."}
  # or include a filename
  files = {"torrents": ("my.torrent", b"...")}
  ```

### `JsonValueT`

> JSON values accepted/returned by the API.

* **Type:** `None | int | str | bool | Sequence[JsonValueT] | Mapping[str, JsonValueT]`

### `ClientT`

> The “client-bound” generic used by cache-aware containers.

* **Alias:** `TypeVar('ClientT', bound=Request)`

### `ListEntryT`

> The type of an item within a `List`.

* **Alias:** `TypeVar('ListEntryT', bound=ListEntry)`

### `ListInputT`

> For endpoints that accept “list-like” inputs of mapping entries.

* **Type:** `Iterable[Mapping[str, None | int | str | bool | Sequence[JsonValueT] | Mapping[str, JsonValueT]]]`

---

## Base Containers

### `Dictionary`

Base class for **dict-like** responses with attribute access and handy helpers.

* **Bases:** `AttrDict[V]`
* **Signature:** `Dictionary(data=None, **kwargs)`
* **Why it exists:** keep responses flexible yet convenient (access by `obj["key"]` *or* `obj.key`).

### `List`

Base class for **list-like** responses that contain `ListEntry` items.

* **Bases:** `UserList[ListEntryT]`
* **Signature:** `List(list_entries=None, entry_class=None, **kwargs)`
* **Why it exists:** preserve list semantics while enabling richer item behavior.

### `ListEntry`

Base class for **items inside** list responses; dict-like with attribute access.

* **Bases:** `Dictionary[None | int | str | bool | Sequence[JsonValueT] | Mapping[str, JsonValueT]]`

### `ClientCache`

A tiny mixin that **caches and exposes the client** on response objects—so objects can call context-relevant API methods without you passing the client around.

* **Bases:** `Generic[ClientT]`
* **Subclass when:** you want “live” objects that can, for example, refresh their own status or delete themselves.

---

## API Namespaces

### `APINames` enum

String enum for Web API namespaces (used in URL building / routing):

* `Application = "app"`
* `Authorization = "auth"`
* `EMPTY = ""`
* `Log = "log"`
* `RSS = "rss"`
* `Search = "search"`
* `Sync = "sync"`
* `TorrentCreator = "torrentcreator"`
* `Torrents = "torrents"`
* `Transfer = "transfer"`

**Example URL anatomy**

```
http://localhost:8080/api/v2/torrents/addTrackers
                           ^^^^^^^^
                           namespace
```

---

## Torrent State Model

### `TorrentState` enum

String enum mirroring qBittorrent torrent states:

```
ALLOCATING = 'allocating'
CHECKING_DOWNLOAD = 'checkingDL'
CHECKING_RESUME_DATA = 'checkingResumeData'
CHECKING_UPLOAD = 'checkingUP'
DOWNLOADING = 'downloading'
ERROR = 'error'
FORCED_DOWNLOAD = 'forcedDL'
FORCED_METADATA_DOWNLOAD = 'forcedMetaDL'
FORCED_UPLOAD = 'forcedUP'
METADATA_DOWNLOAD = 'metaDL'
MISSING_FILES = 'missingFiles'
MOVING = 'moving'
PAUSED_DOWNLOAD = 'pausedDL'      # → renamed; see below
PAUSED_UPLOAD   = 'pausedUP'      # → renamed; see below
QUEUED_DOWNLOAD = 'queuedDL'
QUEUED_UPLOAD   = 'queuedUP'
STALLED_DOWNLOAD = 'stalledDL'
STALLED_UPLOAD   = 'stalledUP'
STOPPED_DOWNLOAD = 'stoppedDL'
STOPPED_UPLOAD   = 'stoppedUP'
UNKNOWN = 'unknown'
UPLOADING = 'uploading'
```

#### State helpers

Convenience predicates (computed properties) for easy grouping:

* `is_checking: bool` — any of the “checking” states
* `is_complete: bool` — completed upload/seed states
* `is_downloading: bool` — actively acquiring data
* `is_errored: bool` — error state
* `is_paused: bool` — **alias of `is_stopped`**
* `is_stopped: bool` — stopped / paused states
* `is_uploading: bool` — actively seeding

#### State value changes (v5+ / Web API v2.11+)

* In **qBittorrent v5.0.0**:

  * `PAUSED_UPLOAD` was renamed to **`STOPPED_UPLOAD`**
  * `PAUSED_DOWNLOAD` was renamed to **`STOPPED_DOWNLOAD`**
* In **Web API v2.11.0**: field values `pausedDL` / `pausedUP` were renamed to **`stoppedDL` / `stoppedUP`**.

> The enum includes *both* so your code can interoperate with mixed server versions.

#### Usage examples

```python
from qbittorrentapi import Client, TorrentState

client = Client()

# Filter torrents by a semantic condition
for t in client.torrents_info():
    state = TorrentState(t.state)         # derive enum from string
    if state.is_downloading:
        print(f"{t.hash[-6:]} is downloading…")
    if state.is_stopped:
        print(f"{t.name} is stopped")

# Branching on explicit states
for t in client.torrents_info():
    s = TorrentState(t.state)
    if s in (TorrentState.QUEUED_DOWNLOAD, TorrentState.QUEUED_UPLOAD):
        ...
```

---

## Tracker Status Model

### `TrackerStatus` enum

Integer enum for qBittorrent tracker status codes:

```
DISABLED      = 0
NOT_CONTACTED = 1
WORKING       = 2
UPDATING      = 3
NOT_WORKING   = 4
```

**Property**

* `display: str` — a human-friendly string for UIs/logs.

#### Usage example

```python
from qbittorrentapi import Client, TrackerStatus

client = Client()
for t in client.torrents_info():
    for tr in t.trackers:
        status = TrackerStatus(tr.status)
        print(f"{t.hash[-6:]}: {status.display:>13} : {tr.url}")
```

---

### Appendix: Quick Cheats

* Need to ship a list as `a|b|c`? Many endpoints accept the pipe-delimited format; the client provides internal helpers, but building it manually is simply:

  ```python
  hashes = ["abcd", "ef01", "2345"]
  payload = "|".join(hashes)
  ```

* Prefer enums over raw strings/ints; they’re self-documenting and future-proof when qBittorrent renames fields.
* The `Dictionary`/`List` wrappers behave like their built-in counterparts—**plus** attribute access. Use whichever style reads cleanest in your codebase.

---

*That’s the definitions layer in one sitting. Keep this page close; your future self will thank you when a state string changes and your enums don’t flinch.*
