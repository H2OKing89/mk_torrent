"""
Helper utilities for extracting real metadata from the sample audiobook file.

This module provides utilities to extract actual metadata from the real sample audiobook
for use in tests, replacing synthetic/mock data with real data while maintaining
test reliability and performance.
"""

import pytest
from pathlib import Path
from typing import Any

# Real sample file path
SAMPLE_AUDIOBOOK_FILE = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/"
    "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
)

SAMPLE_AUDIOBOOK_DIR = SAMPLE_AUDIOBOOK_FILE.parent


def skip_if_no_sample_file():
    """Pytest skip decorator if the sample file doesn't exist."""
    if not SAMPLE_AUDIOBOOK_FILE.exists():
        pytest.skip(f"Sample audiobook file not found: {SAMPLE_AUDIOBOOK_FILE}")


def get_real_path_metadata() -> dict[str, Any]:
    """Extract real path metadata from the sample audiobook."""
    skip_if_no_sample_file()

    from src.mk_torrent.core.metadata.sources.pathinfo import PathInfoSource

    path_source = PathInfoSource()
    # Use the directory name for parsing (more comprehensive than just filename)
    result = path_source.extract(SAMPLE_AUDIOBOOK_DIR.name)

    # Ensure _src is set
    if "_src" not in result:
        result["_src"] = "path"

    return result


def get_real_embedded_metadata() -> dict[str, Any]:
    """Extract real embedded metadata from the sample audiobook file."""
    skip_if_no_sample_file()

    from src.mk_torrent.core.metadata.sources.embedded import EmbeddedSource

    embedded_source = EmbeddedSource()
    result = embedded_source.extract(SAMPLE_AUDIOBOOK_FILE)

    # Ensure _src is set
    if "_src" not in result:
        result["_src"] = "embedded"

    return result


def get_real_api_metadata() -> dict[str, Any]:
    """Extract real API metadata using the ASIN from the sample audiobook."""
    skip_if_no_sample_file()

    from src.mk_torrent.core.metadata.sources.audnexus import AudnexusSource

    # Extract ASIN from filename
    asin = "B0C8ZW5N6Y"  # Known ASIN from the sample file

    api_source = AudnexusSource()

    # Try to get real API data, but use mock if API is unavailable
    try:
        result = api_source.extract(asin)
        # Normalize _src to "api" for consistency in tests
        if "_src" in result:
            result["_src"] = "api"
        else:
            result["_src"] = "api"
        return result
    except Exception:
        # Fallback to mock API data if real API is unavailable
        return get_mock_api_metadata()


def get_mock_api_metadata() -> dict[str, Any]:
    """Get mock API metadata that matches the real audiobook structure."""
    return {
        "_src": "api",
        "title": "How a Realist Hero Rebuilt the Kingdom: Volume 3",
        "subtitle": "How a Realist Hero Rebuilt the Kingdom, Book 3",
        "author_primary": "Dojyomaru",
        "author_additional": [],
        "narrator_primary": "H2OKing",
        "narrator_additional": [],
        "series": "How a Realist Hero Rebuilt the Kingdom",
        "volume": "3",
        "year": 2023,
        "month": 8,
        "day": 15,
        "publisher": "J-Novel Club",
        "asin": "B0C8ZW5N6Y",
        "isbn": None,
        "rating": 4.7,
        "rating_count": 1205,
        "duration_seconds": 31509,
        "sample_rate": 22050,
        "bitrate": 64000,
        "channels": 1,
        "language": "en-US",
        "region": "US",
        "genre_primary": "Light Novel",
        "genres": ["Light Novel", "Fantasy", "Adventure"],
        "description_html": "<p>The third volume of this exciting light novel series follows our protagonist as he continues to rebuild the kingdom using modern knowledge and realistic strategies.</p>",
        "description_text": "The third volume of this exciting light novel series follows our protagonist as he continues to rebuild the kingdom using modern knowledge and realistic strategies.",
        "cover_url": "https://m.media-amazon.com/images/I/51234567890._SL500_.jpg",
        "cover_dimensions": {"width": 1400, "height": 2100},
        "copyright": "© 2023 J-Novel Club",
        "release_date": "2023-08-15",
        "purchase_date": None,
        "is_adult": False,
        "is_accurate": True,
        "literature_type": "light-novel",
        "format_type": "m4b",
    }


def get_real_three_source_metadata() -> dict[str, dict[str, Any]]:
    """Get all three sources of real metadata for comprehensive testing."""
    skip_if_no_sample_file()

    return {
        "path": get_real_path_metadata(),
        "embedded": get_real_embedded_metadata(),
        "api": get_real_api_metadata(),
    }


def create_real_data_test_case(test_name: str) -> dict[str, Any]:
    """Create a test case using real data for the field merger."""
    skip_if_no_sample_file()

    sources = get_real_three_source_metadata()

    return {
        "name": f"real_audiobook_{test_name}",
        "path_data": sources["path"],
        "embedded_data": sources["embedded"],
        "api_data": sources["api"],
        "expected_title": "How a Realist Hero Rebuilt the Kingdom: Volume 3",  # API should win
        "expected_series": sources["path"].get(
            "series", "How a Realist Hero Rebuilt the Kingdom"
        ),  # Path should win
        "expected_author": sources["api"].get(
            "author_primary", "Dojyomaru"
        ),  # API should win
    }


@pytest.fixture
def real_audiobook_path():
    """Fixture providing the path to the real sample audiobook."""
    skip_if_no_sample_file()
    return SAMPLE_AUDIOBOOK_FILE


@pytest.fixture
def real_path_metadata():
    """Fixture providing real path metadata."""
    return get_real_path_metadata()


@pytest.fixture
def real_embedded_metadata():
    """Fixture providing real embedded metadata."""
    return get_real_embedded_metadata()


@pytest.fixture
def real_api_metadata():
    """Fixture providing real API metadata."""
    return get_real_api_metadata()


@pytest.fixture
def real_three_source_metadata():
    """Fixture providing all three sources of real metadata."""
    return get_real_three_source_metadata()
