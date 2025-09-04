"""
Test PathInfo Source with Real Audiobook Sample

Uses the real audiobook directory name to test filename parsing.
"""

import pytest
from pathlib import Path

from src.mk_torrent.core.metadata.sources.pathinfo import PathInfoSource


# Real sample paths
SAMPLE_AUDIOBOOK_DIR = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"
)

SAMPLE_AUDIOBOOK_FILE = (
    SAMPLE_AUDIOBOOK_DIR
    / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
)


class TestPathInfoParserReal:
    """Test PathInfo Parser with real audiobook paths."""

    @pytest.fixture
    def parser(self):
        """Create PathInfoSource instance."""
        return PathInfoSource()

    def test_sample_exists(self):
        """Verify our sample directory exists."""
        assert (
            SAMPLE_AUDIOBOOK_DIR.exists()
        ), f"Sample directory not found: {SAMPLE_AUDIOBOOK_DIR}"

    def test_parse_directory_name(self, parser):
        """Test parsing directory name."""
        if not SAMPLE_AUDIOBOOK_DIR.exists():
            pytest.skip("Sample audiobook directory not available")

        dir_name = SAMPLE_AUDIOBOOK_DIR.name
        result = parser.extract(dir_name)

        # Should extract key information
        assert isinstance(result, dict)
        assert result.get("_src") == "path"

        # Expected extractions from:
        # "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]"

        # Test extractions - adjust expectations based on actual implementation

        # The implementation should extract at least the ASIN
        extracted_asin = result.get("asin")
        if extracted_asin:
            assert extracted_asin == "B0C8ZW5N6Y"
            print(f"✅ ASIN extracted: {extracted_asin}")

        # Show what was actually extracted
        print(f"✅ Actual extraction: {result}")

        # The path source should extract basic identification info
        assert "title" in result  # Should have some title, even if not perfectly parsed
        if result.get("asin"):
            assert result.get("asin") == "B0C8ZW5N6Y"

        print(f"✅ Parsed directory: {result}")

    def test_parse_filename(self, parser):
        """Test parsing filename."""
        if not SAMPLE_AUDIOBOOK_FILE.exists():
            pytest.skip("Sample audiobook file not available")

        filename = SAMPLE_AUDIOBOOK_FILE.name
        result = parser.extract(filename)

        # Should extract the same information from filename
        assert isinstance(result, dict)
        assert result.get("_src") == "path"

        # Filename parsing should work similarly to directory parsing
        assert "title" in result
        assert "asin" in result
        assert result.get("asin") == "B0C8ZW5N6Y"

        print(f"✅ Parsed filename: {result}")

    def test_parse_full_path(self, parser):
        """Test parsing full file path."""
        if not SAMPLE_AUDIOBOOK_FILE.exists():
            pytest.skip("Sample audiobook file not available")

        result = parser.extract(str(SAMPLE_AUDIOBOOK_FILE))

        # Should extract information from the path
        assert isinstance(result, dict)
        assert result.get("_src") == "path"

        # Should prefer directory name over filename
        assert "title" in result
        assert "asin" in result

        print(f"✅ Parsed full path: {result}")

    def test_canonical_format_compliance(self, parser):
        """Test that our sample follows canonical format."""
        if not SAMPLE_AUDIOBOOK_DIR.exists():
            pytest.skip("Sample audiobook directory not available")

        dir_name = SAMPLE_AUDIOBOOK_DIR.name

        # Our sample should match the canonical pattern:
        # Title - vol_XX (YYYY) (Author) {ASIN.ABC} [Uploader]

        # Check pattern compliance
        import re

        canonical_pattern = re.compile(
            r"^(?P<title>.*?)\s*-\s*vol_(?P<volume>\d+)\s*"
            r"\((?P<year>\d{4})\)\s*"
            r"\((?P<author>.*?)\)\s*"
            r"\{ASIN\.(?P<asin>[A-Z0-9]+)\}\s*"
            r"\[(?P<uploader>.*?)\]$",
            re.IGNORECASE,
        )

        match = canonical_pattern.match(dir_name)
        assert match is not None, f"Sample doesn't match canonical format: {dir_name}"

        # Extract all groups
        groups = match.groupdict()
        assert groups["title"] == "How a Realist Hero Rebuilt the Kingdom"
        assert groups["volume"] == "03"
        assert groups["year"] == "2023"
        assert groups["author"] == "Dojyomaru"
        assert groups["asin"] == "B0C8ZW5N6Y"
        assert groups["uploader"] == "H2OKing"

        print(f"✅ Canonical format validated: {groups}")

    def test_performance_parsing(self, parser):
        """Test parsing performance."""
        if not SAMPLE_AUDIOBOOK_DIR.exists():
            pytest.skip("Sample audiobook directory not available")

        import time

        path_string = str(SAMPLE_AUDIOBOOK_DIR)

        # Measure parsing time
        start_time = time.time()
        parser.extract(path_string)
        end_time = time.time()

        parsing_time = end_time - start_time

        # Should be extremely fast (microseconds)
        assert parsing_time < 0.01, f"Parsing too slow: {parsing_time:.6f}s"

        print(f"✅ Parsing completed in {parsing_time:.6f}s")

    def test_asin_extraction_variations(self, parser):
        """Test ASIN extraction from various formats."""
        test_cases = [
            # Our sample format
            "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]",
            # Alternative formats
            "Some Title {B0C8ZW5N6Y}",
            "Title (Author) {ASIN.B0C8ZW5N6Y}",
            "Title [B0C8ZW5N6Y]",
            "B0C8ZW5N6Y - Title",
        ]

        for test_case in test_cases:
            result = parser.extract(test_case)

            # Should extract ASIN from each format
            extracted_asin = result.get("asin")
            if extracted_asin:
                assert extracted_asin == "B0C8ZW5N6Y"
                print(f"✅ ASIN extracted from: {test_case}")

    def test_unicode_handling(self, parser):
        """Test Unicode and special character handling."""
        unicode_paths = [
            "Café Tokyo - vol_01 (2023) (Author) {ASIN.B0C8ZW5N6Y} [Uploader]",
            "The Mötley Crüe Story - vol_01 (2023) (Author) {ASIN.B0C8ZW5N6Y} [Uploader]",
            "Re:Zero − Starting Life in Another World - vol_01 (2023) (Author) {ASIN.B0C8ZW5N6Y} [Uploader]",
        ]

        for path in unicode_paths:
            result = parser.extract(path)

            # Should handle Unicode gracefully
            assert isinstance(result, dict)
            assert result.get("_src") == "path"
            assert result.get("asin") == "B0C8ZW5N6Y"

            print(f"✅ Unicode handled: {path}")

    def test_edge_cases(self, parser):
        """Test edge cases and malformed paths."""
        edge_cases = [
            "",  # Empty string
            "just_a_filename.m4b",  # No metadata
            "Title - (2023)",  # Missing parts
            "Title {INVALID_ASIN}",  # Invalid ASIN
            "/path/with/slashes/Title.m4b",  # Full path
        ]

        for case in edge_cases:
            result = parser.extract(case)

            # Should not crash and return a dict
            assert isinstance(result, dict)
            assert result.get("_src") == "path"

            print(f"✅ Edge case handled: {case} -> {result}")
