"""
Exception hierarchy for the metadata processing system - Core Modular Metadata System.

This module defines a production-grade exception hierarchy that provides structured error
handling with machine-readable codes, retry semantics, and telemetry support.

The exception hierarchy follows these principles:
- Clear inheritance from base MetadataError with stable telemetry
- Machine-readable codes and retry semantics for orchestration
- Structured, field-level error details for UI/CLI consumption
- Security-conscious serialization with secret redaction
- Rich context for actionable error messages

Exception Categories:
- Source Issues: SourceUnavailable (API down, rate limits, missing dependencies)
- Processing Issues: MetadataConflict, ValidationError, ProcessorNotFound
- Configuration Issues: ConfigurationError
- Extraction Issues: ExtractionError (file I/O, parsing failures)

Retry Semantics:
- temporary=True: Network errors, rate limits, transient I/O
- temporary=False: Missing dependencies, validation failures, configuration errors

Architecture Documentation:
- Error Handling: docs/core/metadata/08-production-grade-exceptions.md
- Base Architecture: docs/core/metadata/03-foundation-architecture.md
"""

from __future__ import annotations
import re
import json
from typing import Any, Literal, cast

# Enhanced secret detection with common patterns
_SECRET_KEYS = re.compile(
    r"(token|password|pass|secret|api[_-]?key|authorization|credential|auth[_-]?token)",
    re.IGNORECASE,
)

Severity = Literal["error", "warning", "info"]


def _json_safe(value: Any) -> Any:
    """Best-effort JSON safety with shallow conversion."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    """Recursive redaction with nested dict support."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if _SECRET_KEYS.search(key):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            # Handle nested dictionaries with safe casting
            result[key] = _redact(value)  # type: ignore[arg-type]
        elif isinstance(value, list):
            # Handle lists with potential nested dictionaries
            redacted_list: list[Any] = []
            for item in cast(list[Any], value):
                if isinstance(item, dict):
                    redacted_list.append(_redact(item))  # type: ignore[arg-type]
                else:
                    redacted_list.append(_json_safe(item))
            result[key] = redacted_list
        else:
            result[key] = _json_safe(value)
    return result


class MetadataError(Exception):
    """Base exception for all metadata processing errors.

    Provides structured error information with machine-readable codes and
    retry semantics for production use:
    - Stable error codes for telemetry and metrics
    - Retry semantics (temporary vs permanent failures)
    - Structured details for programmatic handling
    - Security-conscious serialization with secret redaction
    - CLI/UI friendly formatting
    """

    __slots__ = ("message", "code", "temporary", "severity", "hint", "details")

    def __init__(
        self,
        message: str,
        *,
        code: str = "METADATA_ERROR",
        temporary: bool = False,
        severity: Severity = "error",
        hint: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.temporary = temporary
        self.severity = severity
        self.hint = hint
        self.details = details or {}

    def __str__(self) -> str:
        """CLI-friendly format with error code."""
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Safe, structured payload for logs/metrics/UI.

        Returns:
            Dictionary suitable for logging, telemetry, and API responses.
            Secrets in details are recursively redacted for security.
        """
        result = {
            "code": self.code,
            "message": self.message,
            "temporary": self.temporary,
            "severity": self.severity,
            "hint": self.hint,
            "details": _redact(self.details),
        }

        # Include cause chain if present
        cause = getattr(self, "__cause__", None)
        if cause:
            result["cause"] = repr(cause)

        return result


class SourceUnavailable(MetadataError):
    """Source down, missing dependency, auth issue, or rate-limit.

    This covers network failures, missing dependencies, rate limits, authentication
    failures, and other source accessibility issues with enhanced retry semantics.

    Retry Semantics:
    - Rate limits (429): temporary=True, include rate_limit_reset
    - Network errors (503, timeouts): temporary=True
    - Missing dependencies: temporary=False
    - Bad credentials: temporary=False (usually)
    """

    def __init__(
        self,
        source: str,
        reason: str,
        *,
        http_status: int | None = None,
        rate_limit_reset: int | None = None,  # epoch seconds
        dependency: str | None = None,
        temporary: bool | None = None,  # auto-detect if not provided
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        message = f"Source '{source}' is unavailable: {reason}"

        # Enhanced auto-detection of temporary status
        temp = temporary
        if temp is None:
            temp = http_status in {429, 502, 503, 504} or any(
                term in reason.lower() for term in ["network", "timeout", "connection"]
            )

        # Enhanced hint generation with specific guidance
        if hint is None:
            if http_status == 429:
                hint = "Rate limited—back off until reset."
            elif http_status in {502, 503, 504}:
                hint = "Upstream unavailable—retry with exponential backoff."
            elif dependency:
                hint = f"Install or expose dependency: {dependency}"
            elif any(
                term in reason.lower()
                for term in ["credential", "auth", "unauthorized"]
            ):
                hint = "Check API key or authentication configuration."
            else:
                hint = "Retry or check connectivity/credentials."

        # Build enhanced structured details
        enhanced_details: dict[str, Any] = {
            "source": source,
            "reason": reason,
        }
        if http_status is not None:
            enhanced_details["http_status"] = http_status
        if rate_limit_reset is not None:
            enhanced_details["rate_limit_reset"] = rate_limit_reset
        if dependency is not None:
            enhanced_details["dependency"] = dependency
        if details:
            enhanced_details.update(details)

        super().__init__(
            message,
            code="SRC_UNAVAILABLE",
            temporary=temp,
            severity="error",
            hint=hint,
            details=enhanced_details,
        )
        self.source = source
        self.reason = reason
        self.http_status = http_status
        self.rate_limit_reset = rate_limit_reset
        self.dependency = dependency


class MetadataConflict(MetadataError):
    """Irreconcilable field conflict across sources.

    Occurs when merge logic detects conflicting values that cannot be automatically
    resolved through precedence rules or policy.
    """

    def __init__(
        self,
        field: str,
        conflicting_values: dict[str, Any],
        *,
        policy: str | None = None,
        proposed_resolution: Any = None,
        details: dict[str, Any] | None = None,
    ):
        values_str = ", ".join(f"{k}={v!r}" for k, v in conflicting_values.items())
        message = f"Conflicting values for field '{field}': {values_str}"

        # Enhanced hint with policy context
        hint = "Adjust merge policy or source precedence."
        if policy:
            hint = f"Conflict detected using policy '{policy}'. " + hint
        if proposed_resolution is not None:
            message += f" (resolved to: {proposed_resolution!r})"
            hint = "Conflict resolved by merge policy, check logs for details."

        # Build structured details
        enhanced_details = {
            "field": field,
            "conflicting_values": conflicting_values,
        }
        if policy is not None:
            enhanced_details["policy"] = policy
        if proposed_resolution is not None:
            enhanced_details["proposed_resolution"] = proposed_resolution
        if details:
            enhanced_details.update(details)

        # Use warning severity if we have a resolution, error if not
        severity: Severity = "warning" if proposed_resolution is not None else "error"

        super().__init__(
            message,
            code="MERGE_CONFLICT",
            temporary=False,  # Requires policy or data changes
            severity=severity,
            hint=hint,
            details=enhanced_details,
        )
        self.field = field
        self.conflicting_values = conflicting_values
        self.policy = policy
        self.proposed_resolution = proposed_resolution


class ValidationError(MetadataError):
    """Field-level validation failures.

    Uses field-level structured error reporting for precise UI feedback
    and programmatic handling by mappers and validators.
    """

    def __init__(
        self,
        *,
        errors: dict[str, list[str]],
        warnings: dict[str, list[str]] | None = None,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        warnings = warnings or {}

        # Enhanced human-readable summary
        error_parts: list[str] = []
        for field, field_errors in errors.items():
            error_parts.append(f"{field}: {', '.join(field_errors)}")

        message = (
            f"Validation failed: {'; '.join(error_parts)}"
            if error_parts
            else "Validation failed."
        )

        # Enhanced hint generation with specific guidance
        if hint is None:
            total_errors = sum(len(field_errors) for field_errors in errors.values())
            if "asin" in errors:
                hint = "Add valid ASIN or disable tracker mappings that require it."
            elif total_errors == 1:
                hint = "Fix the validation error to continue processing."
            else:
                hint = f"Fix {total_errors} validation errors to continue processing."

        # Build enhanced structured details
        enhanced_details = {
            "errors": errors,
            "warnings": warnings,
            "error_count": sum(len(field_errors) for field_errors in errors.values()),
            "warning_count": sum(
                len(field_warnings) for field_warnings in warnings.values()
            ),
        }
        if details:
            enhanced_details.update(details)

        super().__init__(
            message,
            code="VALIDATION_FAILED",
            temporary=False,  # Requires data fixes
            hint=hint,
            details=enhanced_details,
        )
        self.errors = errors
        self.warnings = warnings


class ProcessorNotFound(MetadataError):
    """No processor available for a given content type."""

    def __init__(self, content_type: str, available_processors: list[str]):
        available = ", ".join(available_processors) if available_processors else "none"
        message = f"No processor found for content type '{content_type}'. Available: {available}"

        # Enhanced hint with specific guidance
        hint = "Enable or install the appropriate processor."
        if available_processors:
            suggestion = ", ".join(available_processors[:3])
            if len(available_processors) > 3:
                suggestion += "..."
            hint = (
                f"Use one of: {suggestion}. Or install processor for '{content_type}'."
            )

        super().__init__(
            message,
            code="PROCESSOR_NOT_FOUND",
            temporary=False,  # Requires configuration changes
            hint=hint,
            details={
                "content_type": content_type,
                "available_processors": available_processors,
            },
        )
        self.content_type = content_type
        self.available_processors = available_processors


class ConfigurationError(MetadataError):
    """Misconfiguration or missing required configuration."""

    def __init__(
        self,
        config_key: str,
        issue: str,
        *,
        details: dict[str, Any] | None = None,
    ):
        message = f"Configuration error for '{config_key}': {issue}"

        # Enhanced hint generation with specific guidance
        hint = f"Fix config value: {config_key}."
        if "api_key" in config_key.lower():
            hint = (
                f"Set {config_key.upper()} environment variable or update config file."
            )
        elif "missing" in issue.lower():
            hint = f"Add '{config_key}' to your configuration."
        elif "invalid" in issue.lower():
            hint = f"Check format and allowed values for '{config_key}'."

        # Build structured details
        enhanced_details = {
            "config_key": config_key,
            "issue": issue,
        }
        if details:
            enhanced_details.update(details)

        super().__init__(
            message,
            code="CONFIG_ERROR",
            temporary=False,  # Requires configuration changes
            hint=hint,
            details=enhanced_details,
        )
        self.config_key = config_key
        self.issue = issue


class ExtractionError(MetadataError):
    """Failed to extract metadata (I/O, parsing, corruption).

    Covers file I/O errors, parsing failures, corrupt data, and other
    extraction-related issues with enhanced retry semantics.

    Retry Semantics:
    - I/O errors: temporary=True (might be transient disk issues)
    - Corrupt data: temporary=False (file needs repair/replacement)
    - Missing files: temporary=False (unless expecting file to appear)
    """

    def __init__(
        self,
        source: str,
        reason: str,
        *,
        stage: str
        | None = None,  # e.g., "embedded_tags", "chapters", "ffprobe_streams"
        temporary: bool | None = None,
        details: dict[str, Any] | None = None,
        hint: str | None = None,
    ):
        message = f"Failed to extract metadata from '{source}': {reason}"

        # Enhanced heuristics for temporary detection
        if temporary is None:
            # More comprehensive patterns for temporary vs permanent failures
            reason_lower = reason.lower()
            temporary = any(
                term in reason_lower
                for term in [
                    "io error",
                    "permission",
                    "timeout",
                    "disk",
                    "network",
                    "temporary unavailability",
                    "resource temporarily unavailable",
                ]
            )

        # Enhanced hint generation with specific guidance
        if hint is None:
            reason_lower = reason.lower()
            if "permission" in reason_lower:
                hint = "Check file permissions and access rights."
            elif "corrupt" in reason_lower or "invalid format" in reason_lower:
                hint = "Check file integrity/format; re-encode or fix tags."
            elif "not found" in reason_lower:
                hint = "Verify file path and ensure file exists."
            elif temporary:
                hint = "Retry read or verify file access."
            else:
                hint = "Check file integrity/format; re-encode or fix tags."

        # Build structured details
        enhanced_details = {
            "source": source,
            "reason": reason,
        }
        if stage is not None:
            enhanced_details["stage"] = stage
        if details:
            enhanced_details.update(details)

        super().__init__(
            message,
            code="EXTRACTION_FAILED",
            temporary=temporary,
            hint=hint,
            details=enhanced_details,
        )
        self.source = source
        self.reason = reason
        self.stage = stage
