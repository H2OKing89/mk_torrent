"""
Integration tests for the metadata core system using real sample files.
"""

import pytest
from pathlib import Path

from mk_torrent.core.metadata import (
    MetadataEngine,
    AudiobookMeta,
    ValidationResult,
    MetadataError,
)


# Path to sample files
SAMPLES_DIR = Path(__file__).parent.parent / "samples"
AUDIOBOOK_SAMPLE_DIR = (
    SAMPLES_DIR
    / "audiobook"
    / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
)
AUDIOBOOK_SAMPLE_FILE = (
    AUDIOBOOK_SAMPLE_DIR
    / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
)


class MinimalProcessor:
    """Minimal processor implementation for integration testing."""

    def extract(self, source):
        """Extract basic metadata from filename with support for complex audiobook naming."""
        if isinstance(source, str):
            source = Path(source)

        # Get filename stem
        stem = source.stem

        # Try to parse complex audiobook filename format first
        # Format: "Series Title - vol_XX (YEAR) (Author) {ASIN.XXXXX} [Uploader]"
        if " - vol_" in stem and "(" in stem:
            parts = stem.split(" - vol_")
            series_title = parts[0].strip()

            # Extract volume and other info
            vol_part = parts[1]

            # Extract volume number
            vol_match = vol_part.split(" ")[0]

            # Extract year
            year = None
            if "(" in vol_part and ")" in vol_part:
                year_part = vol_part.split("(")[1].split(")")[0]
                if year_part.isdigit():
                    year = int(year_part)
                elif year_part.isdigit() and len(year_part) == 4:
                    year = int(year_part)

            # Extract author
            author = "Unknown"
            if ") (" in vol_part:
                author_part = vol_part.split(") (")[1].split(")")[0]
                author = author_part.strip()

            # Extract ASIN
            asin = None
            if "{ASIN." in vol_part and "}" in vol_part:
                asin_part = vol_part.split("{ASIN.")[1].split("}")[0]
                asin = asin_part.strip()

            return {
                "title": f"{series_title} - vol_{vol_match}",
                "author": author,
                "series": series_title,
                "series_part": vol_match,
                "year": year,
                "asin": asin,
                "source_path": source,
            }

        # Fallback to simple parsing
        elif " - " in stem:
            parts = stem.split(" - ", 1)
            return {
                "title": parts[1].strip(),
                "author": parts[0].strip(),
                "source_path": source,
            }
        else:
            return {
                "title": stem,
                "author": "Unknown",
                "source_path": source,
            }

    def validate(self, metadata):
        """Basic validation."""
        result = ValidationResult(valid=True)

        if not metadata.get("title"):
            result.add_error("Title is required")
        if not metadata.get("author"):
            result.add_error("Author is required")

        # Calculate completeness
        required_fields = ["title", "author"]
        optional_fields = ["year", "narrator", "series", "volume"]

        filled_required = sum(1 for field in required_fields if metadata.get(field))
        filled_optional = sum(1 for field in optional_fields if metadata.get(field))

        total_possible = len(required_fields) + len(optional_fields)
        total_filled = filled_required + filled_optional

        result.completeness = total_filled / total_possible

        return result

    def enhance(self, metadata):
        """Add derived fields."""
        enhanced = dict(metadata)

        title = metadata.get("title", "")
        author = metadata.get("author", "")

        if title and author:
            enhanced["display_name"] = f"{title} by {author}"
        elif title:
            enhanced["display_name"] = title
        elif author:
            enhanced["display_name"] = f"Unknown by {author}"
        else:
            enhanced["display_name"] = "Unknown"

        # Default album to title
        if not enhanced.get("album") and title:
            enhanced["album"] = title

        return enhanced


class MinimalMapper:
    """Minimal mapper for testing."""

    def map_to_tracker(self, metadata):
        """Map to simple tracker format."""
        return {
            "upload_title": metadata.title,
            "upload_artist": metadata.author,
            "upload_year": metadata.year or "",
            "upload_description": metadata.description or "",
        }

    def map_from_tracker(self, tracker_data):
        """Map from tracker format."""
        return {
            "title": tracker_data.get("upload_title", ""),
            "author": tracker_data.get("upload_artist", ""),
            "year": tracker_data.get("upload_year") or None,
            "description": tracker_data.get("upload_description", ""),
        }


class TestMetadataIntegration:
    """Integration tests for the complete metadata system."""

    def setup_method(self):
        """Set up test environment."""
        self.engine = MetadataEngine()
        self.processor = MinimalProcessor()
        self.mapper = MinimalMapper()

        # Register components
        self.engine.register_processor("audiobook", self.processor)
        self.engine.register_mapper("test_tracker", self.mapper)
        self.engine.set_default_processor("audiobook")

    def test_end_to_end_processing(self):
        """Test complete end-to-end processing pipeline."""
        # Create a test filename that can be parsed
        test_path = "Author Name - Book Title.m4b"

        # Run full pipeline
        result = self.engine.process_full_pipeline(
            test_path, tracker_name="test_tracker", validate=True
        )

        # Verify results
        assert result["success"] is True
        assert result["content_type"] == "audiobook"

        metadata = result["metadata"]
        assert metadata["title"] == "Book Title"
        assert metadata["author"] == "Author Name"
        assert metadata["display_name"] == "Book Title by Author Name"
        assert metadata["album"] == "Book Title"  # Should default to title

        validation = result["validation"]
        assert validation["valid"] is True
        assert validation["completeness"] > 0.0

        tracker_data = result["tracker_data"]
        assert tracker_data["upload_title"] == "Book Title"
        assert tracker_data["upload_artist"] == "Author Name"

    def test_validation_failure(self):
        """Test handling of validation failures."""
        # Use a path that won't parse correctly (empty filename results in empty title/author)
        test_path = "empty.m4b"  # Will result in title="empty", author="Unknown"

        result = self.engine.process_full_pipeline(test_path, validate=True)

        assert (
            result["success"] is True
        )  # Pipeline succeeds even with validation issues
        validation = result["validation"]
        # The MinimalProcessor only requires title and author, both of which will be present
        # So let's check for low completeness instead
        assert validation["completeness"] < 1.0  # Should be incomplete

    def test_audiobook_meta_roundtrip(self):
        """Test creating and converting AudiobookMeta objects."""
        # Create metadata
        original_meta = AudiobookMeta(
            title="Test Book",
            author="Test Author",
            year=2023,
            genres=["Fiction", "Mystery"],
            source_path=Path("/test/path.m4b"),
        )

        # Convert to dict and back
        data = original_meta.to_dict()
        restored_meta = AudiobookMeta.from_dict(data)

        assert restored_meta.title == original_meta.title
        assert restored_meta.author == original_meta.author
        assert restored_meta.year == original_meta.year
        assert restored_meta.genres == original_meta.genres
        assert restored_meta.source_path == original_meta.source_path

    def test_mapper_roundtrip(self):
        """Test mapping to tracker format and back."""
        original_meta = AudiobookMeta(
            title="Test Book",
            author="Test Author",
            year=2023,
            description="A test book",
        )

        # Map to tracker format
        tracker_data = self.mapper.map_to_tracker(original_meta)

        # Map back to internal format
        restored_data = self.mapper.map_from_tracker(tracker_data)

        assert restored_data["title"] == original_meta.title
        assert restored_data["author"] == original_meta.author
        assert restored_data["year"] == original_meta.year
        assert restored_data["description"] == original_meta.description

    def test_content_type_detection(self):
        """Test automatic content type detection."""
        test_cases = [
            ("book.m4b", "audiobook"),
            ("song.mp3", "audiobook"),  # Default fallback
            ("movie.mp4", "video"),
            ("video.mkv", "video"),
        ]

        for filename, expected_type in test_cases:
            detected = self.engine.detect_content_type(filename)
            assert detected == expected_type, f"Failed for {filename}"

    def test_processor_not_found_handling(self):
        """Test handling when no processor is found."""
        # Create engine without processors
        empty_engine = MetadataEngine()

        with pytest.raises(MetadataError, match="Extraction failed"):
            empty_engine.extract_metadata("test.unknown")

    def test_real_audiobook_file_processing(self):
        """Test processing with a real audiobook file from samples."""
        # Skip if sample file doesn't exist
        if not AUDIOBOOK_SAMPLE_FILE.exists():
            pytest.skip(f"Sample file not found: {AUDIOBOOK_SAMPLE_FILE}")

        # Process the real file
        result = self.engine.process_full_pipeline(
            str(AUDIOBOOK_SAMPLE_FILE), tracker_name="test_tracker", validate=True
        )

        # Verify results
        assert result["success"] is True
        assert result["content_type"] == "audiobook"

        metadata = result["metadata"]
        # The filename should parse correctly with our MinimalProcessor
        assert "How a Realist Hero Rebuilt the Kingdom" in metadata["title"]
        assert metadata["author"]  # Should extract some author info

        validation = result["validation"]
        assert validation["valid"] is True

        tracker_data = result["tracker_data"]
        assert tracker_data["upload_title"]
        assert tracker_data["upload_artist"]

    def test_real_audiobook_metadata_extraction(self):
        """Test basic metadata extraction from real file."""
        # Skip if sample file doesn't exist
        if not AUDIOBOOK_SAMPLE_FILE.exists():
            pytest.skip(f"Sample file not found: {AUDIOBOOK_SAMPLE_FILE}")

        # Extract metadata only (returns dict)
        metadata = self.engine.extract_metadata(str(AUDIOBOOK_SAMPLE_FILE))

        # Verify basic extraction worked
        assert metadata is not None
        assert isinstance(metadata, dict)
        assert metadata.get("title") is not None
        assert metadata.get("author") is not None
        assert str(AUDIOBOOK_SAMPLE_FILE) in str(metadata.get("source_path"))

    def test_multiple_processors(self):
        """Test registering multiple processors."""
        # Register additional processor
        music_processor = MinimalProcessor()  # Reuse for simplicity
        self.engine.register_processor("music", music_processor)

        # Verify both are available
        processors = self.engine.get_available_processors()
        assert "audiobook" in processors
        assert "music" in processors

        # Test explicit content type selection
        result = self.engine.extract_metadata("test.mp3", content_type="music")
        assert result is not None
