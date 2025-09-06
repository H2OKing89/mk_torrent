#!/usr/bin/env python3
"""Test script to show full BBCode output for debugging template fixes."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mk_torrent.core.metadata import AudiobookMeta
from mk_torrent.core.metadata.mappers.red import REDMapper
from mk_torrent.core.metadata.engine import MetadataEngine
from mk_torrent.core.audio import analyze_audio_file
from mk_torrent.core.file_analysis import analyze_file


def main():
    # Test file path
    file_path = Path(
        "tests/samples/audiobook/The World of Otome Games Is Tough for Mobs - vol_05 (2025) (Yomu Mishima) {ASIN.B0FPXQH971} [H2OKing]/The World of Otome Games Is Tough for Mobs - vol_05 (2025) (Yomu Mishima) {ASIN.B0FPXQH971}.m4b"
    )

    if not file_path.exists():
        print(f"❌ Test file not found: {file_path}")
        return

    print(f"📖 Testing BBCode generation for: {file_path.name}")
    print("=" * 80)

    # Extract metadata using the working approach from test_red_upload_clean.py
    try:
        print("🔍 Analyzing file...")
        analyze_file(file_path)

        print("🎵 Analyzing audio...")
        analyze_audio_file(file_path)

        print("📊 Extracting metadata...")
        # Create metadata engine
        MetadataEngine()

        # Extract using the manual approach for now
        from mk_torrent.core.file_analysis.extractors.filename import FilenameExtractor
        from mk_torrent.core.metadata.sources.audnexus import AudnexusMetadataSource
        from mk_torrent.core.audio.analyzers.mutagen_analyzer import MutagenAnalyzer

        # Get basic info from filename
        filename_extractor = FilenameExtractor()
        path_data = filename_extractor.extract_metadata(file_path)

        # Get ASIN from path data
        asin = path_data.get("asin")
        if not asin:
            print("❌ No ASIN found in filename")
            return

        print(f"� Found ASIN: {asin}")

        # Get API data
        audnexus = AudnexusMetadataSource()
        api_data = audnexus.fetch_metadata(asin)

        # Get embedded data
        mutagen_analyzer = MutagenAnalyzer()
        embedded_data = mutagen_analyzer.extract_metadata(file_path)

        # Create merged metadata
        merged_data = {**api_data, **embedded_data, **path_data}

        # Create AudiobookMeta
        metadata = AudiobookMeta.from_dict(merged_data)

        if not metadata:
            print("❌ Failed to create metadata")
            return

        print(f"✅ Extracted metadata for: {metadata.title}")

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
