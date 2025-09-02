#!/usr/bin/env python3
"""
Demonstration of the new metadata core system.

This example shows how to use the refactored metadata core architecture
with real audiobook files. It demonstrates:

1. Creating a MetadataEngine with dependency injection
2. Registering processors and mappers
3. Processing real audiobook files
4. Full pipeline processing with validation
5. Working with AudiobookMeta objects
"""

import sys
from pathlib import Path

# Add the src directory to Python path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mk_torrent.core.metadata import MetadataEngine, AudiobookMeta


class SimpleAudiobookProcessor:
    """A simple processor that extracts metadata from audiobook filenames."""
    
    def extract(self, source):
        """Extract metadata from audiobook filename."""
        if isinstance(source, str):
            source = Path(source)
        
        stem = source.stem
        
        # Parse complex audiobook filename format
        # Format: "Series Title - vol_XX (YEAR) (Author) {ASIN.XXXXX} [Uploader]"
        if " - vol_" in stem and "(" in stem:
            parts = stem.split(" - vol_")
            series_title = parts[0].strip()
            vol_part = parts[1]
            
            # Extract volume number
            vol_match = vol_part.split(" ")[0]
            
            # Extract year
            year = None
            if "(" in vol_part and ")" in vol_part:
                year_part = vol_part.split("(")[1].split(")")[0]
                if year_part.isdigit() and len(year_part) == 4:
                    year = int(year_part)
            
            # Extract author
            author = "Unknown"
            if ") (" in vol_part:
                author_part = vol_part.split(") (")[1].split(")")[0]
                author = author_part.strip()
            
            # Extract ASIN
            asin = None
            if "{ASIN." in vol_part and "}" in vol_part:
                asin_part = vol_part.split("{ASIN.")[1].split("}")[0]
                asin = asin_part.strip()
            
            return {
                "title": f"{series_title} - vol_{vol_match}",
                "author": author,
                "series": series_title,
                "volume": vol_match,
                "year": year,
                "asin": asin,
                "source_path": source,
            }
        
        # Fallback to simple parsing
        elif " - " in stem:
            parts = stem.split(" - ", 1)
            return {
                "title": parts[1].strip(),
                "author": parts[0].strip(),
                "source_path": source,
            }
        else:
            return {
                "title": stem,
                "author": "Unknown",
                "source_path": source,
            }
    
    def validate(self, metadata):
        """Simple validation."""
        from mk_torrent.core.metadata.base import ValidationResult
        
        result = ValidationResult(valid=True)
        
        if not metadata.get("title"):
            result.add_error("Title is required")
        if not metadata.get("author"):
            result.add_error("Author is required")
        
        # Calculate completeness
        required_fields = ["title", "author"]
        optional_fields = ["year", "narrator", "series", "volume", "asin"]
        
        filled_required = sum(1 for field in required_fields if metadata.get(field))
        filled_optional = sum(1 for field in optional_fields if metadata.get(field))
        
        total_possible = len(required_fields) + len(optional_fields)
        total_filled = filled_required + filled_optional
        
        result.completeness = total_filled / total_possible
        
        return result
    
    def enhance(self, metadata):
        """Add derived fields."""
        enhanced = dict(metadata)
        
        title = metadata.get("title", "")
        author = metadata.get("author", "")
        
        if title and author:
            enhanced["display_name"] = f"{title} by {author}"
        elif title:
            enhanced["display_name"] = title
        else:
            enhanced["display_name"] = "Unknown"
        
        # Add album field
        if not enhanced.get("album") and title:
            enhanced["album"] = title
        
        return enhanced


class SimpleTrackerMapper:
    """A simple mapper for demonstration."""
    
    def map_to_tracker(self, audiobook_meta):
        """Map AudiobookMeta to a simple tracker format."""
        return {
            "upload_title": audiobook_meta.title or "",
            "upload_artist": audiobook_meta.author or "",
            "upload_year": audiobook_meta.year or "",
            "upload_series": audiobook_meta.series or "",
            "upload_volume": audiobook_meta.volume or "",
            "upload_asin": audiobook_meta.asin or "",
        }


def main():
    """Demonstrate the metadata core system."""
    print("🎧 Metadata Core System Demo")
    print("=" * 50)
    
    # 1. Create the engine
    print("\n1. Creating MetadataEngine...")
    engine = MetadataEngine()
    
    # 2. Register components
    print("2. Registering processor and mapper...")
    processor = SimpleAudiobookProcessor()
    mapper = SimpleTrackerMapper()
    
    engine.register_processor("audiobook", processor)
    engine.register_mapper("demo_tracker", mapper)
    engine.set_default_processor("audiobook")
    
    # 3. Find sample file
    samples_dir = Path(__file__).parent.parent / "tests" / "samples"
    sample_file = samples_dir / "audiobook" / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]" / "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
    
    if not sample_file.exists():
        print("\n❌ Sample file not found. Using demo filename instead.")
        sample_file = "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y}.m4b"
    else:
        print(f"\n✅ Found sample file: {sample_file.name}")
    
    # 4. Extract metadata
    print("\n3. Extracting metadata...")
    metadata_dict = engine.extract_metadata(str(sample_file))
    
    print("   Raw metadata:")
    for key, value in metadata_dict.items():
        print(f"     {key}: {value}")
    
    # 5. Convert to AudiobookMeta object
    print("\n4. Converting to AudiobookMeta object...")
    audiobook_meta = AudiobookMeta.from_dict(metadata_dict)
    
    print(f"   Title: {audiobook_meta.title}")
    print(f"   Author: {audiobook_meta.author}")
    print(f"   Series: {audiobook_meta.series}")
    print(f"   Year: {audiobook_meta.year}")
    print(f"   ASIN: {audiobook_meta.asin}")
    
    # 6. Validate
    print("\n5. Validating metadata...")
    validation = engine.validate_metadata(metadata_dict)
    
    print(f"   Valid: {validation.valid}")
    print(f"   Completeness: {validation.completeness:.1%}")
    if validation.errors:
        print(f"   Errors: {validation.errors}")
    if validation.warnings:
        print(f"   Warnings: {validation.warnings}")
    
    # 7. Map to tracker
    print("\n6. Mapping to tracker format...")
    tracker_data = engine.map_to_tracker(audiobook_meta, "demo_tracker")
    
    print("   Tracker data:")
    for key, value in tracker_data.items():
        print(f"     {key}: {value}")
    
    # 8. Full pipeline
    print("\n7. Running full pipeline...")
    result = engine.process_full_pipeline(
        str(sample_file),
        tracker_name="demo_tracker",
        validate=True
    )
    
    print(f"   Success: {result['success']}")
    print(f"   Content Type: {result['content_type']}")
    print(f"   Validation Valid: {result['validation']['valid']}")
    print(f"   Validation Completeness: {result['validation']['completeness']:.1%}")
    
    # 9. Demonstrate backward compatibility
    print("\n8. Backward compatibility...")
    try:
        # This import should work seamlessly
        from mk_torrent.features import MetadataEngine as LegacyEngine
        print("   ✅ Legacy import works (compatibility shim)")
    except ImportError as e:
        print(f"   ❌ Legacy import failed: {e}")
    
    print("\n🎉 Demo completed successfully!")
    print("\nThe new metadata core system provides:")
    print("• Clean separation of concerns with protocols")
    print("• Dependency injection for easy testing")
    print("• Modular architecture for different content types")
    print("• Strong typing with AudiobookMeta dataclass")
    print("• Comprehensive validation system")
    print("• Tracker-specific mapping capabilities")
    print("• Backward compatibility with existing code")


if __name__ == "__main__":
    main()
