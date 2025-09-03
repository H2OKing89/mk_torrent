"""
Tests for the core metadata base classes and protocols.
"""

from pathlib import Path

from mk_torrent.core.metadata.base import (
    AudiobookMeta,
    ValidationResult,
)


class TestAudiobookMeta:
    """Test the AudiobookMeta dataclass."""

    def test_default_initialization(self):
        """Test default values are set correctly."""
        meta = AudiobookMeta()
        assert meta.title == ""
        assert meta.author == ""
        assert meta.language == "en"
        assert meta.genres == []
        assert meta.year is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        meta = AudiobookMeta(title="Test Book", author="Test Author", year=2023)
        data = meta.to_dict()

        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"
        assert data["year"] == 2023

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "title": "Test Book",
            "author": "Test Author",
            "year": 2023,
            "unknown_field": "should be ignored",
        }

        meta = AudiobookMeta.from_dict(data)
        assert meta.title == "Test Book"
        assert meta.author == "Test Author"
        assert meta.year == 2023
        # Unknown fields should be ignored
        assert not hasattr(meta, "unknown_field")

    def test_path_conversion(self):
        """Test Path object handling in from_dict."""
        data = {
            "title": "Test",
            "source_path": "/path/to/file",
            "files": ["/file1.mp3", "/file2.mp3"],
        }

        meta = AudiobookMeta.from_dict(data)
        assert isinstance(meta.source_path, Path)
        assert meta.source_path == Path("/path/to/file")
        assert all(isinstance(f, Path) for f in meta.files)


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_default_initialization(self):
        """Test default values."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.completeness == 0.0

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(valid=True)
        result.add_error("Test error")

        assert result.valid is False
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning")

        assert result.valid is True  # Warnings don't affect validity
        assert "Test warning" in result.warnings

    def test_merge(self):
        """Test merging validation results."""
        result1 = ValidationResult(valid=True, completeness=0.8)
        result1.add_warning("Warning 1")

        result2 = ValidationResult(valid=False, completeness=0.6)
        result2.add_error("Error 1")

        merged = result1.merge(result2)

        assert merged.valid is False  # False if any are False
        assert merged.completeness == 0.6  # Minimum
        assert "Warning 1" in merged.warnings
        assert "Error 1" in merged.errors
