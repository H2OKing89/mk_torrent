#!/usr/bin/env python3
"""
Test the template system and RED mapper integration.

This demonstrates the BBCode template generation for RED tracker uploads.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mk_torrent.core.metadata.base import AudiobookMeta
from mk_torrent.core.metadata.mappers.red import REDMapper


def test_red_template_integration():
    """Test RED mapper with template system."""
    print("🔥 Testing RED Template Integration")
    print("=" * 50)

    # Create sample audiobook metadata
    metadata = AudiobookMeta(
        title="The Martian",
        subtitle="A Novel",
        author="Andy Weir",
        album="The Martian",
        series="",
        volume="",
        year=2014,
        narrator="R.C. Bray",
        duration_sec=10 * 3600 + 53 * 60,  # 10h 53m
        format="AAC",
        encoding="64 kbps VBR",
        asin="B00B5HZGUG",
        isbn="9780553418026",
        publisher="Crown",
        description="Six days ago, astronaut Mark Watney became one of the first people to walk on Mars. Now, he's sure he'll be the first person to die there. After a dust storm nearly kills him and forces his crew to evacuate while thinking him dead, Mark finds himself stranded and completely alone with no way to even signal Earth that he's alive—and even if he could get word out, his supplies would be gone long before a rescue mission could arrive. Chances are, though, he won't have time to starve to death. The damaged machinery, unforgiving environment, or plain-old human error are much more likely to kill him first. But Mark isn't ready to give up yet. Drawing on his ingenuity, his engineering skills—and a relentless, dogged refusal to quit—he steadfastly confronts one seemingly insurmountable obstacle after the next. Will his resourcefulness be enough to overcome the impossible odds against him?",
        language="en",
        genres=["Science Fiction", "Adventure", "Survival"],
        tags=["space", "mars", "survival", "engineering"],
        artwork_url="https://example.com/martian-cover.jpg",
    )

    print(f"📖 Sample Audiobook: {metadata.title}")
    print(f"👤 Author: {metadata.author}")
    print(f"🎧 Narrator: {metadata.narrator}")
    print(
        f"⏱️ Duration: {metadata.duration_sec // 3600}h {(metadata.duration_sec % 3600) // 60}m"
    )
    print()

    # Create RED mapper
    mapper = REDMapper()

    print("🔄 Mapping to RED format...")

    # Generate RED upload data
    red_data = mapper.map_to_red_upload(metadata, include_description=True)

    print("✅ RED Upload Data Generated!")
    print()

    # Display key fields
    print("📋 RED Upload Fields:")
    print("-" * 30)
    for key, value in red_data.items():
        if key == "album_desc":
            print(f"{key}: [BBCode Description - {len(value)} chars]")
        elif isinstance(value, list):
            print(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            print(f"{key}: {value}")

    print()
    print("📝 Generated BBCode Description:")
    print("=" * 50)
    if "album_desc" in red_data:
        print(red_data["album_desc"])
    else:
        print("No description generated")

    print()
    print("🏷️ Tags for RED:")
    print(f"   {red_data.get('tags', 'No tags')}")

    # Assert that we got a valid result
    assert red_data is not None
    assert isinstance(red_data, dict)
    assert len(red_data) > 0


def test_template_rendering_only():
    """Test just the template rendering system."""
    print("\n" + "🎨 Testing Template Rendering System")
    print("=" * 50)

    try:
        from mk_torrent.core.metadata.templates import TemplateRenderer

        renderer = TemplateRenderer()
        print("✅ Template renderer created successfully")

        # Test custom filters
        test_data = {
            "release": {
                "filesize_bytes": 1024 * 1024 * 350,  # 350 MB
                "duration_ms": 10 * 3600 * 1000 + 53 * 60 * 1000,  # 10h 53m
                "chapters_present": True,
            }
        }

        # Test filters directly
        print(
            f"📊 File size: {renderer._format_bytes(test_data['release']['filesize_bytes'])}"
        )
        print(
            f"⏱️ Duration: {renderer._format_duration(test_data['release']['duration_ms'])}"
        )
        print(
            f"📑 Chapters: {renderer._yesno_filter(test_data['release']['chapters_present'])}"
        )

        # List available templates
        templates = renderer.list_templates()
        print(f"📁 Available templates: {templates}")

        assert renderer is not None  # Template renderer working

    except ImportError as e:
        print(f"❌ Template system not available: {e}")
        assert False, f"Template system not available: {e}"


if __name__ == "__main__":
    print("🚀 RED Template System Integration Test")
    print("=" * 60)

    # Test template rendering
    template_success = test_template_rendering_only()

    if template_success:
        # Test full integration
        red_data = test_red_template_integration()
        print("\n🎉 All tests completed successfully!")
        print(f"Generated {len(red_data)} RED upload fields")
    else:
        print("\n⚠️ Template system not fully available, testing basic functionality...")
        # Still test the mapper without templates
        test_red_template_integration()
