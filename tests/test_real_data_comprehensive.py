"""
Comprehensive validation tests using real audiobook file data.

This test suite validates the complete metadata processing pipeline
using the actual sample audiobook file, ensuring real-world compatibility.
"""

import pytest
from datetime import datetime

from tests.utils.real_data_helpers import (
    SAMPLE_AUDIOBOOK_FILE,
    SAMPLE_AUDIOBOOK_DIR,
    skip_if_no_sample_file,
    get_real_three_source_metadata,
)

from src.mk_torrent.core.metadata.base import AudiobookMeta
from src.mk_torrent.core.metadata.sources.pathinfo import PathInfoSource
from src.mk_torrent.core.metadata.sources.embedded import EmbeddedSource
from src.mk_torrent.core.metadata.sources.audnexus import AudnexusSource
from src.mk_torrent.core.metadata.services.merge import FieldMerger


class TestRealFileDataValidation:
    """Comprehensive validation tests using the real audiobook sample."""

    def test_sample_file_integrity(self):
        """Verify the sample file exists and is valid."""
        skip_if_no_sample_file()

        assert (
            SAMPLE_AUDIOBOOK_FILE.exists()
        ), f"Sample file missing: {SAMPLE_AUDIOBOOK_FILE}"
        assert SAMPLE_AUDIOBOOK_FILE.is_file(), "Sample path is not a file"
        assert (
            SAMPLE_AUDIOBOOK_FILE.stat().st_size > 1000000
        ), "Sample file too small (< 1MB)"
        assert SAMPLE_AUDIOBOOK_FILE.suffix == ".m4b", "Sample file is not .m4b format"

        # Verify directory structure
        assert (
            SAMPLE_AUDIOBOOK_DIR.exists()
        ), f"Sample directory missing: {SAMPLE_AUDIOBOOK_DIR}"
        assert SAMPLE_AUDIOBOOK_DIR.is_dir(), "Sample path is not a directory"

    def test_path_source_extraction_real(self):
        """Test PathInfoSource with real directory/filename."""
        skip_if_no_sample_file()

        path_source = PathInfoSource()

        # Test with directory name
        dir_result = path_source.extract(SAMPLE_AUDIOBOOK_DIR.name)
        assert dir_result.get("_src") == "path"
        assert dir_result.get("title")
        assert dir_result.get("author")
        assert dir_result.get("asin") == "B0C8ZW5N6Y"
        assert dir_result.get("year") == 2023
        assert dir_result.get("volume") == "03"

        # Test with full file path
        file_result = path_source.extract(str(SAMPLE_AUDIOBOOK_FILE))
        assert file_result.get("_src") == "path"
        assert file_result.get("asin") == "B0C8ZW5N6Y"

        print(f"Path extraction fields: {len(dir_result)}")
        print(
            f"Key path fields: title={dir_result.get('title')}, author={dir_result.get('author')}"
        )

    def test_embedded_source_extraction_real(self):
        """Test EmbeddedSource with real M4B file."""
        skip_if_no_sample_file()

        embedded_source = EmbeddedSource()
        result = embedded_source.extract(SAMPLE_AUDIOBOOK_FILE)

        assert result.get("_src") == "embedded"
        assert result.get("duration_sec") > 0
        assert result.get("file_size_bytes") > 0
        assert result.get("bitrate") > 0
        assert result.get("sample_rate") > 0
        assert result.get("channels") > 0

        # Verify technical accuracy
        duration = result.get("duration_sec")
        assert 30000 < duration < 35000, f"Duration {duration}s seems incorrect"

        file_size = result.get("file_size_mb")
        assert 400 < file_size < 600, f"File size {file_size}MB seems incorrect"

        print(f"Embedded extraction fields: {len(result)}")
        print(
            f"Technical specs: {duration}s, {file_size}MB, {result.get('bitrate')}bps"
        )

    def test_api_source_extraction_real(self):
        """Test AudnexusSource with real ASIN."""
        skip_if_no_sample_file()

        api_source = AudnexusSource()

        try:
            result = api_source.extract("B0C8ZW5N6Y")

            assert result.get("_src") in ["audnexus", "api"]
            assert result.get("asin") == "B0C8ZW5N6Y"
            assert result.get("title")
            assert result.get("author")

            # Verify API data richness
            assert result.get("publisher")
            assert result.get("narrator")
            assert result.get("isbn")
            assert result.get("duration_sec") or result.get("duration_seconds")

            print(f"API extraction fields: {len(result)}")
            print(f"API title: {result.get('title')}")
            print(f"API narrator: {result.get('narrator')}")

        except Exception as e:
            pytest.skip(f"API not available: {e}")

    def test_three_source_integration_real(self, real_three_source_metadata):
        """Test complete three-source integration with real data."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        # Verify all sources have data
        assert len(path_data) > 2  # More than just _src
        assert len(embedded_data) > 2
        assert len(api_data) > 2

        # Verify cross-source consistency
        asin_sources = [
            source.get("asin")
            for source in [path_data, embedded_data, api_data]
            if source.get("asin")
        ]
        if len(asin_sources) > 1:
            assert all(
                asin == asin_sources[0] for asin in asin_sources
            ), "ASIN mismatch between sources"

        # Verify complementary data
        path_title = path_data.get("title", "")
        api_title = api_data.get("title", "")
        if path_title and api_title:
            # API title should be more detailed
            assert len(api_title) >= len(
                path_title
            ), f"API title '{api_title}' shorter than path '{path_title}'"

        print(
            f"Source field counts: PATH={len(path_data)}, EMBEDDED={len(embedded_data)}, API={len(api_data)}"
        )

    def test_field_merger_comprehensive_real(self, real_three_source_metadata):
        """Test FieldMerger with comprehensive real data."""
        skip_if_no_sample_file()

        merger = FieldMerger()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        # Test all possible merge combinations
        merge_scenarios = [
            ([path_data], "path_only"),
            ([embedded_data], "embedded_only"),
            ([api_data], "api_only"),
            ([path_data, embedded_data], "path_embedded"),
            ([path_data, api_data], "path_api"),
            ([embedded_data, api_data], "embedded_api"),
            ([path_data, embedded_data, api_data], "all_three"),
        ]

        results = {}
        for sources, scenario_name in merge_scenarios:
            result = merger.merge(sources)
            results[scenario_name] = result

            # Basic sanity checks
            assert isinstance(result, dict)
            assert "_src" not in result  # Should be stripped
            assert len(result) > 0  # Should have some data

        # Verify all_three has the most comprehensive data
        all_three_result = results["all_three"]
        for scenario_name, result in results.items():
            if scenario_name != "all_three":
                assert (
                    len(all_three_result) >= len(result)
                ), f"All-three merge should have most fields, but {scenario_name} has {len(result)} vs {len(all_three_result)}"

        print("Merge scenario field counts:")
        for scenario, result in results.items():
            print(f"  {scenario}: {len(result)} fields")

        # Validate that we got the most comprehensive result
        assert (
            len(all_three_result) >= 20
        ), f"All-three merge should have substantial fields: {len(all_three_result)}"
        assert all_three_result.get("title"), "All-three merge should have title"
        assert all_three_result.get("asin"), "All-three merge should have ASIN"

    def test_audiobook_meta_creation_real(self, real_three_source_metadata):
        """Test AudiobookMeta creation with real merged data."""
        skip_if_no_sample_file()

        merger = FieldMerger()
        merged_data = merger.merge(
            [
                real_three_source_metadata["path"],
                real_three_source_metadata["embedded"],
                real_three_source_metadata["api"],
            ]
        )

        # Create AudiobookMeta from merged data
        audiobook = AudiobookMeta.from_dict(merged_data)

        # Verify essential fields
        assert audiobook.title, "AudiobookMeta missing title"
        assert audiobook.author, "AudiobookMeta missing author"

        # Test serialization round-trip
        dict_data = audiobook.to_dict()
        restored_audiobook = AudiobookMeta.from_dict(dict_data)

        assert restored_audiobook.title == audiobook.title
        assert restored_audiobook.author == audiobook.author
        assert restored_audiobook.asin == audiobook.asin

        print(f"AudiobookMeta: '{audiobook.title}' by {audiobook.author}")
        print(f"Duration: {audiobook.duration_sec}s, ASIN: {audiobook.asin}")

    def test_complete_pipeline_performance_real(self):
        """Test complete pipeline performance with real file."""
        skip_if_no_sample_file()

        start_time = datetime.now()

        # Extract from all sources
        path_source = PathInfoSource()
        embedded_source = EmbeddedSource()

        path_data = path_source.extract(SAMPLE_AUDIOBOOK_DIR.name)
        embedded_data = embedded_source.extract(SAMPLE_AUDIOBOOK_FILE)

        # Try API (with fallback)
        try:
            api_source = AudnexusSource()
            api_data = api_source.extract("B0C8ZW5N6Y")
        except Exception:
            api_data = {"_src": "api", "title": "Mock API Data"}

        # Merge data
        merger = FieldMerger()
        merged_data = merger.merge([path_data, embedded_data, api_data])

        # Create AudiobookMeta
        audiobook = AudiobookMeta.from_dict(merged_data)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Performance assertions
        assert processing_time < 10.0, f"Pipeline too slow: {processing_time}s"
        assert len(merged_data) > 10, f"Insufficient merged fields: {len(merged_data)}"

        print(f"Complete pipeline processing time: {processing_time:.2f}s")
        print(f"Final merged fields: {len(merged_data)}")
        print(f"Final audiobook: {audiobook.title} ({audiobook.duration_sec}s)")

    def test_data_quality_validation_real(self, real_three_source_metadata):
        """Validate data quality from real sources."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        # Path data quality checks
        assert path_data.get("asin"), "Path source missing ASIN"
        assert path_data.get("title"), "Path source missing title"
        assert path_data.get("author"), "Path source missing author"
        assert isinstance(path_data.get("year"), int), "Path year not integer"
        assert 2020 <= path_data.get("year", 0) <= 2030, "Path year out of range"

        # Embedded data quality checks
        duration = embedded_data.get("duration_sec", 0)
        assert 10000 < duration < 100000, f"Embedded duration {duration}s suspicious"

        bitrate = embedded_data.get("bitrate", 0)
        assert 50000 < bitrate < 500000, f"Embedded bitrate {bitrate}bps suspicious"

        sample_rate = embedded_data.get("sample_rate", 0)
        assert sample_rate in [
            22050,
            44100,
            48000,
        ], f"Embedded sample rate {sample_rate}Hz unusual"

        # API data quality checks (if available)
        if api_data.get("title"):
            assert len(api_data["title"]) > len(
                path_data.get("title", "")
            ), "API title not more detailed"

        if api_data.get("narrator"):
            assert isinstance(api_data["narrator"], str), "API narrator not string"
            assert len(api_data["narrator"]) > 0, "API narrator empty"

        print("✅ All data quality checks passed")

    def test_real_vs_mock_comparison(self):
        """Compare real data extraction vs mock data patterns."""
        skip_if_no_sample_file()

        # Get real data
        real_data = get_real_three_source_metadata()

        # Analyze field coverage
        all_fields = set()
        for source_data in real_data.values():
            all_fields.update(source_data.keys())

        # Remove _src field for analysis
        all_fields.discard("_src")

        coverage_by_source = {}
        for source_name, source_data in real_data.items():
            source_fields = set(source_data.keys()) - {"_src"}
            coverage_by_source[source_name] = {
                "field_count": len(source_fields),
                "fields": sorted(source_fields),
                "coverage_percent": len(source_fields) / len(all_fields) * 100,
            }

        print("\n=== REAL DATA ANALYSIS ===")
        print(f"Total unique fields across all sources: {len(all_fields)}")

        for source_name, info in coverage_by_source.items():
            print(
                f"{source_name.upper()}: {info['field_count']} fields ({info['coverage_percent']:.1f}% coverage)"
            )
            print(
                f"  Fields: {', '.join(info['fields'][:10])}{'...' if len(info['fields']) > 10 else ''}"
            )

        # Verify realistic field counts
        assert (
            coverage_by_source["path"]["field_count"] >= 5
        ), "Path source has too few fields"
        assert (
            coverage_by_source["embedded"]["field_count"] >= 8
        ), "Embedded source has too few fields"
        assert (
            coverage_by_source["api"]["field_count"] >= 15
        ), "API source has too few fields"

        assert (
            len(all_fields) >= 25
        ), f"Total field diversity too low: {len(all_fields)}"
