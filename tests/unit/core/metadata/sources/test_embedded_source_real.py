"""
Test Embedded Source with Real Audiobook Sample

Uses the real m4b file to test technical metadata extraction.
"""

import pytest
from pathlib import Path

from src.mk_torrent.core.metadata.sources.embedded import EmbeddedSource


# Real sample file path
SAMPLE_AUDIOBOOK = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
)

SAMPLE_ARTWORK = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.jpg"
)


class TestEmbeddedSourceReal:
    """Test Embedded Source with real audiobook file."""

    @pytest.fixture
    def embedded_source(self):
        """Create EmbeddedSource instance."""
        return EmbeddedSource()

    def test_sample_file_exists(self):
        """Verify our sample files exist."""
        assert (
            SAMPLE_AUDIOBOOK.exists()
        ), f"Sample audiobook not found: {SAMPLE_AUDIOBOOK}"
        assert SAMPLE_ARTWORK.exists(), f"Sample artwork not found: {SAMPLE_ARTWORK}"

    def test_extract_technical_metadata(self, embedded_source):
        """Test extraction of technical metadata from real m4b file."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        result = embedded_source.extract(SAMPLE_AUDIOBOOK)

        # Should return technical metadata dict
        assert isinstance(result, dict)
        assert result.get("_src") == "embedded"

        # Technical properties should be extracted
        assert "duration_sec" in result
        assert "file_size_bytes" in result
        assert "source" in result  # ffprobe, mutagen, or basic

        # Duration should be reasonable for an audiobook
        duration = result.get("duration_sec")
        if duration:
            assert isinstance(duration, (int, float))
            assert 3600 <= duration <= 43200  # 1-12 hours is reasonable

        # File size should match actual file
        expected_size = SAMPLE_AUDIOBOOK.stat().st_size
        actual_size = result.get("file_size_bytes")
        if actual_size:
            assert actual_size == expected_size

        # Should have technical audio properties
        if "bitrate" in result:
            assert isinstance(result["bitrate"], (int, float))
        if "sample_rate" in result:
            assert isinstance(result["sample_rate"], (int, float))
        if "channels" in result:
            assert isinstance(result["channels"], (int, float))

        print(f"✅ Technical metadata extracted: {result}")

    def test_chapter_detection(self, embedded_source):
        """Test chapter detection from real m4b file."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        result = embedded_source.extract(SAMPLE_AUDIOBOOK)

        # Check for chapter information
        chapter_count = result.get("chapter_count")
        has_chapters = result.get("has_chapters", False)

        if chapter_count is not None:
            assert isinstance(chapter_count, int)
            assert chapter_count >= 0

        if has_chapters:
            assert chapter_count is None or chapter_count > 0

        print(f"✅ Chapter info: count={chapter_count}, has_chapters={has_chapters}")

    def test_cover_art_detection(self, embedded_source):
        """Test embedded cover art detection."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        result = embedded_source.extract(SAMPLE_AUDIOBOOK)

        # Check for cover art information
        has_cover = result.get("has_cover_art", False)
        cover_dimensions = result.get("cover_dimensions")

        if has_cover:
            print(f"✅ Cover art detected, dimensions: {cover_dimensions}")

        # This is informational - not all files have embedded covers
        assert isinstance(has_cover, bool)

    def test_backend_selection(self, embedded_source):
        """Test which backend was used for extraction."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        result = embedded_source.extract(SAMPLE_AUDIOBOOK)

        source = result.get("source")
        assert source in ["ffprobe", "mutagen", "basic"], f"Unknown source: {source}"

        print(f"✅ Using backend: {source}")

    def test_error_handling_missing_file(self, embedded_source):
        """Test error handling for missing files."""
        missing_file = Path("/nonexistent/file.m4b")

        result = embedded_source.extract(missing_file)

        # Should return empty dict or basic file info
        assert isinstance(result, dict)
        assert result.get("_src") == "embedded"

    def test_bulk_extraction(self, embedded_source):
        """Test bulk extraction from sample directory."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        sample_dir = SAMPLE_AUDIOBOOK.parent

        # Manual bulk extraction since no bulk method exists
        results = []
        audio_extensions = {".m4b", ".mp3", ".m4a", ".flac"}

        for file_path in sample_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                try:
                    result = embedded_source.extract(file_path)
                    if result and result.get("_src") == "embedded":
                        results.append(result)
                except Exception as e:
                    print(f"Failed to extract from {file_path}: {e}")

        # Should find at least our sample file
        assert isinstance(results, list)
        assert len(results) >= 1

        # Each result should be technical metadata
        for result in results:
            assert isinstance(result, dict)
            assert result.get("_src") == "embedded"

        print(f"✅ Bulk extraction found {len(results)} audio files")

    def test_performance_benchmark(self, embedded_source):
        """Benchmark extraction performance."""
        if not SAMPLE_AUDIOBOOK.exists():
            pytest.skip("Sample audiobook file not available")

        import time

        start_time = time.time()
        result = embedded_source.extract(SAMPLE_AUDIOBOOK)
        end_time = time.time()

        extraction_time = end_time - start_time

        # Should be reasonably fast (under 5 seconds for 500MB file)
        assert extraction_time < 5.0, f"Extraction too slow: {extraction_time:.2f}s"

        print(f"✅ Extraction completed in {extraction_time:.3f}s")
        print(f"   File size: {SAMPLE_AUDIOBOOK.stat().st_size / 1024 / 1024:.1f}MB")
        print(f"   Backend: {result.get('source', 'unknown')}")
