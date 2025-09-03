"""Test enhanced metadata fields"""

from datetime import date
from mk_torrent.core.metadata import AudiobookMeta
from mk_torrent.core.metadata.entities import AudiobookMetaRich, PersonRef, GenreTag


def test_audiobook_meta_enhanced_fields():
    """Test AudiobookMeta with enhanced fields."""
    audiobook = AudiobookMeta(
        title="Test Audiobook",
        subtitle="An Enhanced Test",
        author="Test Author",
        year=2023,
        release_date="2023-06-15",
        publisher="Test Publisher",
        copyright="Copyright 2023 Test Publisher",
        rating=4.5,
        cover_dimensions={"width": 500, "height": 500},
    )

    # Verify new fields
    assert audiobook.subtitle == "An Enhanced Test"
    assert audiobook.release_date == "2023-06-15"
    assert audiobook.copyright == "Copyright 2023 Test Publisher"
    assert audiobook.rating == 4.5
    assert audiobook.cover_dimensions == {"width": 500, "height": 500}

    # Verify to_dict includes new fields
    data = audiobook.to_dict()
    assert data["subtitle"] == "An Enhanced Test"
    assert data["release_date"] == "2023-06-15"
    assert data["copyright"] == "Copyright 2023 Test Publisher"
    assert data["rating"] == 4.5
    assert data["cover_dimensions"] == {"width": 500, "height": 500}


def test_audiobook_meta_rich_enhanced_fields():
    """Test AudiobookMetaRich with enhanced fields."""
    rich_audiobook = AudiobookMetaRich(
        title="Test Audiobook",
        subtitle="An Enhanced Test",
        copyright="Copyright 2023 Test Publisher",
        release_date=date(2023, 6, 15),
        rating=4.5,
        authors=[PersonRef(name="Test Author", asin="B123456789", role="author")],
        genres=[GenreTag(name="Science Fiction", type="genre")],
    )

    # Verify new fields
    assert rich_audiobook.subtitle == "An Enhanced Test"
    assert rich_audiobook.copyright == "Copyright 2023 Test Publisher"
    assert rich_audiobook.release_date == date(2023, 6, 15)
    assert rich_audiobook.rating == 4.5

    # Test conversion to simple format
    simple_data = rich_audiobook.to_simple_audiobook_meta()
    assert simple_data["subtitle"] == "An Enhanced Test"
    assert simple_data["copyright"] == "Copyright 2023 Test Publisher"
    assert simple_data["release_date"] == "2023-06-15"
    assert simple_data["rating"] == 4.5


def test_conversion_round_trip_with_enhanced_fields():
    """Test conversion between simple and rich models with enhanced fields."""
    # Start with simple model with enhanced fields
    simple_data = {
        "title": "Test Book",
        "subtitle": "Enhanced Edition",
        "author": "Jane Doe",
        "year": 2023,
        "release_date": "2023-06-15",
        "copyright": "Copyright 2023",
        "rating": 4.2,
        "cover_dimensions": {"width": 600, "height": 600},
        "genres": ["Fantasy", "Adventure"],
    }

    # Convert to rich model
    rich_audiobook = AudiobookMetaRich.from_dict(simple_data)

    # Verify enhanced fields
    assert rich_audiobook.subtitle == "Enhanced Edition"
    assert rich_audiobook.copyright == "Copyright 2023"
    assert rich_audiobook.rating == 4.2

    # Verify cover dimensions were converted to ImageAsset
    assert rich_audiobook.cover.width == 600
    assert rich_audiobook.cover.height == 600

    # Convert back to simple
    converted_data = rich_audiobook.to_simple_audiobook_meta()

    # Debug: print what we got
    print(f"Converted cover_dimensions: {converted_data.get('cover_dimensions')}")
    print(
        f"Rich cover: width={rich_audiobook.cover.width}, height={rich_audiobook.cover.height}"
    )

    # Verify round trip preserves enhanced fields
    assert converted_data["subtitle"] == "Enhanced Edition"
    assert converted_data["copyright"] == "Copyright 2023"
    assert converted_data["rating"] == 4.2
    assert converted_data["cover_dimensions"] == {"width": 600, "height": 600}
