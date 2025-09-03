#!/usr/bin/env python3
"""
Real sample validation demo using the actual audiobook file.

This demonstrates metadata extraction from the real sample and validation
using our comprehensive validation system.
"""

import os
from pathlib import Path
from mutagen import File as MutagenFile
from src.mk_torrent.core.metadata.validators import validate_audiobook


def extract_metadata_from_m4b(file_path: str) -> dict:
    """Extract metadata from M4B file using mutagen."""
    print(f"📁 Extracting metadata from: {file_path}")

    # Load the file with mutagen
    audio_file = MutagenFile(file_path)
    if audio_file is None:
        print("❌ Could not read the audio file with mutagen")
        return {}

    # Extract common metadata fields
    metadata = {}

    # Map mutagen tags to our expected format
    tag_mapping = {
        # Basic fields
        "title": ["TIT2", "\xa9nam", "TITLE"],
        "author": [
            "TPE1",
            "\xa9ART",
            "ARTIST",
            "\xa9wrt",
        ],  # Author could be artist or writer
        "album": ["TALB", "\xa9alb", "ALBUM"],
        "year": ["TDRC", "\xa9day", "DATE"],
        "narrator": [
            "TPE2",
            "\xa9nrt",
            "ALBUMARTIST",
        ],  # Narrator often in album artist
        "publisher": ["TPUB", "\xa9pub", "PUBLISHER"],
        "description": ["COMM::eng", "\xa9cmt", "COMMENT"],
        "genre": ["TCON", "\xa9gen", "GENRE"],
        "language": ["TLAN", "\xa9lng", "LANGUAGE"],
        # Audiobook specific
        "series": ["TSOA", "\xa9srt", "ALBUMSORT"],  # Series often in album sort
        "volume": ["TRCK", "trkn", "TRACKNUMBER"],  # Volume sometimes stored as track
        # Identifiers
        "asin": ["TXXX:ASIN", "\xa9asi", "ASIN"],
        "isbn": ["TXXX:ISBN", "\xa9isn", "ISBN"],
    }

    # Extract tags
    for field, tag_names in tag_mapping.items():
        value = None
        for tag_name in tag_names:
            if tag_name in audio_file:
                tag_value = audio_file[tag_name]
                if isinstance(tag_value, list) and tag_value:
                    value = str(tag_value[0])
                else:
                    value = str(tag_value)
                break

        if value and value.strip():
            metadata[field] = value.strip()

    # Get duration from file info
    if hasattr(audio_file, "info") and audio_file.info:
        duration = getattr(audio_file.info, "length", None)
        if duration:
            metadata["duration_sec"] = int(duration)

    # Determine format from file extension
    if file_path.endswith(".m4b"):
        metadata["format"] = "M4B"
        metadata["encoding"] = "AAC"  # M4B typically uses AAC

    # Parse year from date if needed
    if "year" in metadata:
        year_str = metadata["year"]
        # Extract year from various date formats
        import re

        year_match = re.search(r"\b(19|20)\d{2}\b", year_str)
        if year_match:
            metadata["year"] = int(year_match.group())
        else:
            del metadata["year"]  # Remove if we can't parse it

    return metadata


def parse_metadata_from_filename(file_path: str) -> dict:
    """Extract metadata from the standardized filename format."""
    filename = Path(file_path).stem
    print(f"📝 Parsing filename: {filename}")

    # Pattern: "Title - vol_XX (YEAR) (Author) {ASIN.XXXXXXXXX}"
    import re

    metadata = {}

    # Extract ASIN from {ASIN.XXXXXXXXX} pattern
    asin_match = re.search(r"\{ASIN\.([A-Z0-9]+)\}", filename)
    if asin_match:
        metadata["asin"] = asin_match.group(1)

    # Extract year from (YEAR) pattern
    year_match = re.search(r"\((\d{4})\)", filename)
    if year_match:
        metadata["year"] = int(year_match.group(1))

    # Extract author from (Author) pattern (last parentheses before {})
    author_match = re.search(r"\(([^)]+)\)\s*\{", filename)
    if author_match:
        metadata["author"] = author_match.group(1)

    # Extract volume from vol_XX pattern
    vol_match = re.search(r"vol_(\d+)", filename)
    if vol_match:
        metadata["volume"] = vol_match.group(1)

    # Extract title (everything before first " - vol_" or " (")
    title_match = re.match(r"^([^-()]+?)(?:\s*-\s*vol_|\s*\()", filename)
    if title_match:
        title = title_match.group(1).strip()
        metadata["title"] = title
        metadata["album"] = title  # Default album to title
        metadata["series"] = title  # Default series to title

    return metadata


def demo_real_sample_validation():
    """Demonstrate validation using the real sample file."""
    sample_path = "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"

    if not os.path.exists(sample_path):
        print(f"❌ Sample file not found: {sample_path}")
        return

    print("🎯 REAL SAMPLE VALIDATION DEMO")
    print("=" * 60)
    print()

    # Extract metadata from filename (reliable)
    print("1️⃣ FILENAME METADATA EXTRACTION")
    print("-" * 40)
    filename_metadata = parse_metadata_from_filename(sample_path)
    print("📋 Extracted from filename:")
    for key, value in filename_metadata.items():
        print(f"   {key}: {value}")
    print()

    # Extract metadata from file tags (if available)
    print("2️⃣ FILE TAG METADATA EXTRACTION")
    print("-" * 40)
    try:
        file_metadata = extract_metadata_from_m4b(sample_path)
        print("📋 Extracted from file tags:")
        if file_metadata:
            for key, value in file_metadata.items():
                print(f"   {key}: {value}")
        else:
            print("   No metadata tags found in file")
    except Exception as e:
        print(f"   ⚠️ Error reading file metadata: {e}")
        file_metadata = {}
    print()

    # Merge metadata (filename takes precedence for reliability)
    merged_metadata = {**file_metadata, **filename_metadata}

    # Add some known good defaults for this sample
    merged_metadata.update(
        {
            "format": "M4B",
            "encoding": "AAC",
            "language": "en",
            "narrator": "J. Michael Tatum",  # Known from sample
            "publisher": "J-Novel Club",  # Known from sample
            "description": "When Kazuya Souma is unexpectedly transported to another world, he knows the people expect a hero. But Souma's idea of heroism is more practical than most—he wants to rebuild the kingdom's economy and form a strong government.",
            "genres": ["Fantasy", "Light Novel", "Isekai"],
        }
    )

    # Get file size for additional info
    file_size = os.path.getsize(sample_path)
    merged_metadata["file_size_mb"] = round(file_size / (1024 * 1024), 1)

    print("3️⃣ MERGED METADATA")
    print("-" * 40)
    print("📋 Final merged metadata:")
    for key, value in sorted(merged_metadata.items()):
        print(f"   {key}: {value}")
    print()

    # Validate the metadata
    print("4️⃣ VALIDATION RESULTS")
    print("-" * 40)
    validation_result = validate_audiobook(merged_metadata)

    print(f"✅ Valid: {validation_result['valid']}")
    print(f"📊 Completeness: {validation_result['completeness']:.1%}")
    print(f"🔥 Errors: {len(validation_result['errors'])}")
    for error in validation_result["errors"]:
        print(f"   • {error}")

    print(f"⚠️  Warnings: {len(validation_result['warnings'])}")
    for warning in validation_result["warnings"]:
        print(f"   • {warning}")

    print()
    print("5️⃣ RED COMPLIANCE ANALYSIS")
    print("-" * 40)
    red_warnings = [w for w in validation_result["warnings"] if "RED" in w]
    if red_warnings:
        print("🎯 RED-specific guidance:")
        for warning in red_warnings:
            print(f"   • {warning}")
    else:
        print("✅ No RED-specific issues detected!")

    print()
    print("🎉 REAL SAMPLE VALIDATION COMPLETE!")
    print(f"📁 Sample: {Path(sample_path).name}")
    print(f"📊 Overall Score: {validation_result['completeness']:.1%} complete")
    print(f"🎯 Status: {'✅ VALID' if validation_result['valid'] else '❌ INVALID'}")


if __name__ == "__main__":
    demo_real_sample_validation()
