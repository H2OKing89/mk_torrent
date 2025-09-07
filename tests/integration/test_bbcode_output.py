#!/usr/bin/env python3
"""Test script to show full BBCode output for debugging template fixes."""

import sys
from pathlib import Path

# Add src to path
sys.path.append("src")

from mk_torrent.core.metadata import AudiobookMeta
from mk_torrent.core.metadata.mappers.red import REDMapper
from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.metadata.processors.audiobook import AudiobookProcessor


def main():
    # Test file path
    file_path = Path(
        "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 {ASIN.B0C8ZW5N6Y}.m4b"
    )

    if not file_path.exists():
        print(f"❌ Test file not found: {file_path}")
        return

    print(f"📖 Testing BBCode generation for: {file_path.name}")
    print("=" * 80)

    try:
        # Extract metadata using the same approach as test_red_upload_clean.py
        print("📊 Extracting metadata...")
        engine = MetadataEngine()
        audiobook_processor = AudiobookProcessor()
        engine.register_processor("audiobook", audiobook_processor)
        engine.set_default_processor("audiobook")

        metadata_dict = engine.extract_metadata(file_path)

        # Convert to AudiobookMeta (same logic as test_red_upload_clean.py)
        audiobookmeta_fields = {
            field.name for field in AudiobookMeta.__dataclass_fields__.values()
        }
        filtered_metadata = {
            k: v for k, v in metadata_dict.items() if k in audiobookmeta_fields
        }

        # Use the longer summary content for description if available
        if "summary" in metadata_dict and metadata_dict["summary"]:
            summary_content = metadata_dict["summary"]
            description_content = metadata_dict.get("description", "")

            # Use whichever is longer and more detailed
            if len(summary_content) > len(description_content):
                print(
                    f"📝 Using longer summary content ({len(summary_content)} chars) instead of description ({len(description_content)} chars)"
                )
                filtered_metadata["description"] = summary_content

        # Convert year to int if it's a string
        if "year" in filtered_metadata and isinstance(filtered_metadata["year"], str):
            try:
                filtered_metadata["year"] = int(filtered_metadata["year"])
            except (ValueError, TypeError):
                filtered_metadata["year"] = None

        metadata = AudiobookMeta.from_dict(filtered_metadata)

        if not metadata:
            print("❌ Failed to create metadata")
            return

        print(f"✅ Extracted metadata for: {metadata.title}")
        print(f"🌐 Language field: '{metadata.language}'")  # Debug language

        # Map to RED format
        mapper = REDMapper()
        red_data = mapper.map_to_red_upload(metadata, include_description=True)

        print("\n🎨 Generated BBCode Description:")
        print("=" * 80)
        print(red_data.get("album_desc", "No description generated"))
        print("=" * 80)
        print(f"📏 Total length: {len(red_data.get('album_desc', ''))} characters")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
