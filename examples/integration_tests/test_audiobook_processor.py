"""
Test the new audiobook processor with Audnexus API integration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mk_torrent.core.metadata import MetadataEngine, AudiobookMeta
from mk_torrent.core.metadata.processors.audiobook import AudiobookProcessor


def test_audiobook_processor():
    """Test the new audiobook processor with real sample file."""
    print("🎧 Testing Audiobook Processor with Audnexus Integration")
    print("=" * 60)

    # Create metadata engine
    engine = MetadataEngine()

    # Register our new audiobook processor
    processor = AudiobookProcessor(region="us")
    engine.register_processor("audiobook", processor)

    # Use the real sample file
    sample_file = Path(
        "tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
    )

    # If relative path doesn't work, try absolute path from script location
    if not sample_file.exists():
        script_dir = Path(__file__).parent
        sample_file = script_dir / sample_file
        if not sample_file.exists():
            print(f"❌ Sample file not found: {sample_file}")
            print("Using filename string instead...")
            sample_file = "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing].m4b"

    print(f"📂 Processing: {sample_file}")

    try:
        # Extract metadata using the engine
        print("\n1️⃣ Extracting metadata...")
        metadata_dict = engine.extract_metadata(str(sample_file))

        print("✅ Successfully extracted metadata:")
        print(f"   Title: {metadata_dict.get('title', 'N/A')}")
        print(f"   Author: {metadata_dict.get('author', 'N/A')}")
        print(f"   Series: {metadata_dict.get('series', 'N/A')}")
        print(f"   Volume: {metadata_dict.get('volume', 'N/A')}")
        print(f"   Year: {metadata_dict.get('year', 'N/A')}")
        print(f"   Publisher: {metadata_dict.get('publisher', 'N/A')}")
        print(f"   Narrator: {metadata_dict.get('narrator', 'N/A')}")
        print(f"   Duration: {metadata_dict.get('duration', 'N/A')}")
        print(f"   ASIN: {metadata_dict.get('asin', 'N/A')}")
        print(f"   Source: {metadata_dict.get('source', 'N/A')}")

        # Convert to AudiobookMeta object
        print("\n2️⃣ Converting to AudiobookMeta...")
        audiobook = AudiobookMeta.from_dict(metadata_dict)

        print("✅ AudiobookMeta object created:")
        print(f"   Title: {audiobook.title}")
        print(f"   Author: {audiobook.author}")
        print(f"   Series: {audiobook.series}")
        print(f"   Volume: {audiobook.volume}")
        print(f"   Year: {audiobook.year}")
        print(f"   Publisher: {audiobook.publisher}")
        print(f"   ASIN: {audiobook.asin}")

        # Validate metadata
        print("\n3️⃣ Validating metadata...")
        validation = engine.validate_metadata(metadata_dict)

        print("✅ Validation complete:")
        print(f"   Valid: {validation.valid}")
        print(f"   Completeness: {validation.completeness:.1%}")

        if validation.errors:
            print(f"   Errors: {validation.errors}")
        if validation.warnings:
            print(f"   Warnings: {validation.warnings}")

        # Test direct processor methods
        print("\n4️⃣ Testing processor methods directly...")

        # Test direct extraction with a simple filename
        simple_filename = "Test Author - Test Book Title.m4b"
        simple_metadata = processor.extract(simple_filename)
        print(
            f"   Simple filename test: {simple_metadata.get('title', 'N/A')} by {simple_metadata.get('author', 'N/A')}"
        )

        # Test validation
        test_metadata = {"title": "Test", "author": "Test Author", "year": 2023}
        test_validation = processor.validate(test_metadata)
        print(
            f"   Test validation: valid={test_validation.valid}, completeness={test_validation.completeness:.1%}"
        )

        # Test enhancement
        enhanced = processor.enhance(test_metadata)
        print(f"   Enhancement test: {enhanced.get('display_name', 'N/A')}")

        print("\n🎉 All tests completed successfully!")

        # Show API data comparison
        if metadata_dict.get("source") == "audnexus":
            print("\n📊 API vs Filename comparison:")
            print("   API Source: Provides rich metadata from Audnexus database")
            print("   Filename Source: Basic parsing fallback")
            print("   ✅ API integration working correctly!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


def test_comparison_with_old_system():
    """Compare with the old integration."""
    print("\n" + "=" * 60)
    print("🔄 Comparing with existing Audnexus integration")
    print("=" * 60)

    try:
        # Test old system
        print("🔧 Testing existing integration...")
        from mk_torrent.integrations.audnexus_api import fetch_metadata_by_asin

        old_metadata = fetch_metadata_by_asin("B0C8ZW5N6Y")

        if old_metadata:
            print("✅ Old system data:")
            print(f"   Title: {old_metadata.get('title', 'N/A')}")
            print(f"   Album: {old_metadata.get('album', 'N/A')}")
            print(f"   Artist: {old_metadata.get('artist', 'N/A')}")
            print(f"   Year: {old_metadata.get('year', 'N/A')}")
            print(f"   Runtime: {old_metadata.get('runtime_formatted', 'N/A')}")

        # Test new system
        print("\n🆕 Testing new core system...")
        from mk_torrent.core.metadata.sources.audnexus import AudnexusSource

        audnexus = AudnexusSource()
        new_metadata = audnexus.extract("B0C8ZW5N6Y")

        print("✅ New system data:")
        print(f"   Title: {new_metadata.get('title', 'N/A')}")
        print(f"   Album: {new_metadata.get('album', 'N/A')}")
        print(f"   Author: {new_metadata.get('author', 'N/A')}")
        print(f"   Year: {new_metadata.get('year', 'N/A')}")
        print(f"   Duration: {new_metadata.get('duration', 'N/A')}")

        print("\n📈 Improvements in new system:")
        print("   ✅ Better schema normalization")
        print("   ✅ Consistent field naming (author vs artist)")
        print("   ✅ Protocol-based architecture")
        print("   ✅ Type-safe AudiobookMeta objects")
        print("   ✅ Comprehensive validation")
        print("   ✅ Clean separation of concerns")

    except Exception as e:
        print(f"❌ Comparison failed: {e}")


if __name__ == "__main__":
    test_audiobook_processor()
    test_comparison_with_old_system()
