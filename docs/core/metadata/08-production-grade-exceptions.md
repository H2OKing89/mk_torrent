# Production-Grade Exception System - Implementation & Usage Guide

## Overview

This document outlines the comprehensive improvements made to the metadata core exception system to support production-grade error handling, telemetry, and operational requirements. It includes both the implementation details and practical usage patterns for integrating the system throughout the metadata processing pipeline.

## Key Improvements Implemented

### 1. Enhanced Base Exception (`MetadataError`)

**New Capabilities:**

- **Machine-readable codes**: Every exception has a stable `code` field for programmatic handling
- **Retry semantics**: `temporary` boolean indicates if retry might succeed
- **Severity levels**: `error`, `warning`, `info` for filtering and display
- **User hints**: Actionable guidance for users/operators
- **Structured details**: JSON-safe context for telemetry and debugging
- **Secret redaction**: Automatic redaction of sensitive data in serialization
- **CLI-friendly formatting**: `[CODE] message` format for terminal output

**Example:**

```python
exc = MetadataError(
    "Validation failed",
    code="VALIDATION_FAILED",
    temporary=False,
    severity="error",
    hint="Fix validation errors to continue",
    details={"field_count": 3, "api_key": "secret123"}
)

# CLI output: "[VALIDATION_FAILED] Validation failed"
# Serialized: {"code": "VALIDATION_FAILED", "details": {"api_key": "[REDACTED]"}}
```

### 2. Field-Level Validation Structure

**Breaking Change:** `ValidationError` now uses structured field-level error reporting instead of flat string lists:

**Old Format:**

```python
ValidationError(["asin missing", "bitrate invalid"])
```

**New Format:**

```python
ValidationError({
    "asin": ["missing", "invalid-format"],
    "bitrate_mode": ["inconsistent-with-sample-rate"]
})
```

**Benefits:**

- UI can highlight specific fields
- Programmatic handling by mappers
- Better user experience with targeted error messages

### 3. Intelligent Retry Semantics

Each exception type now provides clear retry guidance:

| Exception Type | Temporary Examples | Permanent Examples |
|----------------|-------------------|-------------------|
| `SourceUnavailable` | HTTP 429, 503, network timeout | Missing dependencies, invalid credentials |
| `ExtractionError` | I/O errors, permission issues | Corrupt files, unsupported formats |
| `MetadataConflict` | N/A (requires policy) | All conflicts are permanent |
| `ValidationError` | N/A (requires data fixes) | All validation failures are permanent |

### 4. HTTP-Aware Error Handling

`SourceUnavailable` now captures HTTP status codes and provides appropriate retry guidance:

```python
# Rate limit with reset time
SourceUnavailable(
    "audnexus",
    "Rate limited",
    http_status=429,
    rate_limit_reset=1699999999,
    temporary=True  # Auto-detected from status
)

# Missing dependency
SourceUnavailable(
    "embedded",
    "ffprobe not found",
    temporary=False  # Permanent until resolved
)
```

### 5. Enhanced Error Context

All exceptions now carry rich, structured context:

- **Source information**: Which component/service failed
- **Stage information**: What operation was being performed
- **Technical details**: HTTP status, file paths, configuration keys
- **Resolution hints**: Specific guidance for users/operators

### 6. Security-Conscious Design

- **Automatic secret redaction**: API keys, tokens, passwords automatically redacted in logs
- **JSON-safe serialization**: All details converted to safely serializable format
- **Sanitized output**: No sensitive data leaks in error messages or telemetry

## Error Code Reference

| Code | Exception | When To Use | Retry Policy |
|------|-----------|-------------|--------------|
| `SRC_UNAVAILABLE` | `SourceUnavailable` | API down, missing deps, auth issues | Depends on cause |
| `MERGE_CONFLICT` | `MetadataConflict` | Irreconcilable source conflicts | No retry |
| `VALIDATION_FAILED` | `ValidationError` | Required fields missing/invalid | No retry |
| `PROCESSOR_NOT_FOUND` | `ProcessorNotFound` | No processor for content type | No retry |
| `CONFIG_ERROR` | `ConfigurationError` | Missing/invalid configuration | No retry |
| `EXTRACTION_FAILED` | `ExtractionError` | File I/O, parsing failures | Depends on cause |

## Usage Patterns

### Engine Retry Logic

```python
try:
    result = source.extract(file_path)
except MetadataError as exc:
    if exc.temporary:
        # Apply backoff and retry
        await asyncio.sleep(get_backoff_delay(attempt))
        return await retry_operation()
    else:
        # Log and fail fast
        logger.error("Permanent failure", **exc.to_dict())
        raise
```

### CLI Error Display

```python
try:
    process_metadata(source)
except ValidationError as exc:
    console.print(Panel(
        title=f"[bold red]{exc.code}[/]",
        content=str(exc),
        subtitle=exc.hint
    ))

    # Show field-level errors
    table = Table("Field", "Issues")
    for field, issues in exc.errors.items():
        table.add_row(field, ", ".join(issues))
    console.print(table)
```

### Telemetry Integration

```python
try:
    result = process_metadata(source)
except MetadataError as exc:
    # Structured logging with full context
    logger.error("metadata_exception", **exc.to_dict())

    # Metrics for monitoring
    metrics.increment("metadata.error", tags={
        "code": exc.code,
        "temporary": str(exc.temporary),
        "severity": exc.severity
    })
```

## Migration Guide

### Updating ValidationError Usage

**Old Code:**

```python
raise ValidationError(["asin missing"], ["year suspicious"])
```

**New Code:**

```python
raise ValidationError(
    errors={"asin": ["missing"]},
    warnings={"year": ["suspicious-future-year"]}
)
```

### Updating Exception Handling

**Old Code:**

```python
except SourceUnavailable as exc:
    logger.error(f"Source failed: {exc}")
    # Always retry
```

**New Code:**

```python
except SourceUnavailable as exc:
    logger.error("source_unavailable", **exc.to_dict())
    if exc.temporary:
        return await retry_with_backoff()
    else:
        raise  # Permanent failure
```

## Testing Coverage

The following test scenarios are implemented:

1. **Base exception functionality**: Codes, serialization, secret redaction
2. **Retry semantics**: Temporary vs permanent classification
3. **Field-level validation**: Structured error reporting
4. **HTTP status handling**: Rate limits, server errors, not found
5. **Cause chaining**: Exception context preservation
6. **Hint generation**: Contextual user guidance

## Performance Considerations

- **`__slots__`**: Used in base class to minimize memory overhead
- **Lazy serialization**: `to_dict()` only called when needed
- **Efficient pattern matching**: Compiled regex for secret detection
- **Minimal overhead**: Exception construction optimized for hot paths

## Future Enhancements

1. **Rich UI integration**: Ready for Rich Panel/Table rendering
2. **Metrics integration**: Structured data for monitoring systems
3. **Documentation links**: `doc_url` field for context-sensitive help
4. **Fingerprinting**: Deduplication of repeated errors
5. **Internationalization**: Ready for multi-language error messages

## Usage Patterns & Integration Examples

### Error Code Taxonomy

| Code | Exception | Scope | Typical Producers | Retry Policy |
|------|-----------|-------|-------------------|--------------|
| `SRC_UNAVAILABLE` | `SourceUnavailable` | Sources | audnexus (HTTP), embedded (deps) | Depends on `temporary` |
| `EXTRACTION_FAILED` | `ExtractionError` | Sources/Parsers | pathinfo/embedded/ffprobe/chapters | Depends on `temporary` |
| `MERGE_CONFLICT` | `MetadataConflict` | Services (merge) | merge_audiobook | No retry |
| `VALIDATION_FAILED` | `ValidationError` | Validators | audiobook_validator | No retry |
| `PROCESSOR_NOT_FOUND` | `ProcessorNotFound` | Engine/DI | engine/registry | No retry |
| `CONFIG_ERROR` | `ConfigurationError` | Boot/Runtime config | engine, sources | No retry |

### HTTP Status & CLI Exit Code Mapping

| Code | HTTP Status | CLI Exit Code | Description |
|------|-------------|---------------|-------------|
| `VALIDATION_FAILED` | 422 | 3 | Unprocessable Entity |
| `CONFIG_ERROR` | 400 | 4 | Bad Request |
| `PROCESSOR_NOT_FOUND` | 501 | 5 | Not Implemented |
| `SRC_UNAVAILABLE` (temp) | 503 | 10 | Service Unavailable |
| `SRC_UNAVAILABLE` (perm) | 502 | 1 | Bad Gateway |
| `MERGE_CONFLICT` | 409 | 6 | Conflict |
| `EXTRACTION_FAILED` | 500 | 1 | Internal Server Error |

### Common Throw Site Patterns (Copy-Paste Ready)

#### 1. Rate-Limited API

```python
try:
    resp = client.get(...)
    resp.raise_for_status()
except HTTPError as e:
    status = getattr(e.response, "status_code", None)
    reset = int(e.response.headers.get("X-RateLimit-Reset", 0)) or None
    raise SourceUnavailable(
        "audnexus",
        f"{status} {e}",
        http_status=status,
        rate_limit_reset=reset
    ) from e
```

#### 2. Missing Dependency (ffprobe)

```python
try:
    subprocess.run(["ffprobe", "-version"], check=True, capture_output=True)
except FileNotFoundError as e:
    raise SourceUnavailable(
        "embedded",
        "ffprobe not found",
        dependency="ffprobe",
        temporary=False
    ) from e
```

#### 3. Embedded Tag Corruption

```python
try:
    metadata = mutagen.File(file_path)
    if not metadata:
        raise ValueError("No metadata found")
except ValueError as e:
    raise ExtractionError(
        "embedded",
        "corrupt tag block",
        stage="embedded_tags",
        temporary=False
    ) from e
```

#### 4. Merge Conflict

```python
if abs(api_year - embedded_year) >= 2:
    raise MetadataConflict(
        "year",
        {"api": api_year, "embedded": embedded_year},
        policy="embedded-wins-if-delta<2"
    )
```

#### 5. Field Validation

```python
errors: Dict[str, List[str]] = {}
warnings: Dict[str, List[str]] = {}

if not asin:
    errors.setdefault("asin", []).append("missing")
if asin and not re.match(r"^B[0-9A-Z]{9}$", asin):
    errors.setdefault("asin", []).append("invalid-format")

if year and year > datetime.now().year:
    warnings.setdefault("year", []).append("suspicious-future-year")

if errors:
    raise ValidationError(
        errors=errors,
        warnings=warnings,
        details={"file": str(file_path), "source": "embedded"}
    )
```

#### 6. Configuration Error

```python
def get_api_key() -> str:
    api_key = os.getenv("AUDNEXUS_API_KEY")
    if not api_key:
        raise ConfigurationError(
            "audnexus.api_key",
            "missing required value",
            details={"env_var": "AUDNEXUS_API_KEY"}
        )
    return api_key
```

### Engine Integration Patterns

#### 1. Retry Logic with Backoff

```python
import asyncio
from typing import Optional

async def run_with_retry(operation, max_retries: int = 3) -> Any:
    """Execute operation with intelligent retry based on exception semantics."""

    for attempt in range(max_retries + 1):
        try:
            return await operation()

        except MetadataError as exc:
            logger.error("metadata_exception", **exc.to_dict())

            # Metrics for monitoring
            metrics.increment("metadata.error.count", tags={
                "code": exc.code,
                "temporary": str(exc.temporary),
                "severity": exc.severity,
                "attempt": str(attempt)
            })

            # Fast-fail for permanent errors
            if not exc.temporary or attempt >= max_retries:
                raise

            # Calculate backoff delay
            delay = calculate_backoff_delay(exc, attempt)
            logger.info(f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)

    raise  # Should not reach here

def calculate_backoff_delay(exc: MetadataError, attempt: int) -> float:
    """Calculate backoff delay based on exception type and attempt."""
    details = exc.details

    # Honor rate limit reset time
    if exc.code == "SRC_UNAVAILABLE" and "rate_limit_reset" in details:
        reset_time = details["rate_limit_reset"]
        current_time = time.time()
        if reset_time > current_time:
            return min(reset_time - current_time, 300)  # Cap at 5 minutes

    # Exponential backoff for HTTP errors
    if exc.code == "SRC_UNAVAILABLE":
        base_delay = 2 ** attempt
        jitter = random.uniform(0.1, 0.9)
        return min(base_delay + jitter, 60)  # Cap at 1 minute

    # Linear backoff for I/O errors
    if exc.code == "EXTRACTION_FAILED":
        return min(0.1 + (attempt * 0.1), 0.5)  # Cap at 500ms

    return 1.0  # Default delay
```

#### 2. Structured Logging Integration

```python
import structlog

logger = structlog.get_logger()

try:
    result = processor.extract_metadata(source)
except MetadataError as exc:
    # Structured logging with full context
    log_data = exc.to_dict()
    log_data.update({
        "operation": "extract_metadata",
        "source_path": str(source),
        "processor": processor.__class__.__name__
    })

    if exc.temporary:
        logger.warning("metadata.temporary_failure", **log_data)
    else:
        logger.error("metadata.permanent_failure", **log_data)

    raise
```

#### 3. OpenTelemetry Integration

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

try:
    with tracer.start_as_current_span("extract_metadata") as span:
        span.set_attribute("source.type", source_type)
        span.set_attribute("file.path", str(file_path))

        result = extractor.extract(file_path)

        span.set_attribute("result.status", "success")
        return result

except MetadataError as exc:
    with tracer.start_as_current_span("handle_metadata_error") as span:
        # Add exception details as span events
        span.add_event("metadata.exception", attributes=exc.to_dict())

        span.set_attribute("error.code", exc.code)
        span.set_attribute("error.temporary", exc.temporary)
        span.set_attribute("error.severity", exc.severity)

        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
        raise
```

### CLI Integration Patterns

#### 1. Rich Panel Display

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def display_exception(exc: MetadataError) -> None:
    """Display exception with Rich formatting."""

    # Choose color based on severity
    color_map = {
        "error": "red",
        "warning": "yellow",
        "info": "blue"
    }
    color = color_map.get(exc.severity, "red")

    # Create main panel
    panel = Panel(
        str(exc.message),
        title=f"[bold {color}]{exc.code}[/]",
        subtitle=exc.hint or "",
        border_style=color
    )
    console.print(panel)

    # Show field-level validation errors if applicable
    if isinstance(exc, ValidationError):
        display_validation_table(exc)

def display_validation_table(exc: ValidationError) -> None:
    """Display field-level validation errors in a table."""

    table = Table(title="Validation Issues")
    table.add_column("Field", style="cyan")
    table.add_column("Issues", style="red")
    table.add_column("Type", style="dim")

    # Add errors
    for field, issues in exc.errors.items():
        table.add_row(field, ", ".join(issues), "Error")

    # Add warnings
    for field, issues in exc.warnings.items():
        table.add_row(field, ", ".join(issues), "Warning")

    console.print(table)
```

#### 2. JSON Output Mode

```python
import json
import sys

def handle_cli_exception(exc: MetadataError, json_output: bool = False) -> int:
    """Handle CLI exception with appropriate output format."""

    if json_output:
        # JSON output for scripting
        error_data = exc.to_dict()
        error_data["exit_code"] = get_exit_code(exc.code)
        json.dump(error_data, sys.stderr, indent=2)
    else:
        # Human-friendly output
        display_exception(exc)

    return get_exit_code(exc.code)

def get_exit_code(error_code: str) -> int:
    """Map error codes to CLI exit codes."""
    exit_map = {
        "VALIDATION_FAILED": 3,
        "CONFIG_ERROR": 4,
        "PROCESSOR_NOT_FOUND": 5,
        "MERGE_CONFLICT": 6,
        "SRC_UNAVAILABLE": 10,  # Use 10 for temporary, 1 for permanent
        "EXTRACTION_FAILED": 1,
    }
    return exit_map.get(error_code, 1)
```

### Mapper Integration (RED Tracker Example)

```python
class REDMapper:
    """RED tracker mapper with validation requirements."""

    def validate_for_upload(self, metadata: AudiobookMeta) -> None:
        """Validate metadata meets RED requirements."""

        errors: Dict[str, List[str]] = {}
        warnings: Dict[str, List[str]] = {}

        # Required fields for RED
        if not metadata.asin:
            errors.setdefault("asin", []).append("missing")
        elif not re.match(r"^B[0-9A-Z]{9}$", metadata.asin):
            errors.setdefault("asin", []).append("invalid-format")

        if not metadata.year:
            errors.setdefault("year", []).append("missing")
        elif metadata.year < 1900 or metadata.year > datetime.now().year:
            errors.setdefault("year", []).append("invalid-range")

        # Audio quality requirements
        if hasattr(metadata, 'technical_audio'):
            audio = metadata.technical_audio
            if audio.bitrate_kbps and audio.bitrate_kbps < 64:
                errors.setdefault("bitrate", []).append("too-low-for-red")

        # Warnings for missing optional fields
        if not metadata.narrator:
            warnings.setdefault("narrator", []).append("missing-recommended")

        if errors:
            raise ValidationError(
                errors=errors,
                warnings=warnings,
                details={
                    "tracker": "RED",
                    "requirements_doc": "https://redacted.ch/wiki/uploading-guide"
                }
            )
```

### Testing Patterns

#### 1. Exception Verification

```python
import pytest

def test_validation_error_structure():
    """Test ValidationError maintains proper structure."""

    errors = {"asin": ["missing"], "year": ["invalid"]}
    warnings = {"narrator": ["missing-recommended"]}

    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError(errors=errors, warnings=warnings)

    exc = exc_info.value
    assert exc.code == "VALIDATION_FAILED"
    assert exc.temporary is False
    assert exc.errors == errors
    assert exc.warnings == warnings

    # Test serialization
    data = exc.to_dict()
    assert data["details"]["error_count"] == 2
    assert data["details"]["warning_count"] == 1

def test_secret_redaction():
    """Test that secrets are properly redacted."""

    exc = SourceUnavailable(
        "audnexus",
        "Auth failed",
        details={
            "api_key": "secret123",
            "user_id": "12345",
            "nested": {"auth_token": "token456", "public": "value"}
        }
    )

    data = exc.to_dict()
    assert data["details"]["api_key"] == "[REDACTED]"
    assert data["details"]["user_id"] == "12345"  # Not redacted
    assert data["details"]["nested"]["auth_token"] == "[REDACTED]"
    assert data["details"]["nested"]["public"] == "value"
```

#### 2. Retry Logic Testing

```python
@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry behavior with different exception types."""

    call_count = 0

    async def failing_operation():
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            # Temporary failure
            raise SourceUnavailable(
                "audnexus",
                "503 Service Unavailable",
                http_status=503,
                temporary=True
            )
        return "success"

    result = await run_with_retry(failing_operation, max_retries=3)
    assert result == "success"
    assert call_count == 3  # Initial + 2 retries
```

### Security Considerations

#### 1. Secret Redaction Patterns

The system automatically redacts keys matching:

- `token`, `password`, `pass`, `secret`
- `api_key`, `api-key`, `authorization`
- `credential`, `auth_token`, `auth-token`

To extend redaction:

```python
# Add custom patterns to _SECRET_KEYS regex
_SECRET_KEYS = re.compile(
    r"(token|password|pass|secret|api[_-]?key|authorization|credential|your_custom_key)",
    re.IGNORECASE
)
```

#### 2. Safe Path Handling

```python
def safe_file_error(file_path: Path, reason: str) -> ExtractionError:
    """Create ExtractionError with sanitized path for logging."""

    # Sanitize path for public logs (remove user home directory)
    safe_path = str(file_path).replace(str(Path.home()), "~")

    return ExtractionError(
        safe_path,
        reason,
        details={"full_path_hash": hashlib.sha256(str(file_path).encode()).hexdigest()[:8]}
    )
```

## Conclusion

This production-grade exception system provides:

- **Operational visibility**: Clear error codes and retry semantics
- **Developer productivity**: Rich context and actionable hints
- **Security**: Automatic secret redaction and safe serialization
- **Maintainability**: Structured data instead of string soup
- **Scalability**: Ready for monitoring, metrics, and automation

The system is backward-compatible where possible, with clear migration paths for breaking changes like the ValidationError field structure.

This comprehensive implementation and pattern library provides everything needed to integrate the production-grade exception system into your metadata processing pipeline!
