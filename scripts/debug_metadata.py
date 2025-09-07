#!/usr/bin/env python3
"""
Quick script to check what metadata is actually extracted from the sample audiobook.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mk_torrent.core.metadata.engine import MetadataEngine

# Sample audiobook path
SAMPLE_AUDIOBOOK = Path(
    "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/"
    "How a Realist Hero Rebuilt the Kingdom - vol_09 (2023) (Dojyomaru) "
    "{ASIN.B0CPML76KX} [H2OKing]/How a Realist Hero Rebuilt the Kingdom - "
    "vol_09 {ASIN.B0CPML76KX}.m4b"
)


def main():
    # Initialize metadata engine
    engine = MetadataEngine()
    engine.setup_default_processors()

    # Extract metadata
    metadata = engine.extract_metadata(SAMPLE_AUDIOBOOK, content_type="audiobook")

    print("Extracted metadata keys:")
    for key in sorted(metadata.keys()):
        value = metadata[key]
        if isinstance(value, list) and len(value) > 3:
            print(f"  {key}: {type(value).__name__}[{len(value)}] = {value[:2]}...")
        elif isinstance(value, str) and len(value) > 100:
            print(f"  {key}: '{value[:50]}...'")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
