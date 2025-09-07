# qBittorrent Torrent Creator API (Python) – `qBittorrent_api_create.md`

> Create `.torrent` files from local files or directories via qBittorrent’s Web API using the `qbittorrent-api` Python client. Includes usage patterns, parameters, return types, and robust examples with error handling.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="qBittorrent Web API" src="https://img.shields.io/badge/Web%20API-%E2%89%A52.10.4-blue">
  <img alt="qBittorrent" src="https://img.shields.io/badge/qBittorrent-%E2%89%A55.0.0-005f9e">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `TorrentCreatorAPIMixIn`](#class-torrentcreatorapimixin)
  * [Class: `TorrentCreator`](#class-torrentcreator)
  * [Class: `TorrentCreatorTaskDictionary`](#class-torrentcreatortaskdictionary)
  * [Class: `TorrentCreatorTaskStatus`](#class-torrentcreatortaskstatus)
  * [Enum: `TaskStatus`](#enum-taskstatus)
  * [Class: `TorrentCreatorTaskStatusList`](#class-torrentcreatortaskstatuslist)
* [Usage Patterns](#usage-patterns)

  * [Minimal: create, poll, download, delete](#minimal-create-poll-download-delete)
  * [Hybrid vs v1 vs v2 format](#hybrid-vs-v1-vs-v2-format)
  * [Trackers and Web Seeds](#trackers-and-web-seeds)
  * [Start seeding automatically](#start-seeding-automatically)
  * [Saving the `.torrent` to disk](#saving-the-torrent-to-disk)
* [Parameters & Types](#parameters--types)
* [Errors & Exceptions](#errors--exceptions)
* [Status & Progress](#status--progress)
* [FAQ](#faq)
* [Version Notes](#version-notes)
* [See Also](#see-also)

</details>

---

## Overview

The **Torrent Creator** endpoints let you ask the qBittorrent Web UI to build a `.torrent` from a local file or directory path accessible to the qBittorrent host. You enqueue a creation task, poll its status, fetch the resulting `.torrent` bytes, and optionally instruct qBittorrent to start seeding immediately.

These methods are exposed in `qbittorrent-api` via the `Client.torrentcreator` namespace and corresponding mixin methods.

updated: 2025-09-06T19:09:40-05:00
---

## Quick Start

```python
from qbittorrentapi import Client
from qbittorrentapi import exceptions as qba_exc
from qbittorrentapi.torrentcreator import TaskStatus
import time
from pathlib import Path

client = Client(host="localhost:8080", username="admin", password="adminadmin")

# 1) enqueue a creation task
task = client.torrentcreator.add_task(
    source_path="/path/to/data",
    format="hybrid",           # 'v1' | 'v2' | 'hybrid' (default if None)
    start_seeding=False,       # set True to auto-add when finished
    is_private=False,
    comment="Created via qbittorrent-api",
    trackers=[
        "udp://tracker.opentrackr.org:1337/announce",
        "https://tracker.example.com/announce",
    ],
    url_seeds=["https://my.cdn.example.com/file.mkv"],
)

# 2) poll status until finished or failed
while True:
    status = task.status()  # -> TorrentCreatorTaskStatus
    state = TaskStatus(status.status)
    if state in (TaskStatus.FINISHED, TaskStatus.FAILED):
        break
    time.sleep(0.5)

if state is TaskStatus.FINISHED:
    # 3) get bytes for the .torrent
    torrent_bytes = task.torrent_file()
    out_path = Path("output.torrent")
    out_path.write_bytes(torrent_bytes)
else:
    print("Torrent creation failed:", getattr(status, "message", "<no message>"))

# 4) clean up the task (recommended)
task.delete()
```

---

## API Surface

### Class: `TorrentCreatorAPIMixIn`

**Bases:** `AppAPIMixIn`
Implementation of all Torrent Creator API methods.

**Signature**

```text
TorrentCreatorAPIMixIn(
  host=None, port=None, username=None, password=None,
  EXTRA_HEADERS=None, REQUESTS_ARGS=None, HTTPADAPTER_ARGS=None,
  VERIFY_WEBUI_CERTIFICATE=True, FORCE_SCHEME_FROM_HOST=False,
  RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
  RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
  VERBOSE_RESPONSE_LOGGING=False, SIMPLE_RESPONSES=False,
  DISABLE_LOGGING_DEBUG_OUTPUT=False
) -> None
```

#### Methods

##### `torrentcreator_add_task(...) -> TorrentCreatorTaskDictionary`

Add a task to create a new torrent.

* **Introduced:** qBittorrent **v5.0.0** (Web API **v2.10.4**)
* **Raises:** `Conflict409Error` (too many existing torrent creator tasks)

Parameters (see [Parameters & Types](#parameters--types)):

* `source_path`, `torrent_file_path`, `format`, `start_seeding`,
  `is_private`, `optimize_alignment`, `padded_file_size_limit`,
  `piece_size`, `comment`, `trackers`, `url_seeds`, `source`, `**kwargs`

Returns: **`TorrentCreatorTaskDictionary`**

---

##### `torrentcreator_delete_task(task_id=None, **kwargs) -> None`

Delete a torrent creation task.

* **Introduced:** qBittorrent **v5.0.0** (Web API **v2.10.4**)
* **Raises:** `NotFound404Error` (task not found)

Parameters: `task_id`

Returns: **`None`**

---

##### `torrentcreator_status(task_id=None, **kwargs) -> TorrentCreatorTaskStatusList`

Get status for a torrent creation task.

* **Introduced:** qBittorrent **v5.0.0** (Web API **v2.10.4**)
* **Raises:** `NotFound404Error` (task not found)

Parameters: `task_id`

Returns: **`TorrentCreatorTaskStatusList`**

---

##### `torrentcreator_torrent_file(task_id=None, **kwargs) -> bytes`

Fetch the `.torrent` file bytes for a completed task.

* **Introduced:** qBittorrent **v5.0.0** (Web API **v2.10.4**)
* **Raises:**

  * `NotFound404Error` (task not found)
  * `Conflict409Error` (task not yet finished or it failed)

Parameters: `task_id`

Returns: **`bytes`**

---

### Class: `TorrentCreator`

Allows interaction with Torrent Creator endpoints through the object-style API:

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")
task = client.torrentcreator.add_task(source_path="/path/to/data")

from qbittorrentapi.torrentcreator import TaskStatus
if TaskStatus(task.status().status) == TaskStatus.FINISHED:
    torrent_bytes = task.torrent_file()
task.delete()

# or
client.torrentcreator.delete_task(task_id=task.taskID)
```

#### Methods

* `add_task(...) -> TorrentCreatorTaskDictionary`
  Implements `torrentcreator_add_task()`.

* `delete_task(task_id=None, **kwargs) -> None`
  Implements `torrentcreator_delete_task()`.

* `status(task_id=None, **kwargs) -> TorrentCreatorTaskStatusList`
  Implements `torrentcreator_status()`.

* `torrent_file(task_id=None, **kwargs) -> bytes`
  Implements `torrentcreator_torrent_file()`.

---

### Class: `TorrentCreatorTaskDictionary`

**Bases:** `ClientCache[TorrentCreatorAPIMixIn]`, `Dictionary[...]`
Response object returned by `add_task()`.

Convenience instance methods:

* `delete(**kwargs) -> None` – Implements `torrentcreator_delete_task()`
* `status(**kwargs) -> TorrentCreatorTaskStatus` – Implements `torrentcreator_status()`
* `torrent_file(**kwargs) -> bytes` – Implements `torrentcreator_torrent_file()`

---

### Class: `TorrentCreatorTaskStatus`

**Bases:** `ListEntry`
Represents a single task status entry in a status list.

> *Definition details may vary with qBittorrent version.*

Commonly used attribute(s):

* `status` → one of `TaskStatus` enum values

---

### Enum: `TaskStatus`

Enumeration of possible task states:

```text
FAILED = 'Failed'
FINISHED = 'Finished'
QUEUED = 'Queued'
RUNNING = 'Running'
```

---

### Class: `TorrentCreatorTaskStatusList`

**Bases:** `list[TorrentCreatorTaskStatus]`
Response type returned by `status()` calls.

---

## Usage Patterns

### Minimal: create, poll, download, delete

```python
task = client.torrentcreator.add_task(source_path="/path/to/dir_or_file")
while True:
    st = task.status()
    if TaskStatus(st.status) in (TaskStatus.FINISHED, TaskStatus.FAILED):
        break
torrent_bytes = task.torrent_file() if TaskStatus(st.status) is TaskStatus.FINISHED else None
task.delete()
```

### Hybrid vs v1 vs v2 format

* `format="hybrid"` (default when `None`) includes **both** v1 and v2 metadata.
* `format="v1"` and `format="v2"` generate the corresponding single-format metadata.
* Hybrid maximizes compatibility with older clients/trackers; single-format reduces size and hashing overhead for specific ecosystems.

### Trackers and Web Seeds

You may provide trackers and web seeds as a **string** (single endpoint) or a **list of strings**:

```python
task = client.torrentcreator.add_task(
    source_path="/path/to/data",
    trackers=[
        "udp://tracker.opentrackr.org:1337/announce",
        "https://tracker.example.com/announce",
    ],
    url_seeds="https://mirror.example.com/myfile.bin",
    source="MyContent Release Group v1.0",  # Content identification
)
```

### Start seeding automatically

Set `start_seeding=True` to instruct qBittorrent to automatically add and begin seeding the newly created torrent once it’s finished:

```python
task = client.torrentcreator.add_task(
    source_path="/path/to/data",
    start_seeding=True,
)
```

> If you plan to **manually** handle the resulting `.torrent`, keep `start_seeding=False` and fetch bytes with `task.torrent_file()`.

### Saving the `.torrent` to disk

```python
from pathlib import Path
torrent_bytes = task.torrent_file()
Path("my_content.torrent").write_bytes(torrent_bytes)
```

### Source identification

Use the `source` parameter to add content identification metadata:

```python
task = client.torrentcreator.add_task(
    source_path="/path/to/data",
    source="MyReleaseGroup v1.0",
    comment="Official release with source identification",
)
```

The source field helps identify the origin or release group of the content.

---

## Parameters & Types

Parameters accepted by `add_task(...)` / `torrentcreator_add_task(...)`:

| Parameter                | Type                           | Description                    |                                                                       |                                                                                                                           |
| ------------------------ | ------------------------------ | ------------------------------ | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `source_path`            | \`str                          | os.PathLike                    | None\`                                                                | Absolute path (file or directory) **on the qBittorrent host** for content.                                                |
| `torrent_file_path`      | \`str                          | os.PathLike                    | None\`                                                                | Path where qBittorrent should save the resulting `.torrent` file (server-side). Optional if you plan to retrieve via API. |
| `format`                 | \`Literal\['v1','v2','hybrid'] | None\`                         | Metadata format. `None` defaults to `"hybrid"`.                       |                                                                                                                           |
| `start_seeding`          | \`bool                         | None\`                         | If `True`, qBittorrent adds the torrent to the session automatically. |                                                                                                                           |
| `is_private`             | \`bool                         | None\`                         | Mark torrent as private.                                              |                                                                                                                           |
| `optimize_alignment`     | \`bool                         | None\`                         | Enforce optimized file alignment when creating the torrent.           |                                                                                                                           |
| `padded_file_size_limit` | \`int                          | None\`                         | Size threshold (bytes) for adding padding files.                      |                                                                                                                           |
| `piece_size`             | \`int                          | None\`                         | Piece size in bytes. If omitted, qBittorrent chooses automatically.   |                                                                                                                           |
| `comment`                | \`str                          | None\`                         | Optional comment embedded in the torrent.                             |                                                                                                                           |
| `trackers`               | \`str                          | list\[str]                     | None\`                                                                | Tracker announce URLs.                                                                                                    |
| `url_seeds`              | \`str                          | list\[str]                     | None\`                                                                | Web seeds (a.k.a. URL seeds).                                                                                             |
| `source`                 | \`str                          | None\`                         | Source identifier for content identification and metadata.             |                                                                                                                           |
| `**kwargs`               | —                              | Reserved for future expansion. |                                                                       |                                                                                                                           |

**Return Types**

* `add_task(...)` → `TorrentCreatorTaskDictionary`
* `delete_task(...)` → `None`
* `status(...)` → `TorrentCreatorTaskStatusList` (or a `TorrentCreatorTaskStatus` from the task instance method)
* `torrent_file(...)` → `bytes`

---

## Errors & Exceptions

Typical exceptions (import from `qbittorrentapi.exceptions` as needed):

* **`Conflict409Error`**

  * When enqueuing: too many existing torrent-creator tasks.
  * When fetching `.torrent` bytes: creation not finished or it failed.

* **`NotFound404Error`**

  * Task ID does not exist (deleted or never existed).

**Example handling**

```python
from qbittorrentapi import exceptions as qba_exc

try:
    task = client.torrentcreator.add_task(source_path="/not/a/real/path")
except qba_exc.Conflict409Error as e:
    print("Task queue limit reached:", e)
except qba_exc.NotFound404Error as e:
    print("Task not found:", e)
```

---

## Status & Progress

`task.status()` returns a `TorrentCreatorTaskStatus`. Common usage:

```python
st = task.status()
print("Status:", st.status)  # 'Queued' | 'Running' | 'Finished' | 'Failed'

# Introspect available fields (differs by version—treat as dict-like if needed)
try:
    # If object supports dict-like access in your version
    keys = list(dict(st).keys())
    print("Known status keys:", keys)
except Exception:
    # Fallback: raw repr
    print("Status repr:", repr(st))
```

**Typical lifecycle**

1. `Queued` → creation request accepted by qBittorrent.
2. `Running` → hashing/metadata build in progress.
3. `Finished` → `.torrent` is ready; call `torrent_file()`.
4. `Failed` → creation failed; check any message fields/logs in qBittorrent.

---

## FAQ

**Q: Does `source_path` need to be on the same machine as qBittorrent?**
**A:** Yes. The Web API instructs qBittorrent to read that path locally (or via a path it can reach via mounts/shares).

**Q: Can I control piece size?**
**A:** Yes via `piece_size`; otherwise qBittorrent chooses automatically.

**Q: What happens if I set `start_seeding=True`?**
**A:** After `Finished`, qBittorrent automatically adds the torrent and begins seeding; you can still fetch the `.torrent` bytes if needed.

**Q: How do I limit how many creation tasks run?**
**A:** If you hit `Conflict409Error` on enqueue, wait for active tasks to complete or delete queued tasks before submitting more.

**Q: Can I save directly to a `.torrent` on the server?**
**A:** Use `torrent_file_path` to instruct qBittorrent to write the file on the host. You may also fetch bytes via `torrent_file()` and save client-side.

---

## Version Notes

* **Introduced:** qBittorrent **5.0.0** with Web API **2.10.4**.
* Behavior and available fields in `TorrentCreatorTaskStatus` may evolve with newer qBittorrent releases.

---

## See Also

* Python package: **`qbittorrent-api`** – general client usage and authentication.
* qBittorrent Web UI settings for default save paths and behavior (piece size, privacy, etc.).

---

### Appendix: Full Reference Blocks

> These mirror the Sphinx/autodoc objects in Markdown form for GitHub.

#### `TorrentCreatorAPIMixIn`

* `torrentcreator_add_task(source_path=None, torrent_file_path=None, format=None, start_seeding=None, is_private=None, optimize_alignment=None, padded_file_size_limit=None, piece_size=None, comment=None, trackers=None, url_seeds=None, source=None, **kwargs) -> TorrentCreatorTaskDictionary`
  *Add a task to create a new torrent.*
  **Raises:** `Conflict409Error`

* `torrentcreator_delete_task(task_id=None, **kwargs) -> None`
  *Delete a torrent creation task.*
  **Raises:** `NotFound404Error`

* `torrentcreator_status(task_id=None, **kwargs) -> TorrentCreatorTaskStatusList`
  *Get status for a torrent creation task.*
  **Raises:** `NotFound404Error`

* `torrentcreator_torrent_file(task_id=None, **kwargs) -> bytes`
  *Retrieve torrent file for created torrent.*
  **Raises:** `NotFound404Error`, `Conflict409Error`

#### `TorrentCreator`

* `add_task(...) -> TorrentCreatorTaskDictionary`
* `delete_task(task_id=None, **kwargs) -> None`
* `status(task_id=None, **kwargs) -> TorrentCreatorTaskStatusList`
* `torrent_file(task_id=None, **kwargs) -> bytes`

#### `TorrentCreatorTaskDictionary`

* `delete(**kwargs) -> None`
* `status(**kwargs) -> TorrentCreatorTaskStatus`
* `torrent_file(**kwargs) -> bytes`

#### `TorrentCreatorTaskStatus`

* *ListEntry; fields vary by Web API version. Common field:* `status`.

#### `TaskStatus` (Enum)

* `FAILED`, `FINISHED`, `QUEUED`, `RUNNING`

#### `TorrentCreatorTaskStatusList`

* *List of `TorrentCreatorTaskStatus`.*

---

<sub><em>Tip:</em> For reproducible builds in CI, pin both qBittorrent and `qbittorrent-api` versions, and surface `TaskStatus` values in logs during polling so failures are obvious at a glance.</sub>
