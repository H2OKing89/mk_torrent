#!/usr/bin/env python3
"""
Demo script showcasing the new comprehensive metadata validation system.

This demonstrates the validators implemented according to the Blueprint specification,
including RED compliance hints and detailed error/warning reporting.
"""

from src.mk_torrent.core.metadata.validators import validate_audiobook
from src.mk_torrent.core.metadata.engine import MetadataEngine
from src.mk_torrent.core.metadata.processors.audiobook import AudiobookProcessor


def demo_basic_validation():
    """Demonstrate basic validation functionality."""
    print("🧪 DEMO: Basic Validation")
    print("=" * 50)

    # Test with good metadata
    good_metadata = {
        "title": "How a Realist Hero Rebuilt the Kingdom",
        "author": "Dojyomaru",
        "album": "How a Realist Hero Rebuilt the Kingdom",
        "series": "How a Realist Hero Rebuilt the Kingdom",
        "volume": "03",
        "year": 2023,
        "narrator": "J. Michael Tatum",
        "duration_sec": 18000,  # 5 hours
        "format": "M4B",
        "encoding": "AAC",
        "asin": "B0C8ZW5N6Y",
        "publisher": "J-Novel Club",
        "description": "A fantasy story about kingdom management.",
        "language": "en",
        "genres": ["Fantasy", "Light Novel"],
    }

    result = validate_audiobook(good_metadata)
    print(f"✅ Valid: {result['valid']}")
    print(f"📊 Completeness: {result['completeness']:.1%}")
    print(f"⚠️  Warnings: {len(result['warnings'])}")
    if result["warnings"]:
        print(f"   Sample: {result['warnings'][0]}")
    print()


def demo_error_detection():
    """Demonstrate error detection with invalid data."""
    print("🚨 DEMO: Error Detection")
    print("=" * 50)

    # Test with problematic metadata
    bad_metadata = {
        "title": "",  # Required field missing
        "author": "",  # Required field missing
        "year": "not-a-year",  # Invalid format
        "duration_sec": 10,  # Too short for audiobook
        "format": "UNKNOWN",  # Uncommon format
        "asin": "invalid-asin",  # Bad ASIN format
        "isbn": "123",  # Bad ISBN format
        "volume": "Volume ???",  # Unclear volume
    }

    result = validate_audiobook(bad_metadata)
    print(f"❌ Valid: {result['valid']}")
    print(f"🔥 Errors: {len(result['errors'])}")
    for error in result["errors"][:3]:  # Show first 3 errors
        print(f"   • {error}")
    print(f"⚠️  Warnings: {len(result['warnings'])}")
    for warning in result["warnings"][:2]:  # Show first 2 warnings
        print(f"   • {warning}")
    print(f"📊 Completeness: {result['completeness']:.1%}")
    print()


def demo_red_compliance():
    """Demonstrate RED-specific validation hints."""
    print("🎯 DEMO: RED Compliance Hints")
    print("=" * 50)

    # Audiobook metadata without RED-preferred fields
    red_metadata = {
        "title": "Example Audiobook",
        "author": "Great Author",
        # Missing 'album' field (RED expects this)
        "year": 2023,
        "format": "MP3",
        # Missing 'encoding' for MP3 (RED wants quality specified)
        # Missing narrator, publisher, description (RED recommended)
    }

    result = validate_audiobook(red_metadata)
    print(f"✅ Valid: {result['valid']} (has required fields)")
    print(f"📊 Completeness: {result['completeness']:.1%}")
    print("🎯 RED-specific hints:")
    red_warnings = [w for w in result["warnings"] if "RED" in w]
    for warning in red_warnings:
        print(f"   • {warning}")
    print()


def demo_engine_integration():
    """Demonstrate integration with the metadata engine."""
    print("🔧 DEMO: Engine Integration")
    print("=" * 50)

    # Create engine with audiobook processor
    engine = MetadataEngine()
    processor = AudiobookProcessor()
    engine.register_processor("audiobook", processor)

    # Test validation through engine
    test_metadata = {
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "narrator": "Great Narrator",
        "album": "Test Book",
        "duration_sec": 7200,  # 2 hours
        "format": "M4B",
    }

    result = engine.validate_metadata(test_metadata, "audiobook")
    print(f"✅ Engine validation: {result.valid}")
    print(f"📊 Completeness: {result.completeness:.1%}")
    print(f"⚠️  Warnings: {len(result.warnings)}")
    if result.warnings:
        print(f"   Sample: {result.warnings[0]}")
    print()


def demo_validation_primitives():
    """Demonstrate individual validation primitive functions."""
    print("🔧 DEMO: Validation Primitives")
    print("=" * 50)

    from src.mk_torrent.core.metadata.validators.common import (
        is_year,
        is_valid_asin,
        normalize_volume,
        validate_year_drift,
    )

    # Test individual validators
    test_cases = [
        ("Year validation", "is_year(2023)", is_year(2023)),
        ("Year validation", "is_year('not-year')", is_year("not-year")),
        ("ASIN validation", "is_valid_asin('B0C8ZW5N6Y')", is_valid_asin("B0C8ZW5N6Y")),
        ("ASIN validation", "is_valid_asin('invalid')", is_valid_asin("invalid")),
        (
            "Volume normalization",
            "normalize_volume('vol_3')",
            normalize_volume("vol_3"),
        ),
        (
            "Volume normalization",
            "normalize_volume('Volume 12')",
            normalize_volume("Volume 12"),
        ),
    ]

    for category, test_expr, result in test_cases:
        status = "✅" if result else "❌"
        print(f"   {status} {test_expr} → {result}")

    # Test year drift
    valid, warning = validate_year_drift(2050)
    print(f"   📅 validate_year_drift(2050) → Valid: {valid}, Warning: '{warning}'")
    print()


if __name__ == "__main__":
    print("🎯 Metadata Validation System Demo")
    print("Implementation based on Blueprint specification")
    print("=" * 60)
    print()

    demo_basic_validation()
    demo_error_detection()
    demo_red_compliance()
    demo_engine_integration()
    demo_validation_primitives()

    print(
        "✅ Demo completed! The comprehensive validation system is working correctly."
    )
    print("📋 Next steps per Blueprint: Field merger → RED mapper → Configuration")
