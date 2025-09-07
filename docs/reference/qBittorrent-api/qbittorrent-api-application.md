# qBittorrent Application API (Python) — `qBittorrent_api_application.md`

> Control global application settings and metadata via qBittorrent’s Web API using the `qbittorrent-api` Python client. This page covers versions/build info, preferences (read & write), cookies, default save paths, network interfaces, directory listings, shutdown, and version queries—with examples and error-handling patterns.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Web API" src="https://img.shields.io/badge/Web%20API-%E2%89%A52.3-blue">
  <img alt="qBittorrent" src="https://img.shields.io/badge/qBittorrent-%E2%89%A54.2.0-005f9e">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `AppAPIMixIn`](#class-appapimixin)
  * [Class: `Application`](#class-application)
  * [Dictionary/List Types](#dictionarylist-types)
* [Method Reference](#method-reference)

  * [`app_build_info`](#app_build_info)
  * [`app_cookies` / `app_set_cookies`](#app_cookies--app_set_cookies)
  * [`app_default_save_path`](#app_default_save_path)
  * [`app_get_directory_content`](#app_get_directory_content)
  * [`app_network_interface_list` & `app_network_interface_address_list`](#app_network_interface_list--app_network_interface_address_list)
  * [`app_preferences` / `app_set_preferences`](#app_preferences--app_set_preferences)
  * [`app_send_test_email`](#app_send_test_email)
  * [`app_shutdown`](#app_shutdown)
  * [`app_version` & `app_web_api_version`](#app_version--app_web_api_version)
* [Usage Patterns](#usage-patterns)

  * [Reading and Partially Updating Preferences](#reading-and-partially-updating-preferences)
  * [Working with Cookies](#working-with-cookies)
  * [Enumerating Interfaces & Addresses](#enumerating-interfaces--addresses)
  * [Listing a Directory](#listing-a-directory)
  * [Shutdown Safety Checklist](#shutdown-safety-checklist)
* [Errors & Exceptions](#errors--exceptions)
* [Version Notes & Compatibility](#version-notes--compatibility)
* [Appendix: Property vs Method Mapping](#appendix-property-vs-method-mapping)
* [See Also](#see-also)

</details>

---

## Overview

The **Application** endpoints expose global qBittorrent capabilities: application version/build info, Web API version, preferences (as a dictionary you can read and partially update), cookies (read/set), default save path, network interface information, directory listings on the host, and a programmatic shutdown hook.

In `qbittorrent-api`, these are accessible either as **methods** (e.g., `client.app_version()`) or via the object-style **`client.application`** interface with properties and helpers.

updated: 2025-09-06T19:14:05-05:00
---

## Quick Start

```python
from qbittorrentapi import Client

client = Client(host="localhost:8080", username="admin", password="adminadmin")

print("qBittorrent:", client.app_version())        # e.g., "v5.0.0"
print("Web API:",    client.app_web_api_version())  # e.g., "2.10.4"

prefs = client.app_preferences()
print("Default Save Path:", client.app_default_save_path())
print("DHT enabled?", prefs.get("dht"))

# Toggle a single preference (partial update)
client.app_set_preferences({"dht": not prefs.get("dht", True)})

# Object-style access:
print(client.application.version)
print(client.application.web_api_version)
is_dht_enabled = client.application.preferences["dht"]
client.application.preferences = dict(dht=not is_dht_enabled)
```

---

## API Surface

### Class: `AppAPIMixIn`

**Bases:** `AuthAPIMixIn`
**Signature:**

```text
AppAPIMixIn(
  host=None, port=None, username=None, password=None,
  EXTRA_HEADERS=None, REQUESTS_ARGS=None, HTTPADAPTER_ARGS=None,
  VERIFY_WEBUI_CERTIFICATE=True, FORCE_SCHEME_FROM_HOST=False,
  RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
  RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
  VERBOSE_RESPONSE_LOGGING=False, SIMPLE_RESPONSES=False,
  DISABLE_LOGGING_DEBUG_OUTPUT=False
) -> None
```

Implements all Application API methods listed in [Method Reference](#method-reference).

---

### Class: `Application`

High-level, attribute-friendly wrapper around the same endpoints.

**Usage:**

```python
from qbittorrentapi import Client
client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Properties
print(client.application.version)
print(client.application.web_api_version)
print(client.application.default_save_path)

# Preferences can be read and partially updated
prefs = client.application.preferences
prefs["web_ui_clickjacking_protection_enabled"] = True
client.application.preferences = prefs

# Helpers equivalent to app_* methods
client.application.send_test_email()
client.application.shutdown()
```

**Implements** (property/methods):

* `build_info: BuildInfoDictionary`
* `cookies: CookieList` / `set_cookies(cookies)`
* `default_save_path: str`
* `get_directory_content(directory_path) -> DirectoryContentList`
* `network_interface_list: NetworkInterfaceList`
* `network_interface_address_list(interface_name='') -> NetworkInterfaceAddressList`
* `preferences: ApplicationPreferencesDictionary` / `set_preferences(prefs)`
* `send_test_email() -> None`
* `shutdown() -> None`
* `version: str`
* `web_api_version: str`

---

### Dictionary/List Types

* `ApplicationPreferencesDictionary` — Response for `app_preferences()`
  Definition: <a href="https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-application-preferences">wiki: get-application-preferences</a>

* `BuildInfoDictionary` — Response for `app_build_info()`
  Definition: <a href="https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-build-info">wiki: get-build-info</a>

* `DirectoryContentList` — `list[str]` for `app_get_directory_content()`

* `Cookie` / `CookieList` — Response for `app_cookies()`; see [Working with Cookies](#working-with-cookies)

* `NetworkInterface` / `NetworkInterfaceList` — Response for `app_network_interface_list()`

* `NetworkInterfaceAddressList` — `list[str]` for `app_network_interface_address_list()`

---

## Method Reference

### `app_build_info`

**Signature:** `app_build_info(**kwargs) -> BuildInfoDictionary`
qBittorrent build info.
**Introduced:** qBittorrent **v4.2.0** (Web API **v2.3**)

---

### `app_cookies` / `app_set_cookies`

* **Get:** `app_cookies(**kwargs) -> CookieList`
  Retrieve current cookies.

* **Set:** `app_set_cookies(cookies=None, **kwargs) -> None`
  Set cookies. Accepts a `CookieList` or a list of mappings like:

  ```python
  cookies = [
      {
          "domain": "example.com",
          "path": "/example/path",
          "name": "cookie name",
          "value": "cookie value",
          "expirationDate": 1729366667,  # epoch seconds
      },
  ]
  ```

---

### `app_default_save_path`

**Signature:** `app_default_save_path(**kwargs) -> str`
The default path where torrents are saved.

---

### `app_get_directory_content`

**Signature:** `app_get_directory_content(directory_path=None) -> DirectoryContentList`
List the contents of a directory on the **qBittorrent host**.

* **Raises:** `NotFound404Error` — path not found or is not a directory
* **Params:** `directory_path: str | PathLike | None`

---

### `app_network_interface_list` & `app_network_interface_address_list`

* **List:** `app_network_interface_list(**kwargs) -> NetworkInterfaceList`
  Get network interfaces on the host.
  **Introduced:** qBittorrent **v4.2.0** (Web API **v2.3**)

* **Addresses:** `app_network_interface_address_list(interface_name='', **kwargs) -> NetworkInterfaceAddressList`
  Addresses for a given interface; omit `interface_name` to retrieve all.
  **Introduced:** qBittorrent **v4.2.0** (Web API **v2.3**)

---

### `app_preferences` / `app_set_preferences`

* **Get:** `app_preferences(**kwargs) -> ApplicationPreferencesDictionary`
  Full preferences dictionary.

* **Set (partial OK):** `app_set_preferences(prefs=None, **kwargs) -> None`
  Send one or more keys to update. You don’t need to post the entire dictionary.

---

### `app_send_test_email`

**Signature:** `app_send_test_email() -> None`
Sends a test email using the configured email account.

---

### `app_shutdown`

**Signature:** `app_shutdown(**kwargs) -> None`
Shut down qBittorrent. See [Shutdown Safety Checklist](#shutdown-safety-checklist).

---

### `app_version` & `app_web_api_version`

* `app_version(**kwargs) -> str` — qBittorrent application version
* `app_web_api_version(**kwargs) -> str` — Web API version string

---

## Usage Patterns

### Reading and Partially Updating Preferences

```python
from qbittorrentapi import Client
client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Read everything (dict-like)
prefs = client.app_preferences()
print("Clickjacking protection:", prefs.get("web_ui_clickjacking_protection_enabled"))

# Partial update 1: toggle a single boolean
client.app_set_preferences({"web_ui_clickjacking_protection_enabled": True})

# Partial update 2: batch update only the keys you need
client.app_set_preferences({
    "dht": False,
    "web_ui_secure_cookie": True,
})

# Object-style with property write (under the hood calls app_set_preferences)
p = client.application.preferences
p["dht"] = not p.get("dht", True)
client.application.preferences = p
```

**Tips**

* Prefer **partial updates**: send only the keys you want to change.
* Read–modify–write to avoid stomping unrelated settings.
* Keep a small allow-list of keys your tool manages to reduce accidents.

---

### Working with Cookies

```python
cookies = client.app_cookies()     # -> CookieList
for c in cookies:
    print(c.name, "=", c.value, "domain:", c.domain)

client.app_set_cookies([
    {
        "domain": "example.com",
        "path": "/",
        "name": "session",
        "value": "abc123",
        "expirationDate": 1893456000,
    }
])
```

**Notes**

* `expirationDate` is epoch seconds.
* Use domain/path scoping responsibly; avoid leaking cookies to unintended paths.

---

### Enumerating Interfaces & Addresses

```python
# All interfaces (objects may include name/flags/mtu depending on version)
ifaces = client.app_network_interface_list()
for nic in ifaces:
    print("Interface:", getattr(nic, "name", str(nic)))

# Addresses for a particular interface
addrs = client.app_network_interface_address_list(interface_name="eth0")
print("eth0 addresses:", list(addrs))

# Or omit to get all addresses known to qBittorrent
all_addrs = client.app_network_interface_address_list()
```

---

### Listing a Directory

```python
from qbittorrentapi import exceptions as qba_exc

try:
    contents = client.app_get_directory_content("/data/torrents")
    for entry in contents:
        print(entry)
except qba_exc.NotFound404Error:
    print("Directory missing or not a directory on the qBittorrent host.")
```

**Important:** `directory_path` must be accessible **on the qBittorrent host**, not your local workstation.

---

### Shutdown Safety Checklist

The shutdown endpoint is powerful—treat it with care.

* Verify **no critical operations** are underway (e.g., moving data).
* In automations, require a **confirmation flag** or **interactive consent**.
* Prefer scheduling maintenance windows for automated shutdowns.

```python
confirm = True  # gate this behind a CLI flag or UI switch
if confirm:
    client.app_shutdown()
```

---

## Errors & Exceptions

Import from `qbittorrentapi.exceptions` as needed:

* `NotFound404Error` — e.g., `app_get_directory_content` when path is invalid.
* `APIConnectionError` / `Timeout` — connectivity issues to Web UI.
* `Forbidden403Error` / `Unauthorized401Error` — auth/permission problems.

Basic pattern:

```python
from qbittorrentapi import exceptions as qba_exc

try:
    info = client.app_build_info()
except qba_exc.Unauthorized401Error:
    print("Bad credentials or session expired.")
except qba_exc.APIConnectionError as e:
    print("Cannot reach Web UI:", e)
```

---

## Version Notes & Compatibility

* `app_build_info`, `app_network_interface_list`, and `app_network_interface_address_list` were **introduced in qBittorrent v4.2.0** (Web API **v2.3**).
* Field shapes for list/dict entries can vary by qBittorrent/Web API version; code defensively (use `.get()` and feature-detect when possible).
* For reproducible tooling, pin both **qBittorrent** and **`qbittorrent-api`** versions.

---

## Appendix: Property vs Method Mapping

| Object-style (`client.application`)       | Method-style (`client.app_*`)                 | Notes                                      |
| ----------------------------------------- | --------------------------------------------- | ------------------------------------------ |
| `version`                                 | `app_version()`                               | Returns `str`                              |
| `web_api_version`                         | `app_web_api_version()`                       | Returns `str`                              |
| `build_info`                              | `app_build_info()`                            | Returns `BuildInfoDictionary`              |
| `cookies`                                 | `app_cookies()`                               | Returns `CookieList`                       |
| `set_cookies(cookies)`                    | `app_set_cookies(cookies)`                    | Mutates cookies                            |
| `default_save_path`                       | `app_default_save_path()`                     | Returns `str`                              |
| `get_directory_content(path)`             | `app_get_directory_content(path)`             | Returns `DirectoryContentList`             |
| `network_interface_list`                  | `app_network_interface_list()`                | Returns `NetworkInterfaceList`             |
| `network_interface_address_list(name='')` | `app_network_interface_address_list(name='')` | Returns `NetworkInterfaceAddressList`      |
| `preferences` (get)                       | `app_preferences()`                           | Returns `ApplicationPreferencesDictionary` |
| `preferences = {...}` (set)               | `app_set_preferences({...})`                  | Partial updates supported                  |
| `send_test_email()`                       | `app_send_test_email()`                       | —                                          |
| `shutdown()`                              | `app_shutdown()`                              | —                                          |

---

## See Also

* qBittorrent Web UI API (Application):

  * <a href="https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-application-preferences">Get Application Preferences</a>
  * <a href="https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#user-content-get-build-info">Get Build Info</a>
* Python package: **`qbittorrent-api`** on PyPI for installation and general usage.
