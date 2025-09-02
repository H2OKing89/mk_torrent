"""
Tests for the metadata engine core functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.base import (
    AudiobookMeta,
    ValidationResult,
    MetadataProcessor,
    MetadataMapper,
)
from mk_torrent.core.metadata.exceptions import (
    ProcessorNotFound,
    MetadataError,
)


class MockProcessor:
    """Mock processor for testing."""
    
    def extract(self, source):
        return {"title": "Test Book", "author": "Test Author"}
    
    def validate(self, metadata):
        return ValidationResult(valid=True, completeness=0.8)
    
    def enhance(self, metadata):
        metadata["display_name"] = f"{metadata.get('title', '')} by {metadata.get('author', '')}"
        return metadata


class MockMapper:
    """Mock mapper for testing."""
    
    def map_to_tracker(self, metadata):
        return {
            "tracker_title": metadata.title,
            "tracker_author": metadata.author,
        }
    
    def map_from_tracker(self, tracker_data):
        return {
            "title": tracker_data.get("tracker_title", ""),
            "author": tracker_data.get("tracker_author", ""),
        }


class TestMetadataEngine:
    """Test the MetadataEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = MetadataEngine()
        self.mock_processor = MockProcessor()
        self.mock_mapper = MockMapper()
        
    def test_register_processor(self):
        """Test processor registration."""
        self.engine.register_processor("test", self.mock_processor)
        assert "test" in self.engine._processors
        assert self.engine._processors["test"] == self.mock_processor
        
    def test_register_mapper(self):
        """Test mapper registration."""
        self.engine.register_mapper("test_tracker", self.mock_mapper)
        assert "test_tracker" in self.engine._mappers
        assert self.engine._mappers["test_tracker"] == self.mock_mapper
        
    def test_set_default_processor(self):
        """Test setting default processor."""
        self.engine.register_processor("audiobook", self.mock_processor)
        self.engine.set_default_processor("audiobook")
        assert self.engine._default_processor == "audiobook"
        
    def test_set_default_processor_not_found(self):
        """Test setting default processor that doesn't exist."""
        with pytest.raises(ProcessorNotFound):
            self.engine.set_default_processor("nonexistent")
            
    def test_detect_content_type_file(self):
        """Test content type detection from files."""
        # Test audiobook extensions
        assert self.engine.detect_content_type(Path("test.m4b")) == "audiobook"
        assert self.engine.detect_content_type(Path("test.m4a")) == "audiobook"
        
        # Test video extensions
        assert self.engine.detect_content_type(Path("test.mp4")) == "video"
        assert self.engine.detect_content_type(Path("test.mkv")) == "video"
        
    def test_detect_content_type_string_path(self):
        """Test content type detection from string paths."""
        result = self.engine.detect_content_type("test.m4b")
        assert result == "audiobook"
        
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.glob')
    def test_detect_content_type_directory(self, mock_glob, mock_is_dir):
        """Test content type detection from directories."""
        mock_is_dir.return_value = True
        mock_glob.return_value = [Path("book.m4b")]
        
        result = self.engine.detect_content_type(Path("/test/dir"))
        assert result == "audiobook"
        
    def test_extract_metadata(self):
        """Test metadata extraction."""
        self.engine.register_processor("audiobook", self.mock_processor)
        
        result = self.engine.extract_metadata("test.m4b")
        
        assert result["title"] == "Test Book"
        assert result["author"] == "Test Author"
        assert "display_name" in result  # Should be enhanced by default
        
    def test_extract_metadata_no_enhance(self):
        """Test metadata extraction without enhancement."""
        self.engine.register_processor("audiobook", self.mock_processor)
        
        result = self.engine.extract_metadata("test.m4b", enhance=False)
        
        assert result["title"] == "Test Book"
        assert result["author"] == "Test Author"
        assert "display_name" not in result  # Should not be enhanced
        
    def test_extract_metadata_processor_not_found(self):
        """Test extraction with unknown content type."""
        with pytest.raises(MetadataError, match="Extraction failed"):
            self.engine.extract_metadata("test.unknown")
            
    def test_validate_metadata_dict(self):
        """Test validation with dictionary metadata."""
        self.engine.register_processor("audiobook", self.mock_processor)
        
        metadata = {"title": "Test", "author": "Author"}
        result = self.engine.validate_metadata(metadata, "audiobook")
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.completeness == 0.8
        
    def test_validate_metadata_audiobook_meta(self):
        """Test validation with AudiobookMeta object."""
        self.engine.register_processor("audiobook", self.mock_processor)
        
        metadata = AudiobookMeta(title="Test", author="Author")
        result = self.engine.validate_metadata(metadata)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        
    def test_map_to_tracker(self):
        """Test mapping to tracker format."""
        self.engine.register_mapper("test_tracker", self.mock_mapper)
        
        metadata = AudiobookMeta(title="Test Book", author="Test Author")
        result = self.engine.map_to_tracker(metadata, "test_tracker")
        
        assert result["tracker_title"] == "Test Book"
        assert result["tracker_author"] == "Test Author"
        
    def test_map_to_tracker_not_found(self):
        """Test mapping with unknown tracker."""
        metadata = AudiobookMeta(title="Test")
        
        with pytest.raises(MetadataError, match="No mapper found"):
            self.engine.map_to_tracker(metadata, "unknown_tracker")
            
    def test_process_full_pipeline(self):
        """Test the complete processing pipeline."""
        self.engine.register_processor("audiobook", self.mock_processor)
        self.engine.register_mapper("test_tracker", self.mock_mapper)
        
        result = self.engine.process_full_pipeline(
            "test.m4b",
            tracker_name="test_tracker"
        )
        
        assert result["success"] is True
        assert result["content_type"] == "audiobook"
        assert result["metadata"]["title"] == "Test Book"
        assert result["validation"]["valid"] is True
        assert result["tracker_data"]["tracker_title"] == "Test Book"
        
    def test_get_available_processors(self):
        """Test getting available processors."""
        self.engine.register_processor("audiobook", self.mock_processor)
        self.engine.register_processor("music", self.mock_processor)
        
        processors = self.engine.get_available_processors()
        assert "audiobook" in processors
        assert "music" in processors
        
    def test_get_available_mappers(self):
        """Test getting available mappers."""
        self.engine.register_mapper("red", self.mock_mapper)
        self.engine.register_mapper("opp", self.mock_mapper)
        
        mappers = self.engine.get_available_mappers()
        assert "red" in mappers
        assert "opp" in mappers
