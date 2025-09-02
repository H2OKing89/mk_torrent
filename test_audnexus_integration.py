"""
Test script to verify Audnexus API integration matches the v1.8.0 specification.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mk_torrent.core.metadata.sources.audnexus import AudnexusSource


def test_asin_extraction():
    """Test ASIN extraction from various formats."""
    print("🔍 Testing ASIN extraction...")
    
    source = AudnexusSource()
    
    test_cases = [
        # Test cases with ASIN patterns
        ("{ASIN.B0C8ZW5N6Y}", "B0C8ZW5N6Y"),
        ("How a Realist Hero - vol_03 {ASIN.B0C8ZW5N6Y} [H2OKing].m4b", "B0C8ZW5N6Y"),
        ("/path/to/book {ASIN.B08G9PRS1K}.m4b", "B08G9PRS1K"),
        # Direct ASIN
        ("B0C8ZW5N6Y", "B0C8ZW5N6Y"),
        ("B08G9PRS1K", "B08G9PRS1K"),
        # Invalid cases
        ("no_asin_here.m4b", None),
        ("", None),
    ]
    
    for test_input, expected in test_cases:
        asin = source._extract_asin(test_input)
        if asin == expected:
            print(f"  ✅ '{test_input}' -> {asin}")
        else:
            print(f"  ❌ '{test_input}' -> {asin} (expected {expected})")


def test_asin_validation():
    """Test ASIN validation."""
    print("\n🔍 Testing ASIN validation...")
    
    source = AudnexusSource()
    
    test_cases = [
        ("B0C8ZW5N6Y", True),
        ("B08G9PRS1K", True),
        ("1234567890", True),
        ("ABCDEF1234", True),
        ("invalid", False),
        ("", False),
        ("B0C8ZW5N6Y123", False),  # too long
        ("B0C8ZW", False),  # too short
    ]
    
    for asin, expected in test_cases:
        result = source._is_valid_asin(asin)
        if result == expected:
            print(f"  ✅ '{asin}' -> {result}")
        else:
            print(f"  ❌ '{asin}' -> {result} (expected {expected})")


def test_real_api_call():
    """Test actual API call with a known ASIN."""
    print("\n🌐 Testing real API call...")
    
    source = AudnexusSource()
    
    # Use the ASIN from our sample file
    test_asin = "B0C8ZW5N6Y"
    
    try:
        print(f"  📡 Fetching metadata for ASIN: {test_asin}")
        
        # Test direct book fetch
        book_data = source._get_book(test_asin, region="us", update=1)
        
        if book_data:
            print(f"  ✅ Successfully fetched book data")
            print(f"     Title: {book_data.get('title', 'N/A')}")
            print(f"     Authors: {[a.get('name') for a in book_data.get('authors', [])]}")
            print(f"     Runtime: {book_data.get('runtimeLengthMin', 'N/A')} minutes")
            print(f"     Publisher: {book_data.get('publisherName', 'N/A')}")
            
            # Test normalization
            print(f"  🔄 Testing data normalization...")
            normalized = source._normalize_book_data(book_data)
            print(f"     Normalized title: {normalized.get('title', 'N/A')}")
            print(f"     Normalized author: {normalized.get('author', 'N/A')}")
            print(f"     Series: {normalized.get('series', 'N/A')}")
            print(f"     Volume: {normalized.get('volume', 'N/A')}")
            print(f"     Year: {normalized.get('year', 'N/A')}")
            
        else:
            print(f"  ❌ No data returned for ASIN: {test_asin}")
            
    except Exception as e:
        print(f"  ❌ API call failed: {e}")


def test_extract_method():
    """Test the main extract method."""
    print("\n🎯 Testing extract method...")
    
    source = AudnexusSource()
    
    # Test with ASIN pattern (matching our sample file)
    test_path = "How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing].m4b"
    
    try:
        print(f"  📂 Extracting from: {test_path}")
        metadata = source.extract(test_path)
        
        print(f"  ✅ Successfully extracted metadata:")
        print(f"     Title: {metadata.get('title', 'N/A')}")
        print(f"     Author: {metadata.get('author', 'N/A')}")
        print(f"     Series: {metadata.get('series', 'N/A')}")
        print(f"     Volume: {metadata.get('volume', 'N/A')}")
        print(f"     Publisher: {metadata.get('publisher', 'N/A')}")
        print(f"     Year: {metadata.get('year', 'N/A')}")
        print(f"     Duration: {metadata.get('duration', 'N/A')}")
        print(f"     Source: {metadata.get('source', 'N/A')}")
        print(f"     Source ASIN: {metadata.get('source_asin', 'N/A')}")
        
    except Exception as e:
        print(f"  ❌ Extract failed: {e}")


def test_chapters():
    """Test chapter fetching."""
    print("\n📖 Testing chapter fetching...")
    
    source = AudnexusSource()
    test_asin = "B0C8ZW5N6Y"
    
    try:
        print(f"  📚 Fetching chapters for ASIN: {test_asin}")
        chapters = source.get_chapters(test_asin, region="us", update=1)
        
        if chapters:
            print(f"  ✅ Successfully fetched chapters:")
            print(f"     ASIN: {chapters.get('asin', 'N/A')}")
            print(f"     Runtime: {chapters.get('runtimeLengthMs', 0) / 1000 / 60:.1f} minutes")
            print(f"     Chapter count: {len(chapters.get('chapters', []))}")
            
            # Show first few chapters
            chapter_list = chapters.get('chapters', [])
            for i, chapter in enumerate(chapter_list[:3]):
                title = chapter.get('title', 'N/A')
                start_sec = chapter.get('startOffsetSec', 0)
                print(f"     Chapter {i+1}: {title} (starts at {start_sec}s)")
                
            if len(chapter_list) > 3:
                print(f"     ... and {len(chapter_list) - 3} more chapters")
        else:
            print(f"  ❌ No chapters returned for ASIN: {test_asin}")
            
    except Exception as e:
        print(f"  ❌ Chapter fetch failed: {e}")


def main():
    """Run all tests."""
    print("🧪 Audnexus API Integration Tests")
    print("=" * 50)
    
    try:
        test_asin_extraction()
        test_asin_validation()
        test_real_api_call()
        test_extract_method()
        test_chapters()
        
        print("\n🎉 All tests completed!")
        print("\nNote: Some tests may fail if:")
        print("- No internet connection")
        print("- Audnexus API is down")
        print("- httpx/requests not installed")
        print("- ASIN not found in Audnexus database")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")


if __name__ == "__main__":
    main()
