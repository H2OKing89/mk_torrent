"""
pytest test suite for the production-grade metadata exception system.

This module provides comprehensive testing of the enhanced exception hierarchy
with structured data, retry semantics, and telemetry support.
"""

import pytest
import json

from mk_torrent.core.metadata.exceptions import (
    MetadataError,
    SourceUnavailable,
    MetadataConflict,
    ValidationError,
    ProcessorNotFound,
    ConfigurationError,
    ExtractionError,
)


class TestMetadataError:
    """Test the base MetadataError class functionality."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        exc = MetadataError("Test error")

        assert str(exc) == "[METADATA_ERROR] Test error"
        assert exc.code == "METADATA_ERROR"
        assert exc.temporary is False
        assert exc.severity == "error"
        assert exc.hint is None
        assert exc.details == {}

    def test_custom_parameters(self):
        """Test initialization with custom parameters."""
        details = {"key": "value", "count": 42}
        exc = MetadataError(
            "Custom error",
            code="CUSTOM_ERROR",
            temporary=True,
            severity="warning",
            hint="Custom hint",
            details=details,
        )

        assert str(exc) == "[CUSTOM_ERROR] Custom error"
        assert exc.code == "CUSTOM_ERROR"
        assert exc.temporary is True
        assert exc.severity == "warning"
        assert exc.hint == "Custom hint"
        assert exc.details == details

    def test_to_dict_serialization(self):
        """Test safe serialization to dictionary."""
        exc = MetadataError(
            "Test error",
            code="TEST_ERROR",
            temporary=True,
            details={"normal": "value", "visible_field": "visible"},
        )

        data = exc.to_dict()

        assert data["code"] == "TEST_ERROR"
        assert data["message"] == "Test error"
        assert data["temporary"] is True
        assert data["severity"] == "error"
        assert data["hint"] is None
        assert data["details"]["normal"] == "value"
        assert data["details"]["visible_field"] == "visible"  # Not a secret pattern

    def test_secret_redaction(self):
        """Test automatic secret redaction in serialization."""
        sensitive_data = {
            "api_key": "secret123",
            "password": "mypass",
            "auth_token": "token456",
            "normal_field": "visible",
            "nested": {"secret": "nested_secret", "public": "nested_public"},
        }

        exc = MetadataError("Test", details=sensitive_data)
        data = exc.to_dict()

        # Sensitive fields should be redacted
        assert data["details"]["api_key"] == "[REDACTED]"
        assert data["details"]["password"] == "[REDACTED]"
        assert data["details"]["auth_token"] == "[REDACTED]"
        assert data["details"]["nested"]["secret"] == "[REDACTED]"

        # Non-sensitive fields should remain
        assert data["details"]["normal_field"] == "visible"
        assert data["details"]["nested"]["public"] == "nested_public"

    def test_cause_chaining(self):
        """Test exception cause chaining preservation."""
        original_error = ValueError("Original problem")

        try:
            raise original_error
        except ValueError as e:
            wrapped = MetadataError("Wrapped error")
            wrapped.__cause__ = e

        data = wrapped.to_dict()
        assert "cause" in data
        assert "Original problem" in data["cause"]

    def test_json_safe_conversion(self):
        """Test that complex objects are safely converted."""

        class CustomObject:
            def __repr__(self):
                return "CustomObject()"

        exc = MetadataError("Test", details={"object": CustomObject()})
        data = exc.to_dict()

        # Should be converted to string representation
        assert data["details"]["object"] == "CustomObject()"


class TestSourceUnavailable:
    """Test SourceUnavailable exception with HTTP awareness."""

    def test_basic_initialization(self):
        """Test basic source unavailable error."""
        exc = SourceUnavailable("test_source", "Connection failed")

        assert exc.code == "SRC_UNAVAILABLE"
        assert exc.source == "test_source"
        assert exc.reason == "Connection failed"
        assert "Source 'test_source' is unavailable: Connection failed" in str(exc)

    def test_rate_limit_handling(self):
        """Test rate limit specific handling."""
        reset_time = 1699999999
        exc = SourceUnavailable(
            "audnexus",
            "Too many requests",
            http_status=429,
            rate_limit_reset=reset_time,
        )

        assert exc.temporary is True  # Auto-detected from status
        assert exc.http_status == 429
        assert exc.rate_limit_reset == reset_time
        assert exc.hint == "Rate limited—back off until reset."

        data = exc.to_dict()
        assert data["details"]["http_status"] == 429
        assert data["details"]["rate_limit_reset"] == reset_time

    def test_missing_dependency(self):
        """Test missing dependency handling."""
        exc = SourceUnavailable(
            "embedded", "ffprobe not found", dependency="ffprobe", temporary=False
        )

        assert exc.temporary is False
        assert exc.dependency == "ffprobe"
        assert "Install or expose dependency: ffprobe" in exc.hint

    def test_network_error_auto_detection(self):
        """Test automatic detection of temporary network errors."""
        network_reasons = [
            "network timeout",
            "connection refused",
            "connection error",  # This should match "connection" pattern
        ]

        for reason in network_reasons:
            exc = SourceUnavailable("test", reason)
            assert exc.temporary is True, f"'{reason}' should be temporary"

    def test_server_error_status_codes(self):
        """Test handling of various HTTP status codes."""
        temporary_codes = [429, 502, 503, 504]
        for code in temporary_codes:
            exc = SourceUnavailable("api", "Server error", http_status=code)
            assert exc.temporary is True, f"HTTP {code} should be temporary"

    def test_authentication_error(self):
        """Test authentication error handling."""
        exc = SourceUnavailable("api", "Unauthorized access")
        assert exc.temporary is False  # Auth errors are typically permanent
        assert "Check API key or authentication configuration" in exc.hint


class TestValidationError:
    """Test ValidationError with field-level structure."""

    def test_basic_validation_error(self):
        """Test basic validation error creation."""
        errors = {"field1": ["required"], "field2": ["invalid"]}
        exc = ValidationError(errors=errors)

        assert exc.code == "VALIDATION_FAILED"
        assert exc.temporary is False
        assert exc.errors == errors
        assert exc.warnings == {}

        # Should contain field details in message
        assert "field1: required" in str(exc)
        assert "field2: invalid" in str(exc)

    def test_errors_and_warnings(self):
        """Test validation with both errors and warnings."""
        errors = {"asin": ["missing", "invalid-format"]}
        warnings = {
            "year": ["suspicious-future-year"],
            "narrator": ["missing-recommended"],
        }

        exc = ValidationError(errors=errors, warnings=warnings)

        assert exc.errors == errors
        assert exc.warnings == warnings

        data = exc.to_dict()
        assert data["details"]["error_count"] == 2  # 2 asin errors
        assert data["details"]["warning_count"] == 2  # 2 warnings
        assert data["details"]["errors"] == errors
        assert data["details"]["warnings"] == warnings

    def test_asin_specific_hint(self):
        """Test ASIN-specific hint generation."""
        errors = {"asin": ["missing"]}
        exc = ValidationError(errors=errors)

        assert "Add valid ASIN or disable tracker mappings" in exc.hint

    def test_single_error_hint(self):
        """Test hint for single validation error."""
        errors = {"title": ["required"]}
        exc = ValidationError(errors=errors)

        assert "Fix the validation error to continue" in exc.hint

    def test_multiple_errors_hint(self):
        """Test hint for multiple validation errors."""
        errors = {"title": ["required"], "year": ["invalid"], "duration": ["missing"]}
        exc = ValidationError(errors=errors)

        assert "Fix 3 validation errors to continue" in exc.hint

    def test_empty_errors_handling(self):
        """Test handling of empty errors (should still work)."""
        exc = ValidationError(errors={})

        assert exc.errors == {}
        assert "Validation failed." in str(exc)  # Generic message


class TestMetadataConflict:
    """Test MetadataConflict with policy support."""

    def test_basic_conflict(self):
        """Test basic metadata conflict."""
        values = {"source1": "value1", "source2": "value2"}
        exc = MetadataConflict("test_field", values)

        assert exc.code == "MERGE_CONFLICT"
        assert exc.temporary is False
        assert exc.field == "test_field"
        assert exc.conflicting_values == values
        assert exc.severity == "error"  # No resolution = error

    def test_conflict_with_policy(self):
        """Test conflict with policy information."""
        values = {"embedded": 2024, "api": 2023}
        exc = MetadataConflict("year", values, policy="embedded-preferred")

        assert exc.policy == "embedded-preferred"
        assert "Conflict detected using policy 'embedded-preferred'" in exc.hint

    def test_conflict_with_resolution(self):
        """Test conflict with proposed resolution."""
        values = {"embedded": 2024, "api": 2023}
        exc = MetadataConflict(
            "year", values, policy="embedded-wins", proposed_resolution=2024
        )

        assert exc.severity == "warning"  # With resolution = warning
        assert exc.proposed_resolution == 2024
        assert "resolved to: 2024" in str(exc)
        assert "Conflict resolved by merge policy" in exc.hint


class TestProcessorNotFound:
    """Test ProcessorNotFound exception."""

    def test_no_available_processors(self):
        """Test when no processors are available."""
        exc = ProcessorNotFound("video", [])

        assert exc.code == "PROCESSOR_NOT_FOUND"
        assert exc.content_type == "video"
        assert exc.available_processors == []
        assert "Available: none" in str(exc)

    def test_with_available_processors(self):
        """Test with some available processors."""
        available = ["audiobook", "music", "document"]
        exc = ProcessorNotFound("video", available)

        assert exc.available_processors == available
        assert "audiobook, music, document" in str(exc)
        assert "Use one of: audiobook, music, document" in exc.hint

    def test_many_available_processors(self):
        """Test hint truncation with many processors."""
        available = ["proc1", "proc2", "proc3", "proc4", "proc5"]
        exc = ProcessorNotFound("unknown", available)

        # Should truncate in hint but not in details
        assert "proc1, proc2, proc3..." in exc.hint
        assert exc.available_processors == available


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_basic_config_error(self):
        """Test basic configuration error."""
        exc = ConfigurationError("test.setting", "invalid value")

        assert exc.code == "CONFIG_ERROR"
        assert exc.config_key == "test.setting"
        assert exc.issue == "invalid value"
        assert exc.temporary is False

    def test_api_key_config_error(self):
        """Test API key specific error handling."""
        exc = ConfigurationError("audnexus.api_key", "missing required value")

        assert "AUDNEXUS.API_KEY environment variable" in exc.hint

    def test_missing_config_error(self):
        """Test missing configuration handling."""
        exc = ConfigurationError("timeout", "missing required value")

        assert "Add 'timeout' to your configuration" in exc.hint

    def test_invalid_config_error(self):
        """Test invalid configuration handling."""
        exc = ConfigurationError("port", "invalid format")

        assert "Check format and allowed values for 'port'" in exc.hint


class TestExtractionError:
    """Test ExtractionError with enhanced scenarios."""

    def test_basic_extraction_error(self):
        """Test basic extraction error."""
        exc = ExtractionError("test.m4b", "failed to read")

        assert exc.code == "EXTRACTION_FAILED"
        assert exc.source == "test.m4b"
        assert exc.reason == "failed to read"

    def test_extraction_with_stage(self):
        """Test extraction error with processing stage."""
        exc = ExtractionError("test.m4b", "corrupt metadata", stage="embedded_tags")

        assert exc.stage == "embedded_tags"
        assert exc.temporary is False  # Corrupt data is permanent

        data = exc.to_dict()
        assert data["details"]["stage"] == "embedded_tags"

    def test_permission_error_detection(self):
        """Test automatic detection of permission errors."""
        exc = ExtractionError("test.m4b", "permission denied")

        assert exc.temporary is True  # Permission errors can be temporary
        assert "Check file permissions" in exc.hint

    def test_io_error_detection(self):
        """Test automatic detection of I/O errors."""
        io_reasons = [
            "io error occurred",
            "disk read error",
            "resource temporarily unavailable",
        ]

        for reason in io_reasons:
            exc = ExtractionError("test.file", reason)
            assert exc.temporary is True, f"'{reason}' should be temporary"

    def test_corruption_error_detection(self):
        """Test automatic detection of corruption errors."""
        corruption_reasons = [
            "corrupt metadata",
            "invalid format detected",
            "file corruption found",
        ]

        for reason in corruption_reasons:
            exc = ExtractionError("test.file", reason)
            assert exc.temporary is False, f"'{reason}' should be permanent"
            assert "Check file integrity" in exc.hint

    def test_explicit_temporary_override(self):
        """Test explicit temporary parameter override."""
        # Override auto-detection
        exc = ExtractionError(
            "test.m4b",
            "corrupt metadata",  # Would normally be False
            temporary=True,  # Explicit override
        )

        assert exc.temporary is True  # Should use explicit value


class TestExceptionIntegration:
    """Integration tests for exception system features."""

    def test_all_exceptions_have_stable_codes(self):
        """Test that all exceptions have stable, unique codes."""
        exceptions = [
            MetadataError("test"),
            SourceUnavailable("src", "reason"),
            MetadataConflict("field", {"a": 1, "b": 2}),
            ValidationError(errors={"field": ["error"]}),
            ProcessorNotFound("type", []),
            ConfigurationError("key", "issue"),
            ExtractionError("source", "reason"),
        ]

        codes = [exc.code for exc in exceptions]
        expected_codes = [
            "METADATA_ERROR",
            "SRC_UNAVAILABLE",
            "MERGE_CONFLICT",
            "VALIDATION_FAILED",
            "PROCESSOR_NOT_FOUND",
            "CONFIG_ERROR",
            "EXTRACTION_FAILED",
        ]

        assert codes == expected_codes

    def test_all_exceptions_serializable(self):
        """Test that all exceptions can be safely serialized."""
        exceptions = [
            MetadataError("test", details={"key": "value"}),
            SourceUnavailable("src", "reason", http_status=503),
            ValidationError(errors={"field": ["error"]}, warnings={"warn": ["msg"]}),
            ExtractionError("source", "reason", stage="test"),
        ]

        for exc in exceptions:
            data = exc.to_dict()
            # Should be JSON serializable
            json_str = json.dumps(data)
            reconstructed = json.loads(json_str)
            assert reconstructed["code"] == exc.code
            assert reconstructed["message"] == exc.message

    def test_retry_semantics_consistency(self):
        """Test that retry semantics are consistent and logical."""
        # These should typically be temporary
        temporary_cases = [
            SourceUnavailable("api", "network timeout"),
            SourceUnavailable("api", "rate limit", http_status=429),
            ExtractionError("file", "io error"),
        ]

        for exc in temporary_cases:
            assert exc.temporary is True, f"{exc} should be temporary"

        # These should typically be permanent
        permanent_cases = [
            ValidationError(errors={"field": ["required"]}),
            ConfigurationError("key", "missing"),
            ProcessorNotFound("type", []),
            MetadataConflict("field", {"a": 1, "b": 2}),
            ExtractionError("file", "corrupt data"),
        ]

        for exc in permanent_cases:
            assert exc.temporary is False, f"{exc} should be permanent"

    @pytest.mark.parametrize(
        "exc_class,kwargs",
        [
            (MetadataError, {"message": "test"}),
            (SourceUnavailable, {"source": "test", "reason": "test"}),
            (ValidationError, {"errors": {"field": ["error"]}}),
            (MetadataConflict, {"field": "test", "conflicting_values": {"a": 1}}),
            (ProcessorNotFound, {"content_type": "test", "available_processors": []}),
            (ConfigurationError, {"config_key": "test", "issue": "test"}),
            (ExtractionError, {"source": "test", "reason": "test"}),
        ],
    )
    def test_exception_inheritance(self, exc_class, kwargs):
        """Test that all exceptions properly inherit from MetadataError."""
        exc = exc_class(**kwargs)

        assert isinstance(exc, MetadataError)
        assert isinstance(exc, Exception)
        assert hasattr(exc, "code")
        assert hasattr(exc, "temporary")
        assert hasattr(exc, "to_dict")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_conflicting_values(self):
        """Test metadata conflict with empty values."""
        exc = MetadataConflict("field", {})
        data = exc.to_dict()
        assert data["details"]["conflicting_values"] == {}

    def test_none_values_in_details(self):
        """Test handling of None values in details."""
        exc = MetadataError("test", details={"key": None})
        data = exc.to_dict()
        assert data["details"]["key"] is None

    def test_nested_secret_redaction(self):
        """Test deep nested secret redaction."""
        nested_data = {
            "level1": {
                "level2": {"api_key": "secret", "level3": {"password": "hidden"}},
                "public": "visible",
            }
        }

        exc = MetadataError("test", details=nested_data)
        data = exc.to_dict()

        assert data["details"]["level1"]["level2"]["api_key"] == "[REDACTED]"
        assert data["details"]["level1"]["level2"]["level3"]["password"] == "[REDACTED]"
        assert data["details"]["level1"]["public"] == "visible"

    def test_list_with_mixed_types(self):
        """Test list handling with mixed types including dicts."""
        mixed_list = [
            "string",
            42,
            {"api_key": "secret", "public": "visible"},
            {"normal": "value"},
        ]

        exc = MetadataError("test", details={"mixed": mixed_list})
        data = exc.to_dict()

        result_list = data["details"]["mixed"]
        assert result_list[0] == "string"
        assert result_list[1] == 42
        assert result_list[2]["api_key"] == "[REDACTED]"
        assert result_list[2]["public"] == "visible"
        assert result_list[3]["normal"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
