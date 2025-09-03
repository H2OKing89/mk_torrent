"""Test enhanced fields with real audiobook sample."""

import pytest
from pathlib import Path
from datetime import date
from mk_torrent.core.metadata.base import AudiobookMeta
from mk_torrent.core.metadata.entities import AudiobookMetaRich


def test_real_audiobook_with_enhanced_fields():
    """Test enhanced fields using metadata that could come from the actual sample audiobook file."""

    # Path to the real sample audiobook (for reference)
    sample_path = Path(
        "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
    )

    if not sample_path.exists():
        pytest.skip(f"Sample audiobook file not found: {sample_path}")

    # Create enhanced metadata that represents what could be extracted from:
    # - Filename parsing (title, author, year, ASIN, volume)
    # - Embedded metadata (copyright, release_date, description)
    # - API data (rating, cover_dimensions, additional details)
    enhanced_metadata = {
        "title": "How a Realist Hero Rebuilt the Kingdom - vol_03",
        "subtitle": "A Light Novel Adventure",
        "author_primary": "Dojyomaru",
        "year": 2023,
        "asin": "B0C8ZW5N6Y",
        "copyright": "© 2023 J-Novel Club",
        "release_date": "2023-08-15",
        "rating": 4.7,
        "cover_dimensions": {"width": 1400, "height": 2100},
        "region": "JP",
        "literature_type": "light-novel",
        "format_type": "m4b",
        "is_adult": False,
        "language": "en-US",
        "description_html": "<p>The third volume of this exciting light novel series...</p>",
        "description_text": "The third volume of this exciting light novel series...",
    }

    # Test conversion to simple AudiobookMeta
    simple_audiobook = AudiobookMeta.from_dict(enhanced_metadata)
    assert simple_audiobook.title == "How a Realist Hero Rebuilt the Kingdom - vol_03"
    assert simple_audiobook.subtitle == "A Light Novel Adventure"
    assert simple_audiobook.copyright == "© 2023 J-Novel Club"
    assert simple_audiobook.release_date == "2023-08-15"
    assert simple_audiobook.rating == 4.7
    assert simple_audiobook.cover_dimensions == {"width": 1400, "height": 2100}

    # Test conversion to rich AudiobookMetaRich
    rich_audiobook = AudiobookMetaRich.from_dict(enhanced_metadata)
    assert rich_audiobook.title == "How a Realist Hero Rebuilt the Kingdom - vol_03"
    assert rich_audiobook.subtitle == "A Light Novel Adventure"
    assert rich_audiobook.copyright == "© 2023 J-Novel Club"
    assert rich_audiobook.release_date == date(2023, 8, 15)
    assert rich_audiobook.rating == 4.7
    assert rich_audiobook.cover.width == 1400
    assert rich_audiobook.cover.height == 2100
    assert rich_audiobook.region == "JP"
    assert rich_audiobook.literature_type == "light-novel"
    assert rich_audiobook.format_type == "m4b"
    assert rich_audiobook.is_adult is False
    assert rich_audiobook.language == "en-US"

    # Test round-trip conversion
    simple_dict = rich_audiobook.to_simple_audiobook_meta()
    assert simple_dict["cover_dimensions"]["width"] == 1400
    assert simple_dict["cover_dimensions"]["height"] == 2100
    assert simple_dict["subtitle"] == "A Light Novel Adventure"
    assert simple_dict["copyright"] == "© 2023 J-Novel Club"
    assert simple_dict["rating"] == 4.7

    # Test that we can convert back to rich from the simple dict
    rich_from_simple = AudiobookMetaRich.from_dict(simple_dict)
    assert rich_from_simple.cover.width == 1400
    assert rich_from_simple.cover.height == 2100
    assert rich_from_simple.subtitle == "A Light Novel Adventure"
    assert rich_from_simple.rating == 4.7


def test_enhanced_fields_demonstrate_chatgpt_feedback():
    """
    This test demonstrates the enhanced fields that address ChatGPT's feedback
    about expanding the canonical data model to include fields like:
    subtitle, release_date, copyright, cover_dimensions, rating, etc.
    """

    # Sample metadata showing the expanded fields we can now capture
    comprehensive_metadata = {
        # Basic fields (always supported)
        "title": "Sample Audiobook",
        "author_primary": "Author Name",
        "year": 2023,
        # Enhanced fields (new additions per ChatGPT feedback)
        "subtitle": "The Complete Edition",
        "release_date": "2023-12-01",
        "copyright": "© 2023 Publisher Name",
        "rating": 4.8,
        "cover_dimensions": {"width": 1200, "height": 1800},
        "region": "US",
        "literature_type": "fiction",
        "format_type": "m4b",
        "is_adult": False,
        "language": "en-US",
        "description_html": "<b>Bold description</b> with <i>formatting</i>",
        "description_text": "Plain text description without formatting",
    }

    # Both simple and rich models now support these enhanced fields
    simple = AudiobookMeta.from_dict(comprehensive_metadata)
    rich = AudiobookMetaRich.from_dict(comprehensive_metadata)

    # Verify all the enhanced fields are properly handled
    assert simple.subtitle == "The Complete Edition"
    assert simple.copyright == "© 2023 Publisher Name"
    assert simple.rating == 4.8
    assert simple.cover_dimensions == {"width": 1200, "height": 1800}

    assert rich.subtitle == "The Complete Edition"
    assert rich.copyright == "© 2023 Publisher Name"
    assert rich.rating == 4.8
    assert rich.cover.width == 1200
    assert rich.cover.height == 1800
    assert rich.region == "US"
    assert rich.literature_type == "fiction"
    assert rich.is_adult is False
