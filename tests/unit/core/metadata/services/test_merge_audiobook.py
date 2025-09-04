"""
Tests for the enhanced field merger with three-source strategy.

Tests cover:
- Scalar field precedence resolution
- List field union logic with deduplication
- Technical vs descriptive field separation
- Real-world audiobook examples using actual sample file
- Edge cases and error handling
"""

import pytest
from src.mk_torrent.core.metadata.services.merge_audiobook import (
    FieldMerger,
    merge_metadata,
    DEFAULT_PRECEDENCE,
    _is_meaningful,
    _dedupe_preserve_order,
    _values_for_field,
)
from tests.utils.real_data_helpers import (
    skip_if_no_sample_file,
    SAMPLE_AUDIOBOOK_FILE,
)


class TestMeaningfulValueDetection:
    """Test the _is_meaningful helper function."""

    def test_none_values(self):
        assert not _is_meaningful(None)

    def test_empty_strings(self):
        assert not _is_meaningful("")
        assert not _is_meaningful("   ")
        assert not _is_meaningful("\t\n")

    def test_valid_strings(self):
        assert _is_meaningful("hello")
        assert _is_meaningful(" hello ")
        assert _is_meaningful("0")  # string "0" is meaningful

    def test_empty_collections(self):
        assert not _is_meaningful([])
        assert not _is_meaningful({})
        assert not _is_meaningful(())
        assert not _is_meaningful(set())

    def test_non_empty_collections(self):
        assert _is_meaningful([1, 2, 3])
        assert _is_meaningful({"key": "value"})
        assert _is_meaningful((1, 2))
        assert _is_meaningful({"item"})

    def test_scalar_values(self):
        assert _is_meaningful(0)  # number 0 is meaningful
        assert _is_meaningful(42)
        assert _is_meaningful(False)  # boolean False is meaningful
        assert _is_meaningful(True)


class TestDeduplication:
    """Test the list deduplication logic."""

    def test_preserve_order(self):
        items = ["Fantasy", "Science Fiction", "Epic", "Fantasy"]
        result = _dedupe_preserve_order(items)
        assert result == ["Fantasy", "Science Fiction", "Epic"]

    def test_case_insensitive(self):
        items = ["Fantasy", "FANTASY", "fantasy", "Science Fiction"]
        result = _dedupe_preserve_order(items)
        assert result == ["Fantasy", "Science Fiction"]

    def test_strip_whitespace(self):
        items = [" Fantasy ", "Fantasy", "  Science Fiction  "]
        result = _dedupe_preserve_order(items)
        assert result == ["Fantasy", "Science Fiction"]

    def test_empty_items_filtered(self):
        items = ["Fantasy", "", "Science Fiction", "   ", "Epic"]
        result = _dedupe_preserve_order(items)
        assert result == ["Fantasy", "Science Fiction", "Epic"]


class TestValueExtraction:
    """Test the _values_for_field helper function."""

    def test_extract_existing_field(self):
        candidates = [
            {"_src": "path", "title": "Path Title", "author": "Path Author"},
            {"_src": "api", "title": "API Title", "year": 2023},
        ]

        assert _values_for_field(candidates, "title", "path") == "Path Title"
        assert _values_for_field(candidates, "title", "api") == "API Title"
        assert _values_for_field(candidates, "year", "api") == 2023

    def test_missing_field_returns_none(self):
        candidates = [{"_src": "path", "title": "Title"}]
        assert _values_for_field(candidates, "missing", "path") is None

    def test_missing_source_returns_none(self):
        candidates = [{"_src": "path", "title": "Title"}]
        assert _values_for_field(candidates, "title", "api") is None

    def test_empty_value_returns_none(self):
        candidates = [{"_src": "path", "title": "", "author": "   "}]
        assert _values_for_field(candidates, "title", "path") is None
        assert _values_for_field(candidates, "author", "path") is None


class TestFieldMergerBasics:
    """Test basic field merger functionality."""

    def test_initialization_with_defaults(self):
        merger = FieldMerger()
        assert merger.precedence == DEFAULT_PRECEDENCE

    def test_initialization_with_custom_precedence(self):
        custom = {"title": ["path", "api"]}
        merger = FieldMerger(custom)
        assert merger.precedence == custom

    def test_validation_requires_src_field(self):
        merger = FieldMerger()
        candidates = [{"title": "No source field"}]

        with pytest.raises(ValueError, match="missing '_src' field"):
            merger.merge(candidates)


class TestScalarFieldMerging:
    """Test scalar field precedence resolution."""

    @pytest.fixture
    def merger(self):
        return FieldMerger()

    @pytest.fixture
    def simple_candidates(self):
        return [
            {"_src": "path", "title": "Path Title", "year": 2020},
            {"_src": "api", "title": "API Title", "year": 2023, "author": "API Author"},
            {"_src": "embedded", "title": "Embedded Title", "duration_sec": 3600},
        ]

    def test_api_wins_for_title(self, merger, simple_candidates):
        result = merger.merge(simple_candidates)
        assert result["title"] == "API Title"  # api > path for title

    def test_path_wins_for_series(self, merger):
        candidates = [
            {"_src": "path", "series": "Path Series"},
            {"_src": "api", "series": "API Series"},
        ]
        result = merger.merge(candidates)
        assert result["series"] == "Path Series"  # path > api for series

    def test_embedded_wins_for_duration(self, merger, simple_candidates):
        result = merger.merge(simple_candidates)
        assert result["duration_sec"] == 3600  # embedded > api for duration

    def test_fallback_to_lower_precedence(self, merger):
        candidates = [
            {"_src": "path", "title": ""},  # empty, not meaningful
            {"_src": "api"},  # missing title field
            {"_src": "embedded", "title": "Embedded Title"},
        ]
        result = merger.merge(candidates)
        assert result["title"] == "Embedded Title"  # fallback to embedded

    def test_no_meaningful_value_excludes_field(self, merger):
        candidates = [
            {"_src": "path", "title": ""},
            {"_src": "api"},
            {"_src": "embedded", "title": "   "},
        ]
        result = merger.merge(candidates)
        assert "title" not in result


class TestListFieldMerging:
    """Test list field union logic."""

    @pytest.fixture
    def merger(self):
        return FieldMerger()

    def test_genres_union_from_api_primary(self, merger):
        candidates = [
            {"_src": "api", "genres": ["Fantasy", "Epic", "Adventure"]},
            {"_src": "embedded", "genres": ["Fantasy", "Audiobook"]},  # Dedupes Fantasy
        ]
        result = merger.merge(candidates)
        # API first (precedence), then unique items from embedded
        assert result["genres"] == ["Fantasy", "Epic", "Adventure", "Audiobook"]

    def test_comma_separated_string_parsing(self, merger):
        candidates = [
            {"_src": "api", "genres": "Fantasy, Epic, Adventure"},
            {"_src": "embedded", "genres": ["Science Fiction"]},
        ]
        result = merger.merge(candidates)
        assert result["genres"] == ["Fantasy", "Epic", "Adventure", "Science Fiction"]

    def test_semicolon_separated_string_parsing(self, merger):
        candidates = [{"_src": "api", "genres": "Fantasy; Epic; Adventure"}]
        result = merger.merge(candidates)
        assert result["genres"] == ["Fantasy", "Epic", "Adventure"]

    def test_single_item_as_list(self, merger):
        candidates = [{"_src": "api", "genres": "Fantasy"}]  # Single string
        result = merger.merge(candidates)
        assert result["genres"] == ["Fantasy"]

    def test_case_insensitive_deduplication(self, merger):
        candidates = [
            {"_src": "api", "genres": ["Fantasy", "EPIC"]},
            {"_src": "embedded", "genres": ["fantasy", "Adventure", "epic"]},
        ]
        result = merger.merge(candidates)
        # First occurrence wins for case
        assert result["genres"] == ["Fantasy", "EPIC", "Adventure"]

    def test_empty_lists_ignored(self, merger):
        candidates = [
            {"_src": "api", "genres": []},
            {"_src": "embedded", "genres": ["Fantasy"]},
        ]
        result = merger.merge(candidates)
        assert result["genres"] == ["Fantasy"]


class TestRealisticAudiobookExample:
    """Test with realistic audiobook metadata extracted from actual sample file."""

    def test_sample_file_available(self):
        """Verify sample file exists before running tests."""
        skip_if_no_sample_file()
        assert SAMPLE_AUDIOBOOK_FILE.exists()

    def test_complete_audiobook_merge(self, real_three_source_metadata):
        """Test merging real metadata from all three sources."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        merger = FieldMerger()
        result = merger.merge([path_data, embedded_data, api_data])

        # Verify we have meaningful data from all sources
        assert result.get("_src") is None  # No _src in final merged result

        # Descriptive fields - verify precedence works with real data
        # API has more detailed title, so it should win for title
        if api_data.get("title") and path_data.get("title"):
            assert result.get("title") == api_data["title"]  # API should win for title
            print(
                f"Title: API '{api_data['title']}' won over PATH '{path_data['title']}'"
            )

        # Path should win for series (per precedence rules)
        if path_data.get("series"):
            assert (
                result.get("series") == path_data["series"]
            )  # Path should win for series
            print(f"Series: PATH '{path_data['series']}' won")

        # Technical fields - embedded should win
        if embedded_data.get("duration_sec"):
            assert result.get("duration_sec") == embedded_data["duration_sec"]
            print(
                f"Duration: EMBEDDED {embedded_data['duration_sec']}s won over API {api_data.get('duration_sec', 'N/A')}s"
            )

        if embedded_data.get("bitrate"):
            assert result.get("bitrate") == embedded_data["bitrate"]

        if embedded_data.get("sample_rate"):
            assert result.get("sample_rate") == embedded_data["sample_rate"]

        # Verify we got meaningful merged data
        assert len(result) > 5  # Should have multiple merged fields

        # Test with real ASIN - path should win
        if path_data.get("asin"):
            assert result.get("asin") == path_data["asin"]  # Path wins for ASIN

        print("\n=== REAL AUDIOBOOK MERGE RESULTS ===")
        print(f"Total merged fields: {len(result)}")
        print(f"Title: {result.get('title')}")
        print(f"Series: {result.get('series')}")
        print(f"Author: {result.get('author')}")
        print(f"Volume: {result.get('volume')}")
        print(f"Duration: {result.get('duration_sec')} seconds")
        print(f"ASIN: {result.get('asin')}")
        print(f"Codec: {result.get('codec', result.get('format'))}")
        print(f"Sample Rate: {result.get('sample_rate')}")
        print(f"Chapters: {result.get('chapter_count')}")

        # Verify some key fields made it through
        assert result.get("title")  # Should have a title
        assert result.get("author")  # Should have an author
        assert result.get("asin")  # Should have ASIN
        assert result.get("duration_sec")  # Should have duration

    def test_handles_missing_sources_gracefully(self, real_three_source_metadata):
        """Test merge with missing sources using real data."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        api_data = real_three_source_metadata["api"]

        # Test with only path and API (no embedded)
        merger = FieldMerger()
        result = merger.merge([path_data, api_data])

        # Should still get meaningful results
        assert result.get("title") or result.get(
            "series"
        )  # At least one descriptive field
        assert len(result) > 3  # Should have multiple fields

        # Test with only one source
        result_single = merger.merge([path_data])
        assert len(result_single) > 1  # Should have at least some fields from path

    def test_real_data_precedence_rules(self, real_three_source_metadata):
        """Test that precedence rules work correctly with real data."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        merger = FieldMerger()
        result = merger.merge([path_data, embedded_data, api_data])

        # Check specific precedence rules with real data, but be flexible about what fields exist
        critical_fields = {
            "title": ["api", "path", "embedded"],  # API should win for title
            "series": ["path", "api", "embedded"],  # Path should win for series
            "asin": ["path", "api", "embedded"],  # Path should win for ASIN
            "duration_sec": [
                "embedded",
                "api",
                "path",
            ],  # Embedded should win for duration
            "bitrate": ["embedded", "api", "path"],  # Embedded should win for bitrate
        }

        for field_name, expected_precedence in critical_fields.items():
            if field_name in result:
                # Find which source should have won
                winning_source = None
                winning_value = None

                for source_name in expected_precedence:
                    source_data = {
                        "path": path_data,
                        "embedded": embedded_data,
                        "api": api_data,
                    }.get(source_name, {})

                    if source_data.get(field_name) and _is_meaningful(
                        source_data[field_name]
                    ):
                        winning_source = source_name
                        winning_value = source_data[field_name]
                        break

                if winning_source and winning_value is not None:
                    actual_value = result[field_name]

                    # For list fields, check if it starts with the winning source's values
                    if isinstance(winning_value, list) and isinstance(
                        actual_value, list
                    ):
                        # List union - should contain winning source's values
                        if winning_value:  # Non-empty list
                            assert set(
                                winning_value
                            ).issubset(
                                set(actual_value)
                            ), f"Field '{field_name}' list union failed: {winning_value} not subset of {actual_value}"
                    else:
                        assert (
                            actual_value == winning_value
                        ), f"Field '{field_name}' precedence failed: expected {winning_value} from {winning_source}, got {actual_value}"

        print("\n=== PRECEDENCE VERIFICATION ===")
        for field_name in critical_fields:
            if field_name in result:
                print(f"{field_name}: {result[field_name]}")
            else:
                print(f"{field_name}: (not present in result)")

    def test_source_validation_with_real_data(self, real_three_source_metadata):
        """Test that real sources have required _src fields."""
        skip_if_no_sample_file()

        path_data = real_three_source_metadata["path"]
        embedded_data = real_three_source_metadata["embedded"]
        api_data = real_three_source_metadata["api"]

        # All sources should have _src field
        assert path_data.get("_src") == "path"
        assert embedded_data.get("_src") == "embedded"
        assert api_data.get("_src") == "api"

        # All sources should have at least some data
        assert len(path_data) > 1  # More than just _src
        assert len(embedded_data) > 1
        assert len(api_data) > 1


class TestPartialSourceHandling:
    """Test merger works with only partial source data."""

    def test_handles_missing_sources_gracefully(self):
        """Test merger works with only partial source data."""
        merger = FieldMerger()

        # Only path and embedded data, no API
        candidates = [
            {"_src": "path", "series": "Test Series", "volume": "01"},
            {"_src": "embedded", "duration_sec": 3600, "codec": "aac"},
        ]

        result = merger.merge(candidates)
        assert result["series"] == "Test Series"  # Path wins
        assert result["volume"] == "01"  # Path only
        assert result["duration_sec"] == 3600  # Embedded only
        assert result["codec"] == "aac"  # Embedded only

        # No API-only fields should be present
        assert "narrator" not in result
        assert "publisher" not in result
        assert "isbn" not in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_candidates_list(self):
        merger = FieldMerger()
        result = merger.merge([])
        assert result == {}

    def test_custom_precedence_override(self):
        # Override title to prefer path over API
        custom_precedence = DEFAULT_PRECEDENCE.copy()
        custom_precedence["title"] = ["path", "api"]

        merger = FieldMerger(custom_precedence)
        candidates = [
            {"_src": "path", "title": "Path Title"},
            {"_src": "api", "title": "API Title"},
        ]

        result = merger.merge(candidates)
        assert result["title"] == "Path Title"  # Path wins with custom precedence

    def test_unknown_field_uses_default_order(self):
        merger = FieldMerger()
        candidates = [
            {"_src": "path", "unknown_field": "Path Value"},
            {"_src": "api", "unknown_field": "API Value"},
            {"_src": "embedded", "unknown_field": "Embedded Value"},
        ]

        result = merger.merge(candidates)
        # Default order is ["api", "embedded", "path"]
        assert result["unknown_field"] == "API Value"

    def test_field_merger_utilities(self):
        merger = FieldMerger()

        # Test precedence getters/setters
        assert "api" in merger.get_precedence_for_field("title")

        merger.set_precedence_for_field("title", ["embedded", "api", "path"])
        assert merger.get_precedence_for_field("title") == ["embedded", "api", "path"]

        # Test adding list fields
        merger.add_list_field("custom_list")
        from src.mk_torrent.core.metadata.services.merge_audiobook import LIST_FIELDS

        assert "custom_list" in LIST_FIELDS


class TestConvenienceFunction:
    """Test the convenience merge_metadata function."""

    def test_merge_metadata_with_defaults(self):
        candidates = [
            {"_src": "api", "title": "API Title"},
            {"_src": "path", "series": "Path Series"},
        ]

        result = merge_metadata(candidates)
        assert result["title"] == "API Title"
        assert result["series"] == "Path Series"

    def test_merge_metadata_with_custom_precedence(self):
        candidates = [
            {"_src": "api", "title": "API Title"},
            {"_src": "path", "title": "Path Title"},
        ]

        custom_precedence = {"title": ["path", "api"]}
        result = merge_metadata(candidates, custom_precedence)
        assert result["title"] == "Path Title"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])
