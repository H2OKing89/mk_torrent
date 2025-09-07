# qBittorrent Authentication API (Python) — `qBittorrent_api_authentication.md`

> Log in and out of the qBittorrent Web UI and check session validity using the `qbittorrent-api` Python client. This page covers methods, properties, return types, exceptions, and practical usage patterns.

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-api/"><img alt="qbittorrent-api" src="https://img.shields.io/pypi/v/qbittorrent-api.svg"></a>
  <img alt="Auth API" src="https://img.shields.io/badge/API-Authentication-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Quick Start](#quick-start)
* [API Surface](#api-surface)

  * [Class: `AuthAPIMixIn`](#class-authapimixin)
  * [Class: `Authorization`](#class-authorization)
* [Method Reference](#method-reference)

  * [`auth_log_in`](#auth_log_in)
  * [`auth_log_out`](#auth_log_out)
  * [`is_logged_in` (property)](#is_logged_in-property)
* [Usage Patterns](#usage-patterns)

  * [Basic login/logout](#basic-loginlogout)
  * [Checking session validity](#checking-session-validity)
  * [Handling auth errors](#handling-auth-errors)
  * [Self-signed TLS / reverse proxies](#self-signed-tls--reverse-proxies)
* [Appendix: Property vs Method Mapping](#appendix-property-vs-method-mapping)
* [See Also](#see-also)

</details>

---

## Overview

The **Authentication** endpoints let you create and destroy sessions against the qBittorrent Web UI and perform a low-overhead check to see whether your current session cookie is still accepted. Because qBittorrent invalidates cookies when they expire, the only reliable way to confirm an existing session is to attempt a request. ([qbittorrent-api.readthedocs.io][1])

updated: 2025-09-06T19:09:40-05:00
---

## Quick Start

```python
from qbittorrentapi import Client
from qbittorrentapi import exceptions as qba_exc

client = Client(host="localhost:8080", username="admin", password="adminadmin")

# Lightweight check (does not guarantee future validity)
print("logged in?", client.is_logged_in)  # bool

try:
    client.auth_log_in(username="admin", password="adminadmin")
    # ... make API calls ...
finally:
    client.auth_log_out()
```

The client also exposes an object-style interface:

```python
is_in = client.auth.is_logged_in
client.auth.log_in(username="admin", password="adminadmin")
client.auth.log_out()
```

(See [API Surface](#api-surface) below.) ([qbittorrent-api.readthedocs.io][1])

---

## API Surface

### Class: `AuthAPIMixIn`

**Bases:** `Request`
Implements all Authentication methods: `auth_log_in`, `auth_log_out`, and the `is_logged_in` property. Constructor accepts options such as `VERIFY_WEBUI_CERTIFICATE`, `EXTRA_HEADERS`, and `REQUESTS_ARGS`. ([qbittorrent-api.readthedocs.io][1])

```text
AuthAPIMixIn(
  host=None, port=None, username=None, password=None,
  EXTRA_HEADERS=None, REQUESTS_ARGS=None, HTTPADAPTER_ARGS=None,
  VERIFY_WEBUI_CERTIFICATE=True, FORCE_SCHEME_FROM_HOST=False,
  RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
  RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
  VERBOSE_RESPONSE_LOGGING=False, SIMPLE_RESPONSES=False,
  DISABLE_LOGGING_DEBUG_OUTPUT=False
) -> None
```

([qbittorrent-api.readthedocs.io][1])

---

### Class: `Authorization`

High-level, attribute-friendly wrapper around the same endpoints:

```python
from qbittorrentapi import Client
client = Client(host="localhost:8080", username="admin", password="adminadmin")

is_logged_in = client.auth.is_logged_in
client.auth.log_in(username="admin", password="adminadmin")
client.auth.log_out()
```

Implements `is_logged_in`, `log_in(...)`, and `log_out()`. ([qbittorrent-api.readthedocs.io][1])

---

## Method Reference

### `auth_log_in`

**Signature:** `auth_log_in(username=None, password=None, **kwargs) -> None`
Starts a session with the qBittorrent host.

**Raises**

* `LoginFailed` — credentials failed to log in
* `Forbidden403Error` — user is banned or not logged in (e.g., cookie rejected) ([qbittorrent-api.readthedocs.io][1])

**Parameters**

* `username: str | None` — qBittorrent username
* `password: str | None` — qBittorrent password ([qbittorrent-api.readthedocs.io][1])

---

### `auth_log_out`

**Signature:** `auth_log_out(**kwargs) -> None`
Ends the current qBittorrent session (invalidates cookie). ([qbittorrent-api.readthedocs.io][1])

---

### `is_logged_in` (property)

**Type:** `bool`
Returns `True` if a low-overhead call indicates the current auth cookie is accepted; `False` otherwise. There is no fully reliable way to know if an existing session is *still* valid without attempting to use it (cookies can expire server-side). ([qbittorrent-api.readthedocs.io][1])

Available both as `client.is_logged_in` and `client.auth.is_logged_in`. ([qbittorrent-api.readthedocs.io][1])

---

## Usage Patterns

### Basic login/logout

```python
client = Client(host="localhost:8080", username="admin", password="adminadmin")
client.auth_log_in(username="admin", password="adminadmin")
# ... use the API ...
client.auth_log_out()
```

Object-style:

```python
client.auth.log_in(username="admin", password="adminadmin")
# ... use the API ...
client.auth.log_out()
```

([qbittorrent-api.readthedocs.io][1])

---

### Checking session validity

```python
if client.is_logged_in:
    # The current cookie is accepted right now.
    # Still, always be prepared to handle expiration later.
    pass
else:
    client.auth_log_in(username="admin", password="adminadmin")
```

This property performs a lightweight call and may flip to `False` after cookie expiry. Always handle auth errors on subsequent requests. ([qbittorrent-api.readthedocs.io][1])

---

### Handling auth errors

```python
from qbittorrentapi import exceptions as qba_exc

try:
    client.auth_log_in(username="admin", password="adminadmin")
except qba_exc.LoginFailed:
    print("Invalid username or password.")
except qba_exc.Forbidden403Error as e:
    print("Forbidden: account banned or session not authorized.", e)
```

`LoginFailed` and `Forbidden403Error` are the primary auth-related exceptions you'll encounter. ([qbittorrent-api.readthedocs.io][1])

---

### Self-signed TLS / reverse proxies

If you terminate TLS with a self-signed cert (e.g., via a local reverse proxy) and need to bypass certificate verification **for local development/labs**, you can pass `VERIFY_WEBUI_CERTIFICATE=False`:

```python
client = Client(
    host="https://qb.local:8443",
    username="admin",
    password="adminadmin",
    VERIFY_WEBUI_CERTIFICATE=False,  # only if you understand the risks
)
```

This option is accepted by the mixin/client initializer. Prefer proper CA-trusted certificates in production. ([qbittorrent-api.readthedocs.io][1])

---

## Appendix: Property vs Method Mapping

| Object-style (`client.auth`) | Method-style (`client.*`)         | Notes                             |
| ---------------------------- | --------------------------------- | --------------------------------- |
| `is_logged_in`               | `is_logged_in`                    | Boolean property on both surfaces |
| `log_in(username, password)` | `auth_log_in(username, password)` | Starts session                    |
| `log_out()`                  | `auth_log_out()`                  | Ends session                      |

(All surfaces documented in the upstream API reference.) ([qbittorrent-api.readthedocs.io][1])

---

## See Also

* Upstream docs: **Authentication** — `qbittorrent-api` API reference. ([qbittorrent-api.readthedocs.io][1])
* Package on PyPI: `qbittorrent-api` (installation and general usage).

[1]: https://qbittorrent-api.readthedocs.io/en/latest/apidoc/auth.html "Authentication - qbittorrent-api 2025.7.1.dev4+g4fc2ae4 documentation"
