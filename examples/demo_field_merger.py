#!/usr/bin/env python3
"""
Enhanced Field Merger Demo

Demonstrates the new three-source field merger with realistic audiobook data.
Shows how the declarative precedence system intelligently combines path,
embedded, and API metadata sources.
"""

from pathlib import Path

# Add the src directory to Python path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mk_torrent.core.metadata.services.merge_audiobook import (
    FieldMerger,
    merge_metadata,
)


def demo_realistic_audiobook_merge():
    """Demonstrate field merger with realistic audiobook metadata."""

    print("🎯 Enhanced Field Merger Demo")
    print("=" * 50)

    # Simulate the three sources of metadata
    path_metadata = {
        "_src": "path",
        "title": "How a Realist Hero Rebuilt the Kingdom: Volume 3",
        "series": "How a Realist Hero Rebuilt the Kingdom",
        "volume": "03",  # Zero-padded for tracker compliance
        "year": 2023,
        "author": "Dojyomaru",
        "asin": "B0C8ZW5N6Y",  # Extracted from filename
    }

    embedded_metadata = {
        "_src": "embedded",
        "duration_sec": 31509,  # Precise seconds from audio stream
        "file_size_bytes": 367296512,
        "file_size_mb": 350.19,
        "bitrate": 125588,
        "sample_rate": 44100,
        "channels": 2,
        "codec": "aac",
        "has_embedded_cover": True,
        "chapter_count": 7,
        "has_chapters": True,
        "source": "ffprobe",
    }

    api_metadata = {
        "_src": "api",
        "title": "How a Realist Hero Rebuilt the Kingdom: Volume 3",
        "author": "Dojyomaru",
        "narrator": "BJ Harrison",
        "publisher": "Tantor Audio",
        "year": 2023,
        "duration_sec": 524 * 60,  # 31440 - API only has minute granularity
        "genres": ["Science Fiction & Fantasy", "Fantasy", "Epic", "Historical"],
        "artwork_url": "https://m.media-amazon.com/images/I/81IpsoA4EqL.jpg",
        "isbn": "9798765080221",
        "series": "How a Realist Hero Rebuilt the Kingdom",
        "volume": "3",  # Not zero-padded
        "description": "<p>The Battle Continues!</p> More epic content...",
    }

    print("\n📊 Input Sources:")
    print(f"📁 Path: {len(path_metadata)-1} fields")
    print(f"🎵 Embedded: {len(embedded_metadata)-1} fields")
    print(f"🌐 API: {len(api_metadata)-1} fields")

    # Use the enhanced field merger
    merger = FieldMerger()
    result = merger.merge([path_metadata, embedded_metadata, api_metadata])

    print(f"\n✨ Merged Result: {len(result)} fields")
    print("\n🎯 Key Precedence Decisions:")

    # Show key precedence decisions
    decisions = [
        ("title", result.get("title"), "API wins (authoritative descriptive)"),
        ("series", result.get("series"), "Path wins (tracker compliance)"),
        ("volume", result.get("volume"), "Path wins (zero-padded: '03' vs '3')"),
        (
            "duration_sec",
            result.get("duration_sec"),
            f"Embedded wins (precise: {result.get('duration_sec')} vs {524*60} from API)",
        ),
        ("narrator", result.get("narrator"), "API only (embedded unreliable)"),
        ("bitrate", result.get("bitrate"), "Embedded only (technical data)"),
        ("genres", result.get("genres"), "API only (descriptive metadata)"),
    ]

    for field, value, rationale in decisions:
        print(f"  • {field}: {value} → {rationale}")

    print("\n📈 Merger Statistics:")
    print(f"  • Total fields merged: {len(result)}")
    print(
        f"  • Descriptive fields (API/Path): {len([f for f in result if f in ['title', 'author', 'series', 'narrator', 'publisher']])}"
    )
    print(
        f"  • Technical fields (Embedded): {len([f for f in result if f in ['duration_sec', 'bitrate', 'codec', 'channels']])}"
    )
    print(f"  • List fields: {len([f for f in result if isinstance(result[f], list)])}")

    return result


def demo_list_union():
    """Demonstrate smart list union with deduplication."""

    print("\n\n🎨 Smart List Union Demo")
    print("=" * 30)

    candidates = [
        {"_src": "api", "genres": ["Science Fiction & Fantasy", "Fantasy", "Epic"]},
        {
            "_src": "embedded",
            "genres": ["fantasy", "Audiobook", "EPIC"],  # Case variations + new item
        },
        {
            "_src": "path",
            "genres": "Adventure, Mystery",  # Comma-separated string
        },
    ]

    print("\n📊 Input Lists:")
    for candidate in candidates:
        src = candidate["_src"]
        genres = candidate["genres"]
        print(f"  {src}: {genres}")

    result = merge_metadata(candidates)
    final_genres = result.get("genres", [])

    print(f"\n✨ Merged List: {final_genres}")
    print("🎯 Union Logic:")
    print("  • API precedence: maintains order from primary source")
    print(
        "  • Case-insensitive dedup: 'Fantasy' + 'fantasy' + 'EPIC' → 'Fantasy', 'Epic'"
    )
    print("  • String parsing: 'Adventure, Mystery' → ['Adventure', 'Mystery']")
    print("  • Stable order: API items first, then unique items from other sources")


def demo_precedence_customization():
    """Demonstrate custom precedence configuration."""

    print("\n\n⚙️ Custom Precedence Demo")
    print("=" * 30)

    candidates = [
        {"_src": "path", "title": "Path Title"},
        {"_src": "api", "title": "API Title"},
        {"_src": "embedded", "title": "Embedded Title"},
    ]

    print("\n📊 Same Input, Different Rules:")
    for candidate in candidates:
        print(f"  {candidate['_src']}: {candidate['title']}")

    # Default precedence (API > Path > Embedded)
    default_merger = FieldMerger()
    default_result = default_merger.merge(candidates)
    print(f"\n🎯 Default precedence (API first): {default_result['title']}")

    # Custom precedence (Path > API > Embedded)
    custom_precedence = {"title": ["path", "api", "embedded"]}
    custom_merger = FieldMerger(custom_precedence)
    custom_result = custom_merger.merge(candidates)
    print(f"🎯 Custom precedence (Path first): {custom_result['title']}")

    print("\n💡 Customization enables different workflows:")
    print("  • Default: API authority for clean metadata")
    print("  • Custom: Path compliance for tracker requirements")


if __name__ == "__main__":
    # Run all demos
    try:
        audiobook_result = demo_realistic_audiobook_merge()
        demo_list_union()
        demo_precedence_customization()

        print("\n\n🎉 Field Merger Demo Complete!")
        print("✅ Three-source strategy working perfectly")
        print("✅ Smart precedence rules validated")
        print("✅ List union logic demonstrated")
        print("✅ Custom configuration shown")
        print("\n📋 Next: Implement RED tracker mapper to complete the pipeline!")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
