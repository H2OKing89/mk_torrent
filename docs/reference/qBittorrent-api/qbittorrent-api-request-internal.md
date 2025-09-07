# qBittorrent Request Internals — `qBittorrent_api_request_internal.md`

> The plumbing beneath `qbittorrent-api`: HTTP session handling, URL building, scheme detection, retries, payload formatting, casting, and version-gated endpoint checks. If the public client is the dashboard, this is the wiring harness.

<details>
<summary><strong>Table of Contents</strong></summary>

* [Overview](#overview)
* [Architecture at a Glance](#architecture-at-a-glance)
* [Class: `QbittorrentSession`](#class-qbittorrentsession)

  * [Purpose](#purpose)
  * [Signature](#signature)
  * [request(...)](#request)
  * [Usage Notes & Examples](#usage-notes--examples)
* [Class: `QbittorrentURL`](#class-qbittorrenturl)

  * [Purpose](#purpose-1)
  * [build(...)](#build)
  * [build\_base\_url(...)](#build_base_url)
  * [detect\_scheme(...)](#detect_scheme)
  * [Example: Reverse Proxy & Base Path](#example-reverse-proxy--base-path)
* [Class: `Request`](#class-request)

  * [Purpose](#purpose-2)
  * [Initialization & Settings](#initialization--settings)
  * [Core Flow: `_request_manager` → `_request` → `_auth_request`](#core-flow-_request_manager--_request--_auth_request)
  * [Convenience Wrappers: `_get` / `_post` (+ cast variants)](#convenience-wrappers-_get--_post--cast-variants)
  * [Payload & Files: `_format_payload`](#payload--files-_format_payload)
  * [Casting: `_cast`](#casting-_cast)
  * [HTTP Errors: `_handle_error_responses`](#http-errors-_handle_error_responses)
  * [Version Gating: `_is_endpoint_supported_for_version`](#version-gating-_is_endpoint_supported_for_version)
  * [Utilities: `_list2string`, `_verbose_logging`, session lifecycle](#utilities-_list2string-_verbose_logging-session-lifecycle)
  * [End-to-End Example](#end-to-end-example)
* [Gotchas & Best Practices](#gotchas--best-practices)

</details>

---

## Overview

The **request layer** is the internal, reusable scaffolding that all endpoint mixins rely on. It:

* Configures a **Requests Session** with consistent defaults.
* Builds and caches the **base URL**, including **scheme detection** (HTTP ↔ HTTPS) and **base path** support.
* Normalizes **payloads** (`params`, `data`, `files`) and applies **headers**, **timeouts**, **adapters**, and **TLS** behavior.
* Manages **retries** (notably when the first attempt reveals the wrong scheme), **re-authentication**, and **response casting** into typed objects.
* Gates calls against **Web API version** (introduced/removed) to prevent unsupported usage.

updated: 2025-09-06T19:00:01-05:00
---

## Architecture at a Glance

```
┌────────────────────┐
│  API Mixins        │  e.g., TorrentsAPIMixIn.torrents_info()
└─────────┬──────────┘
          │ calls
┌─────────▼──────────┐
│  Request           │  _get/_post → _request_manager → _request → _auth_request
│  (HTTP orchestration)
└─────────┬──────────┘
          │ uses
┌─────────▼──────────┐
│ QbittorrentURL     │  build_base_url + detect_scheme + build
│ (URL construction)
└─────────┬──────────┘
          │ uses
┌─────────▼──────────┐
│ QbittorrentSession │  requests.Session with defaulted kwargs
│ (HTTP transport)
└────────────────────┘
```

---

## Class: `QbittorrentSession`

### Purpose

A thin wrapper around `requests.Session` that **injects default kwargs** (timeouts, proxies, verify, etc.) into **every** request—solving the “Requests can’t easily default per-session args” problem.

### Signature

```text
class QbittorrentSession(Session)
```

### `request(...)`

Constructs, prepares, and sends a request; returns a `Response`.

**Parameters** (subset of Requests’ standard args):

* `method: str` – HTTP verb
* `url: str` – absolute URL
* `params, data, json, headers, cookies, files, auth`
* `timeout: float | (float, float)` – connect/read tuple supported
* `allow_redirects: bool = True`
* `proxies, hooks, stream`
* `verify: bool | str` – `False` or CA bundle path
* `cert: str | tuple[str, str]` – client cert

**Returns:** `Response`

### Usage Notes & Examples

* **Global defaults** (e.g., timeouts) are baked into the session wrapper; you can still override per call.
* **TLS**: `verify=False` disables verification (okay for lab, risky in prod).
* **Proxies** and **cookies** can be passed or pre-set on the session as needed.

```python
# Internally used; example here is illustrative
sess = QbittorrentSession()
resp = sess.request(
    "GET",
    "https://qbt.local/api/v2/app/version",
    timeout=(3.1, 30),
    verify=True,
)
```

---

## Class: `QbittorrentURL`

### Purpose

Builds the **fully qualified** endpoint URL, including host, optional base path, API base (`api/v2`), namespace, and method. Also detects and caches the **scheme** when not explicit.

```text
class QbittorrentURL(object):
    def __init__(self, client): ...
```

### `build(api_namespace, api_method, headers=None, requests_kwargs=None, base_path='api/v2') -> str`

Return the **full endpoint URL**.

* `api_namespace: APINames | str` (e.g., `"torrents"`)
* `api_method: str` (e.g., `"info"`)
* `base_path: str` (default: `"api/v2"`)
* `headers: Mapping[str, str] | None`
* `requests_kwargs: Mapping[str, Any] | None`

**Returns:** full URL string

### `build_base_url(headers, requests_kwargs) -> str`

Compute (or reuse cached) base URL. If no scheme provided, it **tries HTTP**, and if that fails, **falls back to HTTPS** (redirects are respected). Any user-supplied **path** segment is preserved and prefixed to all API calls.

**Returns:** base URL string

### `detect_scheme(base_url, default_scheme, alt_scheme, headers, requests_kwargs) -> str`

Probe which scheme (HTTP/HTTPS) actually works. Returns the chosen scheme.

---

### Example: Reverse Proxy & Base Path

If qBittorrent is reachable at `https://example.com/qbt/`, callers can provide `host="https://example.com/qbt/"`. The internal URL builder will preserve `/qbt/` and generate endpoints like:

```
https://example.com/qbt/api/v2/torrents/info
```

If no scheme is provided, the builder will first try `http://example.com/qbt/…` and then pivot to `https://…` if needed.

---

## Class: `Request`

### Purpose

One class to **initialize settings**, **send requests**, **manage retries & scheme switching**, **refresh auth** on 401/403, **cast responses**, and **enforce version gates**.

```text
class Request(object):
    def __init__(host=None, port=None, username=None, password=None,
                 EXTRA_HEADERS=None, REQUESTS_ARGS=None, HTTPADAPTER_ARGS=None,
                 VERIFY_WEBUI_CERTIFICATE=True, FORCE_SCHEME_FROM_HOST=False,
                 RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False,
                 RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
                 VERBOSE_RESPONSE_LOGGING=False, SIMPLE_RESPONSES=False,
                 DISABLE_LOGGING_DEBUG_OUTPUT=False) -> None
```

---

### Initialization & Settings

* **`_initialize_settings(...)`**: applies extra headers, requests/adapter args, TLS settings, logging verbosity toggles, and behavior flags (`FORCE_SCHEME_FROM_HOST`, `SIMPLE_RESPONSES`, version checks, etc.).
* **`_initialize_context()`**: (re)creates base URL state and auth context—used at startup and whenever cookies/settings change.

**Session Access**

* **`_session` (property)**: returns (or lazily creates) a `QbittorrentSession`.
* **`_trigger_session_initialization()`**: drops the current session reference; next request builds a fresh one.

---

### Core Flow: `_request_manager` → `_request` → `_auth_request`

* **`_request_manager(...)`**: wraps an HTTP call with **retry**/scheme flip logic. At least one retry is performed so the second pass can use the discovered scheme.
* **`_request(...)`**: creates URL (`QbittorrentURL.build`), headers, kwargs, and dispatches a GET/POST via the session; handles casting & error mapping.
* **`_auth_request(...)`**: performs the HTTP call and, on “not authorized,” transparently **re-auths** and retries.

**Common kwargs (flow-through):**

* `requests_args` (primary) or `requests_params` (alternate) for Requests kwargs (timeout, proxies, etc.)
* `headers` for per-call headers
* `params` (GET), `data` (POST), `files` (multipart)
* `response_class` for casting
* `version_introduced`, `version_removed` for version gating

**Returns:** casted object or raw `Response` (depending on `response_class`)

---

### Convenience Wrappers: `_get` / `_post` (+ cast variants)

* **`_get(...)` / `_post(...)`**: thin helpers around `_request(...)` with `http_method` fixed.
* **`_get_cast(...)` / `_post_cast(...)`**: same, but returns a **typed** response (`ResponseT`).

Each accepts the same kwargs as `_request(...)` plus `response_class`.

---

### Payload & Files: `_format_payload`

```text
static _format_payload(http_method, params=None, data=None, files=None, **kwargs)
  -> (params_dict, data_dict, files_mapping)
```

* Ensures **GET** requests use `params`, **POST** requests use `data`.
* Normalizes **`files`** into the `requests` multipart format:

  * `{ field: b"bytes" }` or `{ field: (filename, b"bytes") }`

---

### Casting: `_cast`

```text
_cast(response: Response, response_class: type, **response_kwargs) -> Any
```

* Returns `response` as-is if `response_class` is the raw `Response`.
* Otherwise, converts the `Response` JSON (or bytes) into the **requested typed container**—the same objects used throughout higher-level APIs (e.g., dictionary/list wrappers with methods).

---

### HTTP Errors: `_handle_error_responses`

```text
static _handle_error_responses(data, params, response) -> None
```

* Interprets non-2xx statuses and raises the **appropriate exception class** (e.g., `Unauthorized401Error`, `Forbidden403Error`, `NotFound404Error`, `Conflict409Error`, `InternalServerError500Error`, etc.).
* Exceptions are shaped so higher layers can handle auth, permission, and validation issues distinctly.

---

### Version Gating: `_is_endpoint_supported_for_version`

```text
_is_endpoint_supported_for_version(endpoint, version_introduced, version_removed) -> bool
```

* Prevents calls to endpoints that **don’t exist** for the connected Web API version (or were **removed**).
* Often used with behavior flags to either **raise** immediately or **no-op** (return `None`) depending on configuration.

---

### Utilities: `_list2string`, `_verbose_logging`, session lifecycle

* **`_list2string(input_list, delimiter='|')`**: converts lists to the delimited format expected by certain endpoints (e.g., `"hash1|hash2|hash3"`).
* **`_verbose_logging(url, data, params, requests_kwargs, response)`**: dumps request/response context when `VERBOSE_RESPONSE_LOGGING=True`—great for development.
* **Session lifecycle**: `_session` caches a live session; `_trigger_session_initialization()` forces a rebuild (useful after major settings changes).

---

### End-to-End Example

Below is a **representative** flow showing how a mixin might call the internal layer. (You typically won’t call these methods directly.)

```python
# Pseudo-code inside a mixin:
def torrents_info(self, **kwargs):
    # Ask for a typed list (e.g., TorrentInfoList)
    return self._get_cast(
        _name="torrents",
        _method="info",
        response_class=TorrentInfoList,        # typed wrapper
        requests_args={"timeout": (3.1, 30)},  # per-call overrides (optional)
        version_introduced="2.0.1",            # for example
        version_removed="",                    # empty if still present
        params={"filter": kwargs.get("filter")},
    )
```

The call sequence:

1. `_get_cast(...)` → `_request_manager("get", "torrents", "info", ...)`
2. URL layer builds/rehydrates base URL, **detects scheme if needed**, and composes the final endpoint.
3. **First attempt** fires; on “wrong scheme”/redirect, the manager flips and **retries**.
4. On **401/403**, `_auth_request` refreshes the cookie and retries.
5. `_handle_error_responses` maps HTTP errors to typed exceptions.
6. `_cast` returns a **typed** result (`TorrentInfoList`) or raw `Response`.

---

## Gotchas & Best Practices

* **Per-call overrides vs defaults**: Prefer setting sane defaults during `Request`/`Client` initialization; use `requests_args` for the **few** calls that need different timeouts or proxies.
* **Files vs data**: If you’re uploading torrents or forms with binary content, ensure you pass the `files` mapping, not `data`.
* **Scheme detection**: If you know you’re behind HTTPS (or a strict reverse proxy), set a proper `https://` host; auto-detection will still work, but explicit is faster.
* **Re-auth is automatic**: `_auth_request` handles cookie expiry; still, be ready to catch and respond to `LoginFailed`/`Forbidden403Error` in higher layers.
* **Version gating**: When adding new endpoints, always specify `version_introduced`/`version_removed` so older daemons yield predictable behavior under your configured policy.
* **Verbose logging**: Turn on `VERBOSE_RESPONSE_LOGGING` when developing new endpoints—then turn it off in production unless you like very chatty logs.
* **Resetting state**: Call `_trigger_session_initialization()` after drastic TLS/adapter/header changes to force a clean session.

---

*That’s the tour. The internals keep the request path clean so the public API can stay pleasant. Go forth and make clean calls!*
