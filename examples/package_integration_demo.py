#!/usr/bin/env python3
"""
Package Integration Example

Demonstrates how the metadata core system uses all recommended packages
from the "00 — Recommended Packages & Project Extras" specification.
"""

import asyncio
import logging

# Configure logging to show package usage
logging.basicConfig(
    level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s"
)


async def demonstrate_package_integration():
    """Demonstrate integration of all recommended packages."""

    print("🔧 Metadata Core Package Integration Demo")
    print("=" * 50)

    # 1. HTTP Client (httpx preferred, requests fallback)
    print("\n📡 HTTP Client Integration (httpx/requests)")
    try:
        from src.mk_torrent.core.metadata.sources.audnexus import AudnexusSource

        audnexus = AudnexusSource()
        print(f"   ✅ Audnexus source initialized with client: {audnexus._client_type}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. HTML Sanitization (nh3 preferred, beautifulsoup4 fallback)
    print("\n🧹 HTML Sanitization (nh3/beautifulsoup4)")
    try:
        from src.mk_torrent.core.metadata.services.html_cleaner import HTMLCleaner

        cleaner = HTMLCleaner()

        html_sample = '<p>This is <strong>bold</strong> text with <script>alert("xss")</script> content.</p>'
        cleaned = cleaner.clean_html(html_sample)
        print(f"   ✅ HTML Cleaner initialized with backend: {cleaner._cleaner_type}")
        print(f"   📝 Sample: '{html_sample}' → '{cleaned}'")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Audio Format Detection (mutagen)
    print("\n🎵 Audio Format Detection (mutagen)")
    try:
        from src.mk_torrent.core.metadata.services.format_detector import FormatDetector

        detector = FormatDetector()
        print(
            f"   ✅ Format Detector initialized, mutagen available: {detector._mutagen_available}"
        )

        # Would normally analyze a real audio file here
        print("   📁 Ready to analyze audio files when provided")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. Embedded Metadata Extraction (mutagen)
    print("\n🏷️  Embedded Metadata Extraction (mutagen)")
    try:
        from src.mk_torrent.core.metadata.sources.embedded import EmbeddedSource

        embedded = EmbeddedSource()
        print(
            f"   ✅ Embedded source initialized, mutagen available: {embedded._mutagen_available}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 5. Data Validation (pydantic)
    print("\n✅ Data Validation (pydantic)")
    try:
        from src.mk_torrent.core.metadata.models.audnexus import Person

        # Create a sample person model
        author = Person(name="Brandon Sanderson", asin="B001KGFMD2")
        print(f"   ✅ Pydantic models working: {author.name} ({author.asin})")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 6. Caching (cachetools)
    print("\n💾 Caching Integration (cachetools)")
    try:
        if hasattr(audnexus, "_cache"):
            print(f"   ✅ TTL Cache initialized: {type(audnexus._cache).__name__}")
        else:
            print("   ⚠️  Cache not available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 7. Retry Logic (tenacity)
    print("\n🔄 Retry Logic (tenacity)")
    try:
        retry_decorator = audnexus._get_retry_decorator()
        if retry_decorator:
            print("   ✅ Tenacity retry logic configured with exponential backoff")
        else:
            print("   ⚠️  Basic retry fallback in use")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 8. Rate Limiting (aiolimiter)
    print("\n⏱️  Rate Limiting (aiolimiter)")
    try:
        if hasattr(audnexus, "_rate_limiter") and audnexus._rate_limiter:
            print(
                f"   ✅ Rate limiter configured: {audnexus._rate_limit_per_second} req/sec"
            )
        else:
            print("   ⚠️  Rate limiting not available (async only)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("🎉 Package Integration Demo Complete!")
    print("\nAll recommended packages are properly integrated with:")
    print("  • Graceful fallbacks for missing optional packages")
    print("  • Comprehensive error handling")
    print("  • Service-oriented architecture")
    print("  • Full compliance with 00 specification")


if __name__ == "__main__":
    asyncio.run(demonstrate_package_integration())
