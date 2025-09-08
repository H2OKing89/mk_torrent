#!/usr/bin/env python3
"""
Test script for the new production-grade exception system.

This script verifies that the enhanced exception hierarchy works correctly
with structured data, retry semantics, and telemetry support.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mk_torrent.core.metadata.exceptions import (
    MetadataError,
    SourceUnavailable,
    MetadataConflict,
    ValidationError,
    ProcessorNotFound,
    ConfigurationError,
    ExtractionError,
)


def test_base_exception():
    """Test MetadataError base class functionality."""
    print("🧪 Testing MetadataError base class...")

    exc = MetadataError(
        "Test error",
        code="TEST_ERROR",
        temporary=True,
        severity="warning",
        hint="This is a test hint",
        details={"test_key": "test_value", "api_key": "secret123"},
    )

    # Test string representation
    assert str(exc) == "[TEST_ERROR] Test error"

    # Test serialization with secret redaction
    data = exc.to_dict()
    assert data["code"] == "TEST_ERROR"
    assert data["temporary"] is True
    assert data["severity"] == "warning"
    assert data["hint"] == "This is a test hint"
    assert data["details"]["test_key"] == "test_value"
    assert data["details"]["api_key"] == "[REDACTED]"  # Should be redacted

    print("✅ MetadataError tests passed")


def test_source_unavailable():
    """Test SourceUnavailable with enhanced features."""
    print("🧪 Testing SourceUnavailable...")

    # Rate limit error with enhanced features
    exc = SourceUnavailable(
        "audnexus", "Rate limited", http_status=429, rate_limit_reset=1699999999
    )

    assert exc.temporary is True
    assert exc.http_status == 429
    assert exc.hint == "Rate limited—back off until reset."

    data = exc.to_dict()
    assert data["code"] == "SRC_UNAVAILABLE"
    assert data["details"]["http_status"] == 429
    assert data["details"]["rate_limit_reset"] == 1699999999

    # Missing dependency with enhanced context
    exc2 = SourceUnavailable(
        "embedded", "ffprobe not found", dependency="ffprobe", temporary=False
    )

    assert exc2.temporary is False
    assert exc2.dependency == "ffprobe"
    assert "Install or expose dependency: ffprobe" in exc2.hint

    print("✅ SourceUnavailable tests passed")


def test_validation_error():
    """Test ValidationError with enhanced field-level structure."""
    print("🧪 Testing ValidationError...")

    errors = {"asin": ["missing", "invalid-format"], "bitrate_mode": ["missing"]}
    warnings = {"year": ["suspicious-future-year"]}

    exc = ValidationError(errors=errors, warnings=warnings)

    assert exc.temporary is False
    assert exc.code == "VALIDATION_FAILED"
    assert "asin: missing, invalid-format" in str(exc)
    assert exc.hint == "Add valid ASIN or disable tracker mappings that require it."

    data = exc.to_dict()
    assert data["details"]["error_count"] == 3  # 2 asin + 1 bitrate_mode
    assert data["details"]["warning_count"] == 1
    assert data["details"]["errors"] == errors
    assert data["details"]["warnings"] == warnings

    print("✅ ValidationError tests passed")


def test_metadata_conflict():
    """Test MetadataConflict with enhanced policy support."""
    print("🧪 Testing MetadataConflict...")

    conflicting_values = {"embedded": 2024, "api": 2023}

    # Without resolution (error)
    exc = MetadataConflict("year", conflicting_values)
    assert exc.severity == "error"
    assert exc.temporary is False

    # With policy and resolution (warning)
    exc2 = MetadataConflict(
        "year",
        conflicting_values,
        policy="embedded-wins-if-delta<2",
        proposed_resolution=2024,
    )
    assert exc2.severity == "warning"
    assert exc2.policy == "embedded-wins-if-delta<2"
    assert exc2.proposed_resolution == 2024
    assert "resolved to: 2024" in str(exc2)

    print("✅ MetadataConflict tests passed")


def test_processor_not_found():
    """Test ProcessorNotFound."""
    print("🧪 Testing ProcessorNotFound...")

    exc = ProcessorNotFound("video", ["audiobook", "music"])

    assert exc.temporary is False
    assert exc.code == "PROCESSOR_NOT_FOUND"
    assert exc.content_type == "video"
    assert exc.available_processors == ["audiobook", "music"]
    assert "audiobook, music" in exc.hint

    print("✅ ProcessorNotFound tests passed")


def test_configuration_error():
    """Test ConfigurationError."""
    print("🧪 Testing ConfigurationError...")

    exc = ConfigurationError("audnexus.api_key", "missing required value")

    assert exc.temporary is False
    assert exc.code == "CONFIG_ERROR"
    assert "AUDNEXUS.API_KEY" in exc.hint  # Should suggest env var

    print("✅ ConfigurationError tests passed")


def test_extraction_error():
    """Test ExtractionError with enhanced scenarios."""
    print("🧪 Testing ExtractionError...")

    # Corrupt file (permanent)
    exc = ExtractionError("test.m4b", "corrupt metadata", stage="embedded_tags")

    assert exc.temporary is False  # Corrupt files are permanent
    assert exc.stage == "embedded_tags"
    assert "Check file integrity/format" in exc.hint

    # I/O error (temporary)
    exc2 = ExtractionError("test.m4b", "permission denied", temporary=True)

    assert exc2.temporary is True
    assert exc2.hint is not None and "permission" in exc2.hint

    # Enhanced auto-detection
    exc3 = ExtractionError("test.m4b", "resource temporarily unavailable")

    assert exc3.temporary is True  # Should auto-detect as temporary

    print("✅ ExtractionError tests passed")


def test_cause_chaining():
    """Test exception cause chaining."""
    print("🧪 Testing cause chaining...")

    try:
        try:
            raise ValueError("Original error")
        except ValueError as e:
            raise SourceUnavailable("test", "Wrapped error") from e
    except SourceUnavailable as exc:
        data = exc.to_dict()
        assert "cause" in data
        assert "Original error" in data["cause"]
        assert exc.__cause__ is not None

    print("✅ Cause chaining tests passed")


def main():
    """Run all tests."""
    print("🚀 Testing production-grade exception system...\n")

    test_base_exception()
    test_source_unavailable()
    test_validation_error()
    test_metadata_conflict()
    test_processor_not_found()
    test_configuration_error()
    test_extraction_error()
    test_cause_chaining()

    print("\n🎉 All exception tests passed!")
    print("\nKey improvements implemented:")
    print("✅ Machine-readable error codes")
    print("✅ Retry semantics (temporary vs permanent)")
    print("✅ Structured field-level validation errors")
    print("✅ Secret redaction in serialization")
    print("✅ HTTP status code support")
    print("✅ CLI-friendly formatting")
    print("✅ Rich context for debugging")
    print("✅ Cause chaining support")


if __name__ == "__main__":
    main()
