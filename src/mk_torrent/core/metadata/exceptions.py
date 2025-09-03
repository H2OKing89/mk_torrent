"""
Custom exceptions for the metadata system.

Provides typed error classes for better error handling and debugging.
"""

from typing import Any, Dict, List, Optional


class MetadataError(Exception):
    """Base exception for all metadata-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class SourceUnavailable(MetadataError):
    """Raised when a metadata source is unavailable.

    This could be due to missing dependencies, network issues,
    API rate limits, etc.
    """

    def __init__(
        self, source_name: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Source '{source_name}' is unavailable: {reason}"
        super().__init__(message, details)
        self.source_name = source_name
        self.reason = reason


class MetadataConflict(MetadataError):
    """Raised when there are irreconcilable conflicts between sources."""

    def __init__(
        self,
        field: str,
        conflicting_values: Dict[str, Any],
        details: Optional[Dict[str, Any]] = None,
    ):
        values_str = ", ".join(f"{k}={v}" for k, v in conflicting_values.items())
        message = f"Conflicting values for field '{field}': {values_str}"
        super().__init__(message, details)
        self.field = field
        self.conflicting_values = conflicting_values


class ValidationError(MetadataError):
    """Raised when metadata validation fails."""

    def __init__(
        self,
        errors: List[str],
        warnings: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_list = "; ".join(errors)
        message = f"Validation failed: {error_list}"
        super().__init__(message, details)
        self.errors = errors
        self.warnings = warnings or []


class ProcessorNotFound(MetadataError):
    """Raised when no suitable processor is found for a content type."""

    def __init__(self, content_type: str, available_processors: List[str]):
        available = ", ".join(available_processors) if available_processors else "none"
        message = f"No processor found for content type '{content_type}'. Available: {available}"
        super().__init__(message)
        self.content_type = content_type
        self.available_processors = available_processors


class ConfigurationError(MetadataError):
    """Raised when there's an issue with configuration."""

    def __init__(
        self, config_key: str, issue: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Configuration error for '{config_key}': {issue}"
        super().__init__(message, details)
        self.config_key = config_key
        self.issue = issue


class ExtractionError(MetadataError):
    """Raised when metadata extraction fails."""

    def __init__(
        self, source: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Failed to extract metadata from '{source}': {reason}"
        super().__init__(message, details)
        self.source = source
        self.reason = reason
